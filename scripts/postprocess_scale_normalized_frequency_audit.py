import csv
import json
from pathlib import Path
from collections import defaultdict

import numpy as np


ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

IN_DIR = (
    ROOT
    / "records"
    / "physical_frequency_audit_20260913"
)

OUT_DIR = (
    ROOT
    / "records"
    / "physical_frequency_audit_scale_normalized_20260913"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


GSD = {
    "Vaihingen": 0.09,
    "Potsdam": 0.05,
}

PHYSICAL_SIGMA_M = [
    0.18,
    0.36,
    0.72,
    1.44,
    2.88,
]

PIXEL_SIGMA = [
    2.0,
    4.0,
    8.0,
    16.0,
    32.0,
]

CLASSES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
]

MODALITIES = [
    "DSM",
    "Optical_shared_RG",
    "Optical_native",
]

REGIONS = [
    "All",
    "Boundary",
    "Interior",
]


# ============================================================
# Discrete Gaussian / DoG filter norm
#
# Mirrors scipy gaussian_filter(..., truncate=4.0)
# sufficiently closely for response-energy normalization.
# ============================================================

def gaussian_1d(sigma, truncate=4.0):

    sigma = float(sigma)

    radius = int(
        truncate * sigma
        + 0.5
    )

    x = np.arange(
        -radius,
        radius + 1,
        dtype=np.float64,
    )

    g = np.exp(
        -0.5
        * (x / sigma) ** 2
    )

    g /= g.sum()

    return g


def gaussian_2d(sigma):

    g = gaussian_1d(
        sigma
    )

    return np.outer(
        g,
        g,
    )


def center_pad(kernel, radius):

    h, w = kernel.shape

    target = (
        2 * radius + 1
    )

    out = np.zeros(
        (target, target),
        dtype=np.float64,
    )

    y0 = (
        radius
        - h // 2
    )

    x0 = (
        radius
        - w // 2
    )

    out[
        y0:y0+h,
        x0:x0+w
    ] = kernel

    return out


def dog_norm2(
    sigma_low,
    sigma_high,
):

    high = gaussian_2d(
        sigma_high
    )

    high_radius = (
        high.shape[0]
        // 2
    )

    if sigma_low is None:

        low = np.zeros_like(
            high
        )

        low[
            high_radius,
            high_radius
        ] = 1.0

        dog = (
            low
            - high
        )

    else:

        low = gaussian_2d(
            sigma_low
        )

        low_radius = (
            low.shape[0]
            // 2
        )

        radius = max(
            low_radius,
            high_radius,
        )

        low = center_pad(
            low,
            radius,
        )

        high = center_pad(
            high,
            radius,
        )

        dog = (
            low
            - high
        )

    value = float(
        np.sum(
            dog * dog
        )
    )

    if value <= 0:
        raise RuntimeError(
            "Invalid DoG norm"
        )

    return value


def sigma_sequence(
    dataset,
    profile_type,
):

    if profile_type == "pixel":

        return [
            float(x)
            for x in PIXEL_SIGMA
        ]

    if profile_type == "physical":

        return [
            float(x) / GSD[dataset]
            for x in PHYSICAL_SIGMA_M
        ]

    raise ValueError(
        profile_type
    )


FILTER_NORM2 = {}

for dataset in GSD:

    for profile_type in [
        "pixel",
        "physical",
    ]:

        sigmas = sigma_sequence(
            dataset,
            profile_type,
        )

        previous = None

        for band_idx, current in enumerate(
            sigmas
        ):

            FILTER_NORM2[
                (
                    dataset,
                    profile_type,
                    band_idx,
                )
            ] = dog_norm2(
                previous,
                current,
            )

            previous = current


# ============================================================
# Utilities
# ============================================================

def normalize(values):

    x = np.asarray(
        values,
        dtype=np.float64,
    )

    x = np.clip(
        x,
        0.0,
        None,
    )

    total = float(
        x.sum()
    )

    if total <= 0:
        return np.zeros_like(
            x
        )

    return (
        x / total
    )


def jsd(p, q):

    p = normalize(p)
    q = normalize(q)

    eps = 1e-12

    p = np.clip(
        p,
        eps,
        None,
    )

    q = np.clip(
        q,
        eps,
        None,
    )

    p /= p.sum()
    q /= q.sum()

    m = (
        0.5
        * (p + q)
    )

    return float(
        0.5
        * np.sum(
            p
            * np.log2(
                p / m
            )
        )
        +
        0.5
        * np.sum(
            q
            * np.log2(
                q / m
            )
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

    np_ = float(
        np.linalg.norm(p)
    )

    nq_ = float(
        np.linalg.norm(q)
    )

    if np_ <= 0 or nq_ <= 0:
        return float("nan")

    return float(
        1.0
        - np.dot(p, q)
        / (np_ * nq_)
    )


# ============================================================
# Read original aggregated energies
# ============================================================

src = (
    IN_DIR
    / "frequency_energy_by_class.csv"
)

if not src.is_file():
    raise FileNotFoundError(
        src
    )

with src.open(
    "r",
    newline="",
    encoding="utf-8",
) as f:

    rows = list(
        csv.DictReader(f)
    )


profiles = defaultdict(
    lambda: np.zeros(
        5,
        dtype=np.float64,
    )
)

out_rows = []

for r in rows:

    dataset = r[
        "dataset"
    ]

    profile_type = r[
        "profile_type"
    ]

    modality = r[
        "modality"
    ]

    cls = r[
        "class"
    ]

    region = r[
        "region"
    ]

    band_idx = int(
        r["band_idx"]
    )

    original_energy = float(
        r["mean_energy"]
    )

    norm2 = FILTER_NORM2[
        (
            dataset,
            profile_type,
            band_idx,
        )
    ]

    corrected = (
        original_energy
        / norm2
    )

    key = (
        dataset,
        profile_type,
        modality,
        cls,
        region,
    )

    profiles[key][
        band_idx
    ] = corrected

    out = dict(r)

    out[
        "filter_l2_norm2"
    ] = norm2

    out[
        "scale_normalized_mean_energy"
    ] = corrected

    out_rows.append(
        out
    )


# Add normalized fractions after all bands are known.

fraction_lookup = {}

for key, values in profiles.items():

    p = normalize(
        values
    )

    for i in range(5):

        fraction_lookup[
            key + (i,)
        ] = float(
            p[i]
        )


for r in out_rows:

    key = (
        r["dataset"],
        r["profile_type"],
        r["modality"],
        r["class"],
        r["region"],
        int(
            r["band_idx"]
        ),
    )

    r[
        "scale_normalized_fraction"
    ] = fraction_lookup[
        key
    ]


# ============================================================
# Save corrected energy
# ============================================================

out_energy = (
    OUT_DIR
    / "frequency_energy_scale_normalized.csv"
)

with out_energy.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            out_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        out_rows
    )


# ============================================================
# Dominant bands
# ============================================================

dominant_rows = []

for key, values in profiles.items():

    (
        dataset,
        profile_type,
        modality,
        cls,
        region,
    ) = key

    p = normalize(
        values
    )

    idx = int(
        np.argmax(p)
    )

    dominant_rows.append({
        "dataset":
            dataset,

        "profile_type":
            profile_type,

        "modality":
            modality,

        "class":
            cls,

        "region":
            region,

        "dominant_band_idx":
            idx,

        "dominant_fraction":
            float(
                p[idx]
            ),
    })


dominant_csv = (
    OUT_DIR
    / "dominant_scale_normalized.csv"
)

with dominant_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            dominant_rows[
                0
            ].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        dominant_rows
    )


# ============================================================
# Cross-dataset distances
# ============================================================

distance_rows = []

for modality in MODALITIES:

    for cls in CLASSES:

        for region in REGIONS:

            row = {
                "modality":
                    modality,

                "class":
                    cls,

                "region":
                    region,
            }

            valid = True

            for profile_type in [
                "pixel",
                "physical",
            ]:

                vk = (
                    "Vaihingen",
                    profile_type,
                    modality,
                    cls,
                    region,
                )

                pk = (
                    "Potsdam",
                    profile_type,
                    modality,
                    cls,
                    region,
                )

                if (
                    vk not in profiles
                    or pk not in profiles
                ):
                    valid = False
                    break

                vp = normalize(
                    profiles[vk]
                )

                pp = normalize(
                    profiles[pk]
                )

                row[
                    f"jsd_{profile_type}"
                ] = jsd(
                    vp,
                    pp,
                )

                row[
                    f"cosdist_{profile_type}"
                ] = cosine_distance(
                    vp,
                    pp,
                )

            if not valid:
                continue

            row[
                "jsd_improvement_pixel_minus_physical"
            ] = (
                row[
                    "jsd_pixel"
                ]
                - row[
                    "jsd_physical"
                ]
            )

            row[
                "comparison_validity"
            ] = (
                "PRIMARY_COMPARABLE"
                if modality in {
                    "DSM",
                    "Optical_shared_RG",
                }
                else
                "SECONDARY_SPECTRAL_MISMATCH"
            )

            distance_rows.append(
                row
            )


distance_csv = (
    OUT_DIR
    / "cross_dataset_distance_scale_normalized.csv"
)

with distance_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            distance_rows[
                0
            ].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        distance_rows
    )


# ============================================================
# Boundary vs interior
# ============================================================

boundary_rows = []

for dataset in GSD:

    for modality in [
        "DSM",
        "Optical_shared_RG",
    ]:

        for cls in CLASSES:

            bk = (
                dataset,
                "physical",
                modality,
                cls,
                "Boundary",
            )

            ik = (
                dataset,
                "physical",
                modality,
                cls,
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

                "modality":
                    modality,

                "class":
                    cls,

                "jsd":
                    jsd(
                        profiles[bk],
                        profiles[ik],
                    ),

                "cosdist":
                    cosine_distance(
                        profiles[bk],
                        profiles[ik],
                    ),
            })


boundary_csv = (
    OUT_DIR
    / "boundary_vs_interior_scale_normalized.csv"
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


# ============================================================
# Optical vs DSM
# ============================================================

modality_rows = []

for dataset in GSD:

    for cls in CLASSES:

        for region in REGIONS:

            ok = (
                dataset,
                "physical",
                "Optical_shared_RG",
                cls,
                region,
            )

            dk = (
                dataset,
                "physical",
                "DSM",
                cls,
                region,
            )

            if (
                ok not in profiles
                or dk not in profiles
            ):
                continue

            modality_rows.append({
                "dataset":
                    dataset,

                "class":
                    cls,

                "region":
                    region,

                "jsd":
                    jsd(
                        profiles[ok],
                        profiles[dk],
                    ),

                "cosdist":
                    cosine_distance(
                        profiles[ok],
                        profiles[dk],
                    ),
            })


modality_csv = (
    OUT_DIR
    / "modality_difference_scale_normalized.csv"
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


# ============================================================
# Summary
# ============================================================

primary_all = [
    r
    for r in distance_rows
    if (
        r[
            "comparison_validity"
        ]
        == "PRIMARY_COMPARABLE"
        and r["region"] == "All"
    )
]

boundary_values = [
    r["jsd"]
    for r in boundary_rows
]

modality_all = [
    r["jsd"]
    for r in modality_rows
    if r["region"] == "All"
]

mean_pixel = float(
    np.mean([
        r["jsd_pixel"]
        for r in primary_all
    ])
)

mean_physical = float(
    np.mean([
        r["jsd_physical"]
        for r in primary_all
    ])
)

improved = sum(
    r[
        "jsd_improvement_pixel_minus_physical"
    ] > 0
    for r in primary_all
)

summary = {
    "status":
        "PASS",

    "method":
        (
            "Post-hoc discrete DoG filter L2-energy "
            "normalization; no image reprocessing."
        ),

    "mean_crossdataset_jsd_pixel":
        mean_pixel,

    "mean_crossdataset_jsd_physical":
        mean_physical,

    "pixel_minus_physical":
        (
            mean_pixel
            - mean_physical
        ),

    "physical_alignment_improved":
        f"{improved}/{len(primary_all)}",

    "mean_boundary_vs_interior_jsd":
        float(
            np.mean(
                boundary_values
            )
        ),

    "max_boundary_vs_interior_jsd":
        float(
            np.max(
                boundary_values
            )
        ),

    "mean_optical_vs_dsm_jsd":
        float(
            np.mean(
                modality_all
            )
        ),

    "max_optical_vs_dsm_jsd":
        float(
            np.max(
                modality_all
            )
        ),
}

summary_path = (
    OUT_DIR
    / "summary.json"
)

summary_path.write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# ============================================================
# Print compact evidence
# ============================================================

print("=" * 100)
print("SCALE-NORMALIZED FREQUENCY SANITY AUDIT")
print("=" * 100)

print(
    "Cross-dataset JSD | pixel    =",
    f"{mean_pixel:.8f}",
)

print(
    "Cross-dataset JSD | physical =",
    f"{mean_physical:.8f}",
)

print(
    "pixel - physical             =",
    f"{mean_pixel - mean_physical:+.8f}",
)

print(
    "physical profiles improved  =",
    f"{improved}/{len(primary_all)}",
)

print()

print(
    "mean Boundary-vs-Interior JSD =",
    f"{np.mean(boundary_values):.8f}",
)

print(
    "max  Boundary-vs-Interior JSD =",
    f"{np.max(boundary_values):.8f}",
)

print()

print(
    "mean Optical-vs-DSM JSD       =",
    f"{np.mean(modality_all):.8f}",
)

print(
    "max  Optical-vs-DSM JSD       =",
    f"{np.max(modality_all):.8f}",
)

print()

print(
    "ratio Modality / Boundary     =",
    f"{np.mean(modality_all) / np.mean(boundary_values):.4f}",
)

print()
print("Outputs:")

for p in [
    out_energy,
    dominant_csv,
    distance_csv,
    boundary_csv,
    modality_csv,
    summary_path,
]:
    print(" ", p)
