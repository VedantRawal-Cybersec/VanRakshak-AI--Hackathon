from __future__ import annotations
from pathlib import Path
import json
import os

def _metrics():
    p=os.getenv("OPENCD_METRICS_JSON","").strip()
    if not p:
        return None,None
    path=Path(p)
    if not path.exists():
        return None,f"Metrics file does not exist: {p}"
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data,None
    except Exception as exc:
        return None,str(exc)

def status() -> dict:
    config=os.getenv("OPENCD_CONFIG","").strip()
    checkpoint=os.getenv("OPENCD_CHECKPOINT","").strip()
    repo=os.getenv("OPENCD_REPO","").strip()
    cfg_ok=bool(config and Path(config).exists())
    ckpt_ok=bool(checkpoint and Path(checkpoint).exists())
    repo_ok=bool(repo and Path(repo).exists())
    metrics,metrics_error=_metrics()
    aggregate=(metrics or {}).get("aggregate") or {}
    region_count=int((metrics or {}).get("region_count") or 0)
    validated=bool(cfg_ok and ckpt_ok and repo_ok and metrics and region_count>=2 and aggregate.get("f1") is not None and aggregate.get("iou") is not None)
    return {
        "baseline_remote_change": {
            "ready": True,
            "method": "Sentinel-2 multispectral NDVI/NDMI/NBR/NDWI + SCL mask + IsolationForest corroboration + optional measured Sentinel-1 SAR change",
        },
        "supervised_benchmark": supervised_benchmark(),\n        "opencd": {
            "ready": bool(cfg_ok and ckpt_ok and repo_ok),
            "validated": validated,
            "repo_path_configured": bool(repo), "repo_path_exists": repo_ok,
            "config_configured": bool(config), "config_exists": cfg_ok,
            "checkpoint_configured": bool(checkpoint), "checkpoint_exists": ckpt_ok,
            "metrics_configured": bool(os.getenv("OPENCD_METRICS_JSON","").strip()),
            "metrics_error": metrics_error,
            "geographic_holdout_regions": region_count if metrics else 0,
            "metrics": aggregate if metrics else None,
            "note": "A deep model is marked validated only when a real checkout/config/checkpoint and geographic-holdout metrics JSON exist. VanRakshak never invents model accuracy.",
        },
    }


def supervised_benchmark() -> dict:
    """Load measured metrics from the real Sentinel-2 + INPE PRODES labelled benchmark."""
    path = Path(__file__).resolve().parents[3] / "ai" / "supervised_ndvi" / "benchmark_model.json"
    if not path.exists():
        return {"available": False, "note": "Real supervised benchmark artifact is not packaged."}
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        test=((data.get("metrics") or {}).get("test") or {})
        ds=data.get("dataset") or {}
        return {
            "available": True,
            "precision": test.get("precision"), "recall": test.get("recall"),
            "f1": test.get("f1"), "iou": test.get("iou"), "dice": test.get("dice"),
            "false_positive_rate": test.get("fpr"), "accuracy": test.get("accuracy"),
            "tp": test.get("tp"), "tn": test.get("tn"), "fp": test.get("fp"), "fn": test.get("fn"),
            "test_n": test.get("n"),
            "model_type": data.get("model_type"),
            "dataset": ds.get("name"), "label_source": ds.get("labels"),
            "region": ds.get("region"), "split_method": (data.get("split") or {}).get("method"),
            "baseline": ((data.get("metrics") or {}).get("baseline_ndvi_drop") or {}),
            "note": ds.get("limitation"),
            "validation_class": "REAL_LABELLED_SPATIAL_BLOCK_HOLDOUT",
        }
    except Exception as exc:
        return {"available": False, "note": f"Benchmark artifact could not be read: {exc}"}
