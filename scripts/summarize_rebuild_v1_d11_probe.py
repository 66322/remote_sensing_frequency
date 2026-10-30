"""Report fixed-threshold D11 screening, never choose thresholds on Val2."""
import csv
import json
from pathlib import Path
import numpy as np

ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
BASE=ROOT/"records/rebuild_v1_d11_benefit_probe_20260923"


def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def family_average(values):
    return float(np.mean([values["clean"],values["dsm_blur5"],values["dsm_noise_std010"],
                          np.mean([values[c] for c in ("roll4","roll16","roll32")])]))


def main():
    cfg=json.loads((ROOT/"configs/rebuild_v1/d11_supervised_benefit_probe.json").read_text())
    loaded={};missing=[]
    for seed in cfg["seeds"]:
        for name in cfg["models"]:
            path=BASE/"models"/f"seed{seed}_{name}"
            if not (path/"summary.json").exists():
                missing.append(path.name);continue
            meta=json.loads((path/"summary.json").read_text())
            rows=read(path/"routing.csv")
            values={r["condition"]:float(r["sampled_mIoU_fg5"]) for r in rows
                    if r["tile"]=="ALL" and r["group"]=="all" and r["method"]=="probe"}
            if set(values)!=set(cfg["evaluation_conditions"]) or meta["seed"]!=seed or meta["model"]!=name:
                raise ValueError("incomplete/mismatched model result")
            loaded[seed,name]=(meta,rows,values)
    output=[]
    print("D11 exploratory sampled NoBoundary mIoU; H is empirical, not guaranteed risk")
    print("seed model threshold clean_mIoU clean_minus_RGB_pp noise_minus_RGB_pp worst_H_percent mean_delta_vs_calibrated_scalar_pp screen")
    for (seed,name),(meta,rows,values) in loaded.items():
        rgb={r["condition"]:float(r["sampled_mIoU_fg5"]) for r in rows
             if r["tile"]=="ALL" and r["group"]=="all" and r["method"]=="RGB"}
        worst=max(float(r["harm"]) for r in rows if r["tile"]!="ALL" and r["group"]=="all" and r["method"]=="probe")
        delta=None
        if (seed,"confidence") in loaded and (seed,"entropy") in loaded:
            baseline={c:max(loaded[seed,"confidence"][2][c],loaded[seed,"entropy"][2][c]) for c in values}
            delta=family_average({c:values[c]-baseline[c] for c in values})
        passed=(delta is not None and delta>=.001 and values["clean"]>=rgb["clean"] and worst<=cfg["harm_budget"])
        row=dict(seed=seed,model=name,threshold=meta["threshold"],clean_sampled_mIoU=values["clean"],
                 clean_minus_RGB_pp=100*(values["clean"]-rgb["clean"]),
                 noise_minus_RGB_pp=100*(values["dsm_noise_std010"]-rgb["dsm_noise_std010"]),
                 worst_tile_condition_harm=worst,
                 family_mean_delta_vs_calibrated_scalar_pp=None if delta is None else 100*delta,
                 pass_for_full_resolution_confirmation=passed)
        output.append(row)
        print(seed,name,f'{meta["threshold"]:.2f}',f'{100*values["clean"]:.4f}',
              f'{row["clean_minus_RGB_pp"]:+.4f}',f'{row["noise_minus_RGB_pp"]:+.4f}',
              f'{100*worst:.4f}',"NA" if delta is None else f'{100*delta:+.4f}',"PASS" if passed else "NO")
    increments=[]
    for seed in cfg["seeds"]:
        if (seed,"expert") in loaded and (seed,"expert_frequency") in loaded:
            a,b=loaded[seed,"expert"][2],loaded[seed,"expert_frequency"][2]
            delta=100*family_average({c:b[c]-a[c] for c in a})
            increments.append(dict(seed=seed,expert_frequency_minus_expert_pp=delta))
            print("FREQUENCY_INCREMENT",seed,f"{delta:+.4f} pp (more parameters; not a learned-semantic test)")
    if output:
        with (BASE/"screen_summary.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(output[0]),lineterminator="\n");w.writeheader();w.writerows(output)
    both=[name for name in cfg["models"] if all(any(r["seed"]==seed and r["model"]==name
          and r["pass_for_full_resolution_confirmation"] for r in output) for seed in cfg["seeds"])]
    decision=dict(expected_models=12,completed_models=len(loaded),missing=missing,
                  both_seed_full_resolution_candidates=both,frequency_increments=increments,
                  residual_gate_authorized=False,independent_confirmation=False,
                  note="Screen thresholds are protocol decisions, not significance tests. Never tune after reading Val2.")
    if BASE.exists():
        (BASE/"decision.json").write_text(json.dumps(decision,indent=2)+"\n")
    print("FULL_RESOLUTION_CANDIDATES",both)
    print("COMPLETE",len(loaded),"/12; missing:",missing)
    raise SystemExit(1 if missing else 0)


if __name__=="__main__":
    main()
