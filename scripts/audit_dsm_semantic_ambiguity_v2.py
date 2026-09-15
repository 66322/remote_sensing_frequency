from pathlib import Path
import json
import zlib

import numpy as np
import pandas as pd
import tifffile

from scipy.ndimage import (
    uniform_filter,
    sobel,
)

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    roc_auc_score,
)


# ============================================================
# Global configuration
# ============================================================

SEED = 42

# Enough for statistics but not unnecessarily large.
MAX_PER_CLASS_PER_TILE = 3000

# Approximate matching tolerance for raw DSM value.
ABS_DSM_BIN_M = 0.50

# Local geometry is computed at the same physical support
# in both datasets.
LOCAL_SUPPORT_M = 1.00

# Quantile bins for approximate local-geometry matching.
GEOM_QUANTILE_BINS = 4

OUT_DIR = Path(
    "records/dsm_semantic_ambiguity_audit_v2_20260914"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# ISPRS classes
# ============================================================

CLASSES = {
    0: "Impervious",
    1: "Building",
    2: "LowVeg",
    3: "Tree",
    4: "Car",
}

PALETTE = {
    0: (255, 255, 255),
    1: (0, 0, 255),
    2: (0, 255, 255),
    3: (0, 255, 0),
    4: (255, 255, 0),
}


PAIRS = [
    ("Building", "Tree"),
    ("Tree", "LowVeg"),
    ("Building", "Impervious"),
    ("Car", "Impervious"),
]


# ============================================================
# Dataset paths
# ============================================================

VAI_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen"
)

POT_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped"
)


DATASETS = {
    "Vaihingen": {
        "gsd_m": 0.09,

        "tiles": [
            "1", "3", "7", "11", "13", "17",
            "23", "26", "28", "32", "34", "37",
        ],

        "optical": lambda t:
            VAI_ROOT
            / "top"
            / f"top_mosaic_09cm_area{t}.tif",

        "dsm": lambda t:
            VAI_ROOT
            / "dsm"
            / f"dsm_09cm_matching_area{t}.tif",

        "label": lambda t:
            VAI_ROOT
            / "gts_complete_eroded"
            / f"top_mosaic_09cm_area{t}_noBoundary.tif",
    },

    "Potsdam": {
        "gsd_m": 0.05,

        "tiles": [
            "6_10", "7_10", "2_12", "3_11",
            "2_10", "7_8", "5_10", "3_12",
            "5_12", "7_11", "7_9", "6_9",
            "7_7", "4_12", "6_8", "6_12",
            "6_7", "4_11",
        ],

        "optical": lambda t:
            POT_ROOT
            / "2_Ortho_RGB"
            / f"top_potsdam_{t}_RGB.tif",

        "dsm": lambda t:
            POT_ROOT
            / "1_DSM"
            / "1_DSM"
            / (
                "dsm_potsdam_"
                + "_".join(
                    f"{int(x):02d}"
                    for x in t.split("_")
                )
                + ".tif"
            ),

        "label": lambda t:
            POT_ROOT
            / "5_Labels_for_participants_no_Boundary"
            / f"top_potsdam_{t}_label_noBoundary.tif",
    },
}


# ============================================================
# Helpers
# ============================================================

def deterministic_rng(*parts):
    text = "|".join(
        str(x)
        for x in parts
    )

    value = (
        SEED
        + zlib.crc32(
            text.encode("utf-8")
        )
    ) % (2**32 - 1)

    return np.random.default_rng(
        value
    )


def make_odd_window(
    support_m,
    gsd_m,
):
    k = int(
        round(
            support_m / gsd_m
        )
    )

    k = max(
        k,
        3,
    )

    if k % 2 == 0:
        k += 1

    return k


def read_tif(path):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            path
        )

    x = tifffile.imread(
        path
    )

    if (
        x.ndim == 3
        and x.shape[0] <= 4
        and x.shape[-1] > 4
    ):
        x = np.moveaxis(
            x,
            0,
            -1,
        )

    return x


def class_mask(
    label,
    class_id,
):
    color = np.asarray(
        PALETTE[class_id],
        dtype=np.uint8,
    )

    return np.all(
        label[..., :3] == color,
        axis=-1,
    )


# ============================================================
# Optical features
# ============================================================

def normalize_optical(optical):
    optical = optical[
        ...,
        :3
    ].astype(
        np.float32
    )

    out = np.empty_like(
        optical,
        dtype=np.float32,
    )

    # Lightweight robust percentile estimation.
    probe = optical[
        ::16,
        ::16,
        :
    ]

    for c in range(3):

        lo = float(
            np.percentile(
                probe[..., c],
                1.0,
            )
        )

        hi = float(
            np.percentile(
                probe[..., c],
                99.0,
            )
        )

        if hi <= lo:
            hi = lo + 1.0

        out[..., c] = np.clip(
            (
                optical[..., c]
                - lo
            )
            / (
                hi - lo
            ),
            0.0,
            1.0,
        )

    return out


def optical_feature_maps(
    optical,
    gsd_m,
    window,
):
    gray = optical.mean(
        axis=2,
        dtype=np.float32,
    )

    mean = uniform_filter(
        gray,
        size=window,
        mode="reflect",
    )

    mean_sq = uniform_filter(
        gray * gray,
        size=window,
        mode="reflect",
    )

    var = np.maximum(
        mean_sq
        - mean * mean,
        0.0,
    )

    rough = np.sqrt(
        var,
        dtype=np.float32,
    )

    gx = sobel(
        gray,
        axis=1,
        mode="reflect",
    ) / (
        8.0 * gsd_m
    )

    gy = sobel(
        gray,
        axis=0,
        mode="reflect",
    ) / (
        8.0 * gsd_m
    )

    grad = np.hypot(
        gx,
        gy,
    ).astype(
        np.float32
    )

    return (
        rough.astype(np.float32),
        grad,
    )


# ============================================================
# DSM features
# ============================================================

def dsm_feature_maps(
    dsm,
    gsd_m,
    window,
):
    dsm = np.asarray(
        dsm,
        dtype=np.float32,
    )

    if dsm.ndim == 3:
        dsm = np.squeeze(
            dsm
        )

    finite = np.isfinite(
        dsm
    )

    probe = dsm[
        ::16,
        ::16
    ]

    probe = probe[
        np.isfinite(probe)
    ]

    if len(probe) == 0:
        raise RuntimeError(
            "DSM contains no finite values"
        )

    tile_median = float(
        np.median(
            probe
        )
    )

    # Only for neighborhood operations.
    work = np.where(
        finite,
        dsm,
        tile_median,
    ).astype(
        np.float32
    )

    local_mean = uniform_filter(
        work,
        size=window,
        mode="reflect",
    )

    local_sq_mean = uniform_filter(
        work * work,
        size=window,
        mode="reflect",
    )

    local_var = np.maximum(
        local_sq_mean
        - local_mean * local_mean,
        0.0,
    )

    rough = np.sqrt(
        local_var
    ).astype(
        np.float32
    )

    local_rel = (
        work
        - local_mean
    ).astype(
        np.float32
    )

    contrast = np.abs(
        local_rel
    ).astype(
        np.float32
    )

    gx = sobel(
        work,
        axis=1,
        mode="reflect",
    ) / (
        8.0 * gsd_m
    )

    gy = sobel(
        work,
        axis=0,
        mode="reflect",
    ) / (
        8.0 * gsd_m
    )

    grad = np.hypot(
        gx,
        gy,
    ).astype(
        np.float32
    )

    # Tile-centered elevation is separated from local geometry.
    centered = (
        work
        - tile_median
    ).astype(
        np.float32
    )

    return {
        "valid":
            finite,

        "abs":
            work,

        "centered":
            centered,

        "local_rel":
            local_rel,

        "contrast":
            contrast,

        "rough":
            rough,

        "grad":
            grad,
    }


# ============================================================
# Extract sampled features
# ============================================================

all_chunks = []


for dataset_name, cfg in DATASETS.items():

    gsd_m = float(
        cfg["gsd_m"]
    )

    window = make_odd_window(
        LOCAL_SUPPORT_M,
        gsd_m,
    )

    print()
    print("=" * 100)

    print(
        dataset_name,
        f"GSD={gsd_m:.3f} m",
        f"window={window} px",
        f"physical_support≈{window * gsd_m:.3f} m",
    )

    print("=" * 100)

    for tile in cfg["tiles"]:

        print(
            f"[READ] {dataset_name} tile={tile}",
            flush=True,
        )

        optical = read_tif(
            cfg["optical"](tile)
        )

        dsm = read_tif(
            cfg["dsm"](tile)
        )

        label = read_tif(
            cfg["label"](tile)
        )

        if not (
            optical.shape[:2]
            == dsm.shape[:2]
            == label.shape[:2]
        ):
            raise RuntimeError(
                f"shape mismatch: "
                f"{dataset_name} {tile}: "
                f"opt={optical.shape}, "
                f"dsm={dsm.shape}, "
                f"label={label.shape}"
            )

        optical_n = normalize_optical(
            optical
        )

        dsm_maps = dsm_feature_maps(
            dsm,
            gsd_m,
            window,
        )

        (
            opt_rough,
            opt_grad,
        ) = optical_feature_maps(
            optical_n,
            gsd_m,
            window,
        )

        for class_id, class_name in CLASSES.items():

            mask = class_mask(
                label,
                class_id,
            )

            # Explicitly exclude invalid DSM pixels.
            mask &= dsm_maps[
                "valid"
            ]

            flat = np.flatnonzero(
                mask.ravel()
            )

            if len(flat) == 0:
                print(
                    "   [EMPTY]",
                    class_name,
                )
                continue

            n = min(
                len(flat),
                MAX_PER_CLASS_PER_TILE,
            )

            if n < len(flat):

                rng = deterministic_rng(
                    dataset_name,
                    tile,
                    class_name,
                )

                flat = rng.choice(
                    flat,
                    size=n,
                    replace=False,
                )

            yy, xx = np.unravel_index(
                flat,
                mask.shape,
            )

            chunk = pd.DataFrame({
                "dataset":
                    dataset_name,

                "tile":
                    str(tile),

                "class_id":
                    class_id,

                "class":
                    class_name,

                "dsm_abs":
                    dsm_maps[
                        "abs"
                    ][yy, xx],

                "dsm_centered":
                    dsm_maps[
                        "centered"
                    ][yy, xx],

                "dsm_local_rel":
                    dsm_maps[
                        "local_rel"
                    ][yy, xx],

                "dsm_contrast":
                    dsm_maps[
                        "contrast"
                    ][yy, xx],

                "dsm_rough":
                    dsm_maps[
                        "rough"
                    ][yy, xx],

                "dsm_grad":
                    dsm_maps[
                        "grad"
                    ][yy, xx],

                # Generic channel names deliberately used:
                # Vaihingen and Potsdam do not have identical
                # optical channel semantics.
                "opt_c1":
                    optical_n[
                        yy, xx, 0
                    ],

                "opt_c2":
                    optical_n[
                        yy, xx, 1
                    ],

                "opt_c3":
                    optical_n[
                        yy, xx, 2
                    ],

                "opt_rough":
                    opt_rough[
                        yy, xx
                    ],

                "opt_grad":
                    opt_grad[
                        yy, xx
                    ],
            })

            all_chunks.append(
                chunk
            )

            print(
                f"   {class_name:10s}",
                f"n={len(chunk)}",
            )

        del optical
        del dsm
        del label
        del optical_n
        del dsm_maps
        del opt_rough
        del opt_grad


samples = pd.concat(
    all_chunks,
    ignore_index=True,
)

sample_path = (
    OUT_DIR
    / "sampled_features.csv"
)

samples.to_csv(
    sample_path,
    index=False,
)

print()
print(
    "[SAVE]",
    sample_path,
)


# ============================================================
# Class-level DSM summary
# ============================================================

DSM_ALL = [
    "dsm_abs",
    "dsm_centered",
    "dsm_local_rel",
    "dsm_contrast",
    "dsm_rough",
    "dsm_grad",
]


summary_rows = []

for (
    dataset,
    class_name,
), g in samples.groupby(
    [
        "dataset",
        "class",
    ]
):

    row = {
        "dataset":
            dataset,

        "class":
            class_name,

        "n":
            len(g),
    }

    for feature in DSM_ALL:

        row[
            feature + "_mean"
        ] = float(
            g[feature].mean()
        )

        row[
            feature + "_std"
        ] = float(
            g[feature].std()
        )

        row[
            feature + "_median"
        ] = float(
            g[feature].median()
        )

    summary_rows.append(
        row
    )


class_summary = pd.DataFrame(
    summary_rows
)

class_summary.to_csv(
    OUT_DIR
    / "class_dsm_summary.csv",
    index=False,
)


# ============================================================
# Distribution overlap
# ============================================================

def distribution_metrics(
    x,
    y,
    n_bins=80,
):
    x = np.asarray(
        x,
        dtype=np.float64,
    )

    y = np.asarray(
        y,
        dtype=np.float64,
    )

    x = x[
        np.isfinite(x)
    ]

    y = y[
        np.isfinite(y)
    ]

    pool = np.concatenate(
        [
            x,
            y,
        ]
    )

    lo = float(
        np.percentile(
            pool,
            0.5,
        )
    )

    hi = float(
        np.percentile(
            pool,
            99.5,
        )
    )

    if hi <= lo:
        hi = lo + 1e-6

    edges = np.linspace(
        lo,
        hi,
        n_bins + 1,
    )

    px, _ = np.histogram(
        np.clip(
            x,
            lo,
            hi,
        ),
        bins=edges,
    )

    py, _ = np.histogram(
        np.clip(
            y,
            lo,
            hi,
        ),
        bins=edges,
    )

    px = px.astype(
        np.float64
    )

    py = py.astype(
        np.float64
    )

    px /= max(
        px.sum(),
        1.0,
    )

    py /= max(
        py.sum(),
        1.0,
    )

    overlap = float(
        np.minimum(
            px,
            py,
        ).sum()
    )

    eps = 1e-12

    px += eps
    py += eps

    px /= px.sum()
    py /= py.sum()

    m = 0.5 * (
        px + py
    )

    jsd = 0.5 * (
        np.sum(
            px
            * np.log2(
                px / m
            )
        )
        +
        np.sum(
            py
            * np.log2(
                py / m
            )
        )
    )

    return (
        overlap,
        float(jsd),
    )


overlap_rows = []

for dataset in DATASETS:

    sd = samples[
        samples["dataset"]
        == dataset
    ]

    for class_a, class_b in PAIRS:

        aa = sd[
            sd["class"]
            == class_a
        ]

        bb = sd[
            sd["class"]
            == class_b
        ]

        for feature in DSM_ALL:

            overlap, jsd = (
                distribution_metrics(
                    aa[feature],
                    bb[feature],
                )
            )

            overlap_rows.append({
                "dataset":
                    dataset,

                "class_a":
                    class_a,

                "class_b":
                    class_b,

                "feature":
                    feature,

                "overlap_coefficient":
                    overlap,

                "jsd_bits":
                    jsd,
            })


pd.DataFrame(
    overlap_rows
).to_csv(
    OUT_DIR
    / "pairwise_dsm_distribution_overlap.csv",
    index=False,
)


# ============================================================
# Matching helpers
# ============================================================

def balance_cells(
    a,
    b,
    key_columns,
    seed_prefix,
):
    pieces = []

    a_groups = {
        key: g
        for key, g in a.groupby(
            key_columns,
            sort=False,
        )
    }

    b_groups = {
        key: g
        for key, g in b.groupby(
            key_columns,
            sort=False,
        )
    }

    common = set(
        a_groups
    ).intersection(
        b_groups
    )

    for key in sorted(
        common,
        key=lambda x: str(x),
    ):

        ga = a_groups[key]
        gb = b_groups[key]

        n = min(
            len(ga),
            len(gb),
        )

        if n <= 0:
            continue

        rng_a = deterministic_rng(
            seed_prefix,
            key,
            "A",
        )

        rng_b = deterministic_rng(
            seed_prefix,
            key,
            "B",
        )

        ia = rng_a.choice(
            len(ga),
            size=n,
            replace=False,
        )

        ib = rng_b.choice(
            len(gb),
            size=n,
            replace=False,
        )

        pieces.append(
            ga.iloc[
                ia
            ]
        )

        pieces.append(
            gb.iloc[
                ib
            ]
        )

    if not pieces:
        return pd.DataFrame()

    return pd.concat(
        pieces,
        ignore_index=True,
    )


def match_absolute_dsm(
    pair_df,
    class_a,
    class_b,
):
    pieces = []

    for tile, gt in pair_df.groupby(
        "tile"
    ):

        gt = gt.copy()

        gt["_abs_bin"] = np.floor(
            gt["dsm_abs"]
            / ABS_DSM_BIN_M
        ).astype(
            np.int64
        )

        a = gt[
            gt["class"]
            == class_a
        ]

        b = gt[
            gt["class"]
            == class_b
        ]

        if (
            len(a) == 0
            or len(b) == 0
        ):
            continue

        m = balance_cells(
            a,
            b,
            ["_abs_bin"],
            (
                "ABS",
                tile,
                class_a,
                class_b,
            ),
        )

        if len(m):
            pieces.append(
                m
            )

    if not pieces:
        return pd.DataFrame()

    out = pd.concat(
        pieces,
        ignore_index=True,
    )

    return out.drop(
        columns=[
            "_abs_bin",
        ],
        errors="ignore",
    )


def quantile_codes(
    values,
    n_bins,
):
    values = np.asarray(
        values,
        dtype=np.float64,
    )

    q = np.linspace(
        0.0,
        1.0,
        n_bins + 1,
    )

    edges = np.quantile(
        values,
        q,
    )

    edges = np.unique(
        edges
    )

    if len(edges) <= 2:
        return np.zeros(
            len(values),
            dtype=np.int16,
        )

    internal = edges[
        1:-1
    ]

    return np.digitize(
        values,
        internal,
        right=False,
    ).astype(
        np.int16
    )


def match_local_geometry(
    pair_df,
    class_a,
    class_b,
):
    pieces = []

    for tile, gt in pair_df.groupby(
        "tile"
    ):

        gt = gt.copy()

        a_mask = (
            gt["class"]
            == class_a
        )

        b_mask = (
            gt["class"]
            == class_b
        )

        if (
            not a_mask.any()
            or not b_mask.any()
        ):
            continue

        # Quantile bins are determined from the pooled
        # two-class data inside the SAME tile.
        for src, dst in [
            (
                "dsm_local_rel",
                "_geom_rel",
            ),
            (
                "dsm_rough",
                "_geom_rough",
            ),
            (
                "dsm_grad",
                "_geom_grad",
            ),
        ]:

            gt[dst] = quantile_codes(
                gt[src].to_numpy(),
                GEOM_QUANTILE_BINS,
            )

        a = gt[
            a_mask
        ]

        b = gt[
            b_mask
        ]

        m = balance_cells(
            a,
            b,
            [
                "_geom_rel",
                "_geom_rough",
                "_geom_grad",
            ],
            (
                "GEOM",
                tile,
                class_a,
                class_b,
            ),
        )

        if len(m):
            pieces.append(
                m
            )

    if not pieces:
        return pd.DataFrame()

    out = pd.concat(
        pieces,
        ignore_index=True,
    )

    return out.drop(
        columns=[
            "_geom_rel",
            "_geom_rough",
            "_geom_grad",
        ],
        errors="ignore",
    )


# ============================================================
# Classification test
# ============================================================

FEATURE_SETS = {
    "DSM_abs_only": [
        "dsm_abs",
    ],

    "DSM_geometry": [
        "dsm_local_rel",
        "dsm_contrast",
        "dsm_rough",
        "dsm_grad",
    ],

    "Optical_only": [
        "opt_c1",
        "opt_c2",
        "opt_c3",
        "opt_rough",
        "opt_grad",
    ],

    "DSM_geometry_plus_Optical": [
        "dsm_local_rel",
        "dsm_contrast",
        "dsm_rough",
        "dsm_grad",
        "opt_c1",
        "opt_c2",
        "opt_c3",
        "opt_rough",
        "opt_grad",
    ],
}


def evaluate_subset(
    subset,
    dataset,
    class_a,
    class_b,
    subset_name,
):
    rows = []

    if len(subset) == 0:
        return rows

    if subset["tile"].nunique() < 3:
        print(
            "[SKIP] insufficient tiles:",
            dataset,
            class_a,
            class_b,
            subset_name,
        )
        return rows

    y = (
        subset["class"]
        == class_b
    ).astype(
        np.int64
    ).to_numpy()

    groups = subset[
        "tile"
    ].astype(
        str
    ).to_numpy()

    for feature_set, columns in FEATURE_SETS.items():

        X = subset[
            columns
        ].to_numpy(
            dtype=np.float64
        )

        splitter = GroupShuffleSplit(
            n_splits=3,
            test_size=0.25,
            random_state=SEED,
        )

        scores = []

        for split_id, (
            train_idx,
            test_idx,
        ) in enumerate(
            splitter.split(
                X,
                y,
                groups,
            )
        ):

            y_train = y[
                train_idx
            ]

            y_test = y[
                test_idx
            ]

            if (
                len(
                    np.unique(
                        y_train
                    )
                ) < 2
                or
                len(
                    np.unique(
                        y_test
                    )
                ) < 2
            ):
                continue

            clf = Pipeline([
                (
                    "scale",
                    StandardScaler(),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        solver="liblinear",
                        class_weight="balanced",
                        random_state=SEED,
                    ),
                ),
            ])

            clf.fit(
                X[
                    train_idx
                ],
                y_train,
            )

            pred = clf.predict(
                X[
                    test_idx
                ]
            )

            prob = clf.predict_proba(
                X[
                    test_idx
                ]
            )[:, 1]

            bacc = (
                balanced_accuracy_score(
                    y_test,
                    pred,
                )
            )

            auc = (
                roc_auc_score(
                    y_test,
                    prob,
                )
            )

            scores.append(
                (
                    bacc,
                    auc,
                )
            )

        if not scores:
            continue

        scores = np.asarray(
            scores,
            dtype=np.float64,
        )

        rows.append({
            "dataset":
                dataset,

            "class_a":
                class_a,

            "class_b":
                class_b,

            "subset":
                subset_name,

            "feature_set":
                feature_set,

            "n_samples":
                len(subset),

            "n_tiles":
                subset[
                    "tile"
                ].nunique(),

            "balanced_acc_mean":
                float(
                    scores[
                        :, 0
                    ].mean()
                ),

            "balanced_acc_std":
                float(
                    scores[
                        :, 0
                    ].std()
                ),

            "auc_mean":
                float(
                    scores[
                        :, 1
                    ].mean()
                ),

            "auc_std":
                float(
                    scores[
                        :, 1
                    ].std()
                ),
        })

    return rows


all_results = []
matched_count_rows = []


for dataset in DATASETS:

    ds = samples[
        samples["dataset"]
        == dataset
    ].copy()

    for class_a, class_b in PAIRS:

        pair_df = ds[
            ds["class"].isin(
                [
                    class_a,
                    class_b,
                ]
            )
        ].copy()

        full = pair_df

        abs_matched = match_absolute_dsm(
            pair_df,
            class_a,
            class_b,
        )

        geom_matched = match_local_geometry(
            pair_df,
            class_a,
            class_b,
        )

        subsets = {
            "FULL":
                full,

            "ABS_DSM_MATCHED":
                abs_matched,

            "LOCAL_GEOM_MATCHED":
                geom_matched,
        }

        for subset_name, subset in subsets.items():

            if len(subset) == 0:
                continue

            matched_count_rows.append({
                "dataset":
                    dataset,

                "class_a":
                    class_a,

                "class_b":
                    class_b,

                "subset":
                    subset_name,

                "n_samples":
                    len(subset),

                "n_class_a":
                    int(
                        (
                            subset["class"]
                            == class_a
                        ).sum()
                    ),

                "n_class_b":
                    int(
                        (
                            subset["class"]
                            == class_b
                        ).sum()
                    ),

                "n_tiles":
                    subset[
                        "tile"
                    ].nunique(),
            })

            result_rows = evaluate_subset(
                subset,
                dataset,
                class_a,
                class_b,
                subset_name,
            )

            all_results.extend(
                result_rows
            )

            print()
            print(
                dataset,
                class_a,
                "vs",
                class_b,
                subset_name,
                f"n={len(subset)}",
                flush=True,
            )

            for row in result_rows:
                print(
                    "   ",
                    f"{row['feature_set']:28s}",
                    f"BAcc={row['balanced_acc_mean']:.4f}",
                    f"AUC={row['auc_mean']:.4f}",
                    flush=True,
                )


counts_df = pd.DataFrame(
    matched_count_rows
)

counts_df.to_csv(
    OUT_DIR
    / "subset_counts.csv",
    index=False,
)


results_df = pd.DataFrame(
    all_results
)

results_df.to_csv(
    OUT_DIR
    / "classification_results.csv",
    index=False,
)


# ============================================================
# Compact table for interpretation
# ============================================================

if len(results_df):

    compact = results_df.pivot_table(
        index=[
            "dataset",
            "class_a",
            "class_b",
            "subset",
        ],
        columns="feature_set",
        values="balanced_acc_mean",
        aggfunc="mean",
    ).reset_index()

    for col in [
        "DSM_abs_only",
        "DSM_geometry",
        "Optical_only",
        "DSM_geometry_plus_Optical",
    ]:
        if col not in compact.columns:
            compact[col] = np.nan

    compact[
        "Optical_minus_DSMgeom"
    ] = (
        compact[
            "Optical_only"
        ]
        -
        compact[
            "DSM_geometry"
        ]
    )

    compact[
        "Combined_minus_DSMgeom"
    ] = (
        compact[
            "DSM_geometry_plus_Optical"
        ]
        -
        compact[
            "DSM_geometry"
        ]
    )

    compact.to_csv(
        OUT_DIR
        / "semantic_ambiguity_summary.csv",
        index=False,
    )

else:

    compact = pd.DataFrame()


# ============================================================
# Audit metadata
# ============================================================

metadata = {
    "seed":
        SEED,

    "train_tiles_only":
        True,

    "label":
        "ISPRS noBoundary / eroded labels",

    "ignored_label_color":
        [0, 0, 0],

    "max_samples_per_class_per_tile":
        MAX_PER_CLASS_PER_TILE,

    "absolute_dsm_bin_m":
        ABS_DSM_BIN_M,

    "local_support_m":
        LOCAL_SUPPORT_M,

    "geometry_quantile_bins":
        GEOM_QUANTILE_BINS,

    "matching": {
        "FULL":
            "No matching.",

        "ABS_DSM_MATCHED":
            "Class-balanced matching within the same tile "
            "and 0.5 m raw DSM value bins.",

        "LOCAL_GEOM_MATCHED":
            "Class-balanced matching within the same tile "
            "and joint quantile cells of local-relative DSM, "
            "DSM roughness, and DSM gradient.",
    },

    "important_caveat":
        "Raw DSM is surface elevation, not normalized object height. "
        "Therefore raw DSM matching is interpreted only as elevation-value "
        "ambiguity. LOCAL_GEOM_MATCHED is the main semantic-disambiguation "
        "analysis.",

    "metric_interpretation": {
        "balanced_accuracy":
            "0.5 is approximately chance for binary classification.",

        "overlap_coefficient":
            "1 indicates highly overlapping feature distributions.",

        "jsd_bits":
            "0 indicates identical distributions; larger values mean "
            "greater separation.",
    },
}


(
    OUT_DIR
    / "audit_config.json"
).write_text(
    json.dumps(
        metadata,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


print()
print("=" * 110)
print("FINAL SEMANTIC AMBIGUITY SUMMARY")
print("=" * 110)

if len(compact):
    print(
        compact.to_string(
            index=False
        )
    )

print()
print(
    "OUTPUT:",
    OUT_DIR.resolve()
)

print(
    "DSM SEMANTIC AMBIGUITY AUDIT V2 COMPLETE"
)
