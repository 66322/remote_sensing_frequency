import argparse
import sys

import eval_e51c_fixed_grid_information_degradation as e51c


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--infer-batch", type=int, required=True)
    known, remaining = parser.parse_known_args()

    if known.infer_batch < 1:
        raise ValueError("--infer-batch must be >= 1")

    e51c.INFER_BATCH = int(known.infer_batch)

    print("=" * 100)
    print("E51-C CONFIGURABLE-BATCH WRAPPER")
    print("=" * 100)
    print("infer batch:", e51c.INFER_BATCH)
    print("patch:", e51c.PATCH)
    print("stride:", e51c.TEST_STRIDE)
    print("IMPORTANT: patch/stride/protocol are unchanged; only inference batch is changed.")

    # Rebuild argv so the frozen evaluator parses only its own arguments.
    sys.argv = [sys.argv[0]] + remaining
    e51c.main()


if __name__ == "__main__":
    main()
