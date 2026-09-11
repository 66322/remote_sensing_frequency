from pathlib import Path

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

P1_SRC = ROOT / "scripts/train_vaihingen_P1_detpair.py"
P2H_SRC = ROOT / "scripts/train_vaihingen_P2H_detpair.py"

P1_C256 = ROOT / "scripts/train_vaihingen_P1_C256_screen.py"
P1_RARE = ROOT / "scripts/train_vaihingen_P1_Rare30_screen.py"
P2H_RARE = ROOT / "scripts/train_vaihingen_P2H_Rare30_screen.py"


def replace_once(text, old, new, desc):
    n = text.count(old)
    print(desc, "count =", n)
    if n != 1:
        raise RuntimeError(
            f"{desc}: expected exactly 1 occurrence, got {n}"
        )
    return text.replace(old, new, 1)


def patch_run_prefix(text, old_prefix, new_prefix):
    return replace_once(
        text,
        old_prefix,
        new_prefix,
        f"run prefix {old_prefix}",
    )


# ============================================================
# C256
# ============================================================

text = P1_SRC.read_text(encoding="utf-8")

text = replace_once(
    text,
    "PATCH = 512",
    "PATCH = 256",
    "C256 PATCH",
)

text = patch_run_prefix(
    text,
    "Thesis_Ch4_NoSR_DetPair_P1_",
    "Thesis_Ch4_NoSR_Screen_C256_P1_",
)

P1_C256.write_text(
    text,
    encoding="utf-8",
)

print("WROTE:", P1_C256)


# ============================================================
# Rare/Object-aware sampler
# ============================================================

RARE_CONSTANTS = r'''
# ============================================================
# Screening experiment: Rare/Object-aware sampling
# ============================================================

RARE_PROB = 0.30

# Foreground classes:
# 2 = LowVegetation
# 3 = Tree
# 4 = Car
#
# Car receives a larger probability because it is rare and
# has shown the largest early per-class sensitivity.
RARE_CLASSES = (2, 3, 4)
RARE_WEIGHTS = (0.25, 0.25, 0.50)

# Avoid retaining millions of coordinates per tile/class.
RARE_CACHE_MAX_POINTS = 100000

RARE_COORD_CACHE = {}
'''

RARE_HELPER = r'''
def _rare_flat_indices(
    tile_id,
    gt,
    class_id,
):
    """
    Deterministic capped coordinate cache for targeted sampling.
    """
    key = (
        str(tile_id),
        int(class_id),
    )

    cached = RARE_COORD_CACHE.get(key)

    if cached is not None:
        return cached

    flat = np.flatnonzero(
        gt.reshape(-1) == class_id
    )

    if flat.size > RARE_CACHE_MAX_POINTS:
        step = max(
            1,
            int(
                np.ceil(
                    flat.size
                    / RARE_CACHE_MAX_POINTS
                )
            ),
        )

        flat = flat[
            ::step
        ][:RARE_CACHE_MAX_POINTS]

    RARE_COORD_CACHE[key] = flat

    return flat


'''

OLD_COORD_BLOCK = '''        y = random.randint(
            0,
            H - source_size,
        )

        x = random.randint(
            0,
            W - source_size,
        )
'''

NEW_COORD_BLOCK = '''        # ----------------------------------------------------
        # 70% original random crop
        # 30% rare/object-aware crop
        #
        # Rare branch selects a semantic pixel and places it
        # near the crop center with moderate spatial jitter.
        # ----------------------------------------------------
        use_rare = (
            random.random()
            < RARE_PROB
        )

        if use_rare:
            target_class = random.choices(
                RARE_CLASSES,
                weights=RARE_WEIGHTS,
                k=1,
            )[0]

            rare_flat = _rare_flat_indices(
                tile_id,
                gt,
                target_class,
            )

            # Very defensive fallback if this class does not
            # occur in the selected tile.
            if rare_flat.size == 0:
                use_rare = False

        if use_rare:
            pos = int(
                rare_flat[
                    random.randrange(
                        int(rare_flat.size)
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
                        cy - source_size // 2,
                    ),
                )
            )

            x = int(
                max(
                    0,
                    min(
                        W - source_size,
                        cx - source_size // 2,
                    ),
                )
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
'''


def add_rare_sampling(
    src,
    dst,
    old_prefix,
    new_prefix,
):
    text = src.read_text(
        encoding="utf-8"
    )

    text = patch_run_prefix(
        text,
        old_prefix,
        new_prefix,
    )

    text = replace_once(
        text,
        "RANDOM_SCALE_MAX = 2.0\n",
        (
            "RANDOM_SCALE_MAX = 2.0\n"
            + RARE_CONSTANTS
            + "\n"
        ),
        "insert rare constants",
    )

    marker = (
        "# ============================================================\n"
        "# RAM-only training batch sampler\n"
        "# ============================================================\n"
    )

    text = replace_once(
        text,
        marker,
        marker + "\n" + RARE_HELPER,
        "insert rare helper",
    )

    text = replace_once(
        text,
        OLD_COORD_BLOCK,
        NEW_COORD_BLOCK,
        "replace random coordinate sampler",
    )

    # Make the configuration explicit in the training log.
    text = replace_once(
        text,
        'print("optimizer: AdamW")',
        (
            'print('
            '"rare sampling: 70% random + 30% targeted; "'
            '"target weights LowVeg/Tree/Car = "'
            '"0.25/0.25/0.50"'
            ')\n'
            'print("optimizer: AdamW")'
        ),
        "insert rare config log",
    )

    dst.write_text(
        text,
        encoding="utf-8",
    )

    print("WROTE:", dst)


add_rare_sampling(
    P1_SRC,
    P1_RARE,
    "Thesis_Ch4_NoSR_DetPair_P1_",
    "Thesis_Ch4_NoSR_Screen_Rare30_P1_",
)

add_rare_sampling(
    P2H_SRC,
    P2H_RARE,
    "Thesis_Ch4_NoSR_DetPair_P2H_",
    "Thesis_Ch4_NoSR_Screen_Rare30_P2H_",
)

print("\nALL SCREENING TRAINERS CREATED")
