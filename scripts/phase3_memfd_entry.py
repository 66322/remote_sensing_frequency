"""Opt-in runtime wrapper; frozen experiment sources and binding remain unchanged."""
import argparse
import json
from pathlib import Path
import runpy
import sys
import traceback

from phase3_memfd_compat import probe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("checks", "m2", "combined"), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    base = args.directory.resolve()
    records = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records").resolve()
    if base.parent != records or args.directory.is_symlink():
        raise RuntimeError("exact existing run under records required")
    if args.mode == "checks":
        print("MEMFD_COMPAT_PROBE", json.dumps(probe()), flush=True)
        sys.path[:0] = [str(base/"code"), str(base/"code/scripts")]
        import phase3_m2_common as common
        common.verify(base)
        sys.argv = ["unittest", "discover", "-s", str(base/"code/tests"),
                    "-p", "test_phase3_m2.py", "-v"]
        runpy.run_module("unittest", run_name="__main__")
        return
    script = "control_phase3_m2.py" if args.mode == "m2" else "control_phase3_combined.py"
    sys.argv = [str(base/"code/scripts"/script), "--directory", str(base)]
    try:
        print("MEMFD_COMPAT_PROBE", json.dumps(probe()), flush=True)
        sys.path[:0] = [str(base/"code"), str(base/"code/scripts")]
        runpy.run_path(sys.argv[0], run_name="__main__")
    except BaseException as error:
        # Also surface failures before the frozen M2 controller enters its own try block.
        from datetime import datetime, timezone, timedelta
        from phase3_memfd_repair_common import write
        write(base/"queue_status.json", {
            "status": "FAILED_NO_RETRY" if args.mode == "m2" else "STOPPED_NO_AUTOMATIC_RETRY",
            "error": str(error), "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "runtime_wrapper": str(Path(__file__).resolve()), "automatic_retry": False})
        write(base/"memfd_wrapper_failure.json", {"error": str(error),
              "traceback": traceback.format_exc(), "automatic_retry": False})
        raise


if __name__ == "__main__":
    main()
