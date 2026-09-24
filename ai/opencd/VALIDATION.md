# Deep Change Model Validation Gate

VanRakshak's default Sentinel-2 + Sentinel-1 evidence pipeline works without a deep checkpoint.

For a deep model claim, the project now has a hard validation gate.

## Required artifacts

```env
OPENCD_REPO=/models/open-cd
OPENCD_CONFIG=/models/config.py
OPENCD_CHECKPOINT=/models/best.pth
OPENCD_METRICS_JSON=/models/model-metrics.json
```

The metrics JSON must be produced from **geographically held-out forest regions** using:

```bash
python scripts/evaluate_change_model.py validation-manifest.json --out model-metrics.json
```

The evaluator reports Precision, Recall, F1, IoU, Dice and false-positive rate, both per-region and aggregate.

`/api/ai/change-model/status` reports:

- `ready=true` only if checkout/config/checkpoint are present.
- `validated=true` only if real metrics are also present for at least two geographic holdout regions.

Do not put a claimed accuracy number in the dashboard until `validated=true`.
