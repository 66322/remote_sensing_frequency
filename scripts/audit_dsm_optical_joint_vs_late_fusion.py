from pathlib import Path
import zlib

import numpy as np
import pandas as pd

from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    roc_auc_score,
)


# ============================================================
# Configuration
# ============================================================

SEED = 42
GEOM_QUANTILE_BINS = 4

INPUT = Path(
    "records/dsm_semantic_ambiguity_audit_v2_20260914/"
    "sampled_features.csv"
)

OUT = Path(
    "records/dsm_optical_joint_vs_late_fusion_20260914"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


PAIRS = [
    ("Building", "Tree"),
    ("Tree", "LowVeg"),
    ("Building", "Impervious"),
    ("Car", "Impervious"),
]


DSM_COLS = [
    "dsm_local_rel",
    "dsm_contrast",
    "dsm_rough",
    "dsm_grad",
]

OPT_COLS = [
    "opt_c1",
    "opt_c2",
    "opt_c3",
    "opt_rough",
    "opt_grad",
]

JOINT_COLS = (
    DSM_COLS
    + OPT_COLS
)


# ============================================================
# Deterministic helpers
# ============================================================

def deterministic_seed(*parts):
    text = "|".join(
        str(x)
        for x in parts
    )

    return (
        SEED
        + zlib.crc32(
            text.encode("utf-8")
        )
    ) % (2**31 - 1)


def deterministic_rng(*parts):
    return np.random.default_rng(
        deterministic_seed(
            *parts
        )
    )


# ============================================================
# Local geometry matching
# ============================================================

def quantile_codes(
    values,
    n_bins,
):
    values = np.asarray(
        values,
        dtype=np.float64,
    )

    edges = np.quantile(
        values,
        np.linspace(
            0.0,
            1.0,
            n_bins + 1,
        ),
    )

    edges = np.unique(
        edges
    )

    if len(edges) <= 2:
        return np.zeros(
            len(values),
            dtype=np.int16,
        )

    return np.digitize(
        values,
        edges[1:-1],
        right=False,
    ).astype(
        np.int16
    )


def balance_cells(
    a,
    b,
    keys,
    seed_prefix,
):
    pieces = []

    ag = {
        key: g
        for key, g in a.groupby(
            keys,
            sort=False,
        )
    }

    bg = {
        key: g
        for key, g in b.groupby(
            keys,
            sort=False,
        )
    }

    common = set(
        ag
    ).intersection(
        bg
    )

    for key in sorted(
        common,
        key=lambda x: str(x),
    ):

        ga = ag[key]
        gb = bg[key]

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
            ga.iloc[ia]
        )

        pieces.append(
            gb.iloc[ib]
        )

    if not pieces:
        return pd.DataFrame()

    return pd.concat(
        pieces,
        ignore_index=True,
    )


def match_local_geometry(
    pair_df,
    class_a,
    class_b,
):
    pieces = []

    for tile, gt in pair_df.groupby(
        "tile",
        sort=False,
    ):

        gt = gt.copy()

        a_exists = (
            gt["class"]
            == class_a
        ).any()

        b_exists = (
            gt["class"]
            == class_b
        ).any()

        if not (
            a_exists
            and b_exists
        ):
            continue

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
            gt["class"]
            == class_a
        ]

        b = gt[
            gt["class"]
            == class_b
        ]

        matched = balance_cells(
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

        if len(matched):
            pieces.append(
                matched
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
# Models
# ============================================================

def make_histgb(seed):
    return HistGradientBoostingClassifier(
        learning_rate=0.06,
        max_iter=200,
        max_leaf_nodes=15,
        min_samples_leaf=30,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=seed,
    )


def metrics(
    y,
    prob,
):
    pred = (
        prob >= 0.5
    ).astype(
        np.int64
    )

    return (
        float(
            balanced_accuracy_score(
                y,
                pred,
            )
        ),
        float(
            roc_auc_score(
                y,
                prob,
            )
        ),
    )


# ============================================================
# One outer split
# ============================================================

def run_outer_split(
    subset,
    dataset,
    class_a,
    class_b,
    subset_name,
    split_id,
    outer_train_idx,
    test_idx,
):
    y_all = (
        subset["class"]
        == class_b
    ).astype(
        np.int64
    ).to_numpy()

    groups_all = subset[
        "tile"
    ].astype(
        str
    ).to_numpy()

    outer_train = subset.iloc[
        outer_train_idx
    ].copy()

    y_outer = y_all[
        outer_train_idx
    ]

    groups_outer = groups_all[
        outer_train_idx
    ]

    # --------------------------------------------------------
    # Inner grouped split:
    # fit tiles train modality models;
    # calibration tiles train only the probability-level
    # learned fusion.
    # --------------------------------------------------------

    inner = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=(
            SEED
            + 100
            + split_id
        ),
    )

    fit_rel, cal_rel = next(
        inner.split(
            outer_train,
            y_outer,
            groups_outer,
        )
    )

    fit_idx = np.asarray(
        outer_train_idx
    )[
        fit_rel
    ]

    cal_idx = np.asarray(
        outer_train_idx
    )[
        cal_rel
    ]

    y_fit = y_all[
        fit_idx
    ]

    y_cal = y_all[
        cal_idx
    ]

    y_test = y_all[
        test_idx
    ]

    seed_base = deterministic_seed(
        dataset,
        class_a,
        class_b,
        subset_name,
        split_id,
    )

    # --------------------------------------------------------
    # Independent DSM model
    # --------------------------------------------------------

    dsm_model = make_histgb(
        seed_base + 1
    )

    dsm_model.fit(
        subset.iloc[
            fit_idx
        ][
            DSM_COLS
        ].to_numpy(
            dtype=np.float64
        ),
        y_fit,
    )

    # --------------------------------------------------------
    # Independent Optical model
    # --------------------------------------------------------

    opt_model = make_histgb(
        seed_base + 2
    )

    opt_model.fit(
        subset.iloc[
            fit_idx
        ][
            OPT_COLS
        ].to_numpy(
            dtype=np.float64
        ),
        y_fit,
    )

    # --------------------------------------------------------
    # Joint feature-level model
    #
    # IMPORTANT:
    # Joint uses exactly the same fit subset as DSM/Optical.
    # It does NOT use calibration tiles.
    # --------------------------------------------------------

    joint_model = make_histgb(
        seed_base + 3
    )

    joint_model.fit(
        subset.iloc[
            fit_idx
        ][
            JOINT_COLS
        ].to_numpy(
            dtype=np.float64
        ),
        y_fit,
    )

    # --------------------------------------------------------
    # Calibration predictions for learned late fusion
    # --------------------------------------------------------

    dsm_cal = dsm_model.predict_proba(
        subset.iloc[
            cal_idx
        ][
            DSM_COLS
        ].to_numpy(
            dtype=np.float64
        )
    )[:, 1]

    opt_cal = opt_model.predict_proba(
        subset.iloc[
            cal_idx
        ][
            OPT_COLS
        ].to_numpy(
            dtype=np.float64
        )
    )[:, 1]

    late_cal_X = np.column_stack([
        dsm_cal,
        opt_cal,
    ])

    late_model = LogisticRegression(
        solver="liblinear",
        class_weight="balanced",
        max_iter=1000,
        random_state=seed_base + 4,
    )

    late_model.fit(
        late_cal_X,
        y_cal,
    )

    # --------------------------------------------------------
    # Test predictions
    # --------------------------------------------------------

    dsm_test = dsm_model.predict_proba(
        subset.iloc[
            test_idx
        ][
            DSM_COLS
        ].to_numpy(
            dtype=np.float64
        )
    )[:, 1]

    opt_test = opt_model.predict_proba(
        subset.iloc[
            test_idx
        ][
            OPT_COLS
        ].to_numpy(
            dtype=np.float64
        )
    )[:, 1]

    joint_test = joint_model.predict_proba(
        subset.iloc[
            test_idx
        ][
            JOINT_COLS
        ].to_numpy(
            dtype=np.float64
        )
    )[:, 1]

    # Simple independent late fusion.
    late_avg_test = 0.5 * (
        dsm_test
        + opt_test
    )

    # Learned probability-level late fusion.
    late_learned_test = late_model.predict_proba(
        np.column_stack([
            dsm_test,
            opt_test,
        ])
    )[:, 1]

    predictions = {
        "DSM_only":
            dsm_test,

        "Optical_only":
            opt_test,

        "LateAvg":
            late_avg_test,

        "LateLearned":
            late_learned_test,

        "Joint":
            joint_test,
    }

    rows = []

    for method, prob in predictions.items():

        bacc, auc = metrics(
            y_test,
            prob,
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

            "split_id":
                split_id,

            "method":
                method,

            "n_total":
                len(subset),

            "n_fit":
                len(fit_idx),

            "n_cal":
                len(cal_idx),

            "n_test":
                len(test_idx),

            "fit_tiles":
                "|".join(
                    sorted(
                        set(
                            groups_all[
                                fit_idx
                            ]
                        )
                    )
                ),

            "cal_tiles":
                "|".join(
                    sorted(
                        set(
                            groups_all[
                                cal_idx
                            ]
                        )
                    )
                ),

            "test_tiles":
                "|".join(
                    sorted(
                        set(
                            groups_all[
                                test_idx
                            ]
                        )
                    )
                ),

            "balanced_acc":
                bacc,

            "auc":
                auc,
        })

    return rows


# ============================================================
# Load sampled data
# ============================================================

print(
    "[LOAD]",
    INPUT,
    flush=True,
)

df = pd.read_csv(
    INPUT,
    dtype={
        "dataset":
            str,

        "tile":
            str,

        "class":
            str,
    },
)

print(
    "[LOAD] rows=",
    len(df),
    flush=True,
)

print(
    "[DATASETS]",
    sorted(
        df["dataset"].unique()
    ),
    flush=True,
)


# ============================================================
# Evaluate
# ============================================================

all_rows = []


for dataset in sorted(
    df["dataset"].unique()
):

    ds = df[
        df["dataset"]
        == dataset
    ].copy()

    for class_a, class_b in PAIRS:

        pair = ds[
            ds["class"].isin(
                [
                    class_a,
                    class_b,
                ]
            )
        ].copy()

        matched = match_local_geometry(
            pair,
            class_a,
            class_b,
        )

        subsets = {
            "FULL":
                pair,

            "LOCAL_GEOM_MATCHED":
                matched,
        }

        for subset_name, subset in subsets.items():

            if len(subset) == 0:
                print(
                    "[SKIP empty]",
                    dataset,
                    class_a,
                    class_b,
                    subset_name,
                    flush=True,
                )
                continue

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

            print()
            print(
                "=" * 110,
                flush=True,
            )

            print(
                dataset,
                class_a,
                "vs",
                class_b,
                subset_name,
                "n=",
                len(subset),
                "tiles=",
                subset["tile"].nunique(),
                flush=True,
            )

            outer = GroupShuffleSplit(
                n_splits=3,
                test_size=0.25,
                random_state=SEED,
            )

            for split_id, (
                outer_train_idx,
                test_idx,
            ) in enumerate(
                outer.split(
                    subset,
                    y,
                    groups,
                ),
                start=1,
            ):

                rows = run_outer_split(
                    subset=subset,
                    dataset=dataset,
                    class_a=class_a,
                    class_b=class_b,
                    subset_name=subset_name,
                    split_id=split_id,
                    outer_train_idx=outer_train_idx,
                    test_idx=test_idx,
                )

                all_rows.extend(
                    rows
                )

                print(
                    f"  SPLIT {split_id}",
                    flush=True,
                )

                for row in rows:
                    print(
                        "   ",
                        f"{row['method']:12s}",
                        f"BAcc={row['balanced_acc']:.4f}",
                        f"AUC={row['auc']:.4f}",
                        flush=True,
                    )


# ============================================================
# Save per-split results
# ============================================================

result_df = pd.DataFrame(
    all_rows
)

result_df.to_csv(
    OUT
    / "per_split_results.csv",
    index=False,
)


# ============================================================
# Aggregate
# ============================================================

summary = (
    result_df
    .groupby(
        [
            "dataset",
            "class_a",
            "class_b",
            "subset",
            "method",
        ],
        as_index=False,
    )
    .agg(
        balanced_acc_mean=(
            "balanced_acc",
            "mean",
        ),

        balanced_acc_std=(
            "balanced_acc",
            "std",
        ),

        auc_mean=(
            "auc",
            "mean",
        ),

        auc_std=(
            "auc",
            "std",
        ),
    )
)

summary.to_csv(
    OUT
    / "method_summary.csv",
    index=False,
)


# ============================================================
# Joint vs late-fusion summary
# ============================================================

wide = summary.pivot_table(
    index=[
        "dataset",
        "class_a",
        "class_b",
        "subset",
    ],
    columns="method",
    values="balanced_acc_mean",
).reset_index()


required = [
    "DSM_only",
    "Optical_only",
    "LateAvg",
    "LateLearned",
    "Joint",
]

for col in required:
    if col not in wide.columns:
        wide[col] = np.nan


wide[
    "best_single"
] = wide[
    [
        "DSM_only",
        "Optical_only",
    ]
].max(
    axis=1
)


wide[
    "best_late"
] = wide[
    [
        "LateAvg",
        "LateLearned",
    ]
].max(
    axis=1
)


wide[
    "late_gain_over_best_single"
] = (
    wide[
        "best_late"
    ]
    -
    wide[
        "best_single"
    ]
)


wide[
    "joint_gain_over_best_single"
] = (
    wide[
        "Joint"
    ]
    -
    wide[
        "best_single"
    ]
)


wide[
    "joint_gain_over_best_late"
] = (
    wide[
        "Joint"
    ]
    -
    wide[
        "best_late"
    ]
)


wide.to_csv(
    OUT
    / "joint_vs_late_summary.csv",
    index=False,
)


# ============================================================
# Compact LOCAL_GEOM_MATCHED table
# ============================================================

local = wide[
    wide["subset"]
    == "LOCAL_GEOM_MATCHED"
].copy()

local = local[
    [
        "dataset",
        "class_a",
        "class_b",
        "DSM_only",
        "Optical_only",
        "LateAvg",
        "LateLearned",
        "Joint",
        "best_single",
        "best_late",
        "late_gain_over_best_single",
        "joint_gain_over_best_single",
        "joint_gain_over_best_late",
    ]
]

local.to_csv(
    OUT
    / "local_geom_matched_key_results.csv",
    index=False,
)


print()
print("=" * 120)
print("JOINT VS LATE-FUSION SUMMARY")
print("=" * 120)

print(
    wide.to_string(
        index=False
    )
)


print()
print("=" * 120)
print("LOCAL GEOMETRY MATCHED — KEY RESULTS")
print("=" * 120)

print(
    local.to_string(
        index=False
    )
)


print()
print(
    "OUTPUT:",
    OUT.resolve(),
)

print(
    "JOINT VS LATE FUSION AUDIT COMPLETE"
)
