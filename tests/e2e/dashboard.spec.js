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
