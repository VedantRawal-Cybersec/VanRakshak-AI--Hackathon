from __future__ import annotations
from pathlib import Path
import os


def status() -> dict:
    config=os.getenv("OPENCD_CONFIG","").strip()
    checkpoint=os.getenv("OPENCD_CHECKPOINT","").strip()
    repo=os.getenv("OPENCD_REPO","").strip()
    cfg_ok=bool(config and Path(config).exists())
    ckpt_ok=bool(checkpoint and Path(checkpoint).exists())
    repo_ok=bool(repo and Path(repo).exists())
    return {
        "baseline_remote_change": {"ready": True, "method": "Sentinel-2 NDVI + SCL masking"},
        "opencd": {
            "ready": bool(cfg_ok and ckpt_ok and repo_ok),
            "repo_path_configured": bool(repo), "repo_path_exists": repo_ok,
            "config_configured": bool(config), "config_exists": cfg_ok,
            "checkpoint_configured": bool(checkpoint), "checkpoint_exists": ckpt_ok,
            "note": "A deep model is only marked ready when an actual Open-CD checkout, config and trained checkpoint exist. VanRakshak never invents model accuracy.",
        },
    }
