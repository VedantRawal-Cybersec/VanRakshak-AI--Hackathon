# Runtime reliability audit — 25 September 2026

## Confirmed defects repaired

- WebGL initialization could abort every UI handler. Leaflet 1.9.4 now provides real 2D raster and GeoJSON rendering when WebGL cannot initialize.
- Before/after and Time Machine searched only Sentinel-2. Pre-2015 comparisons now query Planetary Computer Landsat Collection 2 Level 2, including requested years 1987, 2001 and 2011, subject to actual archive/cloud availability.
- Invalid, reversed, future and pre-archive dates are rejected clearly; identical scene comparisons are rejected.
- Long timelines sample windows across the selected interval instead of silently showing only one STAC page.
- TiTiler spectral expressions now reference asset names when asset_as_band=true, as required by rio-tiler's MultiBaseReader.
- Adapter/transport outages in unwrapped routes return explicit 503 provider-unavailable responses instead of uncaught 500s.
- Startup no longer waits for all remote health checks before registering map readiness. Investigation/profile failure is isolated.
- Map updates use style readiness; hidden comparison panels resize on reveal; old loss polygons are cleared; location responses are guarded against stale updates.
- Environmental point layers display actual values, units, depth and timestamp. Soil pH/carbon etc. no longer only display a generic dot.
- Optional terrain/biomass failures no longer leave a checkbox suggesting successful rendering.
- Forest Time Machine now has an opener; user-entered prediction and patrol values are consumed by their advertised controls.

## Relevant upstream projects examined

| Repository | Decision |
|---|---|
| https://github.com/Leaflet/Leaflet | Integrated pinned 1.9.4 browser fallback, BSD-2-Clause. |
| https://github.com/microsoft/PlanetaryComputer | Extended existing STAC/Data API adapter for Landsat archive, no copied model or fabricated scenes. |
| https://github.com/developmentseed/titiler | Retained existing renderer; corrected integration parameters. |
| https://github.com/cogeotiff/rio-tiler | Read MultiBaseReader asset_as_band behavior to correct spectral expressions. |
| https://github.com/maplibre/maplibre-gl-compare | Evaluated; retained existing synchronized comparison controls to avoid redundant map ownership and another dependency. |

Adding repositories cannot provide missing provider credentials, missing observations or a validated trained model.

## Verification and limits

64 backend tests passed locally at the first regression checkpoint. JavaScript syntax checks and the structural acceptance check passed. New browser regression tests cover a WebGL-disabled browser and manual input contracts.

The cloud browser reproduced a fatal WebGL startup failure on the old live app. Direct API navigation was blocked in that browser; local external HTTP access was restricted. Production validation must therefore be recorded separately from local/mocked tests.

Historical visual comparison does not imply that the existing Sentinel-only quantitative change/forecast pipeline supports Landsat. Earth Engine layers require valid credentials. Missing archive scenes and provider outages must remain visible. No zero-error or complete-production-verification claim is made by this report.
