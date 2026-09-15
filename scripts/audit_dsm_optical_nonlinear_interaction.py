from pathlib import Path
import zlib

import numpy as np
import pandas as pd

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    balanced_accuracy_score,
    roc_auc_score,
)


SEED = 42
GEOM_QUANTILE_BINS = 4

INPUT = Path(
    "records/dsm_semantic_ambiguity_audit_v2_20260914/"
    "sampled_features.csv"
)

OUT = Path(
    "records/dsm_optical_nonlinear_interaction_20260914"
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


FEATURE_SETS = {
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

    "Combined": [
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
        k: g
        for k, g in a.groupby(
            keys,
            sort=False,
        )
    }

    bg = {
        k: g
        for k, g in b.groupby(
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

        ra = deterministic_rng(
            seed_prefix,
            key,
            "A",
        )

        rb = deterministic_rng(
            seed_prefix,
            key,
            "B",
        )

        ia = ra.choice(
            len(ga),
            size=n,
            replace=False,
        )

        ib = rb.choice(
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
        "tile"
    ):

        gt = gt.copy()

        if (
            not (
                gt["class"]
                == class_a
            ).any()
            or
            not (
                gt["class"]
                == class_b
            ).any()
        ):
            continue

        for src, dst in [
            (
                "dsm_local_rel",
                "_rel",
            ),
            (
                "dsm_rough",
                "_rough",
            ),
            (
                "dsm_grad",
                "_grad",
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
                "_rel",
                "_rough",
                "_grad",
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
            "_rel",
            "_rough",
            "_grad",
        ],
        errors="ignore",
    )


def make_model(name):

    if name == "Logistic":

        return Pipeline([
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

    if name == "HistGB":

        return HistGradientBoostingClassifier(
            learning_rate=0.06,
            max_iter=200,
            max_leaf_nodes=15,
            min_samples_leaf=30,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=SEED,
        )

    raise ValueError(
        name
    )


def evaluate(
    subset,
    dataset,
    class_a,
    class_b,
    subset_name,
):
    rows = []

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

    splitter = GroupShuffleSplit(
        n_splits=3,
        test_size=0.25,
        random_state=SEED,
    )

    splits = list(
        splitter.split(
            subset,
            y,
            groups,
        )
    )

    for model_name in [
        "Logistic",
        "HistGB",
    ]:

        for feature_name, cols in FEATURE_SETS.items():

            X = subset[
                cols
            ].to_numpy(
                dtype=np.float64
            )

            scores = []

            for split_id, (
                train_idx,
                test_idx,
            ) in enumerate(
                splits
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

                model = make_model(
                    model_name
                )

                model.fit(
                    X[
                        train_idx
                    ],
                    y_train,
                )

                pred = model.predict(
                    X[
                        test_idx
                    ]
                )

                prob = model.predict_proba(
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

                "model":
                    model_name,

                "feature_set":
                    feature_name,

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


print(
    "[LOAD]",
    INPUT,
    flush=True,
)

df = pd.read_csv(
    INPUT
)

print(
    "[LOAD] rows=",
    len(df),
    flush=True,
)

results = []


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

        geom = match_local_geometry(
            pair,
            class_a,
            class_b,
        )

        subsets = {
            "FULL":
                pair,

            "LOCAL_GEOM_MATCHED":
                geom,
        }

        for subset_name, subset in subsets.items():

            if len(subset) == 0:
                continue

            print()
            print(
                "=" * 90,
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

            rows = evaluate(
                subset,
                dataset,
                class_a,
                class_b,
                subset_name,
            )

            results.extend(
                rows
            )

            for r in rows:
                print(
                    f"{r['model']:10s}",
                    f"{r['feature_set']:14s}",
                    f"BAcc={r['balanced_acc_mean']:.4f}",
                    f"AUC={r['auc_mean']:.4f}",
                    flush=True,
                )


results_df = pd.DataFrame(
    results
)

results_df.to_csv(
    OUT
    / "nonlinear_interaction_results.csv",
    index=False,
)


# ============================================================
# Interaction summary
# ============================================================

summary_rows = []


for (
    dataset,
    class_a,
    class_b,
    subset,
    model,
), g in results_df.groupby(
    [
        "dataset",
        "class_a",
        "class_b",
        "subset",
        "model",
    ]
):

    scores = dict(
        zip(
            g[
                "feature_set"
            ],
            g[
                "balanced_acc_mean"
            ],
        )
    )

    dsm = scores.get(
        "DSM_geometry",
        np.nan,
    )

    opt = scores.get(
        "Optical_only",
        np.nan,
    )

    combined = scores.get(
        "Combined",
        np.nan,
    )

    best_single = max(
        dsm,
        opt,
    )

    summary_rows.append({
        "dataset":
            dataset,

        "class_a":
            class_a,

        "class_b":
            class_b,

        "subset":
            subset,

        "model":
            model,

        "DSM_geometry":
            dsm,

        "Optical_only":
            opt,

        "Combined":
            combined,

        "best_single":
            best_single,

        "interaction_gain":
            combined
            - best_single,
    })


summary = pd.DataFrame(
    summary_rows
)

summary.to_csv(
    OUT
    / "interaction_gain_summary.csv",
    index=False,
)


# ============================================================
# Compare nonlinear versus linear interaction gain
# ============================================================

wide = summary.pivot_table(
    index=[
        "dataset",
        "class_a",
        "class_b",
        "subset",
    ],
    columns="model",
    values=[
        "Combined",
        "interaction_gain",
    ],
)

wide.columns = [
    "_".join(
        x
    )
    for x in wide.columns
]

wide = wide.reset_index()


if (
    "interaction_gain_HistGB"
    in wide.columns
    and
    "interaction_gain_Logistic"
    in wide.columns
):

    wide[
        "nonlinear_minus_linear_interaction_gain"
    ] = (
        wide[
            "interaction_gain_HistGB"
        ]
        -
        wide[
            "interaction_gain_Logistic"
        ]
    )


wide.to_csv(
    OUT
    / "linear_vs_nonlinear_summary.csv",
    index=False,
)


print()
print("=" * 110)
print("INTERACTION GAIN SUMMARY")
print("=" * 110)

print(
    summary.to_string(
        index=False
    )
)

print()
print("=" * 110)
print("LINEAR VS NONLINEAR")
print("=" * 110)

print(
    wide.to_string(
        index=False
    )
)

print()
print(
    "OUTPUT:",
    OUT.resolve(),
)

print(
    "NONLINEAR INTERACTION AUDIT COMPLETE"
)
