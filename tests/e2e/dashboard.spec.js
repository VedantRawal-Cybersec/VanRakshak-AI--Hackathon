const { test, expect } = require('@playwright/test');

test('approved dashboard boots with critical command-center controls', async ({ page }) => {
  const fatal=[];
  page.on('pageerror', e => fatal.push(String(e)));
  await page.goto('/');
  await expect(page).toHaveTitle(/VanRakshak AI/i);
  await expect(page.locator('#map')).toBeVisible();
  await expect(page.locator('#regionTitle')).toBeVisible();
  await expect(page.locator('#searchBox')).toBeVisible();
  await expect(page.locator('#layersBtn')).toBeVisible();
  await expect(page.locator('#reportBtn')).toBeVisible();
  await expect(page.locator('#patrolBtn')).toBeVisible();
  await expect(page.locator('#compareShell')).toHaveCount(1);
  await expect(page.locator('#sourceList')).toBeVisible();
  expect(fatal).toEqual([]);
});

test('layer drawer opens and all principal quick controls respond', async ({ page }) => {
  await page.goto('/');
  await page.locator('#layersBtn').click();
  await expect(page.locator('#layerDrawer')).toBeVisible();
  await page.locator('#closeLayers').click();
  await expect(page.locator('#layerDrawer')).toHaveClass(/hidden/);
  await page.locator('#analyticsTop').click();
  await page.locator('#liveDataTop').click();
  await page.locator('#brandHome').click();
});

test('public backend endpoints used by dashboard are live', async ({ request }) => {
  const health=await request.get('/api/health');
  expect(health.ok()).toBeTruthy();
  expect((await health.json()).ok).toBeTruthy();

  const features=await request.get('/api/features/status');
  expect(features.ok()).toBeTruthy();
  const f=await features.json();
  expect(f.count).toBe(37);

  const layers=await request.get('/api/layers');
  expect(layers.ok()).toBeTruthy();

  const gibs=await request.get('/api/gibs/catalog');
  expect(gibs.ok()).toBeTruthy();
  expect((await gibs.json()).auth_required).toBe(false);

  const fallbacks=await request.get('/api/fallbacks/status');
  expect(fallbacks.ok()).toBeTruthy();
});

test('real public data path returns for Kodagu', async ({ request }) => {
  const weather=await request.get('/api/weather?lat=12.3375&lon=75.8069');
  expect(weather.ok()).toBeTruthy();
  const w=await weather.json();
  expect(w.ok).toBeTruthy();

  const sat=await request.get('/api/satellite/latest?lat=12.3375&lon=75.8069&days=60&cloud_lt=80');
  expect(sat.ok()).toBeTruthy();
  const s=await sat.json();
  expect(s.ok).toBeTruthy();
});


test('overview, analysis and environmental panels expose operational detail', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#actionPlanOverview')).toHaveCount(1);
  await expect(page.locator('#actionPlanAnalysis')).toHaveCount(1);
  await expect(page.locator('#environmentUpdated')).toHaveCount(1);

  await page.locator('[data-tab="environment"]').click();
  await expect(page.locator('#tab-environment')).toBeVisible();
  await expect(page.locator('#environmentPanel')).toBeVisible();

  await page.locator('[data-tab="analysis"]').click();
  await expect(page.locator('#tab-analysis')).toBeVisible();

  await page.locator('[data-tab="overview"]').click();
  await expect(page.locator('#tab-overview')).toBeVisible();

  const overflow=await page.locator('#inspector').evaluate(el => getComputedStyle(el).overflowY);
  expect(['auto','scroll']).toContain(overflow);
});


test('quick map filters are exclusive and update thematic legend', async ({ page }) => {
  await page.goto('/');

  await page.locator('[data-quick="fire"]').click();
  await expect(page.locator('#mapLegendTitle')).toContainText('Fire & Heat');
  await expect(page.locator('#mapLegendMeta')).toContainText(/FIRMS|VIIRS|thermal|hotspot/i);
  await expect(page.locator('#mapLegendTicks')).toContainText('Critical');
  await expect(page.locator('.map-pill.active')).toHaveCount(1);
  await expect(page.locator('[data-quick="fire"]')).toHaveClass(/active/);

  await page.locator('[data-quick="ndvi"]').click();
  await expect(page.locator('#mapLegendTitle')).toContainText('NDVI');
  await expect(page.locator('#mapLegendTicks')).toContainText('1');
  await expect(page.locator('.map-pill.active')).toHaveCount(1);
  await expect(page.locator('[data-quick="ndvi"]')).toHaveClass(/active/);

  await page.locator('[data-quick="forest"]').click();
  await expect(page.locator('#mapLegendTitle')).toContainText('Forest Cover');
  await expect(page.locator('#mapLegendTicks')).toContainText('100%');
  await expect(page.locator('.map-pill.active')).toHaveCount(1);
});


test('analysis tab exposes area soil situation workflow and impact panels', async ({ page }) => {
  await page.goto('/');
  await page.locator('[data-tab="analysis"]').click();
  await expect(page.locator('#tab-analysis')).toBeVisible();
  await expect(page.locator('#analysisAreaGrid')).toBeVisible();
  await expect(page.locator('#currentSituationPanel')).toBeVisible();
  await expect(page.locator('#vanrakshakWorkflow')).toBeVisible();
  await expect(page.locator('#analysisImpactSummary')).toBeVisible();
  await expect(page.getByText('Area & Ecosystem Snapshot')).toBeVisible();
  await expect(page.getByText('What Is Happening Now')).toBeVisible();
  await expect(page.getByText('How VanRakshak Responds')).toBeVisible();
  await expect(page.getByText('Expected Impact After Intervention')).toBeVisible();
});


test('profile and alert center expose ecological impact and queue contracts', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#vegetationStatus')).toHaveCount(1);
  await page.locator('[data-tab="analysis"]').click();
  await expect(page.locator('#profilePanel')).toBeVisible();
  await expect(page.locator('#profilePanel')).toContainText(/Location|Sentinel/i);

  await expect(page.locator('#alertQueue')).toHaveCount(1);
  await expect(page.locator('#alertSelectedPlan')).toHaveCount(1);
  await expect(page.locator('#alertCount')).toHaveCount(1);
});


test('selected forest prediction explains what why actions impact and confidence', async ({ page }) => {
  const fatal=[];
  page.on('pageerror', e => fatal.push(String(e)));

  await page.route('**/api/analysis/evidence-chain**', async route => {
    await route.fulfill({
      status:200,
      contentType:'application/json',
      body:JSON.stringify({
        change:{candidate_area_ha:3.4,mean_ndvi_change:-0.08,screening_confidence:0.81,fragmentation:{change:{patch_count_pct:9.5}}},
        warning:{level:'WATCH',score:44,coverage:0.82,factors:[]},
        climate:{temperature_anomaly_c:1.1,rainfall_deficit_pct:22},
        carbon:{estimated_co2e_t:31.5},
        forest_doctor:{probable_drivers:[{driver:'Road-access pressure',relative_support_pct:58}]},
        action_plan:{actions:[{priority:'HIGH',what:'Verify candidate change',where:'Highest-change polygon',how:'Send patrol with geotagged evidence capture.',why:'Forecast is rising.',timeframe:'Within 24 h',expected_impact:'Stop further candidate-area expansion.',success_metric:'No new expansion on next scene.'}]},
        evidence_chain:{items:[]},
        sources:{}
      })
    });
  });

  await page.route('**/api/intelligence/predict-location**', async route => {
    await route.fulfill({
      status:200,
      contentType:'application/json',
      body:JSON.stringify({
        historical_risk_proxy:[12,18,25,33],
        dates:['2026-01-01','2026-02-01','2026-03-01','2026-04-01'],
        projection:{
          projected_values:[39,45,51,57],
          forecast_dates:['2026-05-01','2026-06-01','2026-07-01','2026-08-01'],
          lower:[34,39,43,47],
          upper:[44,51,59,67],
          uncertainty_sigma:3.2,
          trend_per_step:6.1,
          analysis:{direction:'INCREASING',strength:'MODERATE',confidence_pct:78,forecast_final:57,risk_level:'HIGH',observations:4,summary:'Risk trend is increasing.'},
          pipeline:[]
        },
        analysis:{interpretation:'Observed vegetation decline is producing a rising screening-risk trend.',ndvi_change_first_to_latest:-0.12,forest_fraction_change_first_to_latest:-0.09,optical_quality_pct:91,latest_observation:'2026-04-01',scene_read_errors:0,current_risk_index:33,projected_risk_index:57,model_confidence_pct:78},
        forecast_intelligence:{
          what_is_happening:'VanRakshak detects a rising optical screening-risk trend.',
          why_model_is_flagging_it:[
            {factor:'Vegetation index trend',observation:'NDVI declined across the observed period.',meaning:'Negative NDVI contributes to the screening-risk proxy.'},
            {factor:'Forest-fraction trend',observation:'Forest fraction declined.',meaning:'Forest-cover decline contributes to the proxy.'}
          ],
          recommended_actions:[{priority:'HIGH',what:'Verify change',how:'Inspect the candidate location.',why:'Prediction is rising.'}],
          expected_impacts:[{metric:'Screening-risk trend',current:33,target:'Stable or lower',success_check:'Re-run after next scene.'}],
          uncertainty:{confidence_pct:78,forecast_change:24,final_interval:{lower:47,upper:67},note:'Confidence is model quality, not event probability.'},
          verification_next:['Re-run after the next suitable Sentinel-2 observation.'],
          causation_note:'The model explains the signal, not the real-world cause.'
        },
        pipeline:[],
        generated_at:'2026-09-25T06:00:00Z',
        warning:'Prediction is a screening estimate.'
      })
    });
  });

  await page.goto('/');
  await page.locator('[data-nav="predictions"]').click();
  await expect(page.locator('#intelligenceModal')).toBeVisible();
  await page.locator('#runLocationPrediction').click();

  await expect(page.locator('#predictionWhat')).toContainText('rising optical screening-risk trend');
  await expect(page.locator('#predictionWhy')).toContainText('Vegetation index trend');
  await expect(page.locator('#predictionActions')).toContainText('Verify candidate change');
  await expect(page.locator('#predictionImpact')).toContainText('Screening-risk trend');
  await expect(page.locator('#predictionConfidence')).toContainText('model confidence');
  expect(fatal).toEqual([]);
});
