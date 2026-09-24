from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import rasterio

def read_mask(path: Path, threshold: float):
    with rasterio.open(path) as ds:
        a=ds.read(1)
    if np.issubdtype(a.dtype,np.floating):
        return np.isfinite(a) & (a>=threshold)
    return a>0

def metrics(truth: np.ndarray, pred: np.ndarray):
    if truth.shape!=pred.shape:
        raise ValueError(f"Shape mismatch {truth.shape} != {pred.shape}")
    t=truth.astype(bool); p=pred.astype(bool)
    tp=int(np.logical_and(t,p).sum()); tn=int(np.logical_and(~t,~p).sum())
    fp=int(np.logical_and(~t,p).sum()); fn=int(np.logical_and(t,~p).sum())
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/(tp+fn) if tp+fn else None
    f1=(2*precision*recall/(precision+recall)) if precision is not None and recall is not None and precision+recall else None
    iou=tp/(tp+fp+fn) if tp+fp+fn else None
    dice=(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else None
    fpr=fp/(fp+tn) if fp+tn else None
    return {"tp":tp,"tn":tn,"fp":fp,"fn":fn,"precision":precision,"recall":recall,"f1":f1,"iou":iou,"dice":dice,"false_positive_rate":fpr}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("manifest",help="JSON: [{region,truth,prediction}, ...]")
    ap.add_argument("--threshold",type=float,default=.5)
    ap.add_argument("--out",default="model-metrics.json")
    args=ap.parse_args()
    manifest=json.loads(Path(args.manifest).read_text())
    if not isinstance(manifest,list) or not manifest:
        raise SystemExit("Manifest must be a non-empty list")
    rows=[]; agg={"tp":0,"tn":0,"fp":0,"fn":0}
    regions=set()
    for item in manifest:
        region=str(item["region"]); regions.add(region)
        m=metrics(read_mask(Path(item["truth"]),args.threshold),read_mask(Path(item["prediction"]),args.threshold))
        rows.append({"region":region,**m})
        for k in agg: agg[k]+=m[k]
    tp,tn,fp,fn=(agg[k] for k in ("tp","tn","fp","fn"))
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/(tp+fn) if tp+fn else None
    f1=(2*precision*recall/(precision+recall)) if precision is not None and recall is not None and precision+recall else None
    iou=tp/(tp+fp+fn) if tp+fp+fn else None
    dice=(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else None
    fpr=fp/(fp+tn) if fp+tn else None
    payload={
      "schema":"vanrakshak.change-model.metrics.v1",
      "geographic_holdout_regions":sorted(regions),
      "region_count":len(regions),
      "aggregate":{**agg,"precision":precision,"recall":recall,"f1":f1,"iou":iou,"dice":dice,"false_positive_rate":fpr},
      "per_region":rows,
      "warning":"Metrics are meaningful only when predictions were generated without training on these geographic holdout regions."
    }
    Path(args.out).write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2))

if __name__=="__main__":
    main()
