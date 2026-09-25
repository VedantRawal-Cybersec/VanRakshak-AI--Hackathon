const {test,expect}=require('@playwright/test');

test('non-WebGL devices retain maps, tabs, timeline and manual prediction',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/.test(type)?null:original.call(this,type,...args)}});
  await page.route('**/api/**',route=>{
    const path=new URL(route.request().url()).pathname;
    let body={};
    if(path==='/api/layers')body={groups:[]};
    if(path==='/api/demo-scenarios')body={scenarios:[]};
    if(path==='/api/investigate')body={sources:{}};
    if(path==='/api/source-health')body={sources:[]};
    if(path==='/api/map/compare')return route.fulfill({status:404,json:{detail:'No scene in requested window'}});
    if(path==='/api/intelligence/predict')body={projected_values:[40,50,60],label:'AI_ESTIMATE'};
    return route.fulfill({json:body});
  });
  await page.goto('/');
  await expect(page.locator('#map')).toHaveClass(/leaflet-container/);
  await page.getByRole('button',{name:'Before / After',exact:true}).click();
  await expect(page.locator('#beforeDate')).toBeVisible();
  await page.locator('#beforeDate').fill('1987-06-01');
  await page.locator('#afterDate').fill('2011-06-01');
  await page.locator('#loadInlineCompare').click();
  await expect(page.locator('#compareMeta')).toContainText('No scene');
  await page.locator('#openTime').click();
  await expect(page.locator('#timeModal')).toBeVisible();
  await page.locator('#closeTime').click();
  await page.locator('[data-nav="predictions"]').click();
  await page.locator('#predictionValues').fill('10,20,30');
  const request=page.waitForRequest(r=>r.url().endsWith('/api/intelligence/predict'));
  await page.locator('#runPrediction').click();
  expect((await request).postDataJSON().values).toEqual([10,20,30]);
  await expect(page.locator('#predictionResult')).toContainText('User-entered series');
  expect(errors).toEqual([]);
});
