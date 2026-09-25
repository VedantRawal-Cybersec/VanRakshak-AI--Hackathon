const { test, expect } = require('@playwright/test');

function json(route, body, status=200){
  return route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
}

test('all explicit dashboard buttons can be dispatched without page errors', async ({ page }) => {
  const fatal=[];
  page.on('pageerror', e=>fatal.push(String(e)));

  await page.route('**/api/**', async route => {
    const req=route.request();
    const url=new URL(req.url());
    const p=url.pathname;
    if(p==='/api/demo-scenarios') return json(route,{count:1,scenarios:[{
      id:'kodagu',priority:'PRIMARY',name:'Kodagu Forest Region',state:'Karnataka',lat:12.3375,lon:75.8069,zoom:9.2,
      sentinel2:{before:{date:'2025-11-06',id:'B'},after:{date:'2026-02-04',id:'A'}},
      sentinel1:{matched_pair:true}
    }]});
    if(p==='/api/layers') return json(route,{groups:[]});
    if(p==='/api/health') return json(route,{ok:true,capabilities:{}});
    if(p==='/api/source-health') return json(route,{sources:[],healthy_sources:0,configured_sources:0});
    if(p==='/api/investigate') return json(route,{location:{lat:12.3375,lon:75.8069},sources:{
      weather:{ok:true,data:{current:{temperature_2m:24}}},
      fire:{ok:true,data:[],provenance:{source:'NASA EONET'}},
      human_pressure:{ok:true,data:{count:0,elements:[]}},
      news:{ok:true,data:[]},
      reverse_geocode:{ok:true,data:{display_name:'Kodagu, Karnataka',address:{state:'Karnataka'}}}
    }});
    if(p==='/api/forest-profile') return json(route,{location:{},satellite:{available_scenes:2},environment:{},human_pressure:{},fire:{},forest:{},terrain:{},earth_engine:{configured:false,values:{}},provenance:{},raw_sources:{}});
    if(p==='/api/analysis/vegetation-series') return json(route,{observations:[
      {datetime:'2025-11-06T00:00:00Z',mean_ndvi:.7,forest_fraction:.8},
      {datetime:'2026-01-01T00:00:00Z',mean_ndvi:.68,forest_fraction:.79},
      {datetime:'2026-02-04T00:00:00Z',mean_ndvi:.65,forest_fraction:.77}
    ]});
    if(p==='/api/analysis/evidence-chain') return json(route,{change:null,sar_change:null,climate:null,carbon:null,protected_area:null,evidence_chain:[],warning:{level:'UNKNOWN',score:0,coverage:0,factors:[]},forest_doctor:null,sources:{}});
    if(p==='/api/map/compare') return json(route,{before:{id:'B',observed_at:'2025-11-06T00:00:00Z',cloud_cover:.2,tile_url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png'},after:{id:'A',observed_at:'2026-02-04T00:00:00Z',cloud_cover:.1,tile_url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}});
    if(p==='/api/map/satellite-layer') return json(route,{tile_url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',source:'mock'});
    if(p.startsWith('/api/gibs/layer/')) return json(route,{tile_url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',date:'2026-02-04'});
    if(p==='/api/fire') return json(route,{ok:true,data:[],provenance:{source:'NASA EONET'}});
    if(p==='/api/fire/intelligence') return json(route,{context_level:'LOW',context_score:0});
    if(p==='/api/weather') return json(route,{ok:true,data:{current:{temperature_2m:24}},provenance:{source:'Open-Meteo'}});
    if(p==='/api/human-pressure') return json(route,{ok:true,data:{elements:[]}});
    if(p==='/api/protected-area/context') return json(route,{ok:true,data:{inside:false,areas:[]},provenance:{source:'OSM'}});
    if(p.startsWith('/api/satellite/')) return json(route,{ok:true,data:{features:[]}});
    if(p==='/api/geocode') return json(route,{ok:true,data:[{lat:'12.3375',lon:'75.8069',display_name:'Kodagu, Karnataka',geojson:{type:'Point',coordinates:[75.8069,12.3375]}}]});
    if(p==='/api/query') return json(route,{filters:{}});
    if(p==='/api/intelligence/predict') return json(route,{projection:[]});
    if(p==='/api/intelligence/predict-location') return json(route,{historical_risk_proxy:[8,12,18],dates:['2025-11-06','2026-01-01','2026-02-04'],analysis:{current_risk_index:18,interpretation:'Screening risk is rising.',observation_count:3},projection:{projected_values:[22,25],forecast_dates:['2026-03-01','2026-04-01'],lower:[18,19],upper:[26,31],trend_per_step:4,analysis:{direction:'INCREASING',strength:'MODERATE',confidence_pct:78,forecast_final:25,risk_level:'MODERATE',observations:3},pipeline:['Fit robust trends']},pipeline:['Read Sentinel-2 scenes'],generated_at:'2026-09-25T04:00:00Z',source_series:[]});
    if(p==='/api/intelligence/what-if') return json(route,{baseline:{},scenario:{}});
    if(p==='/api/patrol/road-route'||p==='/api/patrol/live') return json(route,{status:'ROAD_ROUTE_READY',analysis:{candidate_area_ha:2.4,screening_confidence:.84,warning_score:77,before_observed_at:'2025-11-06T00:00:00Z',after_observed_at:'2026-02-04T00:00:00Z'},ordering:{ordering_mode:'ROAD_TIME_PRIORITY',route:[{order:1,id:'hotspot-1',lat:12.35,lon:75.82,priority:90,priority_band:'CRITICAL',candidate_context:{area_ha:1.8},why_selected:'Critical priority balanced against road travel time.'}]},road_route:{distance_km:4.2,duration_min:11,source:'OSRM/OpenStreetMap',geometry:{type:'LineString',coordinates:[[75.8069,12.3375],[75.82,12.35]]},legs:[{steps:[{instruction:'Continue on Forest Road',distance_m:900,duration_min:2.4}]}]}});
    if(p.startsWith('/api/report')) return route.fulfill({status:200,contentType:'application/pdf',body:'%PDF-1.4\n%%EOF'});
    return json(route,{ok:true,data:{},features:[],groups:[],scenes:[]});
  });

  await page.goto('/');
  await expect(page.locator('#map')).toBeVisible();
  await page.waitForTimeout(700);

  const ids=await page.locator('button[id]').evaluateAll(btns=>btns.map(b=>b.id));
  expect(ids.length).toBeGreaterThanOrEqual(35);

  for(const id of ids){
    const el=page.locator('#'+id);
    await el.evaluate(node=>node.click());
    await page.waitForTimeout(35);
  }

  await page.locator('[data-nav="predictions"]').evaluate(node=>node.click());
  await page.locator('#runLocationPrediction').evaluate(node=>node.click());
  await expect(page.locator('#predictionSummary .metric-card')).toHaveCount(8);
  await expect(page.locator('#predictionStatus')).toContainText('Screening risk is rising');

  await page.locator('#patrolBtn').evaluate(node=>node.click());
  await page.locator('#runDetectedPatrol').evaluate(node=>node.click());
  await expect(page.locator('#patrolMetrics .metric-card')).toHaveCount(8);
  await expect(page.locator('#patrolStops .route-stop')).toHaveCount(1);
  await expect(page.locator('#patrolInstructions')).toContainText('Forest Road');

  expect(fatal).toEqual([]);
});
