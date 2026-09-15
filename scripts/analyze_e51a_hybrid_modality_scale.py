from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


ROOT = Path(
    "records/e51a_synthetic_gsd_physical_frequency_20260914"
)

INPUT = ROOT / "patch_frequency_profiles.csv"

OUT_DETAIL = ROOT / "hybrid_crossmodal_drift.csv"
OUT_SUMMARY = ROOT / "hybrid_crossmodal_drift_summary.csv"
OUT_COMPARE = ROOT / "hybrid_vs_pixel_paired_test.csv"

NATIVE_GSD = 0.05
TARGET_GSDS = [0.07, 0.09]

PROFILE_COLS = [
    "profile_b1",
    "profile_b2",
    "profile_b3",
    "profile_b4",
]

SCHEMES = {
    "PP_pixelOpt_pixelDSM": (
        "pixel",
        "pixel",
    ),

    "HH_physOpt_physDSM": (
        "physical",
        "physical",
    ),

    "PH_pixelOpt_physDSM": (
        "pixel",
        "physical",
    ),

    "HP_physOpt_pixelDSM": (
        "physical",
        "pixel",
    ),
}


df = pd.read_csv(
    INPUT
)


def get_table(
    modality,
    scheme,
    gsd,
):
    x = df[
        (df["modality"] == modality)
        &
        (df["scheme"] == scheme)
        &
        np.isclose(
            df["target_gsd_m"],
            gsd,
        )
    ].copy()

    return x.set_index(
        "patch_id"
    )


# At native 5 cm, pixel and physical supports are identical
# by construction, so use pixel/pixel native discrepancy
# as the common reference.

native_opt = get_table(
    "optical",
    "pixel",
    NATIVE_GSD,
)

native_dsm = get_table(
    "dsm",
    "pixel",
    NATIVE_GSD,
)

native_ids = sorted(
    set(native_opt.index)
    .intersection(
        native_dsm.index
    )
)


native_disc = {}

for patch_id in native_ids:

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

    native_disc[
        patch_id
    ] = (
        po - pdsm
    )


rows = []


for target_gsd in TARGET_GSDS:

    for (
        hybrid_name,
        (
            opt_scheme,
            dsm_scheme,
        ),
    ) in SCHEMES.items():

        target_opt = get_table(
            "optical",
            opt_scheme,
            target_gsd,
        )

        target_dsm = get_table(
            "dsm",
            dsm_scheme,
            target_gsd,
        )

        common = sorted(
            set(native_disc)
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

            drift = float(
                np.abs(
                    target_disc
                    -
                    native_disc[
                        patch_id
                    ]
                ).sum()
            )

            rows.append({
                "patch_id":
                    patch_id,

                "target_gsd_m":
                    target_gsd,

                "hybrid":
                    hybrid_name,

                "optical_scheme":
                    opt_scheme,

                "dsm_scheme":
                    dsm_scheme,

                "drift_l1":
                    drift,
            })


detail = pd.DataFrame(
    rows
)

detail.to_csv(
    OUT_DETAIL,
    index=False,
)


summary = (
    detail
    .groupby(
        [
            "target_gsd_m",
            "hybrid",
            "optical_scheme",
            "dsm_scheme",
        ],
        as_index=False,
    )
    .agg(
        n=(
            "patch_id",
            "count",
        ),

        mean_drift=(
            "drift_l1",
            "mean",
        ),

        median_drift=(
            "drift_l1",
            "median",
        ),

        std_drift=(
            "drift_l1",
            "std",
        ),
    )
)


# Normalize relative to PP baseline
for gsd in TARGET_GSDS:

    mask = np.isclose(
        summary[
            "target_gsd_m"
        ],
        gsd,
    )

    baseline = summary[
        mask
        &
        (
            summary["hybrid"]
            ==
            "PP_pixelOpt_pixelDSM"
        )
    ][
        "mean_drift"
    ].iloc[0]

    summary.loc[
        mask,
        "reduction_vs_PP_pct",
    ] = (
        1.0
        -
        summary.loc[
            mask,
            "mean_drift",
        ]
        / baseline
    ) * 100.0


summary.to_csv(
    OUT_SUMMARY,
    index=False,
)


# ============================================================
# Paired tests against PP
# ============================================================

compare_rows = []


for gsd in TARGET_GSDS:

    sub = detail[
        np.isclose(
            detail[
                "target_gsd_m"
            ],
            gsd,
        )
    ]

    pivot = sub.pivot(
        index="patch_id",
        columns="hybrid",
        values="drift_l1",
    ).dropna()

    pp = pivot[
        "PP_pixelOpt_pixelDSM"
    ].to_numpy(
        dtype=np.float64
    )

    for hybrid in [
        "HH_physOpt_physDSM",
        "PH_pixelOpt_physDSM",
        "HP_physOpt_pixelDSM",
    ]:

        x = pivot[
            hybrid
        ].to_numpy(
            dtype=np.float64
        )

        try:
            stat, pvalue = wilcoxon(
                x,
                pp,
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
            "target_gsd_m":
                gsd,

            "hybrid":
                hybrid,

            "n":
                len(pivot),

            "PP_mean":
                float(
                    pp.mean()
                ),

            "hybrid_mean":
                float(
                    x.mean()
                ),

            "reduction_vs_PP_pct":
                float(
                    (
                        1.0
                        -
                        x.mean()
                        / pp.mean()
                    )
                    * 100.0
                ),

            "win_rate_vs_PP":
                float(
                    np.mean(
                        x < pp
                    )
                ),

            "wilcoxon_p_less":
                pvalue,
        })


compare = pd.DataFrame(
    compare_rows
)

compare.to_csv(
    OUT_COMPARE,
    index=False,
)


print()
print("=" * 110)
print("HYBRID CROSS-MODAL DRIFT SUMMARY")
print("=" * 110)

print(
    summary
    .sort_values(
        [
            "target_gsd_m",
            "mean_drift",
        ]
    )
    .to_string(
        index=False
    )
)


print()
print("=" * 110)
print("PAIRED TEST VS PP")
print("=" * 110)

print(
    compare
    .sort_values(
        [
            "target_gsd_m",
            "hybrid_mean",
        ]
    )
    .to_string(
        index=False
    )
)


print()
print(
    "OUTPUT:",
    ROOT.resolve(),
)

print(
    "E51-A HYBRID ANALYSIS COMPLETE"
)
