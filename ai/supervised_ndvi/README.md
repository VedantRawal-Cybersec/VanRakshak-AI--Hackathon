# Supervised NDVI benchmark

This folder contains a **real trained supervised benchmark** for VanRakshak AI.

- Input data: 908 real Sentinel-2 L2A NDVI time-series samples.
- Labels: INPE PRODES 2022 yearly deforestation polygons.
- Source: Climate Change AI 2026 deforestation tutorial dataset.
- Split: deterministic 0.02-degree spatial blocks; a block never crosses train/validation/test.
- Model: class-weighted logistic regression over 24 NDVI observations plus transparent summary features.
- Test metrics are stored in `benchmark_model.json` and are loaded by the production model-quality panel.

Important limitation: the public dataset covers one region in southern Pará, Brazil. These measured metrics prove the training/evaluation pipeline is real; they **do not** prove India-wide generalization. VanRakshak therefore keeps the India production detector as a source-backed multispectral/radar screening pipeline until an India-specific labelled model is validated.

The benchmark intentionally reports Precision, Recall, F1, IoU, Dice, false-positive rate, confusion counts and a simple NDVI-drop baseline comparison. No metric is fabricated.
