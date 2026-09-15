import csv
import json
import math
import os
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from scipy.ndimage import (
    gaussian_filter,
    distance_transform_edt,
)
from skimage import io


ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

OUT_DIR = (
    ROOT
    / "records"
    / "physical_frequency_audit_20260913"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Dataset configuration
# ============================================================

VAI_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen"
)

POT_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped"
)

VAI_TRAIN = [
    1, 3, 7, 11, 13, 17,
    23, 26, 28, 32, 34, 37,
]

POT_TRAIN = [
    "6_10", "7_10", "2_12", "3_11",
    "2_10", "7_8", "5_10", "3_12",
    "5_12", "7_11", "7_9", "6_9",
    "7_7", "4_12", "6_8", "6_12",
    "6_7", "4_11",
]

DATASETS = {
    "Vaihingen": {
        "gsd_m": 0.09,
        "tiles": VAI_TRAIN,
    },
    "Potsdam": {
        "gsd_m": 0.05,
        "tiles": POT_TRAIN,
    },
}


# ============================================================
# Frequency scales
# ============================================================

# These are Gaussian sigma values expressed in real-world metres.
#
# Band definitions:
#   B0 = X - G(0.18 m)
#   B1 = G(0.18) - G(0.36)
#   B2 = G(0.36) - G(0.72)
#   B3 = G(0.72) - G(1.44)
#   B4 = G(1.44) - G(2.88)
#
# Important:
# These are physical analysis scales, not literal Fourier wavelengths.

PHYSICAL_SIGMA_M = [
    0.18,
    0.36,
    0.72,
    1.44,
    2.88,
]

# Pixel-coordinate control.
#
# Notice:
# Vaihingen 0.09 m × [2,4,8,16,32]
# = [0.18,0.36,0.72,1.44,2.88] m.
#
# Thus Vaihingen acts as the common anchor, while Potsdam
# distinguishes fixed-pixel from physical-scale processing.

PIXEL_SIGMA = [
    2.0,
    4.0,
    8.0,
    16.0,
    32.0,
]

# Class boundary defined in PHYSICAL space.
# This avoids "3 pixels" meaning different distances on the two datasets.

BOUNDARY_WIDTH_M = 0.27


# ============================================================
# Classes
# ============================================================

CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
]

PALETTE = {
    (255, 255, 255): 0,
    (0, 0, 255): 1,
    (0, 255, 255): 2,
    (0, 255, 0): 3,
    (255, 255, 0): 4,
    (255, 0, 0): 5,
}


# ============================================================
# File paths
# ============================================================

def potsdam_dsm_name(tile):
    a, b = tile.split("_")
    return (
        f"dsm_potsdam_"
        f"{int(a):02d}_{int(b):02d}.tif"
    )


def get_paths(dataset, tile):

    if dataset == "Vaihingen":

        optical = (
            VAI_ROOT
            / "top"
            / f"top_mosaic_09cm_area{tile}.tif"
        )

        dsm = (
            VAI_ROOT
            / "dsm"
            / f"dsm_09cm_matching_area{tile}.tif"
        )

        label = (
            VAI_ROOT
            / "gts_complete_full"
            / f"top_mosaic_09cm_area{tile}.tif"
        )

    elif dataset == "Potsdam":

        optical = (
            POT_ROOT
            / "2_Ortho_RGB"
            / f"top_potsdam_{tile}_RGB.tif"
        )

        dsm = (
            POT_ROOT
            / "1_DSM"
            / "1_DSM"
            / potsdam_dsm_name(tile)
        )

        label = (
            POT_ROOT
            / "5_Labels_for_participants"
            / f"top_potsdam_{tile}_label.tif"
        )

    else:
        raise ValueError(dataset)

    return optical, dsm, label


# ============================================================
# GT
# ============================================================

def convert_gt(rgb):

    gt = np.full(
        rgb.shape[:2],
        255,
        dtype=np.uint8,
    )

    matched = np.zeros(
        rgb.shape[:2],
        dtype=bool,
    )

    for color, idx in PALETTE.items():

        mask = np.all(
            rgb[..., :3]
            == np.asarray(
                color,
                dtype=rgb.dtype,
            ),
            axis=-1,
        )

        gt[mask] = idx
        matched |= mask

    if not matched.all():

        unknown = int(
            (~matched).sum()
        )

        raise RuntimeError(
            f"Unknown GT pixels: {unknown}"
        )

    return gt


# ============================================================
# Normalization
# ============================================================

def standardize_channel(x):

    x = np.asarray(
        x,
        dtype=np.float32,
    )

    finite = np.isfinite(x)

    if not finite.all():
        raise RuntimeError(
            "Non-finite image values detected"
        )

    mean = float(
        x.mean(
            dtype=np.float64
        )
    )

    std = float(
        x.std(
            dtype=np.float64
        )
    )

    if std < 1e-8:
        raise RuntimeError(
            "Near-constant channel"
        )

    return (
        (x - mean)
        / std
    ).astype(
        np.float32,
        copy=False,
    )


# ============================================================
# Region masks
# ============================================================

def build_regions(
    gt,
    gsd_m,
):

    regions = {}

    for cls_id, cls_name in enumerate(
        CLASS_NAMES
    ):

        mask = (
            gt == cls_id
        )

        n_all = int(
            mask.sum()
        )

        if n_all == 0:
            continue

        # Distance from each class pixel to the nearest
        # non-class pixel, directly expressed in metres.
        dist_m = distance_transform_edt(
            mask,
            sampling=(
                gsd_m,
                gsd_m,
            ),
        )

        boundary = (
            mask
            & (dist_m <= BOUNDARY_WIDTH_M)
        )

        interior = (
            mask
            & (dist_m > BOUNDARY_WIDTH_M)
        )

        regions[
            (
                cls_name,
                "All",
            )
        ] = mask

        regions[
            (
                cls_name,
                "Boundary",
            )
        ] = boundary

        regions[
            (
                cls_name,
                "Interior",
            )
        ] = interior

    return regions


# ============================================================
# Accumulator
# ============================================================

def empty_acc():

    return defaultdict(
        lambda: {
            "energy_sum": 0.0,
            "sample_count": 0,
            "pixel_count": 0,
        }
    )


def add_energy(
    acc,
    dataset,
    profile_type,
    modality,
    cls_name,
    region_name,
    band_idx,
    energy,
    mask,
):

    n = int(
        mask.sum()
    )

    if n <= 0:
        return

    value = float(
        energy[mask]
        .sum(
            dtype=np.float64
        )
    )

    key = (
        dataset,
        profile_type,
        modality,
        cls_name,
        region_name,
        band_idx,
    )

    acc[key]["energy_sum"] += value
    acc[key]["sample_count"] += n
    acc[key]["pixel_count"] += n


# ============================================================
# One channel / one scale system
# ============================================================

def process_channel(
    channel,
    sigmas_px,
    callback,
):

    x = standardize_channel(
        channel
    )

    previous = x

    for band_idx, sigma in enumerate(
        sigmas_px
    ):

        current = gaussian_filter(
            x,
            sigma=float(sigma),
            mode="reflect",
            truncate=4.0,
        ).astype(
            np.float32,
            copy=False,
        )

        band = (
            previous
            - current
        )

        energy = (
            band
            * band
        ).astype(
            np.float32,
            copy=False,
        )

        callback(
            band_idx,
            energy,
        )

        previous = current


# ============================================================
# One tile
# ============================================================

def process_tile(job):

    dataset, tile = job

    gsd_m = DATASETS[
        dataset
    ]["gsd_m"]

    optical_path, dsm_path, label_path = (
        get_paths(
            dataset,
            tile,
        )
    )

    for p in (
        optical_path,
        dsm_path,
        label_path,
    ):
        if not p.is_file():
            raise FileNotFoundError(p)

    optical = io.imread(
        str(optical_path)
    )[..., :3].astype(
        np.float32
    )

    dsm = io.imread(
        str(dsm_path)
    ).astype(
        np.float32
    )

    gt = convert_gt(
        io.imread(
            str(label_path)
        )
    )

    if not (
        optical.shape[:2]
        == dsm.shape
        == gt.shape
    ):
        raise RuntimeError(
            f"Shape mismatch {dataset}/{tile}: "
            f"{optical.shape}, "
            f"{dsm.shape}, "
            f"{gt.shape}"
        )

    regions = build_regions(
        gt,
        gsd_m,
    )

    local = empty_acc()

    physical_sigmas_px = [
        s / gsd_m
        for s in PHYSICAL_SIGMA_M
    ]

    profile_systems = {
        "physical": physical_sigmas_px,
        "pixel": PIXEL_SIGMA,
    }

    # --------------------------------------------------------
    # Optical
    # --------------------------------------------------------
    #
    # Potsdam:
    #   channel 0 = R
    #   channel 1 = G
    #   channel 2 = B
    #
    # Vaihingen:
    #   channel 0 = NIR
    #   channel 1 = R
    #   channel 2 = G
    #
    # Cross-dataset primary optical comparison therefore
    # uses shared R/G only.

    if dataset == "Potsdam":
        shared_rg_channels = {
            0, 1
        }
    else:
        shared_rg_channels = {
            1, 2
        }

    for profile_type, sigmas_px in (
        profile_systems.items()
    ):

        for channel_idx in range(3):

            def optical_callback(
                band_idx,
                energy,
                channel_idx=channel_idx,
                profile_type=profile_type,
            ):

                for (
                    cls_name,
                    region_name,
                ), mask in regions.items():

                    add_energy(
                        local,
                        dataset,
                        profile_type,
                        "Optical_native",
                        cls_name,
                        region_name,
                        band_idx,
                        energy,
                        mask,
                    )

                    if (
                        channel_idx
                        in shared_rg_channels
                    ):

                        add_energy(
                            local,
                            dataset,
                            profile_type,
                            "Optical_shared_RG",
                            cls_name,
                            region_name,
                            band_idx,
                            energy,
                            mask,
                        )

            process_channel(
                optical[
                    ...,
                    channel_idx
                ],
                sigmas_px,
                optical_callback,
            )

        # ----------------------------------------------------
        # DSM
        # ----------------------------------------------------

        def dsm_callback(
            band_idx,
            energy,
            profile_type=profile_type,
        ):

            for (
                cls_name,
                region_name,
            ), mask in regions.items():

                add_energy(
                    local,
                    dataset,
                    profile_type,
                    "DSM",
                    cls_name,
                    region_name,
                    band_idx,
                    energy,
                    mask,
                )

        process_channel(
            dsm,
            sigmas_px,
            dsm_callback,
        )

    # Convert defaultdict to ordinary serializable dict.

    packed = {
        "|".join(
            map(str, key)
        ): value
        for key, value in local.items()
    }

    return {
        "dataset": dataset,
        "tile": str(tile),
        "shape": list(gt.shape),
        "physical_sigma_px":
            physical_sigmas_px,
        "stats": packed,
    }


# ============================================================
# Distance metrics
# ============================================================

def normalize_profile(values):

    p = np.asarray(
        values,
        dtype=np.float64,
    )

    p = np.clip(
        p,
        0.0,
        None,
    )

    total = float(
        p.sum()
    )

    if total <= 0:
        return np.zeros_like(p)

    return (
        p / total
    )


def js_divergence(p, q):

    p = normalize_profile(p)
    q = normalize_profile(q)

    eps = 1e-12

    p = np.clip(
        p,
        eps,
        1.0,
    )

    q = np.clip(
        q,
        eps,
        1.0,
    )

    p = (
        p / p.sum()
    )

    q = (
        q / q.sum()
    )

    m = (
        0.5
        * (p + q)
    )

    kl_pm = np.sum(
        p * np.log2(
            p / m
        )
    )

    kl_qm = np.sum(
        q * np.log2(
            q / m
        )
    )

    return float(
        0.5
        * (
            kl_pm
            + kl_qm
        )
    )


def cosine_distance(p, q):

    p = np.asarray(
        p,
        dtype=np.float64,
    )

    q = np.asarray(
        q,
        dtype=np.float64,
    )

    np_norm = float(
        np.linalg.norm(p)
    )

    nq_norm = float(
        np.linalg.norm(q)
    )

    if (
        np_norm <= 0
        or nq_norm <= 0
    ):
        return float("nan")

    similarity = float(
        np.dot(p, q)
        / (np_norm * nq_norm)
    )

    return (
        1.0
        - similarity
    )


# ============================================================
# Main
# ============================================================

def main():

    workers = int(
        os.environ.get(
            "FREQ_AUDIT_WORKERS",
            "4",
        )
    )

    jobs = []

    for dataset, cfg in DATASETS.items():

        for tile in cfg["tiles"]:

            jobs.append(
                (
                    dataset,
                    tile,
                )
            )

    print("=" * 100)
    print(
        "CROSS-DATASET PHYSICAL FREQUENCY AUDIT"
    )
    print("=" * 100)
    print(
        "GPU usage             : NONE"
    )
    print(
        "workers               :",
        workers,
    )
    print(
        "jobs                  :",
        len(jobs),
    )
    print(
        "Vaihingen GSD         : 0.09 m"
    )
    print(
        "Potsdam GSD           : 0.05 m"
    )
    print(
        "physical sigma (m)    :",
        PHYSICAL_SIGMA_M,
    )
    print(
        "fixed pixel sigma     :",
        PIXEL_SIGMA,
    )
    print(
        "boundary width        :",
        BOUNDARY_WIDTH_M,
        "m",
    )
    print("=" * 100)

    global_acc = empty_acc()

    tile_records = []

    with ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        future_map = {
            executor.submit(
                process_tile,
                job,
            ): job
            for job in jobs
        }

        done = 0

        for future in as_completed(
            future_map
        ):

            job = future_map[
                future
            ]

            dataset, tile = job

            result = future.result()

            done += 1

            print(
                f"[{done:02d}/{len(jobs):02d}] "
                f"PASS "
                f"{dataset} {tile} "
                f"shape={tuple(result['shape'])}"
            )

            tile_records.append({
                "dataset":
                    dataset,
                "tile":
                    str(tile),
                "height":
                    result["shape"][0],
                "width":
                    result["shape"][1],
                "physical_sigma_px":
                    result[
                        "physical_sigma_px"
                    ],
            })

            for packed_key, value in (
                result[
                    "stats"
                ].items()
            ):

                parts = (
                    packed_key
                    .split("|")
                )

                key = (
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[3],
                    parts[4],
                    int(parts[5]),
                )

                global_acc[
                    key
                ][
                    "energy_sum"
                ] += value[
                    "energy_sum"
                ]

                global_acc[
                    key
                ][
                    "sample_count"
                ] += value[
                    "sample_count"
                ]

                global_acc[
                    key
                ][
                    "pixel_count"
                ] += value[
                    "pixel_count"
                ]

    # ========================================================
    # Aggregate means
    # ========================================================

    rows = []

    grouped = defaultdict(
        dict
    )

    for key, value in global_acc.items():

        (
            dataset,
            profile_type,
            modality,
            cls_name,
            region_name,
            band_idx,
        ) = key

        count = value[
            "sample_count"
        ]

        if count <= 0:
            mean_energy = 0.0
        else:
            mean_energy = (
                value[
                    "energy_sum"
                ]
                / count
            )

        group_key = (
            dataset,
            profile_type,
            modality,
            cls_name,
            region_name,
        )

        grouped[
            group_key
        ][
            band_idx
        ] = {
            "mean_energy":
                mean_energy,
            "sample_count":
                count,
        }

    profiles = {}

    for group_key, bands in (
        grouped.items()
    ):

        values = [
            bands.get(
                i,
                {
                    "mean_energy":
                        0.0
                },
            )[
                "mean_energy"
            ]
            for i in range(
                len(
                    PHYSICAL_SIGMA_M
                )
            )
        ]

        normalized = (
            normalize_profile(
                values
            )
        )

        profiles[
            group_key
        ] = normalized

        (
            dataset,
            profile_type,
            modality,
            cls_name,
            region_name,
        ) = group_key

        for band_idx in range(
            len(values)
        ):

            if profile_type == "physical":

                high = (
                    PHYSICAL_SIGMA_M[
                        band_idx
                    ]
                )

                low = (
                    0.0
                    if band_idx == 0
                    else PHYSICAL_SIGMA_M[
                        band_idx - 1
                    ]
                )

                band_label = (
                    f"{low:.2f}-"
                    f"{high:.2f}m"
                )

            else:

                high = (
                    PIXEL_SIGMA[
                        band_idx
                    ]
                )

                low = (
                    0.0
                    if band_idx == 0
                    else PIXEL_SIGMA[
                        band_idx - 1
                    ]
                )

                band_label = (
                    f"{low:g}-"
                    f"{high:g}px"
                )

            rows.append({
                "dataset":
                    dataset,
                "profile_type":
                    profile_type,
                "modality":
                    modality,
                "class":
                    cls_name,
                "region":
                    region_name,
                "band_idx":
                    band_idx,
                "band":
                    band_label,
                "mean_energy":
                    values[
                        band_idx
                    ],
                "normalized_energy":
                    float(
                        normalized[
                            band_idx
                        ]
                    ),
                "sample_count":
                    bands.get(
                        band_idx,
                        {
                            "sample_count":
                                0
                        },
                    )[
                        "sample_count"
                    ],
            })

    # ========================================================
    # frequency_energy_by_class.csv
    # ========================================================

    energy_csv = (
        OUT_DIR
        / "frequency_energy_by_class.csv"
    )

    with energy_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        fields = [
            "dataset",
            "profile_type",
            "modality",
            "class",
            "region",
            "band_idx",
            "band",
            "mean_energy",
            "normalized_energy",
            "sample_count",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)

    # ========================================================
    # Dominant scales
    # ========================================================

    dominant_rows = []

    for group_key, p in profiles.items():

        (
            dataset,
            profile_type,
            modality,
            cls_name,
            region_name,
        ) = group_key

        idx = int(
            np.argmax(p)
        )

        if profile_type == "physical":

            hi = (
                PHYSICAL_SIGMA_M[
                    idx
                ]
            )

            lo = (
                0.0
                if idx == 0
                else PHYSICAL_SIGMA_M[
                    idx - 1
                ]
            )

            dominant = (
                f"{lo:.2f}-"
                f"{hi:.2f}m"
            )

        else:

            hi = (
                PIXEL_SIGMA[
                    idx
                ]
            )

            lo = (
                0.0
                if idx == 0
                else PIXEL_SIGMA[
                    idx - 1
                ]
            )

            dominant = (
                f"{lo:g}-"
                f"{hi:g}px"
            )

        dominant_rows.append({
            "dataset":
                dataset,
            "profile_type":
                profile_type,
            "modality":
                modality,
            "class":
                cls_name,
            "region":
                region_name,
            "dominant_band":
                dominant,
            "dominant_band_idx":
                idx,
            "dominant_fraction":
                float(p[idx]),
        })

    dominant_csv = (
        OUT_DIR
        / "dominant_scale.csv"
    )

    with dominant_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        fields = list(
            dominant_rows[
                0
            ].keys()
        )

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(
            dominant_rows
        )

    # ========================================================
    # Cross-dataset comparison
    # ========================================================

    distance_rows = []

    modalities = [
        "DSM",
        "Optical_shared_RG",
        "Optical_native",
    ]

    for modality in modalities:

        for cls_name in CLASS_NAMES:

            for region_name in [
                "All",
                "Boundary",
                "Interior",
            ]:

                record = {
                    "modality":
                        modality,
                    "class":
                        cls_name,
                    "region":
                        region_name,
                }

                complete = True

                for profile_type in [
                    "pixel",
                    "physical",
                ]:

                    vk = (
                        "Vaihingen",
                        profile_type,
                        modality,
                        cls_name,
                        region_name,
                    )

                    pk = (
                        "Potsdam",
                        profile_type,
                        modality,
                        cls_name,
                        region_name,
                    )

                    if (
                        vk not in profiles
                        or pk not in profiles
                    ):
                        complete = False
                        break

                    vp = profiles[vk]
                    pp = profiles[pk]

                    record[
                        f"jsd_{profile_type}"
                    ] = js_divergence(
                        vp,
                        pp,
                    )

                    record[
                        f"cosdist_{profile_type}"
                    ] = cosine_distance(
                        vp,
                        pp,
                    )

                if not complete:
                    continue

                record[
                    "jsd_improvement_pixel_minus_physical"
                ] = (
                    record[
                        "jsd_pixel"
                    ]
                    - record[
                        "jsd_physical"
                    ]
                )

                record[
                    "cosdist_improvement_pixel_minus_physical"
                ] = (
                    record[
                        "cosdist_pixel"
                    ]
                    - record[
                        "cosdist_physical"
                    ]
                )

                if modality in (
                    "DSM",
                    "Optical_shared_RG",
                ):
                    validity = (
                        "PRIMARY_COMPARABLE"
                    )
                else:
                    validity = (
                        "SECONDARY_SPECTRAL_MISMATCH"
                    )

                record[
                    "comparison_validity"
                ] = validity

                distance_rows.append(
                    record
                )

    distance_csv = (
        OUT_DIR
        / "cross_dataset_distance.csv"
    )

    with distance_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        fields = list(
            distance_rows[
                0
            ].keys()
        )

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        writer.writerows(
            distance_rows
        )

    # ========================================================
    # Boundary vs interior
    # ========================================================

    boundary_rows = []

    for dataset in DATASETS:

        for profile_type in [
            "physical",
            "pixel",
        ]:

            for modality in modalities:

                for cls_name in CLASS_NAMES:

                    bk = (
                        dataset,
                        profile_type,
                        modality,
                        cls_name,
                        "Boundary",
                    )

                    ik = (
                        dataset,
                        profile_type,
                        modality,
                        cls_name,
                        "Interior",
                    )

                    if (
                        bk not in profiles
                        or ik not in profiles
                    ):
                        continue

                    boundary_rows.append({
                        "dataset":
                            dataset,
                        "profile_type":
                            profile_type,
                        "modality":
                            modality,
                        "class":
                            cls_name,
                        "jsd_boundary_vs_interior":
                            js_divergence(
                                profiles[bk],
                                profiles[ik],
                            ),
                        "cosdist_boundary_vs_interior":
                            cosine_distance(
                                profiles[bk],
                                profiles[ik],
                            ),
                    })

    boundary_csv = (
        OUT_DIR
        / "boundary_vs_interior.csv"
    )

    with boundary_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                boundary_rows[
                    0
                ].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            boundary_rows
        )

    # ========================================================
    # Optical vs DSM
    # ========================================================

    modality_rows = []

    for dataset in DATASETS:

        for profile_type in [
            "physical",
            "pixel",
        ]:

            for cls_name in CLASS_NAMES:

                for region_name in [
                    "All",
                    "Boundary",
                    "Interior",
                ]:

                    ok = (
                        dataset,
                        profile_type,
                        "Optical_shared_RG",
                        cls_name,
                        region_name,
                    )

                    dk = (
                        dataset,
                        profile_type,
                        "DSM",
                        cls_name,
                        region_name,
                    )

                    if (
                        ok not in profiles
                        or dk not in profiles
                    ):
                        continue

                    modality_rows.append({
                        "dataset":
                            dataset,
                        "profile_type":
                            profile_type,
                        "class":
                            cls_name,
                        "region":
                            region_name,
                        "jsd_opticalRG_vs_DSM":
                            js_divergence(
                                profiles[ok],
                                profiles[dk],
                            ),
                        "cosdist_opticalRG_vs_DSM":
                            cosine_distance(
                                profiles[ok],
                                profiles[dk],
                            ),
                    })

    modality_csv = (
        OUT_DIR
        / "modality_frequency_difference.csv"
    )

    with modality_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                modality_rows[
                    0
                ].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            modality_rows
        )

    # ========================================================
    # Summary
    # ========================================================

    primary = [
        r
        for r in distance_rows
        if r[
            "comparison_validity"
        ] == "PRIMARY_COMPARABLE"
    ]

    primary_all = [
        r
        for r in primary
        if r["region"] == "All"
    ]

    jsd_improved = [
        r
        for r in primary_all
        if (
            r[
                "jsd_improvement_pixel_minus_physical"
            ]
            > 0
        )
    ]

    mean_jsd_pixel = float(
        np.mean([
            r["jsd_pixel"]
            for r in primary_all
        ])
    )

    mean_jsd_physical = float(
        np.mean([
            r["jsd_physical"]
            for r in primary_all
        ])
    )

    summary = {
        "status":
            "PASS",

        "train_only":
            True,

        "datasets": {
            "Vaihingen": {
                "gsd_m":
                    0.09,
                "train_tiles":
                    VAI_TRAIN,
                "optical":
                    "IRRG",
            },
            "Potsdam": {
                "gsd_m":
                    0.05,
                "train_tiles":
                    POT_TRAIN,
                "optical":
                    "RGB",
            },
        },

        "physical_sigma_m":
            PHYSICAL_SIGMA_M,

        "fixed_pixel_sigma":
            PIXEL_SIGMA,

        "boundary_width_m":
            BOUNDARY_WIDTH_M,

        "primary_cross_dataset_modalities": [
            "DSM",
            "Optical_shared_RG",
        ],

        "mean_primary_jsd_pixel":
            mean_jsd_pixel,

        "mean_primary_jsd_physical":
            mean_jsd_physical,

        "mean_primary_jsd_improvement":
            (
                mean_jsd_pixel
                - mean_jsd_physical
            ),

        "primary_all_profiles_improved_count":
            len(
                jsd_improved
            ),

        "primary_all_profiles_total":
            len(
                primary_all
            ),

        "primary_all_profiles_improved_fraction":
            (
                len(jsd_improved)
                / len(primary_all)
                if primary_all
                else None
            ),

        "interpretation_rule":
            (
                "Positive pixel-minus-physical distance "
                "means GSD-aligned physical scales make "
                "Vaihingen and Potsdam frequency profiles "
                "more similar."
            ),
    }

    summary_json = (
        OUT_DIR
        / "summary.json"
    )

    summary_json.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Tile manifest
    manifest = (
        OUT_DIR
        / "tile_manifest.json"
    )

    manifest.write_text(
        json.dumps(
            tile_records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)

    print(
        "mean primary JSD pixel    =",
        f"{mean_jsd_pixel:.8f}",
    )

    print(
        "mean primary JSD physical =",
        f"{mean_jsd_physical:.8f}",
    )

    print(
        "pixel - physical          =",
        f"{mean_jsd_pixel - mean_jsd_physical:+.8f}",
    )

    print(
        "profiles improved         =",
        f"{len(jsd_improved)}/{len(primary_all)}",
    )

    print()
    print("Outputs:")

    for p in [
        energy_csv,
        dominant_csv,
        distance_csv,
        boundary_csv,
        modality_csv,
        summary_json,
        manifest,
    ]:
        print(" ", p)


if __name__ == "__main__":
    main()
