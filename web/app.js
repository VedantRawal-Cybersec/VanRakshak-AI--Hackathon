const API='';
const $=(id)=>document.getElementById(id);
const $$=(sel)=>Array.from(document.querySelectorAll(sel));
const state={
  lat:12.3375,lon:75.8069,place:'Kodagu Forest Region',regionSub:'Karnataka, India',
  investigation:null,profile:null,evidence:null,layers:[],active:new Map(),sourceHealth:null,
  inlineBefore:null,inlineAfter:null,panelBefore:null,panelAfter:null,modalBefore:null,modalAfter:null,
  timeMap:null,timeScenes:[],timeIndex:0,timeTimer:null,trendChart:null
};

const baseStyle={
  version:8,
  sources:{
    imagery:{type:'raster',tiles:['https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Esri World Imagery'},
    labels:{type:'raster',tiles:['https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Esri'}
  },
  layers:[
    {id:'imagery',type:'raster',source:'imagery',paint:{'raster-saturation':-.08,'raster-contrast':.08,'raster-brightness-min':.05,'raster-brightness-max':.84}},
    {id:'labels',type:'raster',source:'labels',paint:{'raster-opacity':.9}}
  ]
};

function toast(msg,ms=3300){const t=$('toast');t.textContent=msg;t.classList.remove('hidden');clearTimeout(t._timer);t._timer=setTimeout(()=>t.classList.add('hidden'),ms)}
async function api(path,opts={}){const r=await fetch(API+path,opts);if(!r.ok)throw new Error(`${r.status} ${await r.text()}`);return r.json()}
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function isoDate(d){return d.toISOString().slice(0,10)}
function clamp(v,min,max){return Math.max(min,Math.min(max,v))}
function pct(v,digits=0){if(v==null||Number.isNaN(Number(v)))return '—';const n=Number(v);return `${(Math.abs(n)<=1?n*100:n).toFixed(digits)}%`}
function fmt(v,d=1){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(d)}
function setText(id,val){const el=$(id);if(el)el.textContent=val}
function showTab(name){$$('.right-tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));$$('.right-panel-view').forEach(x=>x.classList.toggle('active',x.id===`tab-${name}`));}
function incidentId(){const d=new Date();return `VR-${d.getFullYear()}-${String(Math.abs(Math.round(state.lat*100))+Math.abs(Math.round(state.lon*100))).padStart(4,'0').slice(-4)}`}

const now=new Date();
const yearAgo=new Date(now);yearAgo.setFullYear(now.getFullYear()-1);
const monthAgo=new Date(now);monthAgo.setDate(now.getDate()-30);
const threeYearsAgo=new Date(now);threeYearsAgo.setFullYear(now.getFullYear()-3);
['endDate','afterDate','modalAfterDate','timeEnd'].forEach(id=>{if($(id))$(id).value=isoDate(now)});
['startDate'].forEach(id=>{if($(id))$(id).value=isoDate(monthAgo)});
['beforeDate','modalBeforeDate'].forEach(id=>{if($(id))$(id).value=isoDate(yearAgo)});
if($('timeStart'))$('timeStart').value=isoDate(threeYearsAgo);

const map=new maplibregl.Map({container:'map',center:[78.8,22.5],zoom:4.25,style:baseStyle,minZoom:3,maxZoom:16});
map.addControl(new maplibregl.NavigationControl({showCompass:true}),'top-right');
map.on('click',e=>investigate(e.lngLat.lat,e.lngLat.lng,'Selected Forest Region'));

function ensureLocation(){if(state.lat==null||state.lon==null){toast('Select a location on the map first.');return false}return true}
function fitSelected(){if(!ensureLocation())return;map.flyTo({center:[state.lon,state.lat],zoom:10,essential:true});}

function removeLayer(id){const rec=state.active.get(id);if(!rec)return;try{if(map.getLayer(rec.layer))map.removeLayer(rec.layer);if(map.getSource(rec.source))map.removeSource(rec.source)}catch{}state.active.delete(id)}
function addRaster(id,tileUrl,opacity=.72){removeLayer(id);const source=`src-${id}`,layer=`lyr-${id}`;map.addSource(source,{type:'raster',tiles:[tileUrl],tileSize:256});map.addLayer({id:layer,type:'raster',source,paint:{'raster-opacity':opacity}},map.getLayer('labels')?'labels':undefined);state.active.set(id,{source,layer})}
function addGeoPoints(id,features,color='#ff4d5a'){removeLayer(id);const source=`src-${id}`,layer=`lyr-${id}`;map.addSource(source,{type:'geojson',data:{type:'FeatureCollection',features}});map.addLayer({id:layer,type:'circle',source,paint:{'circle-radius':['interpolate',['linear'],['zoom'],4,3,10,6],'circle-color':color,'circle-stroke-width':1,'circle-stroke-color':'#fff','circle-opacity':.88}});state.active.set(id,{source,layer})}
function addGeoPolygon(id,geojson,color='#ff4d5a'){removeLayer(id);const source=`src-${id}`,fill=`lyr-${id}`;map.addSource(source,{type:'geojson',data:geojson});map.addLayer({id:fill,type:'fill',source,paint:{'fill-color':color,'fill-opacity':.32}},map.getLayer('labels')?'labels':undefined);const outline=`${fill}-line`;map.addLayer({id:outline,type:'line',source,paint:{'line-color':color,'line-width':2}});state.active.set(id,{source,layer:fill,outline})}
function clearDynamicLayer(id){const rec=state.active.get(id);if(!rec)return;try{if(rec.outline&&map.getLayer(rec.outline))map.removeLayer(rec.outline)}catch{}removeLayer(id)}

async function loadLayers(){try{const d=await api('/api/layers');state.layers=d.groups||[];renderLayers()}catch(e){toast('Layer registry unavailable: '+e.message)}}
function selectedFilters(){return {fresh:$('freshnessFilter')?.value||'',res:Number($('resolutionFilter')?.value||0),cloud:Number($('cloudFilter')?.value||50),start:$('startDate')?.value||'',end:$('endDate')?.value||'',confidence:$('confidenceFilter')?.value||'high'}}
function allLayers(){return state.layers.flatMap(g=>g.layers||[])}
function findLayerBy(predicate){return allLayers().find(predicate)}
function renderLayers(){if(!$('layerGroups'))return;const {fresh,res}=selectedFilters();$('layerGroups').innerHTML=state.layers.map(g=>{const rows=(g.layers||[]).filter(l=>(!fresh||l.freshness===fresh)&&(!res||!l.resolution_m||l.resolution_m<=res)).map(l=>`<div class="layer-row"><label><input type="checkbox" data-layer="${esc(l.id)}" ${state.active.has(l.id)?'checked':''}> ${esc(l.label)}</label><span class="layer-meta">${esc(l.source||'')}<br>${l.resolution_m?esc(l.resolution_m)+' m ':''}${esc(l.freshness||'')}</span></div>`).join('');return rows?`<div class="layer-group"><h3>${esc(g.icon||'')} ${esc(g.label)}</h3>${rows}</div>`:''}).join('');$$('[data-layer]').forEach(x=>x.onchange=()=>toggleLayer(findLayerBy(l=>l.id===x.dataset.layer),x.checked,x))}

async function toggleLayer(def,enabled,checkbox){if(!def)return;if(!enabled){clearDynamicLayer(def.id);return}const f=selectedFilters();try{
  if(def.render==='satellite'){const s=await api(`/api/map/satellite-layer?lat=${state.lat}&lon=${state.lon}&mode=${def.mode||'true_color'}&cloud_lt=${f.cloud}`);addRaster(def.id,s.tile_url,def.mode==='true_color'?.9:.74);toast(`${def.label} loaded from ${s.source||'satellite source'}`)}
  else if(def.render==='gfw'){let q=`/api/map/gfw-layer?dataset=${encodeURIComponent(def.dataset)}&confidence=${f.confidence}`;if(f.start)q+=`&start_date=${f.start}`;if(f.end)q+=`&end_date=${f.end}`;const s=await api(q);addRaster(def.id,s.tile_url,.76);toast(`${def.label} enabled`)}
  else if(def.render==='gibs'){const d=f.end||isoDate(new Date(Date.now()-86400000));const s=await api(`/api/gibs/layer/${encodeURIComponent(def.gibs_layer)}?date=${encodeURIComponent(d)}`);addRaster(def.id,s.tile_url,.84);toast(`${def.label} enabled from NASA GIBS • ${s.date}`)}
  else if(def.render==='earth_engine'){
    try{const s=await api(`/api/earth-engine/layer/${encodeURIComponent(def.ee_layer)}?lat=${state.lat}&lon=${state.lon}`);addRaster(def.id,s.tile_url,.72);toast(`${def.label} enabled via Earth Engine`)}
    catch(eeErr){
      if(['dynamic_world_trees','dynamic_world_label'].includes(def.ee_layer)){
        const s=await api('/api/map/gfw-layer?dataset=umd_tree_cover_density_2000&confidence=high');addRaster(def.id,s.tile_url,.7);toast(`${def.label}: GFW tree-cover fallback active`)
      }else if(def.ee_layer==='jrc_water_occurrence'){
        const s=await api(`/api/map/satellite-layer?lat=${state.lat}&lon=${state.lon}&mode=ndwi&cloud_lt=${f.cloud}`);addRaster(def.id,s.tile_url,.75);toast('Water context: Sentinel-2 NDWI fallback active')
      }else if(def.ee_layer==='modis_burned_area'){
        const s=await api('/api/map/gfw-layer?dataset=umd_tree_cover_loss_from_fires&confidence=high');addRaster(def.id,s.tile_url,.74);toast('Fire-loss history fallback active from GFW')
      }else if(['modis_lst','chirps_rainfall'].includes(def.ee_layer)){
        showTab('environment');const w=await api(`/api/weather?lat=${state.lat}&lon=${state.lon}`);if(!w.ok)throw eeErr;addGeoPoints(def.id,[{type:'Feature',geometry:{type:'Point',coordinates:[state.lon,state.lat]},properties:{source:'Open-Meteo fallback'}}],'#4ea8ff');toast(`${def.label}: Open-Meteo point fallback active`)
      }else if(['worldpop_population','human_modification'].includes(def.ee_layer)){
        const s=await api(`/api/human-pressure?lat=${state.lat}&lon=${state.lon}&radius_m=10000`);if(!s.ok)throw eeErr;const feats=(s.data?.elements||[]).map(e=>{const lat=e.lat??e.center?.lat,lon=e.lon??e.center?.lon;if(lat==null||lon==null)return null;return {type:'Feature',geometry:{type:'Point',coordinates:[Number(lon),Number(lat)]},properties:e.tags||{}}}).filter(Boolean);addGeoPoints(def.id,feats,'#f2b43a');toast(`${def.label}: OSM human-pressure fallback active`)
      }else if(['srtm_elevation','srtm_slope','srtm_aspect','gedi_agbd','wcmc_carbon_density'].includes(def.ee_layer)){
        showTab(def.ee_layer.startsWith('srtm_')?'environment':'profile');const vals=state.profile||{};const fallbackValue=def.ee_layer==='srtm_elevation'?vals.terrain?.elevation_m:def.ee_layer==='srtm_slope'?vals.terrain?.slope_deg:def.ee_layer==='srtm_aspect'?vals.terrain?.aspect_deg:def.ee_layer==='gedi_agbd'?vals.forest?.gedi_agbd_mg_per_ha:vals.forest?.carbon_density_t_per_ha_reference;if(fallbackValue!=null){addGeoPoints(def.id,[{type:'Feature',geometry:{type:'Point',coordinates:[state.lon,state.lat]},properties:{value:fallbackValue}}],'#56d893');toast(`${def.label}: available point reference ${fmt(fallbackValue,1)}`)}else{toast(`${def.label}: optional high-detail source unavailable; core feature remains active through profile/evidence fallbacks.`)}
      }else throw eeErr
    }
  }
  else if(def.render==='firms_points'){await enableFireLayer(def.id)}
  else if(def.render==='protected_context'){const s=await api(`/api/protected-area/context?lat=${state.lat}&lon=${state.lon}`);if(!s.ok)throw new Error(s.error||'Protected-area context unavailable');const areas=s.data?.areas||[];const feats=areas.map(a=>{const c=a.center;if(!c?.lat||!c?.lon)return null;return {type:'Feature',geometry:{type:'Point',coordinates:[Number(c.lon),Number(c.lat)]},properties:a.tags||{}}}).filter(Boolean);if(feats.length)addGeoPoints(def.id,feats,'#26d98b');toast(`${s.data?.inside?'Inside':'No containing'} protected area • ${s.provenance?.source||'reference source'}`)}
  else if(def.render==='overpass'){const s=await api(`/api/human-pressure?lat=${state.lat}&lon=${state.lon}&radius_m=10000`);if(!s.ok)throw new Error(s.error||'Human-pressure provider unavailable');const feats=(s.data?.elements||[]).map(e=>{const lat=e.lat??e.center?.lat,lon=e.lon??e.center?.lon;if(lat==null||lon==null)return null;return {type:'Feature',geometry:{type:'Point',coordinates:[Number(lon),Number(lat)]},properties:e.tags||{}}}).filter(Boolean);addGeoPoints(def.id,feats,'#f2b43a');toast(`${feats.length} mapped human-pressure features`)}
  else if(def.render==='metadata'||def.render==='planned_adapter'){
    const endpoint=def.id==='sentinel1'?'/api/satellite/sentinel1':def.id==='landsat'?'/api/satellite/landsat':'/api/satellite/latest';
    const s=await api(`${endpoint}?lat=${state.lat}&lon=${state.lon}&days=90`);if(!s.ok)throw new Error(s.error||'Catalogue unavailable');
    const rows=s.data?.features||[];const feats=rows.filter(x=>x.geometry).map(x=>({type:'Feature',geometry:x.geometry,properties:{id:x.id,...(x.properties||{})}}));
    if(feats.length)addGeoPolygon(def.id,{type:'FeatureCollection',features:feats},def.id==='sentinel1'?'#4ea8ff':'#56d893');
    toast(`${def.label}: ${rows.length} catalogue scenes found`);
  }
  else if(def.render==='point_data'){
    showTab('environment');let s;
    if(['soil_type','soil_ph','soc','nitrogen','texture','bulk_density','cec'].includes(def.id))s=await api(`/api/soil?lat=${state.lat}&lon=${state.lon}`);
    else s=await api(`/api/weather?lat=${state.lat}&lon=${state.lon}`);
    if(!s.ok)throw new Error(s.error||'Point data unavailable');
    addGeoPoints(def.id,[{type:'Feature',geometry:{type:'Point',coordinates:[state.lon,state.lat]},properties:{layer:def.label,source:s.provenance?.source||def.source}}],'#4ea8ff');
    toast(`${def.label} loaded • ${s.provenance?.source||def.source}`);
  }
  else if(def.render==='analysis'){
    showTab('analysis');
    if(def.id==='fire_risk'){const d=await api(`/api/fire/intelligence?lat=${state.lat}&lon=${state.lon}&days=1`);toast(`Fire-weather context: ${d.context_level} • ${d.context_score}/100`)}
    else if(['temperature_anomaly','rainfall_anomaly','drought'].includes(def.id)){const d=await api(`/api/climate/anomaly?lat=${state.lat}&lon=${state.lon}`);toast(`${def.label}: temp Δ ${fmt(d.temperature_anomaly_c,1)}°C • rain deficit ${fmt(d.rainfall_deficit_pct,0)}%`)}
    else if(def.id==='vegetation_health'){const d=await api(`/api/analysis/vegetation-series?lat=${state.lat}&lon=${state.lon}&start=${isoDate(yearAgo)}&end=${isoDate(now)}&max_observations=8`);toast(`Vegetation health: ${(d.observations||[]).length} cloud-screened Sentinel observations`)}
    else if(['fragmentation','carbon_loss'].includes(def.id)){await loadEvidence(true)}
    else if(def.id==='erosion'){const slope=state.profile?.terrain?.slope_deg;toast(slope!=null?`Terrain context: slope ${fmt(slope,1)}°`:'Erosion context opened; slope raster is an optional Earth Engine enhancement.')}
    else toast(`${def.label} opened in analysis panel`);
  }
  else{showTab('analysis');toast(`${def.label} opened in its investigation/profile workflow.`)}
}catch(e){if(checkbox)checkbox.checked=false;clearDynamicLayer(def.id);toast(`${def.label}: ${String(e.message).slice(0,170)}`)}}

async function quickLayer(kind){$$('.map-pill').forEach(x=>x.classList.toggle('active',x.dataset.quick===kind));try{
  if(kind==='satellite'){const d=await api(`/api/map/satellite-layer?lat=${state.lat}&lon=${state.lon}&mode=true_color&cloud_lt=60`);addRaster('quick-satellite',d.tile_url,.88);toast('Latest suitable Sentinel-2 imagery loaded')}
  if(kind==='ndvi'){const d=await api(`/api/map/satellite-layer?lat=${state.lat}&lon=${state.lon}&mode=ndvi&cloud_lt=60`);addRaster('quick-ndvi',d.tile_url,.78);toast('NDVI layer loaded')}
  if(kind==='fire'){await enableFireLayer('quick-fire')}
  if(kind==='temperature'){showTab('environment');const cur=state.investigation?.sources?.weather?.data?.current||{};const t=findLayerBy(l=>(l.ee_layer||'').includes('modis')&&(l.label||'').toLowerCase().includes('temp'));if(t&&state.sourceHealth?.sources?.some(x=>x.source==='Google Earth Engine'&&x.ok)){await toggleLayer(t,true,null)}toast(cur.temperature_2m!=null?`Temperature intelligence: ${cur.temperature_2m}°C • Open-Meteo`:'Temperature intelligence panel opened')}
  if(kind==='forest'){const f=findLayerBy(l=>l.id==='tree_cover_2000')||findLayerBy(l=>l.id==='forest_loss')||findLayerBy(l=>/forest cover|dynamic world/i.test(`${l.label||''} ${l.id||''}`));if(f)await toggleLayer(f,true,null);else{showTab('analysis');toast('Forest profile opened.')}}
}catch(e){toast(String(e.message).slice(0,180))}}

async function enableFireLayer(id='fire-hotspots'){const s=await api(`/api/fire?lat=${state.lat}&lon=${state.lon}&days=1`);if(!s.ok)throw new Error(s.error||'Fire intelligence unavailable');const feats=(s.data||[]).map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[Number(r.longitude),Number(r.latitude)]},properties:r})).filter(x=>Number.isFinite(x.geometry.coordinates[0])&&Number.isFinite(x.geometry.coordinates[1]));addGeoPoints(id,feats,'#ff423d');toast(`${feats.length} fire-context points • ${s.provenance?.source||'NASA source'}`)}

async function investigate(lat,lon,place='Selected Forest Region'){
  state.lat=Number(lat);state.lon=Number(lon);state.place=place||'Selected Forest Region';
  setText('regionTitle',state.place);setText('coords',`${state.lat.toFixed(4)}, ${state.lon.toFixed(4)} • India`);setText('incidentId',incidentId());setText('mapStatus','Gathering source-backed forest intelligence…');
  ['areaAffected','aiConfidence','ndviChange','riskScore'].forEach(id=>setText(id,'…'));
  try{
    const [inv,profile]=await Promise.all([
      api(`/api/investigate?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}`),
      api(`/api/forest-profile?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}`)
    ]);
    state.investigation=inv;state.profile=profile;renderInvestigation(inv);renderProfile(profile);renderEnvironment(inv,profile);renderNews(inv.sources?.news);await Promise.allSettled([loadEvidence(false),loadTrend(),loadInlineCompare(false),loadSourceHealth(false)]);setText('mapStatus','Latest available observations loaded • source timestamps retained');
  }catch(e){setText('mapStatus','Some providers unavailable');toast('Investigation: '+String(e.message).slice(0,170))}
}

function renderInvestigation(d){const s=d.sources||{};const reverse=s.reverse_geocode?.data||{};const addr=reverse.address||{};if(reverse.display_name){const district=addr.state_district||addr.county||addr.city||addr.town;const st=addr.state;state.regionSub=[district,st,'India'].filter(Boolean).slice(0,3).join(', ');setText('coords',state.regionSub);setText('sumRegionSub',state.regionSub)}
  const shortName=(addr.state_district||addr.county||state.place||'Selected Region').replace(/ district/i,'');setText('sumRegion',shortName);setText('regionTitle',state.place||shortName);
  const fires=s.fire?.ok?(s.fire.data||[]):[];const fireSource=s.fire?.provenance?.source||'NASA fire intelligence';setText('sumFire',s.fire?.ok?String(fires.length):'—');setText('sumFireDelta',s.fire?.ok?fireSource.replace('NASA ','').slice(0,31):(s.fire?.error||'Fire sources unavailable').slice(0,31));setText('navAlertBadge',s.fire?.ok?String(fires.length):'—');
  const cur=s.weather?.ok?s.weather.data?.current:null;if(cur){setText('regionThumb',cur.temperature_2m!=null?`${Math.round(cur.temperature_2m)}°`:'🌲')}
  renderEnvironment(d,state.profile);
  renderNews(s.news);
}

function renderProfile(p){if(!p)return;state.profile=p;const loc=p.location||{},forest=p.forest||{},env=p.environment||{},terrain=p.terrain||{},human=p.human_pressure||{},fire=p.fire||{};const conservation=p.conservation||{};const pa=conservation?.inside===true||conservation?.value===1||conservation?.inside_protected_area===true?'Inside protected area':conservation?.error?'Unavailable':conservation?.inside===false?'No containing protected area found':'Not confirmed';
  $('profilePanel').innerHTML=`<div class="profile-grid"><div><small>Location</small><b>${esc(loc.display_name||state.place)}</b></div><div><small>Latest Sentinel scene</small><b>${esc(p.satellite?.latest_scene_time||'—')}</b></div><div><small>Dynamic World tree probability</small><b>${forest.dynamic_world_tree_probability!=null?pct(forest.dynamic_world_tree_probability,1):'—'}</b></div><div><small>GEDI biomass</small><b>${forest.gedi_agbd_mg_per_ha!=null?fmt(forest.gedi_agbd_mg_per_ha,1)+' Mg/ha':'—'}</b></div><div><small>Elevation</small><b>${terrain.elevation_m!=null?fmt(terrain.elevation_m,0)+' m':'—'}</b></div><div><small>Slope</small><b>${terrain.slope_deg!=null?fmt(terrain.slope_deg,1)+'°':'—'}</b></div><div><small>Temperature</small><b>${env.temperature_c??'—'} °C</b></div><div><small>Humidity</small><b>${env.humidity_pct??'—'}%</b></div><div><small>Mapped human pressure</small><b>${human.mapped_features??'—'}</b></div><div><small>Fire detections</small><b>${fire.detections_in_window??'—'}</b></div><div><small>Protected status</small><b>${esc(pa)}</b></div><div><small>Earth Engine</small><b>${p.earth_engine?.configured?'Configured':'Credential gated'}</b></div></div>`;
}

function renderEnvironment(inv,profile){const s=inv?.sources||{};const cur=s.weather?.ok?s.weather.data?.current||{}:{};const e=profile?.environment||{};const t=profile?.terrain||{};const soil=s.soil;const fire=s.fire;const cards=[
  ['Temperature',cur.temperature_2m??e.temperature_c, '°C'],['Humidity',cur.relative_humidity_2m??e.humidity_pct,'%'],['Rain',cur.rain??e.rain_mm,' mm'],['Cloud cover',cur.cloud_cover??e.cloud_cover_pct,'%'],['Wind',cur.wind_speed_10m??e.wind_kmh,' km/h'],['Elevation',t.elevation_m,' m'],['Slope',t.slope_deg,'°'],['SoilGrids',soil?.ok?'Available':'Unavailable',''],['Fire source',fire?.ok?`${(fire.data||[]).length} • ${fire.provenance?.source||'NASA'}`:'Unavailable',''],['Earth Engine',profile?.earth_engine?.configured?'Configured':'Optional enhancement','']
];$('environmentPanel').innerHTML=cards.map(([k,v,u])=>`<div class="env-card"><small>${esc(k)}</small><strong>${v==null?'—':esc(v)}${typeof v==='number'?u:''}</strong></div>`).join('')}
function renderNews(n){if(!n||!n.ok){$('newsPanel').innerHTML=`<div class="empty-state">${esc(n?.error||'News context unavailable')}</div>`;return}const arts=n.data?.articles||[];$('newsPanel').innerHTML=arts.length?arts.slice(0,10).map(a=>`<article class="news-item"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title||a.url)}</a><small>${esc(a.domain||'')} • ${esc(a.seendate||'')}</small></article>`).join(''):'<div class="empty-state">No matching recent articles returned.</div>'}

async function loadEvidence(showToast=true){if(!ensureLocation())return null;const before=$('beforeDate').value,after=$('afterDate').value;try{if(showToast)toast('Running satellite change + evidence fusion…',5000);const q=`/api/analysis/evidence-chain?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}&before_date=${encodeURIComponent(before)}&after_date=${encodeURIComponent(after)}&radius_km=2`;const d=await api(q);state.evidence=d;renderEvidence(d);if(showToast)toast('Evidence analysis completed');return d}catch(e){if(showToast)toast('Analysis: '+String(e.message).slice(0,170));renderEvidence({warning:{level:'UNKNOWN',score:null,coverage:0,factors:[]},evidence_chain:{items:[]}});return null}}

function renderEvidence(d){const c=d.change||{},w=d.warning||{},doctor=d.forest_doctor||{},carbon=d.carbon||{};const conf=c.screening_confidence;setText('areaAffected',c.candidate_area_ha!=null?`${fmt(c.candidate_area_ha,1)} ha`:'—');setText('aiConfidence',conf!=null?pct(conf,0):'—');setText('ndviChange',c.mean_ndvi_change!=null?pct(c.mean_ndvi_change,0):'—');setText('riskScore',w.score!=null?`${fmt(w.score,0)}`:'—');setText('analysisWarning',w.level||'UNKNOWN');setText('analysisCoverage',w.coverage!=null?pct(w.coverage,0):'—');setText('sumAlerts',w.score!=null?`${fmt(w.score,0)}/100`:'—');setText('sumCritical',w.level||'UNKNOWN');setText('sumAlertsDelta',w.level?`${w.level} warning`:'Evidence-normalized');
  const sev=$('severityBadge');sev.textContent=w.level||'UNKNOWN';sev.className=`severity ${(w.level||'unknown').toLowerCase()}`;
  if(c.geojson){clearDynamicLayer('candidate-loss');addGeoPolygon('candidate-loss',c.geojson,'#ff473d')}
  const drivers=doctor.probable_drivers||[];renderCauseBars(drivers);renderSignalBars(w.factors||[]);
  const items=d.evidence_chain?.items||[];$('keyEvidence').innerHTML=items.length?items.slice(0,4).map(x=>`<div class="evidence-item"><span class="evidence-check">✓</span><span>${esc(x.statement||x.source||x.kind)}</span></div>`).join(''):'<div class="empty-state">No complete evidence items returned.</div>';
  $('evidenceChain').innerHTML=items.length?items.map(x=>`<p><b>${esc(x.kind)}</b> · ${esc(x.source)} — ${esc(x.statement)}</p>`).join(''):'<p>Evidence sources are unavailable or incomplete for the selected dates.</p>';
  setText('carbonImpact',carbon.estimated_co2e_t!=null?fmt(carbon.estimated_co2e_t,0):'—');setText('carbonImpactSub',carbon.estimated_co2e_t!=null?'tCO₂e estimated':'Requires biomass/carbon reference');
  if(d.protected_area===true){setText('protectedStatus','Inside Boundary');setText('protectedSub','WDPA / Protected Planet context')}else if(d.protected_area===false){setText('protectedStatus','Outside Boundary');setText('protectedSub','WDPA / Protected Planet context')}else{setText('protectedStatus','Unknown');setText('protectedSub','Configure Earth Engine or Protected Planet')}
  const fchange=c.fragmentation?.change||c.fragmentation_change||{};const fval=fchange.patch_count_pct??fchange.patch_density_pct??fchange.edge_density_pct??null;setText('fragmentationStatus',fval!=null?`${Number(fval)>=0?'+':''}${fmt(fval,0)}%`:'—');setText('fragmentationSub',fval!=null?'Patch isolation / edge change':'Derived when change mask exists');
  setText('changeResult',c.candidate_area_ha!=null?`${fmt(c.candidate_area_ha,2)} ha candidate vegetation loss • NDVI Δ ${fmt(c.mean_ndvi_change,3)} • warning ${w.level||'UNKNOWN'} ${w.score??'—'}/100`:'No complete before/after change result for the selected dates.');
}

function renderCauseBars(drivers){if(!drivers.length){$('causeBars').innerHTML='<div class="empty-state">Probable drivers require completed evidence analysis.</div>';return}$('causeBars').innerHTML=drivers.slice(0,4).map(x=>`<div class="cause-row"><span>${esc(x.driver)}</span><div class="cause-track"><div class="cause-fill" style="width:${clamp(Number(x.relative_support_pct)||0,0,100)}%"></div></div><b>${fmt(x.relative_support_pct,0)}%</b></div>`).join('')}
function renderSignalBars(factors){if(!factors.length){$('signalBars').innerHTML='<div class="empty-state">Run analysis to populate source-backed signals.</div>';return}$('signalBars').innerHTML=factors.slice(0,5).map((x,i)=>{const v=clamp(Number(x.contribution)||0,0,100);return `<div class="signal-row"><span>${esc(x.factor)}</span><div class="signal-track"><div class="signal-fill ${i>1?'amber':''}" style="width:${Math.max(4,v)}%"></div></div><b>${fmt(v,0)}</b></div>`}).join('')}

function newMiniMap(container,center,zoom=11){return new maplibregl.Map({container,center,zoom,style:baseStyle,interactive:true,attributionControl:false})}
function addSceneRaster(m,id,url){const draw=()=>{if(m.getLayer(id))m.removeLayer(id);if(m.getSource(id))m.removeSource(id);m.addSource(id,{type:'raster',tiles:[url],tileSize:256});m.addLayer({id,type:'raster',source:id,paint:{'raster-opacity':.96}},m.getLayer('labels')?'labels':undefined)};if(m.loaded())draw();else m.once('load',draw)}
function syncMaps(a,b){let lock=false;a.on('move',()=>{if(lock)return;lock=true;const c=a.getCenter();b.jumpTo({center:[c.lng,c.lat],zoom:a.getZoom(),bearing:a.getBearing(),pitch:a.getPitch()});lock=false});b.on('move',()=>{if(lock)return;lock=true;const c=b.getCenter();a.jumpTo({center:[c.lng,c.lat],zoom:b.getZoom(),bearing:b.getBearing(),pitch:b.getPitch()});lock=false})}
function destroyMap(key){if(state[key]){try{state[key].remove()}catch{}state[key]=null}}

async function loadInlineCompare(showToast=true){if(!ensureLocation())return;const before=$('beforeDate').value,after=$('afterDate').value;if(!before||!after)return;try{if(showToast)toast('Loading real Sentinel-2 before/after scenes…');const d=await api(`/api/map/compare?lat=${state.lat}&lon=${state.lon}&before_date=${before}&after_date=${after}&mode=true_color&cloud_lt=60`);setupInlineCompare(d);setupPanelCompare(d);setText('beforeInlineDate',(d.before.observed_at||before).slice(0,10));setText('afterInlineDate',(d.after.observed_at||after).slice(0,10));setText('compareMeta',`Before ${d.before.observed_at||before} • cloud ${d.before.cloud_cover??'—'}% | After ${d.after.observed_at||after} • cloud ${d.after.cloud_cover??'—'}%`);if(showToast)toast('Before/after scenes loaded')}catch(e){setText('compareMeta',String(e.message).slice(0,200));if(showToast)toast('Comparison: '+String(e.message).slice(0,160))}}
function setupInlineCompare(d){destroyMap('inlineBefore');destroyMap('inlineAfter');const center=[state.lon,state.lat],zoom=11;state.inlineBefore=newMiniMap('inlineBefore',center,zoom);state.inlineAfter=newMiniMap('inlineAfter',center,zoom);addSceneRaster(state.inlineBefore,'inline-b',d.before.tile_url);addSceneRaster(state.inlineAfter,'inline-a',d.after.tile_url);syncMaps(state.inlineBefore,state.inlineAfter);setTimeout(()=>{state.inlineBefore?.resize();state.inlineAfter?.resize()},300)}
function setupPanelCompare(d){destroyMap('panelBefore');destroyMap('panelAfter');const center=[state.lon,state.lat];state.panelBefore=newMiniMap('beforePanelMap',center,11);state.panelAfter=newMiniMap('afterPanelMap',center,11);addSceneRaster(state.panelBefore,'panel-b',d.before.tile_url);addSceneRaster(state.panelAfter,'panel-a',d.after.tile_url);syncMaps(state.panelBefore,state.panelAfter);setTimeout(()=>{state.panelBefore?.resize();state.panelAfter?.resize()},300)}
async function openFullCompare(){if(!ensureLocation())return;$('compareModal').classList.remove('hidden');$('modalBeforeDate').value=$('beforeDate').value;$('modalAfterDate').value=$('afterDate').value;await loadFullCompare()}
async function loadFullCompare(){const before=$('modalBeforeDate').value,after=$('modalAfterDate').value,mode=$('compareMode').value;try{const d=await api(`/api/map/compare?lat=${state.lat}&lon=${state.lon}&before_date=${before}&after_date=${after}&mode=${mode}&cloud_lt=60`);destroyMap('modalBefore');destroyMap('modalAfter');const center=[state.lon,state.lat];state.modalBefore=newMiniMap('compareBefore',center,11);state.modalAfter=newMiniMap('compareAfter',center,11);addSceneRaster(state.modalBefore,'modal-b',d.before.tile_url);addSceneRaster(state.modalAfter,'modal-a',d.after.tile_url);syncMaps(state.modalBefore,state.modalAfter);setText('compareModalMeta',`Before ${d.before.observed_at||before} • After ${d.after.observed_at||after} • ${mode}`);setTimeout(()=>{state.modalBefore?.resize();state.modalAfter?.resize()},300)}catch(e){setText('compareModalMeta',e.message)}}

async function loadTrend(){if(!ensureLocation()||typeof echarts==='undefined')return;try{const start=isoDate(threeYearsAgo),end=isoDate(now);const d=await api(`/api/analysis/vegetation-series?lat=${state.lat}&lon=${state.lon}&start=${start}&end=${end}&max_observations=12&cloud_lt=60`);const pts=d.observations||[];if(!pts.length)throw new Error('No cloud-screened scenes');if(state.trendChart)state.trendChart.dispose();state.trendChart=echarts.init($('forestTrendChart'));const dates=pts.map(x=>(x.datetime||'').slice(0,10));const ndvi=pts.map(x=>x.mean_ndvi??null);const forest=pts.map(x=>x.forest_fraction==null?null:Number(x.forest_fraction)*100);state.trendChart.setOption({animation:true,grid:{left:40,right:38,top:18,bottom:26},tooltip:{trigger:'axis'},xAxis:{type:'category',data:dates,axisLine:{lineStyle:{color:'#29414d'}},axisLabel:{color:'#91a59f',fontSize:9}},yAxis:[{type:'value',min:-1,max:1,axisLine:{show:false},splitLine:{lineStyle:{color:'#17313b'}},axisLabel:{color:'#91a59f',fontSize:9}},{type:'value',min:0,max:100,show:false}],series:[{name:'Mean NDVI',type:'line',smooth:.35,data:ndvi,symbol:'none',lineStyle:{width:2,color:'#72e57e'},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'#4fd47744'},{offset:1,color:'#4fd47700'}]}},markLine:{silent:true,lineStyle:{color:'#29414d'},data:[]}}, {name:'Forest fraction %',type:'line',smooth:.35,yAxisIndex:1,data:forest,symbol:'none',lineStyle:{width:1,color:'#a8d8a1'}}]});setText('trendSubtitle',`${state.place} • ${pts.length} Sentinel-2 observations`)}catch(e){setText('trendSubtitle','Trend unavailable: '+String(e.message).slice(0,80));if(state.trendChart){state.trendChart.clear()}}}

async function loadSourceHealth(showToast=true){try{const [h,sh]=await Promise.all([api('/api/health'),api('/api/source-health')]);state.sourceHealth=sh;const rows=sh.sources||[];const healthy=rows.filter(x=>x.ok).length,configured=rows.filter(x=>x.status!=='NOT_CONFIGURED').length;setText('sumSources',`${healthy}/${configured||rows.length}`);setText('sumSourcesDelta','Healthy/configured providers');const wanted=['Earth Search','Copernicus STAC','NASA GIBS','NASA EONET','Sentinel-1 ASF','NASA FIRMS','Open-Meteo','Protected Planet','Photon Geocoder','Earth Engine'];const selected=[];for(const name of wanted){const r=rows.find(x=>x.source===name);if(r)selected.push(r)}for(const r of rows){if(selected.length>=6)break;if(!selected.includes(r))selected.push(r)}$('sourceList').innerHTML=selected.slice(0,6).map(r=>{const cls=r.ok?'':' '+(r.status==='NOT_CONFIGURED'?'off':'err');return `<div class="source-row"><span class="source-logo">${sourceIcon(r.source)}</span><span>${esc(r.source)}</span><em class="source-status"><i class="source-dot${cls}"></i>${r.ok?(r.latency_ms!=null?`${fmt(r.latency_ms,0)} ms`:'Healthy'):(r.status==='NOT_CONFIGURED'?'Needs credential':'Unavailable')}</em></div>`}).join('');if(h.capabilities?.firms_configured===false&&$('sumFire').textContent==='—')setText('sumFireDelta','FIRMS key not configured at runtime');if(showToast)toast(`${healthy}/${configured||rows.length} configured sources healthy`);return sh}catch(e){$('sourceList').innerHTML='<div class="empty-state">Source health endpoint unavailable.</div>';if(showToast)toast('Source health unavailable');return null}}
function sourceIcon(name){name=name.toLowerCase();if(name.includes('sentinel')||name.includes('copernicus')||name.includes('earth search')||name.includes('gibs'))return '🛰';if(name.includes('firms')||name.includes('eonet'))return '🔥';if(name.includes('meteo'))return '☁';if(name.includes('protected'))return '🛡';if(name.includes('photon')||name.includes('nominatim'))return '⌖';if(name.includes('soil'))return '🌱';if(name.includes('earth engine'))return '🌍';return '●'}

function drawSearchBoundary(hit){const g=hit?.geojson;if(!g)return;for(const id of ['search-boundary-fill','search-boundary-line'])if(map.getLayer(id))map.removeLayer(id);if(map.getSource('search-boundary'))map.removeSource('search-boundary');map.addSource('search-boundary',{type:'geojson',data:{type:'Feature',properties:{},geometry:g}});map.addLayer({id:'search-boundary-fill',type:'fill',source:'search-boundary',paint:{'fill-color':'#20d67b','fill-opacity':.06}},map.getLayer('labels')?'labels':undefined);map.addLayer({id:'search-boundary-line',type:'line',source:'search-boundary',paint:{'line-color':'#e8fff4','line-width':1.6,'line-opacity':.9}})}
async function doSearch(){const q=$('searchBox').value.trim();if(!q)return;try{const g=await api('/api/geocode?q='+encodeURIComponent(q));if(g.ok&&g.data?.length){const hit=g.data[0];state.place=hit.display_name?.split(',').slice(0,2).join(',')||q;drawSearchBoundary(hit);map.flyTo({center:[Number(hit.lon),Number(hit.lat)],zoom:9.5,essential:true});await investigate(Number(hit.lat),Number(hit.lon),state.place);toast('Location resolved and investigation started');return}}catch{}try{const parsed=await api('/api/query?q='+encodeURIComponent(q));toast('AI Earth query parsed: '+JSON.stringify(parsed.filters||parsed));showTab('analysis');await loadEvidence(false)}catch(e){toast('Search: '+String(e.message).slice(0,160))}}

async function generateReport(){if(!ensureLocation())return;try{toast('Generating source-backed PDF report…',5000);const url=`/api/report/investigation?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}&before_date=${encodeURIComponent($('beforeDate').value)}&after_date=${encodeURIComponent($('afterDate').value)}`;const r=await fetch(url);if(!r.ok)throw new Error(`${r.status} ${await r.text()}`);const blob=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='vanrakshak-investigation-report.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1200);toast('Investigation report generated')}catch(e){toast('Report: '+String(e.message).slice(0,170))}}

async function runPrediction(useLocation=false){try{if(useLocation){$('predictionResult').textContent='Reading source-backed vegetation observations…';const d=await api(`/api/intelligence/predict-location?lat=${state.lat}&lon=${state.lon}&start=${isoDate(yearAgo)}&end=${isoDate(now)}&max_observations=8`);$('predictionResult').textContent=JSON.stringify(d,null,2)}else{const values=$('predictionValues').value.split(',').map(Number).filter(Number.isFinite);const d=await api('/api/intelligence/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values,steps:3,floor:0,ceiling:100})});$('predictionResult').textContent=JSON.stringify(d,null,2)}}catch(e){$('predictionResult').textContent=e.message}}
async function runWhatIf(){try{const sources=state.investigation?.sources||{},fires=sources.fire?.ok?(sources.fire.data||[]).length:0,pressure=sources.human_pressure?.ok?Math.min((sources.human_pressure.data?.count||0)/80,1):0;const baseWarning=state.evidence?.warning||{};const payload={base:{ndvi_drop:Math.max(0,-(state.evidence?.change?.mean_ndvi_change||0)),temp_anomaly_c:Math.max(0,state.evidence?.climate?.temperature_anomaly_c||0),rainfall_deficit_pct:Math.max(0,state.evidence?.climate?.rainfall_deficit_pct||0),fire_signal:Math.min(fires/10,1),protected_area:state.evidence?.protected_area===true,fragmentation_change:0,human_pressure:pressure,model_confidence:baseWarning.coverage||.5},temperature_delta_c:Number($('whatTemp').value||0),rainfall_delta_pct:Number($('whatRain').value||0),fire_delta:Number($('whatFire').value||0),ndvi_delta:0};const d=await api('/api/intelligence/what-if',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});$('whatIfResult').textContent=JSON.stringify(d,null,2)}catch(e){$('whatIfResult').textContent=e.message}}

function openPatrol(){if(!ensureLocation())return;$('patrolModal').classList.remove('hidden');if(!$('patrolPoints').value.trim())$('patrolPoints').value=`${state.lat.toFixed(5)},${state.lon.toFixed(5)},95`}
async function runPatrol(){try{const rows=$('patrolPoints').value.trim().split(/\n+/).filter(Boolean).map((r,i)=>{const [lat,lon,priority]=r.split(',').map(Number);if(!Number.isFinite(lat)||!Number.isFinite(lon)||!Number.isFinite(priority))throw new Error(`Bad row ${i+1}`);return {id:`target-${i+1}`,lat,lon,priority}});if(!rows.length)throw new Error('Add at least one patrol point');const d=await api('/api/patrol/road-route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_lat:state.lat,start_lon:state.lon,points:rows})});$('patrolResult').textContent=JSON.stringify(d,null,2);if(d.road_route?.geometry){clearDynamicLayer('patrol-route');map.addSource('src-patrol-route',{type:'geojson',data:{type:'Feature',properties:{},geometry:d.road_route.geometry}});map.addLayer({id:'lyr-patrol-route',type:'line',source:'src-patrol-route',paint:{'line-color':'#37e79c','line-width':4,'line-opacity':.95}});state.active.set('patrol-route',{source:'src-patrol-route',layer:'lyr-patrol-route'});fitSelected()}toast('Patrol route calculated')}catch(e){$('patrolResult').textContent=e.message}}

async function loadTime(){if(!ensureLocation())return;try{const d=await api(`/api/time-machine?lat=${state.lat}&lon=${state.lon}&start=${$('timeStart').value}&end=${$('timeEnd').value}&limit=70`);state.timeScenes=d.scenes||[];state.timeIndex=0;$('timeline').innerHTML=state.timeScenes.length?state.timeScenes.map((x,i)=>`<button class="timeline-item" data-scene="${i}"><b>${esc((x.datetime||'').slice(0,10))}</b><small>Cloud ${x.cloud_cover??'—'}%</small></button>`).join(''):'<div class="empty-state">No suitable scenes returned.</div>';$$('[data-scene]').forEach(btn=>btn.onclick=()=>showTimeScene(Number(btn.dataset.scene)));if(state.timeScenes.length)showTimeScene(0)}catch(e){$('timeline').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`}}
function showTimeScene(i){const scene=state.timeScenes[i];if(!scene)return;state.timeIndex=i;$$('[data-scene]').forEach(x=>x.classList.toggle('active',Number(x.dataset.scene)===i));if(!state.timeMap)state.timeMap=newMiniMap('timeMap',[state.lon,state.lat],9);addSceneRaster(state.timeMap,'time-raster',scene.tile_url);setText('timeCaption',`${(scene.datetime||'').slice(0,10)} • cloud ${scene.cloud_cover??'—'}% • Sentinel-2 L2A`)}
function toggleTimePlay(){if(state.timeTimer){clearInterval(state.timeTimer);state.timeTimer=null;$('playTime').textContent='▶ Play';return}if(!state.timeScenes.length)return toast('Load a timeline first');$('playTime').textContent='⏸ Pause';state.timeTimer=setInterval(()=>{state.timeIndex=(state.timeIndex+1)%state.timeScenes.length;showTimeScene(state.timeIndex)},1700)}

function openLayerDrawer(){$('layerDrawer').classList.remove('hidden');renderLayers()}

// Main interactions
$('searchBtn').onclick=doSearch;$('searchBox').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch()});$('brandHome').onclick=()=>map.flyTo({center:[78.8,22.5],zoom:4.25});
$$('[data-quick]').forEach(b=>b.onclick=()=>quickLayer(b.dataset.quick));$('layersBtn').onclick=openLayerDrawer;$('closeLayers').onclick=()=>$('layerDrawer').classList.add('hidden');$('freshnessFilter').onchange=renderLayers;$('resolutionFilter').onchange=renderLayers;
$$('.right-tab').forEach(b=>b.onclick=()=>showTab(b.dataset.tab));
$('inlineCompareSlider').oninput=e=>{const v=Number(e.target.value);$('inlineAfterWrap').style.left=`${v}%`;if(state.inlineAfter)state.inlineAfter.resize()};
$('expandCompare').onclick=openFullCompare;$('openCompareBtn').onclick=openFullCompare;$('closeCompare').onclick=()=>$('compareModal').classList.add('hidden');$('loadCompare').onclick=loadFullCompare;$('compareSlider').oninput=e=>{$('compareAfterWrap').style.width=`${e.target.value}%`;state.modalAfter?.resize()};
$('loadInlineCompare').onclick=()=>loadInlineCompare(true);$('runChangeAnalysis').onclick=()=>loadEvidence(true);$('runEvidenceAnalysis').onclick=()=>loadEvidence(true);
$('reportBtn').onclick=generateReport;$('generateReportNews').onclick=generateReport;$('reportsTop').onclick=generateReport;$('viewOnMapBtn').onclick=fitSelected;$('patrolBtn').onclick=openPatrol;
$('refreshSources').onclick=()=>loadSourceHealth(true);$('healthBtn').onclick=()=>loadSourceHealth(true);$('liveDataTop').onclick=()=>{showTab('overview');$('liveDataSection').scrollIntoView({behavior:'smooth',block:'center'});loadSourceHealth(true)};$('analyticsTop').onclick=()=>{$('analyticsSection').scrollIntoView({behavior:'smooth',block:'center'});toast('Source-backed regional analytics')};
$('aboutTop').onclick=()=>$('aboutModal').classList.remove('hidden');$('closeAbout').onclick=()=>$('aboutModal').classList.add('hidden');
$('aiAssistantBtn').onclick=()=>{$('searchBox').focus();$('searchBox').placeholder='Ask: show fire risk near Bandipur, forest change in Kodagu…';toast('Type a forest question or place in the search bar')};
$('openLayerDrawerEnv').onclick=openLayerDrawer;
$('closeIntelligence').onclick=()=>$('intelligenceModal').classList.add('hidden');$('runPrediction').onclick=()=>runPrediction(false);$('runLocationPrediction').onclick=()=>runPrediction(true);$('runWhatIf').onclick=runWhatIf;
$('closePatrol').onclick=()=>$('patrolModal').classList.add('hidden');$('runPatrol').onclick=runPatrol;
$('closeTime').onclick=()=>{if(state.timeTimer){clearInterval(state.timeTimer);state.timeTimer=null}$('timeModal').classList.add('hidden')};$('loadTime').onclick=loadTime;$('playTime').onclick=toggleTimePlay;
$('addBhuvan').onclick=()=>{const layer=$('bhuvanLayer').value.trim();if(!layer)return toast('Enter an exact Bhuvan-published WMS layer name');addRaster('bhuvan-custom',`/api/bhuvan/tile/{z}/{x}/{y}.png?layer=${encodeURIComponent(layer)}`,.78);toast('Bhuvan layer added')};

$$('[data-nav]').forEach(b=>b.onclick=async()=>{const n=b.dataset.nav;$$('[data-nav]').forEach(x=>x.classList.toggle('active',x===b));if(n==='map')fitSelected();if(n==='forest')await quickLayer('forest');if(n==='alerts'){const l=findLayerBy(x=>/alert|loss/i.test(`${x.label||''} ${x.id||''}`));if(l)await toggleLayer(l,true,null);else{showTab('analysis');await loadEvidence(true)}}if(n==='analysis'){showTab('analysis');await loadEvidence(false)}if(n==='weather'){showTab('environment')}if(n==='fire'){await quickLayer('fire')}if(n==='soil'){showTab('environment');openLayerDrawer()}if(n==='predictions')$('intelligenceModal').classList.remove('hidden');if(n==='patrol')openPatrol();if(n==='reports')generateReport()});

// Keep paired date controls synchronized.
$('beforeDate').onchange=()=>{$('modalBeforeDate').value=$('beforeDate').value};$('afterDate').onchange=()=>{$('modalAfterDate').value=$('afterDate').value};$('modalBeforeDate').onchange=()=>{$('beforeDate').value=$('modalBeforeDate').value};$('modalAfterDate').onchange=()=>{$('afterDate').value=$('modalAfterDate').value};

window.addEventListener('resize',()=>{state.trendChart?.resize();[state.inlineBefore,state.inlineAfter,state.panelBefore,state.panelAfter,state.modalBefore,state.modalAfter,state.timeMap].forEach(m=>{try{m?.resize()}catch{}})});

// Initial boot: exact dashboard layout opens on Kodagu with real source calls.
(async function boot(){await loadLayers();await loadSourceHealth(false);map.once('load',()=>{map.flyTo({center:[state.lon,state.lat],zoom:8.2,duration:1400});investigate(state.lat,state.lon,state.place)});if(map.loaded()){map.flyTo({center:[state.lon,state.lat],zoom:8.2,duration:1400});investigate(state.lat,state.lon,state.place)}})();
