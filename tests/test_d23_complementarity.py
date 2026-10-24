"""Synthetic correctness and provenance checks; no real imagery or checkpoint."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1]/"scripts/audit_rebuild_v1_d23_complementarity.py"
spec = importlib.util.spec_from_file_location("d23",SCRIPT)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj),encoding="utf-8")


def brute(gt,p0,p1,condition):
    result = {r:np.zeros((6,6,6),np.int64) for r in ("available","missing")}
    h,w = gt.shape
    for y in range(h):
        for x in range(w):
            if gt[y,x]>=6:
                continue
            missing = condition=="aux_zero" or (condition=="aux_local_zero_q1" and
                     h//4<=y<h//4+h//2 and w//4<=x<w//4+w//2)
            result["missing" if missing else "available"][gt[y,x],p0[y,x],p1[y,x]]+=1
    return result


class DiagnosticTests(unittest.TestCase):
    def test_joint_tensor_against_independent_pixel_loop(self):
        rng=np.random.default_rng(42)
        gt=rng.integers(0,6,(9,11),dtype=np.uint8)
        gt[1,3]=255
        p0=rng.integers(0,6,gt.shape,dtype=np.uint8)
        p1=rng.integers(0,6,gt.shape,dtype=np.uint8)
        for condition in d.CONDITIONS:
            counts=d.joint_counts(gt,p0,p1,condition,chunk_rows=2)
            wide=d.joint_counts(gt,p0.astype(np.uint64),p1.astype(np.uint64),condition,chunk_rows=3)
            expected=brute(gt,p0,p1,condition)
            for r in counts:
                np.testing.assert_array_equal(wide[r],expected[r])
                np.testing.assert_array_equal(counts[r],expected[r])
            row=d.summarize(counts)
            a=d.local_availability(gt.shape,condition,0,len(gt))
            safe=np.where(a,p1,p0)
            oracle=np.where(a & (p1==gt) & (p0!=gt),p1,p0)
            for name,pred in (("R0",p0),("M0",p1),("M0_safe",safe),("oracle_safe",oracle)):
                cm=np.zeros((6,6),np.int64)
                for y,x in np.ndindex(gt.shape):
                    if gt[y,x]<6: cm[gt[y,x],pred[y,x]]+=1
                np.testing.assert_array_equal(row["metrics"][name]["cm"],cm)

    def test_complete_missing_exact_R0_counts(self):
        gt=np.arange(6,dtype=np.uint8).reshape(2,3)
        row=d.summarize(d.joint_counts(gt,gt,5-gt,"aux_zero",1))
        self.assertEqual(row["metrics"]["R0"]["cm"],row["metrics"]["M0_safe"]["cm"])
        self.assertEqual(row["metrics"]["R0"]["cm"],row["metrics"]["oracle_safe"]["cm"])
        self.assertEqual((row["safe_harm"],row["safe_rescue"]),(0,0))

    def test_reject_invalid_class_even_on_ignored_GT(self):
        gt=np.array([[255]],np.uint8)
        for pred in (np.array([[6]]),np.array([[-1]]),np.array([[float("nan")]])):
            with self.assertRaises(RuntimeError):
                d.joint_counts(gt,pred,np.array([[0]]),"clean")

    def test_color_palette_and_black_ignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"labels.tif"
            rgb=np.array([list(d.COLORS)+[(0,0,0)]],np.uint8)
            Image.fromarray(rgb).save(path)
            np.testing.assert_array_equal(d.decode_label(path,"noboundary"),[[0,1,2,3,4,5,255]])
            with self.assertRaises(RuntimeError): d.decode_label(path,"full")
            rgb[0,-1]=[1,2,3]
            Image.fromarray(rgb).save(path)
            with self.assertRaises(RuntimeError): d.decode_label(path,"noboundary")

    def test_metric_absent_class_matches_D21_nanmean(self):
        cm=np.zeros((6,6),np.int64)
        cm[0,0]=7
        self.assertEqual(d.metrics(cm)["fg5"],1.0)
        self.assertIsNone(d.metrics(cm)["per_class_iou"][1])

    def fixture(self,root):
        cfg=root/"configs/rebuild_v1/r05_quality_plus_dropout_16k.json"
        split_name="configs/rebuild_v1/potsdam_split_seed20260915.json"
        dump(cfg,{"data_root":str(root/"data"),"split_file":split_name})
        dump(root/split_name,{"val2":list(d.TILES),"historical_exposed_test6":["4_10"]})
        labels={}
        files=[]
        gt=np.tile(np.arange(6,dtype=np.uint8),(8,2))
        for tile in d.TILES:
            for scope,folder,suffix in (("full","5_Labels_for_participants","label"),
                                       ("noboundary","5_Labels_for_participants_no_Boundary","label_noBoundary")):
                path=root/"data"/folder/("top_potsdam_"+tile+"_"+suffix+".tif")
                path.parent.mkdir(parents=True,exist_ok=True)
                rgb=np.asarray(d.COLORS,np.uint8)[gt]
                if scope=="noboundary": rgb[0,:]=0
                Image.fromarray(rgb).save(path)
                labels[tile,scope]=d.decode_label(path,scope)
                files.append({"path":str(path),"size":path.stat().st_size,"sha256":d.sha(path)})
        manifest=root/"records/rebuild_v1_d21_queue_20260928/input_manifest.json"
        dump(manifest,{"files":files,"test6_loaded":False})
        hashes={}
        for arm in ("R0","M0"):
            job={"dataset":"potsdam","arm":arm,"seed":42}
            run=root/"runs/rebuild_v1"/("D21_potsdam_"+arm+"_seed42_16000_20260928")
            run.mkdir(parents=True)
            ck=run/"last_train_state.pth"
            ck.write_bytes(("synthetic-"+arm).encode())
            hashes[arm]=d.sha(ck)
            sig={"job":job,"input_manifest_sha256":d.sha(manifest),
                 "source_sha256":{"configs/rebuild_v1/r05_quality_plus_dropout_16k.json":d.sha(cfg),
                                  split_name:d.sha(root/split_name)},
                 "test6_loaded":False,"independent_final_loaded":False}
            dump(run/"summary.json",{"job":job,"signature":sig,"global_step":16000,
                 "checkpoint_sha256":hashes[arm],"test6_loaded":False})
            signature={"training":sig,"checkpoint_sha256":hashes[arm]}
            ev=root/"records/rebuild_v1_d21_20260928"/("potsdam_"+arm+"_seed42")
            conditions={}
            for condition in d.CONDITIONS:
                tiles={}
                for tile in d.TILES:
                    pred=(gt.copy() if arm=="M0" else (gt+1)%6).astype(np.uint8)
                    path=ev/condition/(tile+".npy")
                    path.parent.mkdir(parents=True,exist_ok=True)
                    np.save(path,pred)
                    scopes={}
                    for scope in ("full","noboundary"):
                        y=labels[tile,scope]
                        cm=np.zeros((6,6),np.int64)
                        for i,j in np.ndindex(y.shape):
                            if y[i,j]<6: cm[y[i,j],pred[i,j]]+=1
                        scopes[scope]={"cm":cm.tolist()}
                    detail={"signature":signature,"tile":tile,"condition":condition,
                            "prediction_sha256":d.sha(path),"scopes":scopes}
                    dump(path.with_suffix(".json"),detail)
                    tiles[tile]={k:v for k,v in detail.items() if k!="signature"}
                conditions[condition]={"tiles":tiles}
            dump(ev/"summary.json",{"job":job,"signature":signature,"smoke":False,
                "conditions":conditions,"evaluation_ids":list(d.TILES),"primary_scope":"noboundary",
                "test6_loaded":False,"independent_final_loaded":False})
        return hashes

    def test_end_to_end_profile_full_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            hashes=self.fixture(root)
            with patch.object(d,"CHECKPOINTS",hashes):
                profile=root/"records/probe"
                with patch.object(sys,"argv",["d23","--root",str(root),"--output",str(profile),"--mode","profile"]):
                    self.assertEqual(d.main(),0)
                full=root/"records/full"
                args=["d23","--root",str(root),"--output",str(full),"--mode","full","--profile",str(profile/"profile.json")]
                with patch.object(sys,"argv",args): self.assertEqual(d.main(),0)
                decision=d.read(full/"decision.json")
                self.assertEqual(decision["status"],"COMPLETE")
                self.assertFalse(decision["test6_loaded"])
                self.assertFalse(decision["decision"]["eligible_to_prepare_B"])
                with patch.object(sys,"argv",args):
                    with self.assertRaises(RuntimeError): d.main()

    def test_prediction_and_checkpoint_corruption_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            hashes=self.fixture(root)
            with patch.object(d,"CHECKPOINTS",hashes):
                summaries,labels,_=d.binding(root)
                path=root/"records/rebuild_v1_d21_20260928/potsdam_M0_seed42/clean/3_11.npy"
                np.save(path,np.zeros((8,12),np.uint8))
                with self.assertRaisesRegex(RuntimeError,"prediction hash"):
                    d.process_pair(root,"3_11","clean",summaries,labels)
                ck=root/"runs/rebuild_v1/D21_potsdam_M0_seed42_16000_20260928/last_train_state.pth"
                ck.write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError,"checkpoint bytes"):
                    d.binding(root)


if __name__=="__main__":
    unittest.main()
