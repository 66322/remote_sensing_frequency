from pathlib import Path
import json
import zlib

import numpy as np
import pandas as pd
import tifffile

from scipy.ndimage import gaussian_filter, zoom
from scipy.spatial.distance import jensenshannon
from scipy.stats import wilcoxon


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

DATA_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped"
)

OUT = (
    ROOT
    / "records"
    / "e51a_synthetic_gsd_physical_frequency_20260914"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


TRAIN_TILES = [
    "6_10",
    "7_10",
    "2_12",
    "3_11",
    "2_10",
    "7_8",
    "5_10",
    "3_12",
    "5_12",
    "7_11",
    "7_9",
    "6_9",
    "7_7",
    "4_12",
    "6_8",
    "6_12",
    "6_7",
    "4_11",
]


SEED = 42

NATIVE_GSD_M = 0.05

TARGET_GSDS_M = [
    0.05,
    0.07,
    0.09,
]

PATCH_SIZE_NATIVE = 512

PATCHES_PER_TILE = 8

BORDER_MARGIN_M = 2.0


# ------------------------------------------------------------
# Pixel-coordinate frequency scales.
#
# Fixed regardless of GSD.
# These are continuous Gaussian equivalents used only for
# the mechanism audit.
# ------------------------------------------------------------

PIXEL_SIGMAS = np.array(
    [
        1.5,
        3.5,
        7.5,
        15.5,
    ],
    dtype=np.float64,
)


# ------------------------------------------------------------
# Physical-coordinate scales.
#
# Anchor them to the native 5-cm sampling.
#
# 1.5 px * 0.05 m = 0.075 m
# 3.5 px * 0.05 m = 0.175 m
# etc.
#
# At another GSD:
#
# sigma_px = sigma_m / GSD
#
# Therefore the real physical support stays fixed.
# ------------------------------------------------------------

PHYSICAL_SIGMAS_M = (
    PIXEL_SIGMAS
    * NATIVE_GSD_M
)


EPS = 1e-12


# ============================================================
# PATHS
# ============================================================

def optical_path(tile):
    return (
        DATA_ROOT
        / "2_Ortho_RGB"
        / f"top_potsdam_{tile}_RGB.tif"
    )


def dsm_path(tile):
    a, b = tile.split("_")

    return (
        DATA_ROOT
        / "1_DSM"
        / "1_DSM"
        / f"dsm_potsdam_{int(a):02d}_{int(b):02d}.tif"
    )


# ============================================================
# DETERMINISTIC RNG
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


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_optical(x):
    x = x.astype(
        np.float32,
        copy=False,
    )

    out = np.empty_like(
        x,
        dtype=np.float32,
    )

    for c in range(
        x.shape[2]
    ):
        ch = x[
            ...,
            c
        ]

        lo, hi = np.percentile(
            ch,
            [
                1.0,
                99.0,
            ],
        )

        if not np.isfinite(lo):
            lo = 0.0

        if (
            not np.isfinite(hi)
            or hi <= lo
        ):
            hi = lo + 1.0

        y = (
            ch - lo
        ) / (
            hi - lo
        )

        out[
            ...,
            c
        ] = np.clip(
            y,
            0.0,
            1.0,
        )

    return out


def normalize_dsm(x):
    x = x.astype(
        np.float32,
        copy=True,
    )

    valid = np.isfinite(
        x
    )

    if not valid.any():
        return np.zeros_like(
            x,
            dtype=np.float32,
        )

    med = np.median(
        x[
            valid
        ]
    )

    q25, q75 = np.percentile(
        x[
            valid
        ],
        [
            25.0,
            75.0,
        ],
    )

    scale = (
        q75
        - q25
    )

    if (
        not np.isfinite(scale)
        or scale < 1e-6
    ):
        scale = np.std(
            x[
                valid
            ]
        )

    if (
        not np.isfinite(scale)
        or scale < 1e-6
    ):
        scale = 1.0

    x[
        ~valid
    ] = med

    x = (
        x - med
    ) / scale

    return x.astype(
        np.float32
    )


# ============================================================
# SYNTHETIC GSD RESAMPLING
# ============================================================

def antialias_sigma(
    native_gsd,
    target_gsd,
):
    if target_gsd <= native_gsd:
        return 0.0

    ratio = (
        native_gsd
        / target_gsd
    )

    # Mild anti-aliasing before downsampling.
    return max(
        0.0,
        0.5
        * (
            1.0 / ratio
            - 1.0
        ),
    )


def resample_patch(
    x,
    native_gsd,
    target_gsd,
):
    if abs(
        target_gsd
        - native_gsd
    ) < 1e-12:
        return x.copy()

    factor = (
        native_gsd
        / target_gsd
    )

    sigma = antialias_sigma(
        native_gsd,
        target_gsd,
    )

    if x.ndim == 3:

        if sigma > 0:
            x = gaussian_filter(
                x,
                sigma=(
                    sigma,
                    sigma,
                    0.0,
                ),
                mode="reflect",
            )

        y = zoom(
            x,
            zoom=(
                factor,
                factor,
                1.0,
            ),
            order=1,
            mode="reflect",
            prefilter=False,
        )

    else:

        if sigma > 0:
            x = gaussian_filter(
                x,
                sigma=sigma,
                mode="reflect",
            )

        y = zoom(
            x,
            zoom=(
                factor,
                factor,
            ),
            order=1,
            mode="reflect",
            prefilter=False,
        )

    return y.astype(
        np.float32,
        copy=False,
    )


# ============================================================
# FREQUENCY PROFILE
# ============================================================

def inner_view(
    x,
    margin_px,
):
    h, w = x.shape[
        :2
    ]

    m = int(
        margin_px
    )

    max_m = max(
        0,
        min(
            h,
            w,
        ) // 4
    )

    m = min(
        m,
        max_m,
    )

    if m <= 0:
        return x

    return x[
        m:-m,
        m:-m,
        ...
    ]


def frequency_profile(
    x,
    sigmas_px,
    margin_px,
):
    prev = x

    energies = []

    for sigma in sigmas_px:

        if x.ndim == 3:
            low = gaussian_filter(
                x,
                sigma=(
                    float(sigma),
                    float(sigma),
                    0.0,
                ),
                mode="reflect",
            )

        else:
            low = gaussian_filter(
                x,
                sigma=float(
                    sigma
                ),
                mode="reflect",
            )

        band = (
            prev
            - low
        )

        band_inner = inner_view(
            band,
            margin_px,
        )

        energy = float(
            np.mean(
                np.abs(
                    band_inner
                )
            )
        )

        energies.append(
            energy
        )

        prev = low

    energies = np.asarray(
        energies,
        dtype=np.float64,
    )

    profile = (
        energies
        + EPS
    ) / (
        energies.sum()
        + EPS
        * len(
            energies
        )
    )

    return (
        energies,
        profile,
    )


# ============================================================
# JSD
# ============================================================

def jsd_bits(
    p,
    q,
):
    p = np.asarray(
        p,
        dtype=np.float64,
    )

    q = np.asarray(
        q,
        dtype=np.float64,
    )

    p = (
        p + EPS
    ) / (
        p.sum()
        + EPS
        * len(p)
    )

    q = (
        q + EPS
    ) / (
        q.sum()
        + EPS
        * len(q)
    )

    d = jensenshannon(
        p,
        q,
        base=2,
    )

    return float(
        d * d
    )


# ============================================================
# PATCH SAMPLING
# ============================================================

def patch_locations(
    h,
    w,
    tile,
):
    rng = deterministic_rng(
        "PATCH",
        tile,
    )

    max_y = (
        h
        - PATCH_SIZE_NATIVE
    )

    max_x = (
        w
        - PATCH_SIZE_NATIVE
    )

    if (
        max_y < 0
        or max_x < 0
    ):
        raise RuntimeError(
            f"Tile too small: "
            f"{tile} "
            f"{h}x{w}"
        )

    coords = []

    for i in range(
        PATCHES_PER_TILE
    ):

        y = int(
            rng.integers(
                0,
                max_y + 1,
            )
        )

        x = int(
            rng.integers(
                0,
                max_x + 1,
            )
        )

        coords.append(
            (
                i,
                y,
                x,
            )
        )

    return coords


# ============================================================
# MAIN EXTRACTION
# ============================================================

records = []


print(
    "=" * 110,
    flush=True,
)

print(
    "E51-A SYNTHETIC-GSD PHYSICAL-FREQUENCY AUDIT",
    flush=True,
)

print(
    "native GSD:",
    NATIVE_GSD_M,
    "m",
    flush=True,
)

print(
    "target GSDs:",
    TARGET_GSDS_M,
    flush=True,
)

print(
    "pixel sigmas:",
    PIXEL_SIGMAS.tolist(),
    flush=True,
)

print(
    "physical sigmas (m):",
    PHYSICAL_SIGMAS_M.tolist(),
    flush=True,
)

print(
    "=" * 110,
    flush=True,
)


for tile_idx, tile in enumerate(
    TRAIN_TILES,
    start=1,
):

    op = optical_path(
        tile
    )

    dp = dsm_path(
        tile
    )

    if not op.exists():
        raise FileNotFoundError(
            op
        )

    if not dp.exists():
        raise FileNotFoundError(
            dp
        )

    print()
    print(
        f"[{tile_idx:02d}/{len(TRAIN_TILES):02d}]",
        tile,
        flush=True,
    )

    print(
        "  read optical:",
        op,
        flush=True,
    )

    opt = tifffile.imread(
        op
    )

    print(
        "  read DSM:",
        dp,
        flush=True,
    )

    dsm = tifffile.imread(
        dp
    )

    if opt.ndim != 3:
        raise RuntimeError(
            f"Unexpected optical shape "
            f"{tile}: {opt.shape}"
        )

    if dsm.ndim != 2:
        raise RuntimeError(
            f"Unexpected DSM shape "
            f"{tile}: {dsm.shape}"
        )

    if opt.shape[:2] != dsm.shape:
        raise RuntimeError(
            f"Shape mismatch "
            f"{tile}: "
            f"{opt.shape} vs {dsm.shape}"
        )

    h, w = dsm.shape

    coords = patch_locations(
        h,
        w,
        tile,
    )

    for (
        patch_idx,
        y,
        x,
    ) in coords:

        patch_id = (
            f"{tile}_p"
            f"{patch_idx:02d}"
        )

        opt_patch = opt[
            y:
            y + PATCH_SIZE_NATIVE,
            x:
            x + PATCH_SIZE_NATIVE,
            :,
        ]

        dsm_patch = dsm[
            y:
            y + PATCH_SIZE_NATIVE,
            x:
            x + PATCH_SIZE_NATIVE,
        ]

        opt_patch = normalize_optical(
            opt_patch
        )

        dsm_patch = normalize_dsm(
            dsm_patch
        )

        for target_gsd in TARGET_GSDS_M:

            opt_g = resample_patch(
                opt_patch,
                NATIVE_GSD_M,
                target_gsd,
            )

            dsm_g = resample_patch(
                dsm_patch,
                NATIVE_GSD_M,
                target_gsd,
            )

            margin_px = int(
                np.ceil(
                    BORDER_MARGIN_M
                    / target_gsd
                )
            )

            schemes = {
                "pixel": (
                    PIXEL_SIGMAS
                ),

                "physical": (
                    PHYSICAL_SIGMAS_M
                    / target_gsd
                ),
            }

            for scheme, sigmas_px in schemes.items():

                for (
                    modality,
                    arr,
                ) in [
                    (
                        "optical",
                        opt_g,
                    ),
                    (
                        "dsm",
                        dsm_g,
                    ),
                ]:

                    (
                        energies,
                        profile,
                    ) = frequency_profile(
                        arr,
                        sigmas_px,
                        margin_px,
                    )

                    row = {
                        "tile":
                            tile,

                        "patch_id":
                            patch_id,

                        "patch_y":
                            y,

                        "patch_x":
                            x,

                        "target_gsd_m":
                            target_gsd,

                        "scheme":
                            scheme,

                        "modality":
                            modality,

                        "height_px":
                            arr.shape[0],

                        "width_px":
                            arr.shape[1],

                        "sigma1_px":
                            sigmas_px[0],

                        "sigma2_px":
                            sigmas_px[1],

                        "sigma3_px":
                            sigmas_px[2],

                        "sigma4_px":
                            sigmas_px[3],

                        "energy_total":
                            float(
                                energies.sum()
                            ),
                    }

                    for k in range(
                        4
                    ):
                        row[
                            f"energy_b{k+1}"
                        ] = float(
                            energies[k]
                        )

                        row[
                            f"profile_b{k+1}"
                        ] = float(
                            profile[k]
                        )

                    records.append(
                        row
                    )

        print(
            f"  patch "
            f"{patch_idx + 1}/"
            f"{PATCHES_PER_TILE} "
            f"done",
            flush=True,
        )

    del opt
    del dsm


profiles = pd.DataFrame(
    records
)

profiles.to_csv(
    OUT
    / "patch_frequency_profiles.csv",
    index=False,
)


# ============================================================
# MODALITY PROFILE DRIFT
# ============================================================

PROFILE_COLS = [
    "profile_b1",
    "profile_b2",
    "profile_b3",
    "profile_b4",
]


drift_rows = []


for modality in [
    "optical",
    "dsm",
]:

    for scheme in [
        "pixel",
        "physical",
    ]:

        native = profiles[
            (
                profiles[
                    "modality"
                ]
                == modality
            )
            &
            (
                profiles[
                    "scheme"
                ]
                == scheme
            )
            &
            np.isclose(
                profiles[
                    "target_gsd_m"
                ],
                NATIVE_GSD_M,
            )
        ].copy()

        native = native.set_index(
            "patch_id"
        )

        for target_gsd in TARGET_GSDS_M:

            if np.isclose(
                target_gsd,
                NATIVE_GSD_M,
            ):
                continue

            target = profiles[
                (
                    profiles[
                        "modality"
                    ]
                    == modality
                )
                &
                (
                    profiles[
                        "scheme"
                    ]
                    == scheme
                )
                &
                np.isclose(
                    profiles[
                        "target_gsd_m"
                    ],
                    target_gsd,
                )
            ].copy()

            target = target.set_index(
                "patch_id"
            )

            common = sorted(
                set(
                    native.index
                ).intersection(
                    target.index
                )
            )

            for patch_id in common:

                p = native.loc[
                    patch_id,
                    PROFILE_COLS,
                ].to_numpy(
                    dtype=np.float64
                )

                q = target.loc[
                    patch_id,
                    PROFILE_COLS,
                ].to_numpy(
                    dtype=np.float64
                )

                drift_rows.append({
                    "patch_id":
                        patch_id,

                    "modality":
                        modality,

                    "scheme":
                        scheme,

                    "target_gsd_m":
                        target_gsd,

                    "jsd_bits":
                        jsd_bits(
                            p,
                            q,
                        ),

                    "l1_profile_drift":
                        float(
                            np.abs(
                                p - q
                            ).sum()
                        ),
                })


drifts = pd.DataFrame(
    drift_rows
)

drifts.to_csv(
    OUT
    / "paired_profile_drift.csv",
    index=False,
)


drift_summary = (
    drifts
    .groupby(
        [
            "modality",
            "scheme",
            "target_gsd_m",
        ],
        as_index=False,
    )
    .agg(
        n=(
            "patch_id",
            "count",
        ),

        jsd_mean=(
            "jsd_bits",
            "mean",
        ),

        jsd_median=(
            "jsd_bits",
            "median",
        ),

        l1_mean=(
            "l1_profile_drift",
            "mean",
        ),

        l1_median=(
            "l1_profile_drift",
            "median",
        ),
    )
)

drift_summary.to_csv(
    OUT
    / "profile_drift_summary.csv",
    index=False,
)


# ============================================================
# PIXEL VS PHYSICAL PAIRED TEST
# ============================================================

compare_rows = []


for modality in [
    "optical",
    "dsm",
]:

    for target_gsd in TARGET_GSDS_M:

        if np.isclose(
            target_gsd,
            NATIVE_GSD_M,
        ):
            continue

        sub = drifts[
            (
                drifts[
                    "modality"
                ]
                == modality
            )
            &
            np.isclose(
                drifts[
                    "target_gsd_m"
                ],
                target_gsd,
            )
        ]

        pivot = sub.pivot(
            index="patch_id",
            columns="scheme",
            values="jsd_bits",
        ).dropna()

        pixel = pivot[
            "pixel"
        ].to_numpy(
            dtype=np.float64
        )

        physical = pivot[
            "physical"
        ].to_numpy(
            dtype=np.float64
        )

        try:
            stat, pvalue = wilcoxon(
                physical,
                pixel,
                alternative="less",
            )

            stat = float(
                stat
            )

            pvalue = float(
                pvalue
            )

        except Exception:
            stat = np.nan
            pvalue = np.nan

        compare_rows.append({
            "modality":
                modality,

            "target_gsd_m":
                target_gsd,

            "n":
                len(
                    pivot
                ),

            "pixel_jsd_mean":
                float(
                    pixel.mean()
                ),

            "physical_jsd_mean":
                float(
                    physical.mean()
                ),

            "physical_over_pixel_ratio":
                float(
                    physical.mean()
                    / (
                        pixel.mean()
                        + EPS
                    )
                ),

            "physical_reduction_pct":
                float(
                    (
                        1.0
                        -
                        physical.mean()
                        / (
                            pixel.mean()
                            + EPS
                        )
                    )
                    * 100.0
                ),

            "physical_win_rate":
                float(
                    np.mean(
                        physical
                        < pixel
                    )
                ),

            "wilcoxon_stat":
                stat,

            "wilcoxon_p_less":
                pvalue,
        })


compare_df = pd.DataFrame(
    compare_rows
)

compare_df.to_csv(
    OUT
    / "pixel_vs_physical_paired_test.csv",
    index=False,
)


# ============================================================
# CROSS-MODAL DISCREPANCY DRIFT
#
# We compare:
#
#   D = Optical profile - DSM profile
#
# at native GSD versus the same patch after synthetic GSD
# change.
#
# This is directly related to frequency-discrepancy-based
# reliability.
# ============================================================

cross_rows = []


for scheme in [
    "pixel",
    "physical",
]:

    native_opt = profiles[
        (
            profiles[
                "scheme"
            ]
            == scheme
        )
        &
        (
            profiles[
                "modality"
            ]
            == "optical"
        )
        &
        np.isclose(
            profiles[
                "target_gsd_m"
            ],
            NATIVE_GSD_M,
        )
    ].set_index(
        "patch_id"
    )

    native_dsm = profiles[
        (
            profiles[
                "scheme"
            ]
            == scheme
        )
        &
        (
            profiles[
                "modality"
            ]
            == "dsm"
        )
        &
        np.isclose(
            profiles[
                "target_gsd_m"
            ],
            NATIVE_GSD_M,
        )
    ].set_index(
        "patch_id"
    )

    common_native = sorted(
        set(
            native_opt.index
        ).intersection(
            native_dsm.index
        )
    )

    native_discrepancy = {}

    for patch_id in common_native:

        po = native_opt.loc[
            patch_id,
            PROFILE_COLS,
        ].to_numpy(
            dtype=np.float64
        )

        pdsm = native_dsm.loc[
            patch_id,
            PROFILE_COLS,
        ].to_numpy(
            dtype=np.float64
        )

        native_discrepancy[
            patch_id
        ] = (
            po - pdsm
        )

    for target_gsd in TARGET_GSDS_M:

        if np.isclose(
            target_gsd,
            NATIVE_GSD_M,
        ):
            continue

        target_opt = profiles[
            (
                profiles[
                    "scheme"
                ]
                == scheme
            )
            &
            (
                profiles[
                    "modality"
                ]
                == "optical"
            )
            &
            np.isclose(
                profiles[
                    "target_gsd_m"
                ],
                target_gsd,
            )
        ].set_index(
            "patch_id"
        )

        target_dsm = profiles[
            (
                profiles[
                    "scheme"
                ]
                == scheme
            )
            &
            (
                profiles[
                    "modality"
                ]
                == "dsm"
            )
            &
            np.isclose(
                profiles[
                    "target_gsd_m"
                ],
                target_gsd,
            )
        ].set_index(
            "patch_id"
        )

        common = sorted(
            set(
                native_discrepancy
            )
            .intersection(
                target_opt.index
            )
            .intersection(
                target_dsm.index
            )
        )

        for patch_id in common:

            po = target_opt.loc[
                patch_id,
                PROFILE_COLS,
            ].to_numpy(
                dtype=np.float64
            )

            pdsm = target_dsm.loc[
                patch_id,
                PROFILE_COLS,
            ].to_numpy(
                dtype=np.float64
            )

            target_disc = (
                po - pdsm
            )

            native_disc = (
                native_discrepancy[
                    patch_id
                ]
            )

            cross_rows.append({
                "patch_id":
                    patch_id,

                "scheme":
                    scheme,

                "target_gsd_m":
                    target_gsd,

                "crossmodal_discrepancy_drift_l1":
                    float(
                        np.abs(
                            target_disc
                            - native_disc
                        ).sum()
                    ),
            })


cross = pd.DataFrame(
    cross_rows
)

cross.to_csv(
    OUT
    / "crossmodal_discrepancy_drift.csv",
    index=False,
)


cross_summary = (
    cross
    .groupby(
        [
            "scheme",
            "target_gsd_m",
        ],
        as_index=False,
    )
    .agg(
        n=(
            "patch_id",
            "count",
        ),

        mean_drift=(
            "crossmodal_discrepancy_drift_l1",
            "mean",
        ),

        median_drift=(
            "crossmodal_discrepancy_drift_l1",
            "median",
        ),
    )
)

cross_summary.to_csv(
    OUT
    / "crossmodal_discrepancy_drift_summary.csv",
    index=False,
)


cross_compare_rows = []


for target_gsd in TARGET_GSDS_M:

    if np.isclose(
        target_gsd,
        NATIVE_GSD_M,
    ):
        continue

    sub = cross[
        np.isclose(
            cross[
                "target_gsd_m"
            ],
            target_gsd,
        )
    ]

    pivot = sub.pivot(
        index="patch_id",
        columns="scheme",
        values="crossmodal_discrepancy_drift_l1",
    ).dropna()

    pixel = pivot[
        "pixel"
    ].to_numpy(
        dtype=np.float64
    )

    physical = pivot[
        "physical"
    ].to_numpy(
        dtype=np.float64
    )

    try:
        stat, pvalue = wilcoxon(
            physical,
            pixel,
            alternative="less",
        )

        stat = float(
            stat
        )

        pvalue = float(
            pvalue
        )

    except Exception:
        stat = np.nan
        pvalue = np.nan

    cross_compare_rows.append({
        "target_gsd_m":
            target_gsd,

        "n":
            len(
                pivot
            ),

        "pixel_mean":
            float(
                pixel.mean()
            ),

        "physical_mean":
            float(
                physical.mean()
            ),

        "physical_reduction_pct":
            float(
                (
                    1.0
                    -
                    physical.mean()
                    / (
                        pixel.mean()
                        + EPS
                    )
                )
                * 100.0
            ),

        "physical_win_rate":
            float(
                np.mean(
                    physical
                    < pixel
                )
            ),

        "wilcoxon_p_less":
            pvalue,
    })


cross_compare = pd.DataFrame(
    cross_compare_rows
)

cross_compare.to_csv(
    OUT
    / "crossmodal_pixel_vs_physical.csv",
    index=False,
)


# ============================================================
# CONFIG RECORD
# ============================================================

config = {
    "experiment":
        "E51-A synthetic GSD physical-frequency audit",

    "dataset":
        "Potsdam TRAIN18 only",

    "native_gsd_m":
        NATIVE_GSD_M,

    "target_gsds_m":
        TARGET_GSDS_M,

    "patch_size_native_px":
        PATCH_SIZE_NATIVE,

    "patches_per_tile":
        PATCHES_PER_TILE,

    "n_tiles":
        len(
            TRAIN_TILES
        ),

    "n_patches_expected":
        (
            len(
                TRAIN_TILES
            )
            * PATCHES_PER_TILE
        ),

    "pixel_sigmas_px":
        PIXEL_SIGMAS.tolist(),

    "physical_sigmas_m":
        PHYSICAL_SIGMAS_M.tolist(),

    "border_margin_m":
        BORDER_MARGIN_M,

    "note":
        (
            "Same physical scene patches are synthetically "
            "resampled from native 5 cm to 7 and 9 cm. "
            "Pixel scheme keeps sigma in pixels fixed. "
            "Physical scheme keeps sigma in meters fixed."
        ),
}

with (
    OUT
    / "audit_config.json"
).open(
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        config,
        f,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# FINAL PRINT
# ============================================================

print()
print(
    "=" * 120
)

print(
    "E51-A PROFILE DRIFT SUMMARY"
)

print(
    "=" * 120
)

print(
    drift_summary.to_string(
        index=False
    )
)


print()
print(
    "=" * 120
)

print(
    "PIXEL VS PHYSICAL — PAIRED JSD"
)

print(
    "=" * 120
)

print(
    compare_df.to_string(
        index=False
    )
)


print()
print(
    "=" * 120
)

print(
    "CROSS-MODAL DISCREPANCY DRIFT"
)

print(
    "=" * 120
)

print(
    cross_compare.to_string(
        index=False
    )
)


print()
print(
    "OUTPUT:",
    OUT.resolve(),
)

print(
    "E51-A AUDIT COMPLETE"
)
