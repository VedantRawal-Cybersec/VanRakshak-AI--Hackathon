# Open-CD production change model integration

VanRakshak ships a real, source-backed Sentinel-2 NDVI/SCL change-screening pipeline that works without a deep-learning checkpoint. The deep deforestation model is intentionally **not** presented as trained until an actual validated checkpoint exists.

## Recommended production path

1. Clone the official Open-CD repository outside this repository or as a deployment dependency: https://github.com/likyoo/open-cd
2. Prepare paired before/after forest-change chips and labels.
3. Split by geography (not only random image tiles).
4. Compare a baseline with TinyCD / Changer / ChangeFormer or suitable current Open-CD configs.
5. Track Precision, Recall, F1, IoU/Dice, false-positive rate and inference latency.
6. Store the selected checkpoint in a private/model-artifact store rather than committing a large binary to Git.
7. Configure:

```bash
OPENCD_REPO=/models/open-cd
OPENCD_CONFIG=/models/config.py
OPENCD_CHECKPOINT=/models/best.pth
```

`GET /api/ai/change-model/status` then reports whether the deep model runtime is truly ready.

## Acceptance gate

Do not replace the baseline with the deep model until it beats the baseline on a geographically held-out validation/test set and its false positives on cloud/shadow/seasonal changes are reviewed.
