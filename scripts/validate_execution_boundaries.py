import argparse
import json
import os
from pathlib import Path


ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/"
    "08_thesis_full_repro"
).resolve()

POLICY = ROOT / "configs/execution_boundaries.json"


def inside(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--torch-check",
        action="store_true",
    )
    args = parser.parse_args()

    policy = json.loads(
        POLICY.read_text(encoding="utf-8")
    )

    configured_root = Path(
        policy["project_root"]
    ).resolve()

    if configured_root != ROOT:
        raise RuntimeError(
            f"project root mismatch: {configured_root}"
        )

    cwd = Path.cwd().resolve()
    if not inside(cwd, ROOT):
        raise RuntimeError(
            f"working directory outside project: {cwd}"
        )

    visible = os.environ.get(
        "CUDA_VISIBLE_DEVICES"
    )
    required = policy["gpu"][
        "cuda_visible_devices"
    ]

    if visible != required:
        raise RuntimeError(
            "CUDA_VISIBLE_DEVICES must be exactly "
            f"{required!r}, got {visible!r}"
        )

    allowed = [
        (ROOT / name).resolve()
        for name in policy[
            "allowed_write_subdirectories"
        ]
    ]

    protected = [
        Path(name).resolve()
        for name in policy["read_only_inputs"]
    ]

    for raw in args.output:
        output = Path(raw)
        if not output.is_absolute():
            output = ROOT / output
        output = output.resolve()

        if not any(
            inside(output, parent)
            for parent in allowed
        ):
            raise RuntimeError(
                f"output outside allowed roots: {output}"
            )

        if any(
            inside(output, parent)
            for parent in protected
        ):
            raise RuntimeError(
                f"output targets read-only input: {output}"
            )

        print("OUTPUT_OK", output)

    if args.torch_check:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable")

        count = torch.cuda.device_count()
        if count != 1:
            raise RuntimeError(
                "Exactly one visible GPU is required; "
                f"found {count}"
            )

        if torch.cuda.current_device() != 0:
            raise RuntimeError(
                "Logical device must be cuda:0"
            )

        print(
            "GPU_OK",
            {
                "physical_gpu": 0,
                "logical_device": "cuda:0",
                "visible_devices": visible,
                "name": torch.cuda.get_device_name(0),
            },
        )

    print(
        "EXECUTION_BOUNDARY_CHECK_PASS",
        {
            "project_root": str(ROOT),
            "persistent_scope":
                policy["persistent_scope_root"],
        },
    )


if __name__ == "__main__":
    main()
