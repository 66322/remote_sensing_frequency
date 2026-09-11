from pathlib import Path

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

BASE = ROOT / "scripts/train_vaihingen_P1_history_audit_10k.py"

OUT_HISTORY = (
    ROOT
    / "scripts/train_vaihingen_P1_History30_screen.py"
)

OUT_HYBRID = (
    ROOT
    / "scripts/train_vaihingen_P1_Rare15History15_screen.py"
)

base = BASE.read_text(
    encoding="utf-8"
)


def replace_once(text, old, new, desc):
    n = text.count(old)

    print(
        f"{desc}: count={n}"
    )

    if n != 1:
        raise RuntimeError(
            f"{desc}: expected 1 occurrence, "
            f"got {n}"
        )

    return text.replace(
        old,
        new,
        1,
    )


def replace_in_sampler(
    text,
    old,
    new,
    desc,
):
    start_marker = (
        "def sample_train_batch(train_cache):"
    )

    start = text.index(
        start_marker
    )

    end = text.index(
        "# ============================================================\n"
        "# Evaluation",
        start,
    )

    block = text[start:end]

    n = block.count(old)

    print(
        f"{desc}: count={n}"
    )

    if n != 1:
        raise RuntimeError(
            f"{desc}: expected 1 occurrence "
            f"inside sampler, got {n}"
        )

    block = block.replace(
        old,
        new,
        1,
    )

    return (
        text[:start]
        + block
        + text[end:]
    )


COMMON_CONFIG = r'''
# ============================================================
# Online History Sampling
# ============================================================

# Fraction of all sampled crops redirected to history.
HISTORY_PROB = 0.30

# Rare/Object-aware settings retained from the validated
# Rare30 screening experiment.
RARE_PROB = 0.30
RARE_CLASSES = (2, 3, 4)
RARE_WEIGHTS = (0.25, 0.25, 0.50)

RARE_CACHE_MAX_POINTS = 100000
RARE_COORD_CACHE = {}

# For the hybrid experiment after history becomes available.
HYBRID_RARE_PROB = 0.15
HYBRID_HISTORY_PROB = 0.15

# Online state.
ACTIVE_HISTORY_POOL = []
ONLINE_HISTORY_STATS = {}
ONLINE_HISTORY_PROCESSED_STEPS = set()
ONLINE_HISTORY_LOAD_ATTEMPTED = False

SAMPLER_COUNTS = {
    "random": 0,
    "rare": 0,
    "history": 0,
}

# Keep the same target budget as Rare30:
# 20% of 780 fixed regions = 156 history candidates.
ONLINE_HISTORY_POOL_FRACTION = 0.20
'''


COMMON_BEFORE_SAMPLER = r'''
def _rare_flat_indices(
    tile_id,
    gt,
    class_id,
):
    """
    Same deterministic rare-coordinate cache used by Rare30.
    """
    key = (
        str(tile_id),
        int(class_id),
    )

    cached = (
        RARE_COORD_CACHE.get(key)
    )

    if cached is not None:
        return cached

    flat = np.flatnonzero(
        gt.reshape(-1) == class_id
    )

    if (
        flat.size
        > RARE_CACHE_MAX_POINTS
    ):
        stride = max(
            1,
            int(
                np.ceil(
                    flat.size
                    / RARE_CACHE_MAX_POINTS
                )
            ),
        )

        flat = flat[
            ::stride
        ][:RARE_CACHE_MAX_POINTS]

    RARE_COORD_CACHE[key] = flat

    return flat


def _record_sampler_branch(name):
    SAMPLER_COUNTS[name] += 1

    total = sum(
        SAMPLER_COUNTS.values()
    )

    # 16 sampled crops / optimizer step.
    # Print approximately every 100 optimizer steps.
    if (
        total > 0
        and total % 1600 == 0
    ):
        print(
            "[SAMPLER-COUNTS] "
            f"total={total} | "
            f"random={SAMPLER_COUNTS['random']} | "
            f"rare={SAMPLER_COUNTS['rare']} | "
            f"history={SAMPLER_COUNTS['history']}"
        )


def _ensure_online_history_loaded(
    run_dir,
):
    """
    Restore history pool from its sidecar state after --resume.

    This contains TRAIN-set sampling information only.
    Test4 metrics are never used by the sampler.
    """
    global ONLINE_HISTORY_LOAD_ATTEMPTED
    global ACTIVE_HISTORY_POOL
    global ONLINE_HISTORY_STATS
    global ONLINE_HISTORY_PROCESSED_STEPS

    if ONLINE_HISTORY_LOAD_ATTEMPTED:
        return

    ONLINE_HISTORY_LOAD_ATTEMPTED = True

    if not args.resume:
        return

    path = (
        run_dir
        / "online_history_state.json"
    )

    if not path.is_file():
        print(
            "[ONLINE-HISTORY] "
            "resume sidecar not found; "
            "pool remains empty."
        )
        return

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        state = json.load(f)

    ACTIVE_HISTORY_POOL[:] = (
        state.get(
            "active_pool",
            [],
        )
    )

    ONLINE_HISTORY_STATS.clear()
    ONLINE_HISTORY_STATS.update(
        state.get(
            "stats",
            {},
        )
    )

    ONLINE_HISTORY_PROCESSED_STEPS.clear()
    ONLINE_HISTORY_PROCESSED_STEPS.update(
        int(x)
        for x in state.get(
            "processed_steps",
            [],
        )
    )

    counts = state.get(
        "sampler_counts",
        {},
    )

    for k in SAMPLER_COUNTS:
        SAMPLER_COUNTS[k] = int(
            counts.get(k, 0)
        )

    print(
        "[ONLINE-HISTORY] restored | "
        f"pool={len(ACTIVE_HISTORY_POOL)} | "
        f"processed="
        f"{sorted(ONLINE_HISTORY_PROCESSED_STEPS)}"
    )


'''


ONLINE_HISTORY_HELPERS = r'''
# ============================================================
# Online history pool construction
# ============================================================

def update_online_history_pool(
    records,
    run_dir,
    global_step,
):
    """
    Update online persistent-hard history using ONLY audits
    observed up to the current training step.

    Ranking:
      1. number of times the window entered current Top20%
      2. mean historical hard_score
      3. window_id for deterministic tie-breaking
    """
    global ACTIVE_HISTORY_POOL

    global ONLINE_HISTORY_STATS

    if (
        global_step
        in ONLINE_HISTORY_PROCESSED_STEPS
    ):
        print(
            "[ONLINE-HISTORY] "
            f"step {global_step} already processed; "
            "skip duplicate update."
        )
        return

    finite = [
        r
        for r in records
        if np.isfinite(
            float(
                r["hard_score"]
            )
        )
    ]

    finite = sorted(
        finite,
        key=lambda r: (
            -float(
                r["hard_score"]
            ),
            str(
                r["window_id"]
            ),
        ),
    )

    n_top = int(
        np.ceil(
            len(finite)
            * ONLINE_HISTORY_POOL_FRACTION
        )
    )

    current_top = {
        str(
            r["window_id"]
        )
        for r in finite[:n_top]
    }

    for r in finite:
        wid = str(
            r["window_id"]
        )

        score = float(
            r["hard_score"]
        )

        if wid not in ONLINE_HISTORY_STATS:
            ONLINE_HISTORY_STATS[wid] = {
                "window_id": wid,
                "tile_id": str(
                    r["tile_id"]
                ),
                "y": int(r["y"]),
                "x": int(r["x"]),
                "n_obs": 0,
                "top20_count": 0,
                "hard_sum": 0.0,
                "last_hard": score,
            }

        s = ONLINE_HISTORY_STATS[
            wid
        ]

        s["n_obs"] += 1
        s["hard_sum"] += score
        s["last_hard"] = score

        if wid in current_top:
            s["top20_count"] += 1

    ranked = []

    for wid, s in (
        ONLINE_HISTORY_STATS.items()
    ):
        n_obs = max(
            1,
            int(s["n_obs"]),
        )

        hard_mean = (
            float(s["hard_sum"])
            / n_obs
        )

        ranked.append(
            {
                "window_id": wid,
                "tile_id": str(
                    s["tile_id"]
                ),
                "y": int(s["y"]),
                "x": int(s["x"]),
                "top20_count": int(
                    s["top20_count"]
                ),
                "n_obs": int(
                    s["n_obs"]
                ),
                "hard_mean": float(
                    hard_mean
                ),
                "last_hard": float(
                    s["last_hard"]
                ),
            }
        )

    ranked.sort(
        key=lambda r: (
            -r["top20_count"],
            -r["hard_mean"],
            r["window_id"],
        )
    )

    pool_n = int(
        np.ceil(
            len(finite)
            * ONLINE_HISTORY_POOL_FRACTION
        )
    )

    ACTIVE_HISTORY_POOL[:] = (
        ranked[:pool_n]
    )

    ONLINE_HISTORY_PROCESSED_STEPS.add(
        int(global_step)
    )

    state_path = (
        run_dir
        / "online_history_state.json"
    )

    with open(
        state_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "global_step": int(
                    global_step
                ),
                "processed_steps": sorted(
                    ONLINE_HISTORY_PROCESSED_STEPS
                ),
                "active_pool": (
                    ACTIVE_HISTORY_POOL
                ),
                "stats": (
                    ONLINE_HISTORY_STATS
                ),
                "sampler_counts": (
                    SAMPLER_COUNTS
                ),
            },
            f,
            indent=2,
        )

    pool_csv = (
        run_dir
        / "online_history_pool.csv"
    )

    new_file = (
        not pool_csv.is_file()
    )

    with open(
        pool_csv,
        "a",
        newline="",
    ) as f:
        writer = csv.writer(f)

        if new_file:
            writer.writerow([
                "step",
                "rank",
                "window_id",
                "tile_id",
                "y",
                "x",
                "top20_count",
                "n_obs",
                "hard_mean",
                "last_hard",
            ])

        for rank, r in enumerate(
            ACTIVE_HISTORY_POOL,
            start=1,
        ):
            writer.writerow([
                global_step,
                rank,
                r["window_id"],
                r["tile_id"],
                r["y"],
                r["x"],
                r["top20_count"],
                r["n_obs"],
                r["hard_mean"],
                r["last_hard"],
            ])

    if ACTIVE_HISTORY_POOL:
        counts = [
            r["top20_count"]
            for r in ACTIVE_HISTORY_POOL
        ]

        print(
            "[ONLINE-HISTORY] "
            f"step={global_step} | "
            f"pool={len(ACTIVE_HISTORY_POOL)} | "
            f"top20count="
            f"{min(counts)}..{max(counts)}"
        )

        print(
            "[ONLINE-HISTORY] "
            "top5:"
        )

        for r in (
            ACTIVE_HISTORY_POOL[:5]
        ):
            print(
                "  "
                f"{r['window_id']} | "
                f"count="
                f"{r['top20_count']}/"
                f"{r['n_obs']} | "
                f"mean="
                f"{r['hard_mean']:.4f}"
            )

    print(
        "[SAMPLER-COUNTS] "
        f"random="
        f"{SAMPLER_COUNTS['random']} | "
        f"rare="
        f"{SAMPLER_COUNTS['rare']} | "
        f"history="
        f"{SAMPLER_COUNTS['history']}"
    )


'''


RANDOM_YX = '''        y = random.randint(
            0,
            H - source_size,
        )

        x = random.randint(
            0,
            W - source_size,
        )
'''


HISTORY30_YX = r'''        # ----------------------------------------------------
        # Online History30
        #
        # Before the first 2k audit ACTIVE_HISTORY_POOL is
        # empty, so this path is EXACTLY original P1 Random.
        #
        # After history becomes available:
        #   70% random
        #   30% history-centered
        # ----------------------------------------------------
        history_item = None

        if ACTIVE_HISTORY_POOL:
            use_history = (
                random.random()
                < HISTORY_PROB
            )

            if use_history:
                history_item = random.choice(
                    ACTIVE_HISTORY_POOL
                )

                tile_id = str(
                    history_item[
                        "tile_id"
                    ]
                )

                optical, dsm, gt = (
                    train_cache[
                        tile_id
                    ]
                )

                H, W = gt.shape

                # Recompute using the SAME sampled scale.
                source_size = int(
                    round(
                        PATCH / scale
                    )
                )

                source_size = max(
                    1,
                    min(
                        source_size,
                        H,
                        W,
                    ),
                )

        if history_item is not None:
            cy = (
                int(
                    history_item["y"]
                )
                + PATCH // 2
            )

            cx = (
                int(
                    history_item["x"]
                )
                + PATCH // 2
            )

            jitter = max(
                1,
                source_size // 4,
            )

            cy += random.randint(
                -jitter,
                jitter,
            )

            cx += random.randint(
                -jitter,
                jitter,
            )

            y = int(
                max(
                    0,
                    min(
                        H - source_size,
                        cy
                        - source_size // 2,
                    ),
                )
            )

            x = int(
                max(
                    0,
                    min(
                        W - source_size,
                        cx
                        - source_size // 2,
                    ),
                )
            )

            _record_sampler_branch(
                "history"
            )

        else:
            y = random.randint(
                0,
                H - source_size,
            )

            x = random.randint(
                0,
                W - source_size,
            )

            _record_sampler_branch(
                "random"
            )
'''


HYBRID_YX = r'''        # ----------------------------------------------------
        # Rare15 + History15
        #
        # BEFORE first audit:
        #   EXACT validated Rare30:
        #       70% random
        #       30% rare
        #
        # AFTER history exists:
        #       70% random
        #       15% rare
        #       15% history
        #
        # Total targeted fraction remains 30%.
        # ----------------------------------------------------
        history_item = None

        if ACTIVE_HISTORY_POOL:
            branch_gate = (
                random.random()
            )

            use_history = (
                branch_gate
                < HYBRID_HISTORY_PROB
            )

            use_rare = (
                (not use_history)
                and branch_gate
                < (
                    HYBRID_HISTORY_PROB
                    + HYBRID_RARE_PROB
                )
            )

        else:
            # This is deliberately identical to Rare30.
            use_history = False

            use_rare = (
                random.random()
                < RARE_PROB
            )

        if use_history:
            history_item = random.choice(
                ACTIVE_HISTORY_POOL
            )

            tile_id = str(
                history_item[
                    "tile_id"
                ]
            )

            optical, dsm, gt = (
                train_cache[
                    tile_id
                ]
            )

            H, W = gt.shape

            source_size = int(
                round(
                    PATCH / scale
                )
            )

            source_size = max(
                1,
                min(
                    source_size,
                    H,
                    W,
                ),
            )

        if use_rare:
            target_class = random.choices(
                RARE_CLASSES,
                weights=RARE_WEIGHTS,
                k=1,
            )[0]

            rare_flat = (
                _rare_flat_indices(
                    tile_id,
                    gt,
                    target_class,
                )
            )

            # Same defensive fallback as Rare30.
            if rare_flat.size == 0:
                use_rare = False

        if history_item is not None:
            cy = (
                int(
                    history_item["y"]
                )
                + PATCH // 2
            )

            cx = (
                int(
                    history_item["x"]
                )
                + PATCH // 2
            )

            jitter = max(
                1,
                source_size // 4,
            )

            cy += random.randint(
                -jitter,
                jitter,
            )

            cx += random.randint(
                -jitter,
                jitter,
            )

            y = int(
                max(
                    0,
                    min(
                        H - source_size,
                        cy
                        - source_size // 2,
                    ),
                )
            )

            x = int(
                max(
                    0,
                    min(
                        W - source_size,
                        cx
                        - source_size // 2,
                    ),
                )
            )

            _record_sampler_branch(
                "history"
            )

        elif use_rare:
            pos = int(
                rare_flat[
                    random.randrange(
                        int(
                            rare_flat.size
                        )
                    )
                ]
            )

            cy = pos // W
            cx = pos % W

            jitter = max(
                1,
                source_size // 4,
            )

            cy += random.randint(
                -jitter,
                jitter,
            )

            cx += random.randint(
                -jitter,
                jitter,
            )

            y = int(
                max(
                    0,
                    min(
                        H - source_size,
                        cy
                        - source_size // 2,
                    ),
                )
            )

            x = int(
                max(
                    0,
                    min(
                        W - source_size,
                        cx
                        - source_size // 2,
                    ),
                )
            )

            _record_sampler_branch(
                "rare"
            )

        else:
            y = random.randint(
                0,
                H - source_size,
            )

            x = random.randint(
                0,
                W - source_size,
            )

            _record_sampler_branch(
                "random"
            )
'''


AUDIT_CALL_OLD = '''            run_history_audit(
                net,
                train_cache,
                global_step,
                RUN_DIR,
                max_windows=(
                    16
                    if args.smoke_steps > 0
                    else None
                ),
            )
'''

AUDIT_CALL_NEW = '''            audit_records = run_history_audit(
                net,
                train_cache,
                global_step,
                RUN_DIR,
                max_windows=(
                    16
                    if args.smoke_steps > 0
                    else None
                ),
            )

            update_online_history_pool(
                audit_records,
                RUN_DIR,
                global_step,
            )
'''


def make_variant(
    policy,
    output_path,
    prefix,
):
    print()
    print("=" * 100)
    print("BUILD", policy)
    print("=" * 100)

    s = base

    s = replace_once(
        s,
        "Thesis_Ch4_NoSR_HistoryAudit_P1_",
        prefix,
        "run prefix",
    )

    s = replace_once(
        s,
        "HISTORY_TOP_FRACTION = 0.20\n",
        (
            "HISTORY_TOP_FRACTION = 0.20\n"
            + COMMON_CONFIG
        ),
        "online config",
    )

    marker = (
        "def sample_train_batch(train_cache):"
    )

    s = replace_once(
        s,
        marker,
        (
            COMMON_BEFORE_SAMPLER
            + marker
        ),
        "insert sampler helpers",
    )

    # Calling this does not consume RNG.
    s = replace_in_sampler(
        s,
        '''    sampled_scales = []

    for _ in range(TRAIN_BATCH):
''',
        '''    sampled_scales = []

    _ensure_online_history_loaded(
        RUN_DIR
    )

    for _ in range(TRAIN_BATCH):
''',
        "history restore call",
    )

    if policy == "history30":
        sampler_replacement = (
            HISTORY30_YX
        )

    elif (
        policy
        == "rare15history15"
    ):
        sampler_replacement = (
            HYBRID_YX
        )

    else:
        raise ValueError(policy)

    s = replace_in_sampler(
        s,
        RANDOM_YX,
        sampler_replacement,
        "sampling branch",
    )

    checkpoint_marker = (
        "# ============================================================\n"
        "# Checkpoint registry"
    )

    s = replace_once(
        s,
        checkpoint_marker,
        (
            ONLINE_HISTORY_HELPERS
            + checkpoint_marker
        ),
        "online history helpers",
    )

    s = replace_once(
        s,
        AUDIT_CALL_OLD,
        AUDIT_CALL_NEW,
        "audit -> online pool",
    )

    # Add explicit policy information to startup log.
    s = replace_once(
        s,
        'print("crop:", PATCH)\n',
        (
            'print("crop:", PATCH)\n'
            f'print("sampling policy:", "{policy}")\n'
            'print("online history pool fraction:", '
            'ONLINE_HISTORY_POOL_FRACTION)\n'
        ),
        "startup policy log",
    )

    output_path.write_text(
        s,
        encoding="utf-8",
    )

    print(
        "WROTE:",
        output_path,
    )


make_variant(
    "history30",
    OUT_HISTORY,
    "Thesis_Ch4_NoSR_ScreenV3_History30_P1_",
)

make_variant(
    "rare15history15",
    OUT_HYBRID,
    "Thesis_Ch4_NoSR_ScreenV3_Rare15History15_P1_",
)

print()
print("[DONE] two online-history trainers generated.")
