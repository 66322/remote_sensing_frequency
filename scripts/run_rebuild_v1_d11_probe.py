"""Fit -> probability calibration -> threshold freeze -> cached exploratory Val2 report."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from d9_benefit_metrics import rank_metrics, benefit_from_probabilities
from d11_benefit_probe import (MODELS, validate_roles, checkpoint_identity, features, targets, fit, calibrate_temperature,
                              probabilities, choose_threshold, binary_calibration, routing_metrics)

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
CONFIG = ROOT / "configs/rebuild_v1/d11_supervised_benefit_probe.json"
BASE = ROOT / "records/rebuild_v1_d11_benefit_probe_20260923"
D10 = ROOT / "records/rebuild_v1_d10m_mechanism_20260923"


def read_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def development(cfg, seed, role, model_name, provenance):
    groups = []
    for tile in cfg[role]:
        folder = BASE / "development" / f"seed{seed}_{tile}"
        meta = json.loads((folder/"summary.json").read_text())
        if (meta["seed"] != seed or meta["tile"] != tile or meta["role"] != role or meta["smoke"]
                or meta["test6_loaded"] or meta["val2_loaded"] or meta["training_completed_steps"] != [16000,16000]
                or meta["config_sha256"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest()):
            raise ValueError(f"development source mismatch: {folder}")
        identity=checkpoint_identity(meta,provenance.get("expert_identity"))
        provenance["expert_identity"]=identity
        for condition in cfg["development_conditions"]:
            path = folder / f"{condition}.npz"
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != meta["files_sha256"][path.name]:
                raise ValueError(f"incomplete/corrupted cache: {path}")
            provenance[str(path)] = digest
            sample = read_npz(path)
            x,names = features(sample,model_name)
            target,eligible,_,_ = targets(sample)
            groups.append((x,target,eligible))
    return groups,names


def selected_rows(groups):
    return np.concatenate([x[m] for x,y,m in groups]), np.concatenate([y[m] for x,y,m in groups])


def report(sample, model, cfg, condition, tile):
    x,_ = features(sample, model["model_name"])
    target,eligible,a,b = targets(sample)
    prob = probabilities(model,x)
    score = prob[:,0]-prob[:,1]
    available = condition != "dsm_zero"
    e1 = -(sample["rgb_prob"]*np.log(sample["rgb_prob"]+1e-8)).sum(0)
    e5 = -(sample["dual_prob"]*np.log(sample["dual_prob"]+1e-8)).sum(0)
    choices = {"probe": available & eligible & (score > model["threshold"]),
               "safe_confidence": available & eligible & (sample["dual_prob"].max(0)>sample["rgb_prob"].max(0)),
               "safe_entropy": available & eligible & (e1>e5),
               "RGB": np.zeros(len(target),bool), "dual": np.ones(len(target),bool),
               "available_oracle": available & eligible & (target==0)}
    if not available and (choices["probe"].any() or choices["safe_confidence"].any() or choices["safe_entropy"].any()):
        raise RuntimeError("missing-DSM fallback failed")
    labels=sample["labels"]
    delta=benefit_from_probabilities(sample["rgb_prob"][labels,np.arange(len(labels))],
                                     sample["dual_prob"][labels,np.arange(len(labels))])
    groups={"all":np.ones(len(labels),bool),"interior":sample["interior"],
            "smallCar":(labels==4)&(sample["sizes"]=="small")}
    groups.update({name:labels==c for c,name in enumerate(("Impervious","Building","LowVegetation","Tree","Car","Clutter"))})
    metrics,ranks=[],[]
    for group,mask in groups.items():
        if not mask.any():
            continue
        ident=dict(seed=model["seed"],model=model["model_name"],condition=condition,tile=tile,group=group)
        for method,choose in choices.items():
            metrics.append(dict(**ident,method=method,**routing_metrics(labels[mask],a[mask],b[mask],choose[mask])))
        m=mask & eligible & available
        flip=m & (target!=2)
        rank=rank_metrics(score[flip],np.where(target[flip]==0,1.,-1.),0.)
        ce=rank_metrics(score[m],delta[m],.01)
        gain=binary_calibration(prob[m,0],target[m]==0)
        harm=binary_calibration(prob[m,1],target[m]==1)
        ranks.append(dict(**ident,disagreement_n=int(m.sum()),flip_n=rank["count"],
                          flip_AUROC=rank["benefit_auroc"],flip_AUPRC=rank["benefit_auprc"],
                          ce_AUROC=ce["benefit_auroc"],ce_AUPRC=ce["benefit_auprc"],ce_n=ce["count"],
                          gain_ECE=gain["ece"],gain_Brier=gain["brier"],gain_rate=gain["positive_rate"],
                          harm_ECE=harm["ece"],harm_Brier=harm["brier"],harm_rate=harm["positive_rate"]))
    return metrics,ranks


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,choices=(17,42),required=True)
    ap.add_argument("--model",choices=MODELS,required=True)
    args=ap.parse_args()
    cfg=json.loads(CONFIG.read_text())
    validate_roles(cfg,json.loads((ROOT/"configs/rebuild_v1/potsdam_split_seed20260915.json").read_text()))
    out=BASE/"models"/f"seed{args.seed}_{args.model}"
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(out)
    provenance={}
    groups,names=development(cfg,args.seed,"fit",args.model,provenance)
    x,y=selected_rows(groups)
    model=fit(x,y,cfg["l2"],cfg["max_iterations"])
    model.update(model_name=args.model,seed=args.seed,feature_names=names)
    del groups,x,y
    groups,_=development(cfg,args.seed,"probability_calibration",args.model,provenance)
    x,y=selected_rows(groups)
    model["temperature"]=calibrate_temperature(model,x,y,cfg["temperature_bounds"])
    model["probability_calibration_n"]=len(y)
    del groups,x,y
    groups,_=development(cfg,args.seed,"threshold_calibration",args.model,provenance)
    scored=[]
    for x,target,eligible in groups:
        p=probabilities(model,x)
        scored.append((p[:,0]-p[:,1],target,eligible))
    best,threshold_table=choose_threshold(scored,cfg["thresholds"],cfg["harm_budget"])
    model.update(threshold=best["threshold"],calibration_selection=best,threshold_table=threshold_table,
                 config_sha256=hashlib.sha256(CONFIG.read_bytes()).hexdigest(),development_sources=provenance,
                 source_sha256={name:hashlib.sha256((ROOT/"scripts"/name).read_bytes()).hexdigest()
                                for name in ("d11_benefit_probe.py","run_rebuild_v1_d11_probe.py")})
    out.mkdir(parents=True,exist_ok=False)
    # Freeze model before any evaluation file is opened; evaluation cannot alter it.
    artifact=out/"model.json"
    artifact.write_text(json.dumps(model,indent=2)+"\n")
    frozen_hash=hashlib.sha256(artifact.read_bytes()).hexdigest()
    del groups,scored
    metrics,ranks=[],[]
    evaluation_sources={}
    for condition in cfg["evaluation_conditions"]:
        folder=D10/f"seed{args.seed}_{condition}"
        meta=json.loads((folder/"summary.json").read_text())
        if (meta["seed"]!=args.seed or meta["condition"]!=condition or meta["smoke"] or meta["test6_loaded"]
                or set(meta["val_ids"])!=set(cfg["evaluation"])):
            raise ValueError("D10M evaluation manifest mismatch")
        checkpoint_identity(meta,provenance["expert_identity"])
        parts=[]
        for tile in cfg["evaluation"]:
            path=folder/f"samples_{tile}.npz"
            evaluation_sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            sample=read_npz(path)
            m,r=report(sample,model,cfg,condition,tile)
            metrics.extend(m);ranks.extend(r);parts.append(sample)
        combined={k:np.concatenate([p[k] for p in parts],axis=1 if k in ("rgb_prob","dual_prob") else 0)
                  for k in parts[0]}
        m,r=report(combined,model,cfg,condition,"ALL")
        metrics.extend(m);ranks.extend(r)
        del parts,combined
    if hashlib.sha256(artifact.read_bytes()).hexdigest()!=frozen_hash:
        raise RuntimeError("model changed during evaluation")
    for name,rows in (("routing",metrics),("calibration_ranking",ranks)):
        with (out/f"{name}.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
    summary=dict(seed=args.seed,model=args.model,threshold=model["threshold"],temperature=model["temperature"],
                 model_sha256=frozen_hash,evaluation_sources=evaluation_sources,test6_loaded=False,
                 val2_used_for_fit_calibration=False,fit_expert_training_exposed=True,
                 parameter_count=int(np.asarray(model["weights"]).size),
                 interpretation="sampled NoBoundary exploratory performance; not full-image mIoU or independent confirmation")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D11 PROBE COMPLETE",out,flush=True)


if __name__=="__main__":
    main()
