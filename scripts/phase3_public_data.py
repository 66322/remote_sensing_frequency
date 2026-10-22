"""On-demand 3DCD/P³ adapters; bounded in-memory cache, no persistent crop cache."""
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np


def _raster(path):
    import rasterio
    with rasterio.open(path) as source:
        return source.read(), source.transform, source.crs, source.nodata


def _resize(array, shape, nearest=False):
    from scipy.ndimage import zoom
    h, w = shape
    factors = (h / array.shape[0], w / array.shape[1])
    if array.ndim == 3:
        factors += (1,)
    result = zoom(array, factors,
                  order=0 if nearest else 1, prefilter=False)
    return result[:h, :w]


def _rgb(array):
    if array.ndim != 3 or array.shape[0] < 3:
        raise ValueError("RGB raster requires at least three bands")
    raw = array[:3].astype(np.float32).transpose(1, 2, 0)
    if not np.isfinite(raw).all():
        raise ValueError("nonfinite RGB")
    scale = (1.0 if np.issubdtype(array.dtype, np.floating) and raw.max() <= 1
             else 65535.0 if raw.max() > 255 else 255.0)
    return np.clip(raw / scale, 0, 1)


def load_3dcd(row, metadata):
    rgb1, _, _, _ = _raster(row["rgb_t1"])
    rgb2, _, _, _ = _raster(row["rgb_t2"])
    d1, _, _, nodata1 = _raster(row["dsm_t1"])
    d2, _, _, nodata2 = _raster(row["dsm_t2"])
    c2, _, _, _ = _raster(row["change2d"])
    c3, _, _, _ = _raster(row["change3d"])
    if any(a.shape[0] != 1 for a in (d1, d2, c2, c3)):
        raise ValueError("3DCD DSM and labels must each be one band")
    height = d1.shape[1:]
    if d2.shape[1:] != height:
        raise ValueError("3DCD DSM time grids differ; explicit registration required")
    r1 = _resize(_rgb(rgb1), height)
    r2 = _resize(_rgb(rgb2), height)
    a = d1[0].astype(np.float32)
    b = d2[0].astype(np.float32)
    valid = np.isfinite(a) & np.isfinite(b)
    if nodata1 is not None:
        valid &= a != nodata1
    if nodata2 is not None:
        valid &= b != nodata2
    measurement_valid = valid.copy()
    scale = float(metadata["dsm_units_to_meters"])
    if not 0 < scale <= 100:
        raise ValueError("DSM unit contract")
    a = np.where(valid, a * scale, 0)
    b = np.where(valid, b * scale, 0)
    label = _resize(c2[0], height, nearest=True)
    positive = metadata["change2d_positive_values"]
    negative = metadata["change2d_negative_values"]
    if not positive or not negative:
        raise ValueError("explicit 2D label coding required")
    known = np.isin(label, positive + negative)
    changed = np.isin(label, positive)
    delta_raw = _resize(c3[0], height, nearest=True).astype(np.float32)
    delta_valid = np.isfinite(delta_raw) & ~np.isin(delta_raw, metadata["change3d_ignore_values"])
    delta = delta_raw * float(metadata["change3d_scale_m"]) + float(metadata["change3d_offset_m"])
    valid &= known & delta_valid
    return dict(rgb1=r1, rgb2=r2, dsm1=a, dsm2=b,
                changed=changed.astype(np.float32), delta=delta,
                valid=valid.astype(bool), measurement_valid=measurement_valid,
                id=row["id"], group=row["group"])


def _lidar_height(path, shape, transform, crs):
    import laspy
    height = np.full(shape, -np.inf, np.float32)
    count = np.zeros(shape, np.uint32)
    with laspy.open(path) as source:
        point_crs = source.header.parse_crs()
        from pyproj import CRS
        if point_crs is None or crs is None or CRS.from_user_input(point_crs) != CRS.from_user_input(crs):
            raise ValueError("LiDAR/image CRS mismatch or absent; prepare an explicit aligned derivative")
        inverse = ~transform
        for points in source.chunk_iterator(200_000):
            col, row = inverse * (np.asarray(points.x), np.asarray(points.y))
            col = np.floor(col).astype(np.int64)
            row = np.floor(row).astype(np.int64)
            keep = (row >= 0) & (row < shape[0]) & (col >= 0) & (col < shape[1])
            flat = row[keep] * shape[1] + col[keep]
            np.maximum.at(height.ravel(), flat, np.asarray(points.z)[keep].astype(np.float32))
            np.add.at(count.ravel(), flat, 1)
    if not count.any():
        raise ValueError("LiDAR has no points within RGB footprint")
    valid = count > 0
    # Local tile reference removes the arbitrary global elevation datum.
    height[valid] -= np.median(height[valid])
    height[~valid] = 0
    return height, valid


_ANNOTATIONS = {}


def _instances(row, shape):
    from PIL import Image, ImageDraw
    path = row["instance"]
    if path not in _ANNOTATIONS:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if "annotations" not in data or "images" not in data:
            raise ValueError("P³ MS COCO JSON required")
        by_image = {}
        for annotation in data["annotations"]:
            by_image.setdefault(annotation["image_id"], []).append(annotation)
        _ANNOTATIONS[path] = (by_image, {x["id"] for x in data["images"]})
    by_image, image_ids = _ANNOTATIONS[path]
    image_id = row["image_id"]
    if image_id not in image_ids:
        raise ValueError("P³ image_id absent from annotations")
    canvas = Image.new("I", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(canvas)
    for index, annotation in enumerate(by_image.get(image_id, []), 1):
        polygons = annotation.get("segmentation")
        if not isinstance(polygons, list):
            raise ValueError("COCO RLE requires a separately frozen raster derivative")
        for coordinates in polygons:
            if len(coordinates) < 6 or len(coordinates) % 2:
                raise ValueError("malformed P³ polygon")
            draw.polygon(list(zip(coordinates[::2], coordinates[1::2])), fill=index)
    return np.asarray(canvas).astype(np.int32)


def load_p3(row, metadata):
    image, transform, crs, _ = _raster(row["rgb"])
    rgb = _rgb(image)
    height, height_valid = _lidar_height(row["lidar"], rgb.shape[:2], transform, crs)
    instance = _instances(row, rgb.shape[:2])
    if instance.max() == 0 and not metadata.get("allow_empty_tiles", False):
        raise ValueError("empty building tile requires an explicit catalog setting")
    return dict(rgb=rgb, height=height, height_valid=height_valid,
                instance=instance, id=row["id"], group=row["group"])


class TileCache:
    def __init__(self, dataset, metadata, max_bytes=3 * 1024**3):
        if dataset not in ("3DCD", "P3"):
            raise ValueError(dataset)
        self.dataset = dataset
        self.metadata = metadata
        self.max_bytes = max_bytes
        self.bytes = 0
        self.items = OrderedDict()

    def get(self, row):
        key = row["id"]
        if key in self.items:
            self.items.move_to_end(key)
            return self.items[key][0]
        value = load_3dcd(row, self.metadata) if self.dataset == "3DCD" else load_p3(row, self.metadata)
        size = sum(a.nbytes for a in value.values() if isinstance(a, np.ndarray))
        while self.items and self.bytes + size > self.max_bytes:
            _, (_, removed) = self.items.popitem(last=False)
            self.bytes -= removed
        if size <= self.max_bytes:
            self.items[key] = (value, size)
            self.bytes += size
        return value

    def clear(self):
        self.items.clear()
        self.bytes = 0
        _ANNOTATIONS.clear()
