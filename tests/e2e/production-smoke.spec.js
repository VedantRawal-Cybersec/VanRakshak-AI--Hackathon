const { test, expect } = require('@playwright/test');

test.skip(process.env.PRODUCTION_E2E !== '1', 'production-only smoke suite');

test('production full stack is ready', async ({ request }) => {
  const health=await request.get('/api/health');
  expect(health.ok()).toBeTruthy();
  expect((await health.json()).ok).toBeTruthy();

  const ready=await request.get('/api/ready');
  const readyText=await ready.text();
  console.log('READY_STATUS',ready.status(),'READY_BODY',readyText);
  expect(ready.ok(),readyText).toBeTruthy();
  const r=JSON.parse(readyText);
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
  expect(body.before?.item_id).toBeTruthy();
  expect(body.after?.item_id).toBeTruthy();
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
  const sarText=await res.text();
  console.log('SAR_STATUS',res.status(),'SAR_BODY',sarText.slice(0,1500));
  expect(res.ok(),sarText).toBeTruthy();
  const body=JSON.parse(sarText);
  expect(body.valid_pixels).toBeGreaterThan(50);
  expect(body.before?.id).toBeTruthy();
  expect(body.after?.id).toBeTruthy();
  expect(body.method).toMatch(/Sentinel-1/i);
});

function tileXY(lat,lon,z){
  const n=2**z;
  const x=Math.floor((lon+180)/360*n);
  const latRad=lat*Math.PI/180;
  const y=Math.floor((1-Math.asinh(Math.tan(latRad))/Math.PI)/2*n);
  return {x,y};
}

function renderedTileUrl(template,lat,lon,z=9){
  const {x,y}=tileXY(lat,lon,z);
  return template.replaceAll('{z}',String(z)).replaceAll('{x}',String(x)).replaceAll('{y}',String(y));
}

function expectHistoricalObservation(scene,requestedDate,maxDays=550){
  expect(scene?.requested_date).toBe(requestedDate);
  expect(scene?.observed_at).toBeTruthy();
  const observed=Date.parse(scene.observed_at);
  const requested=Date.parse(requestedDate+'T00:00:00Z');
  expect(Number.isFinite(observed)).toBeTruthy();
  expect(Math.abs(observed-requested)).toBeLessThanOrEqual((maxDays+2)*86400000);
  expect(Number(scene.date_offset_days)).toBeGreaterThanOrEqual(0);
}

test('historical Landsat before-after comparisons render real tiles', async ({ request }) => {
  test.setTimeout(600000);
  const lat=12.3375,lon=75.8069;
  const cases=[
    {before:'1987-06-01',after:'2001-06-01',mode:'true_color'},
    {before:'2001-06-01',after:'2011-06-01',mode:'ndvi'},
  ];

  for(const row of cases){
    const q=new URLSearchParams({
      lat:String(lat),lon:String(lon),
      before_date:row.before,after_date:row.after,
      mode:row.mode,window_days:'90',cloud_lt:'100'
    });
    const res=await request.get('/api/map/compare?'+q.toString(),{timeout:240000});
    const text=await res.text();
    console.log('HISTORICAL_COMPARE',row,text.slice(0,1600));
    expect(res.ok(),text).toBeTruthy();

    const body=JSON.parse(text);
    for(const [side,requested] of [['before',row.before],['after',row.after]]){
      const scene=body[side];
      expect(scene?.item_id).toBeTruthy();
      expect(scene?.source).toMatch(/Landsat/i);
      expect(scene?.tile_url).toBeTruthy();
      expectHistoricalObservation(scene,requested,550);

      const tileUrl=renderedTileUrl(scene.tile_url,lat,lon,9);
      const tile=await request.get(tileUrl,{timeout:240000});
      const tileText=tile.ok()?'':await tile.text();
      expect(tile.ok(),`${side} ${requested} tile failed: ${tile.status()} ${tileText.slice(0,500)}`).toBeTruthy();
      expect(tile.headers()['content-type']||'').toMatch(/image\/png/i);
      expect((await tile.body()).length).toBeGreaterThan(100);
    }
  }
});
