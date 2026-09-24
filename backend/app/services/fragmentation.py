from __future__ import annotations
from io import BytesIO
import numpy as np
from rasterio.io import MemoryFile
from scipy.ndimage import label, binary_erosion

class FragmentationInputError(ValueError):
    pass

def metrics(blob: bytes, threshold: float = 0.5):
    with MemoryFile(blob) as mem:
        with mem.open() as ds:
            arr = ds.read(1).astype("float32")
            transform = ds.transform
            crs = ds.crs
    forest = np.isfinite(arr) & (arr >= threshold)
    total_px = int(forest.size)
    forest_px = int(forest.sum())
    lab, n = label(forest, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(lab.ravel())[1:] if n else np.array([], dtype=int)
    # 4-neighbour exposed edges; useful, transparent baseline fragmentation metric.
    padded = np.pad(forest.astype(np.uint8), 1, constant_values=0)
    exposed = 0
    core = forest
    for dy, dx in [(1,0),(-1,0),(0,1),(0,-1)]:
        shifted = padded[1+dy:1+dy+forest.shape[0], 1+dx:1+dx+forest.shape[1]]
        exposed += int(((forest == 1) & (shifted == 0)).sum())
    eroded = binary_erosion(forest, structure=np.ones((3,3), dtype=bool), border_value=0)
    core_px = int(eroded.sum())
    px_w = abs(float(transform.a))
    px_h = abs(float(transform.e))
    area_ha = forest_px * px_w * px_h / 10000 if crs and getattr(crs, "is_projected", False) else None
    edge_m = exposed * ((px_w + px_h) / 2) if crs and getattr(crs, "is_projected", False) else None
    return {
        "forest_fraction": round(forest_px / total_px, 5) if total_px else 0,
        "patch_count": int(n),
        "largest_patch_pixels": int(sizes.max()) if sizes.size else 0,
        "mean_patch_pixels": round(float(sizes.mean()), 2) if sizes.size else 0,
        "core_forest_fraction": round(core_px / forest_px, 5) if forest_px else 0,
        "edge_count_pixel_sides": exposed,
        "forest_area_ha": round(area_ha, 3) if area_ha is not None else None,
        "edge_length_m": round(edge_m, 1) if edge_m is not None else None,
        "label": "DERIVED_METRIC",
        "method": "8-neighbour patch labelling + one-pixel core erosion + 4-neighbour edge count",
        "note": "For research-grade landscape ecology, validate against PyLandStats/FRAGSTATS conventions for the selected raster resolution.",
    }
