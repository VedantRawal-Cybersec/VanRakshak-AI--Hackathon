const { test, expect } = require('@playwright/test');

test.skip(process.env.PRODUCTION_E2E !== '1', 'production-only smoke suite');

test('production full stack is ready', async ({ request }) => {
  const health=await request.get('/api/health');
  expect(health.ok()).toBeTruthy();
  expect((await health.json()).ok).toBeTruthy();

  const ready=await request.get('/api/ready');
  expect(ready.ok()).toBeTruthy();
  const r=await ready.json();
  expect(r.ok).toBeTruthy();
  expect(r.checks.static).toBeTruthy();
  expect(r.checks.database).toBeTruthy();
  expect(r.checks.redis).toBeTruthy();
  expect(r.checks.titiler).toBeTruthy();

  const features=await request.get('/api/features/status');
  expect(features.ok()).toBeTruthy();
  expect((await features.json()).count).toBe(37);

  const cache=await request.get('/api/cache/status');
  expect(cache.ok()).toBeTruthy();
  expect((await cache.json()).persistent_backend).toBe('redis_with_memory_fallback');
});

test('production exposes preflight-verified demo scenarios', async ({ request }) => {
  const res=await request.get('/api/demo-scenarios');
  expect(res.ok()).toBeTruthy();
  const body=await res.json();
  expect(body.count).toBe(5);
  const primary=body.scenarios.filter(x=>x.priority==='PRIMARY');
  expect(primary.length).toBeGreaterThanOrEqual(3);
  expect(primary.every(x=>x.sentinel1?.matched_pair===true)).toBeTruthy();
});

test('Kodagu real optical comparison resolves from verified dates', async ({ request }) => {
  test.setTimeout(150000);
  const manifest=await (await request.get('/api/demo-scenarios')).json();
  const s=manifest.scenarios.find(x=>x.id==='kodagu');
  const q=new URLSearchParams({
    lat:String(s.lat),lon:String(s.lon),
    before_date:s.sentinel2.before.date,after_date:s.sentinel2.after.date,
    mode:'true_color',cloud_lt:'60'
  });
  const res=await request.get('/api/map/compare?'+q.toString(),{timeout:120000});
  expect(res.ok()).toBeTruthy();
  const body=await res.json();
  expect(body.before?.tile_url).toBeTruthy();
  expect(body.after?.tile_url).toBeTruthy();
  expect(body.before?.id || body.before?.scene_id).toBeTruthy();
  expect(body.after?.id || body.after?.scene_id).toBeTruthy();
});

test('Kodagu matched Sentinel-1 SAR analysis computes on production', async ({ request }) => {
  test.setTimeout(240000);
  const manifest=await (await request.get('/api/demo-scenarios')).json();
  const s=manifest.scenarios.find(x=>x.id==='kodagu');
  const q=new URLSearchParams({
    lat:String(s.lat),lon:String(s.lon),
    before_date:s.sentinel2.before.date,after_date:s.sentinel2.after.date,
    radius_km:'0.5',window_days:'30',drop_db_threshold:'2.5'
  });
  const res=await request.get('/api/analysis/sar-change?'+q.toString(),{timeout:220000});
  expect(res.ok()).toBeTruthy();
  const body=await res.json();
  expect(body.valid_pixels).toBeGreaterThan(50);
  expect(body.before?.id).toBeTruthy();
  expect(body.after?.id).toBeTruthy();
  expect(body.method).toMatch(/Sentinel-1/i);
});
