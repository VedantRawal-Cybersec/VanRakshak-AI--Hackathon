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
