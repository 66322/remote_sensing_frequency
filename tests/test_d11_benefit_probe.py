"""Probe tests use synthetic arrays only; no training data or GPU."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np
from scipy.optimize import approx_fprime
from d11_benefit_probe import (FREQUENCY,features,targets,objective,fit,probabilities,
                              calibrate_temperature,choose_threshold,validate_roles,
                              binary_calibration,routing_metrics)
from d11_benefit_probe import checkpoint_identity


class ProbeTests(unittest.TestCase):
    def test_best_checkpoint_can_precede_completed_training(self):
        meta=dict(checkpoint_rgb="r01/best_model.pth",checkpoint_dual="r05/best_model.pth",checkpoint_steps=[14000,12000])
        selected=checkpoint_identity(meta)
        self.assertEqual(selected["checkpoint_steps"],[14000,12000])
        with self.assertRaises(ValueError):
            checkpoint_identity({**meta,"checkpoint_steps":[16000,12000]},selected)

    def test_gradient(self):
        rng=np.random.default_rng(7)
        x=np.column_stack([rng.normal(size=(30,4)),np.ones(30)])
        y=rng.integers(0,3,30); w=rng.normal(size=15)*.1
        _,grad=objective(w,x,y,.01)
        numerical=approx_fprime(w,lambda z:objective(z,x,y,.01)[0],1e-6)
        np.testing.assert_allclose(grad,numerical,atol=5e-7)

    def test_learn_and_calibrate(self):
        rng=np.random.default_rng(9)
        y=np.repeat(np.arange(3),100)
        x=np.eye(3)[y]+rng.normal(0,.1,(300,3))
        model=fit(x,y)
        xcal=np.eye(3)[y]+rng.normal(0,.15,(300,3))
        model["temperature"]=calibrate_temperature(model,xcal,y,(.25,4))
        p=probabilities(model,xcal)
        self.assertGreater(np.mean(p.argmax(1)==y),.98)
        np.testing.assert_allclose(p.sum(1),1)
        self.assertLess(binary_calibration(p[:,0],y==0)["brier"],.01)

    def test_labels_are_not_features(self):
        rng=np.random.default_rng(1)
        a=rng.dirichlet(np.ones(6),40).T;b=rng.dirichlet(np.ones(6),40).T
        data={"rgb_prob":a,"dual_prob":b,"labels":np.zeros(40,int),
              **{k:rng.random(40) for k in FREQUENCY}}
        before,_=features(data,"expert_frequency")
        data["labels"]=np.full(40,5)
        after,_=features(data,"expert_frequency")
        np.testing.assert_array_equal(before,after)

    def test_worst_group_threshold_not_pooled(self):
        ga=(np.r_[np.full(99,.7),.3],np.r_[np.zeros(99,int),1],np.ones(100,bool))
        gb=(np.full(10,.7),np.r_[np.zeros(8,int),[1,1]],np.ones(10,bool))
        best,_=choose_threshold([ga,gb],[.5,1.],.02)
        self.assertEqual(best["threshold"],1.)
        self.assertEqual(best["mean_rescue"],0.)

    def test_routing_identity_and_fallback(self):
        gt=np.array([0,1,2,3]);rgb=np.array([0,0,0,3]);dual=np.array([1,1,1,3])
        full=routing_metrics(gt,rgb,dual,np.ones(4,bool))
        self.assertEqual(full["harm"],.25);self.assertEqual(full["rescue"],.25)
        self.assertEqual(full["accuracy_gain"],np.mean(dual==gt)-np.mean(rgb==gt))
        back=routing_metrics(gt,rgb,dual,np.zeros(4,bool))
        self.assertEqual(back["harm"],0);self.assertEqual(back["rescue"],0)

    def test_split_protection(self):
        cfg=dict(fit=["a"],probability_calibration=["b"],threshold_calibration=["c"],evaluation=["v"])
        split=dict(train16=["a","b","c"],val2=["v"],historical_exposed_test6=["t"])
        validate_roles(cfg,split)
        for role,value in (("fit",["v"]),("evaluation",["t"]),("threshold_calibration",["b"])):
            invalid={**cfg,role:value}
            with self.assertRaises(ValueError):validate_roles(invalid,split)

    def test_targets_cover_both_wrong_and_ignore_agreement(self):
        gt=np.array([0,1,2,3]);a=np.array([1,1,0,3]);b=np.array([0,0,1,3])
        sample=dict(labels=gt,rgb_prob=np.eye(6)[a].T,dual_prob=np.eye(6)[b].T)
        y,eligible,_,_=targets(sample)
        np.testing.assert_array_equal(y[:3],[0,1,2])
        np.testing.assert_array_equal(eligible,[True,True,True,False])

    def test_evaluation_missing_fallback_and_no_model_mutation(self):
        import copy
        from run_rebuild_v1_d11_probe import report
        rng=np.random.default_rng(3)
        sample=dict(labels=rng.integers(0,6,200),rgb_prob=rng.dirichlet(np.ones(6),200).T,
                    dual_prob=rng.dirichlet(np.ones(6),200).T,
                    interior=np.ones(200,bool),sizes=np.full(200,"small"))
        model=dict(model_name="confidence",seed=42,mean=[0.],scale=[1.],
                   weights=[[0.,0.,0.],[3.,0.,0.]],temperature=1.,threshold=0.)
        before=copy.deepcopy(model)
        rows,ranks=report(sample,model,{},"dsm_zero","synthetic")
        for row in rows:
            if row["method"] in ("probe","safe_confidence","safe_entropy","available_oracle"):
                self.assertEqual(row["harm"],0.);self.assertEqual(row["rescue"],0.)
                self.assertEqual(row["coverage"],0.)
        self.assertTrue(all(r["gain_ECE"] is None for r in ranks))
        self.assertEqual(model,before)

    def test_cpu_pipeline_with_synthetic_cache(self):
        import contextlib,hashlib,io,json,tempfile
        from unittest.mock import patch
        import run_rebuild_v1_d11_probe as runner
        repo=Path(__file__).resolve().parents[1]
        cfg=json.loads((repo/"configs/rebuild_v1/d11_supervised_benefit_probe.json").read_text())
        split=json.loads((repo/"configs/rebuild_v1/potsdam_split_seed20260915.json").read_text())
        n=90
        a=np.full((6,n),.04);a[0]=.8
        b=np.full((6,n),.06);b[1]=.7
        sample=dict(labels=np.tile([0,1,2],30),rgb_prob=a,dual_prob=b,
                    **{key:np.full(n,.1) for key in FREQUENCY})
        identity=dict(checkpoint_rgb="r01/best",checkpoint_dual="r05/best",checkpoint_steps=[14000,12000])
        with tempfile.TemporaryDirectory(prefix="d11_synthetic_test_") as directory:
            root=Path(directory);config=root/"config.json";config.write_text(json.dumps(cfg))
            sha=hashlib.sha256(config.read_bytes()).hexdigest()
            (root/"configs/rebuild_v1").mkdir(parents=True)
            (root/"configs/rebuild_v1/potsdam_split_seed20260915.json").write_text(json.dumps(split))
            (root/"scripts").mkdir()
            for name in ("d11_benefit_probe.py","run_rebuild_v1_d11_probe.py"):
                (root/"scripts"/name).write_bytes((repo/"scripts"/name).read_bytes())
            base=root/"probe";d10=root/"d10"
            for role in ("fit","probability_calibration","threshold_calibration"):
                for tile in cfg[role]:
                    folder=base/"development"/f"seed42_{tile}";folder.mkdir(parents=True)
                    hashes={}
                    for cond in cfg["development_conditions"]:
                        path=folder/f"{cond}.npz";np.savez(path,**sample)
                        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                    meta=dict(seed=42,tile=tile,role=role,smoke=False,test6_loaded=False,val2_loaded=False,
                              training_completed_steps=[16000,16000],config_sha256=sha,files_sha256=hashes,**identity)
                    (folder/"summary.json").write_text(json.dumps(meta))
            for cond in cfg["evaluation_conditions"]:
                folder=d10/f"seed42_{cond}";folder.mkdir(parents=True)
                for tile in cfg["evaluation"]:
                    np.savez(folder/f"samples_{tile}.npz",**sample,interior=np.ones(n,bool),sizes=np.full(n,"small"))
                (folder/"summary.json").write_text(json.dumps(dict(seed=42,condition=cond,smoke=False,
                    test6_loaded=False,val_ids=cfg["evaluation"],**identity)))
            # Redirect only the path-root guard for synthetic Windows fixtures.
            actual_resolve=Path.resolve
            def resolve_fixture(path,*args,**kwargs):
                if str(path).replace("\\","/")=="/home/jovyan/zzx":return actual_resolve(root)
                return actual_resolve(path,*args,**kwargs)
            with patch.multiple(runner,ROOT=root,CONFIG=config,BASE=base,D10=d10), \
                 patch.object(sys,"argv",["probe","--seed","42","--model","confidence"]), \
                 patch.object(Path,"resolve",resolve_fixture),contextlib.redirect_stdout(io.StringIO()):
                runner.main()
            result=json.loads((base/"models/seed42_confidence/summary.json").read_text())
            self.assertFalse(result["val2_used_for_fit_calibration"])
            self.assertEqual(len(result["evaluation_sources"]),14)
            self.assertEqual(result["model_sha256"],hashlib.sha256((base/"models/seed42_confidence/model.json").read_bytes()).hexdigest())


if __name__=="__main__":unittest.main()
