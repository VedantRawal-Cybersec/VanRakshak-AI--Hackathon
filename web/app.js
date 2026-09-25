const API='';
const $=(id)=>document.getElementById(id);
const $$=(sel)=>Array.from(document.querySelectorAll(sel));
const state={
  lat:12.3375,lon:75.8069,place:'Kodagu Forest Region',regionSub:'Karnataka, India',
  investigation:null,profile:null,evidence:null,layers:[],active:new Map(),sourceHealth:null,
  inlineBefore:null,inlineAfter:null,panelBefore:null,panelAfter:null,modalBefore:null,modalAfter:null,
  timeMap:null,timeScenes:[],timeIndex:0,timeTimer:null,trendChart:null,predictionChart:null,demoScenarios:[],alert:null,alertPatrol:null
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
async function api(path,opts={}){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),120000);
  try{const r=await fetch(API+path,{...opts,signal:opts.signal||controller.signal});const body=await r.text();let d;try{d=JSON.parse(body)}catch{throw new Error(r.ok?'The server returned invalid data.':'The service is unavailable. Please retry.')}
  if(!r.ok){const detail=d.detail;throw new Error(typeof detail==='string'?detail:Array.isArray(detail)?detail.map(x=>x.msg).join('; '):'The request could not be completed.')}return d;
  }catch(e){if(e.name==='AbortError')throw new Error('The provider took too long. Please retry or narrow the date range.');throw e}finally{clearTimeout(timer)}
}
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function isoDate(d){return d.toISOString().slice(0,10)}
function clamp(v,min,max){return Math.max(min,Math.min(max,v))}
function pct(v,digits=0){if(v==null||Number.isNaN(Number(v)))return '—';const n=Number(v);return `${(Math.abs(n)<=1?n*100:n).toFixed(digits)}%`}
function fmt(v,d=1){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(d)}
function setText(id,val){const el=$(id);if(el)el.textContent=val}
function showTab(name){
  $('.right-tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));
  $('.right-panel-view').forEach(x=>x.classList.toggle('active',x.id===`tab-${name}`));
  const inspector=$('inspector');if(inspector)inspector.scrollTo({top:0,behavior:'auto'});
  requestAnimationFrame(()=>{[state.panelBefore,state.panelAfter].forEach(m=>{try{m?.resize()}catch{}});state.trendChart?.resize()});
}
function incidentId(){const d=new Date();return `VR-${d.getFullYear()}-${String(Math.abs(Math.round(state.lat*100))+Math.abs(Math.round(state.lon*100))).padStart(4,'0').slice(-4)}`}

const now=new Date();
const yearAgo=new Date(now);yearAgo.setFullYear(now.getFullYear()-1);
const monthAgo=new Date(now);monthAgo.setDate(now.getDate()-30);
const threeYearsAgo=new Date(now);threeYearsAgo.setFullYear(now.getFullYear()-3);
['endDate','afterDate','modalAfterDate','timeEnd'].forEach(id=>{if($(id))$(id).value=isoDate(now)});
['startDate','endDate'].forEach(id=>{if($(id))$(id).value=''});
['beforeDate','modalBeforeDate'].forEach(id=>{if($(id))$(id).value=isoDate(yearAgo)});
if($('timeStart'))$('timeStart').value=isoDate(threeYearsAgo);

const map=createEarthMap({container:'map',center:[78.8,22.5],zoom:4.25,style:baseStyle,minZoom:3,maxZoom:16});
map.addControl(typeof maplibregl!=='undefined'?new maplibregl.NavigationControl({showCompass:true}):null,'top-right');
map.on('click',e=>investigate(e.lngLat.lat,e.lngLat.lng,'Selected Forest Region'));
map.on('error',e=>{const msg=e?.error?.message||'';if(/tile|raster|source/i.test(msg)){setText('mapStatus','A map tile failed; VanRakshak will keep other real providers active.');console.warn('Map render error',msg)}});

function ensureLocation(){if(state.lat==null||state.lon==null){toast('Select a location on the map first.');return false}return true}
function fitSelected(){if(!ensureLocation())return;map.flyTo({center:[state.lon,state.lat],zoom:10,essential:true});}

function removeLayer(id){const rec=state.active.get(id);if(!rec)return;try{if(rec.outline&&map.getLayer(rec.outline))map.removeLayer(rec.outline);if(map.getLayer(rec.layer))map.removeLayer(rec.layer);if(map.getSource(rec.source))map.removeSource(rec.source)}catch{}state.active.delete(id)}
function addRaster(id,tileUrl,opacity=.72,opts={}){removeLayer(id);const source=`src-${id}`,layer=`lyr-${id}`;const install=()=>{try{if(map.getLayer(layer))map.removeLayer(layer);if(map.getSource(source))map.removeSource(source)}catch{}const src={type:'raster',tiles:[tileUrl],tileSize:Number(opts.tileSize||256)};if(Number.isFinite(Number(opts.maxzoom)))src.maxzoom=Number(opts.maxzoom);if(Number.isFinite(Number(opts.minzoom)))src.minzoom=Number(opts.minzoom);if(opts.attribution)src.attribution=opts.attribution;map.addSource(source,src);map.addLayer({id:layer,type:'raster',source,paint:{'raster-opacity':opacity,'raster-fade-duration':120}},map.getLayer('labels')?'labels':undefined);state.active.set(id,{source,layer,tileUrl,maxzoom:opts.maxzoom});};if(map.isStyleLoaded())install();else map.once('load',install)}
function addGeoPoints(id,features,color='#ff4d5a'){removeLayer(id);const source=`src-${id}`,layer=`lyr-${id}`;map.addSource(source,{type:'geojson',data:{type:'FeatureCollection',features}});map.addLayer({id:layer,type:'circle',source,paint:{'circle-radius':['interpolate',['linear'],['zoom'],4,3,10,6],'circle-color':color,'circle-stroke-width':1,'circle-stroke-color':'#fff','circle-opacity':.88}});state.active.set(id,{source,layer})}
function addGeoPolygon(id,geojson,color='#ff4d5a'){removeLayer(id);const source=`src-${id}`,fill=`lyr-${id}`;map.addSource(source,{type:'geojson',data:geojson});map.addLayer({id:fill,type:'fill',source,paint:{'fill-color':color,'fill-opacity':.32}},map.getLayer('labels')?'labels':undefined);const outline=`${fill}-line`;map.addLayer({id:outline,type:'line',source,paint:{'line-color':color,'line-width':2}});state.active.set(id,{source,layer:fill,outline})}
function clearDynamicLayer(id){const rec=state.active.get(id);if(!rec)return;try{if(rec.outline&&map.getLayer(rec.outline))map.removeLayer(rec.outline)}catch{}removeLayer(id)}

async function loadLayers(){try{const d=await api('/api/layers');state.layers=d.groups||[];const sf=$('sourceFilter');if(sf){const current=sf.value;const sources=[...new Set(allLayers().map(l=>l.source).filter(Boolean))].sort();sf.innerHTML='<option value="">All providers</option>'+sources.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');sf.value=current&&sources.includes(current)?current:''}renderLayers();updateFilterStatus()}catch(e){toast('Layer registry unavailable: '+e.message)}}
function selectedFilters(){const rawCloud=Number($('cloudFilter')?.value??60);return {fresh:$('freshnessFilter')?.value||'',res:Number($('resolutionFilter')?.value||0),source:$('sourceFilter')?.value||'',render:$('renderFilter')?.value||'',cloud:Math.max(0,Math.min(100,Number.isFinite(rawCloud)?rawCloud:60)),start:$('startDate')?.value||'',end:$('endDate')?.value||'',confidence:$('confidenceFilter')?.value||'high'}}
function allLayers(){return state.layers.flatMap(g=>g.layers||[])}
function findLayerBy(predicate){return allLayers().find(predicate)}
function layerMatchesFilters(l,f=selectedFilters()){return (!f.fresh||l.freshness===f.fresh)&&(!f.res||(l.resolution_m!=null&&Number(l.resolution_m)<=f.res))&&(!f.source||l.source===f.source)&&(!f.render||l.render===f.render)}
function satelliteLayerPath(mode='true_color'){const f=selectedFilters(),q=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),mode,days:'90',cloud_lt:String(f.cloud)});if(f.start)q.set('start_date',f.start);if(f.end)q.set('end_date',f.end);return '/api/map/satellite-layer?'+q.toString()}
function renderLayers(){if(!$('layerGroups'))return;const f=selectedFilters();const html=state.layers.map(g=>{const rows=(g.layers||[]).filter(l=>layerMatchesFilters(l,f)).map(l=>`<div class="layer-row"><label><input type="checkbox" data-layer="${esc(l.id)}" ${state.active.has(l.id)?'checked':''}> ${esc(l.label)}</label><span class="layer-meta">${esc(l.source||'')}<br>${l.resolution_m!=null?esc(l.resolution_m)+' m ':''}${esc(l.freshness||'')}</span></div>`).join('');return rows?`<div class="layer-group"><h3>${esc(g.icon||'')} ${esc(g.label)}</h3>${rows}</div>`:''}).join('');$('layerGroups').innerHTML=html||'<div class="empty-state">No layers match these filters. Reset or broaden the provider/resolution/freshness filters.</div>';$$('[data-layer]').forEach(x=>x.onchange=()=>toggleLayer(findLayerBy(l=>l.id===x.dataset.layer),x.checked,x));updateFilterStatus()}
function updateFilterStatus(){const f=selectedFilters(),parts=[];if(f.start||f.end)parts.push(`date ${f.start||'…'} → ${f.end||'…'}`);if(f.fresh)parts.push(f.fresh);if(f.res)parts.push(`≤${f.res}m`);if(f.source)parts.push(f.source);if(f.render)parts.push(f.render);parts.push(`cloud≤${f.cloud}%`);setText('filterStatus',parts.length?parts.join(' • '):'No filters active.')}
function resetLayerFilters(){['startDate','endDate','freshnessFilter','resolutionFilter','sourceFilter','renderFilter'].forEach(id=>{if($(id))$(id).value=''});if($('cloudFilter'))$('cloudFilter').value='60';if($('confidenceFilter'))$('confidenceFilter').value='high';applyLayerFilters();}
let filterApplyTimer=null,filterApplyRunning=false,filterApplyQueued=false;
function scheduleLayerFilterApply(){clearTimeout(filterApplyTimer);filterApplyTimer=setTimeout(()=>applyLayerFilters(),220)}
async function applyLayerFilters(){if(filterApplyRunning){filterApplyQueued=true;return}filterApplyRunning=true;try{await refreshLayerFilters()}finally{filterApplyRunning=false;if(filterApplyQueued){filterApplyQueued=false;applyLayerFilters()}}}
async function refreshLayerFilters(){const f=selectedFilters();if(f.start&&f.end&&f.start>f.end){toast('Filter error: start date must be before end date');return}const activeDefs=allLayers().filter(d=>state.active.has(d.id));for(const d of activeDefs){if(!layerMatchesFilters(d,f))clearDynamicLayer(d.id)}renderLayers();for(const d of activeDefs){if(layerMatchesFilters(d,f)&&['satellite','gfw','gibs'].includes(d.render))await toggleLayer(d,true,null)}try{if(state.active.has('quick-satellite')){const mode=$('satelliteModeQuick')?.value||'true_color';const d=await api(satelliteLayerPath(mode));addRaster('quick-satellite',d.tile_url,.88,{maxzoom:d.max_zoom,attribution:d.attribution})}if(state.active.has('quick-ndvi')){const d=await api(satelliteLayerPath('ndvi'));addRaster('quick-ndvi',d.tile_url,.78,{maxzoom:d.max_zoom,attribution:d.attribution})}}catch(e){toast('Filter refresh: '+String(e.message).slice(0,150))}}

const installRaster=addRaster,installGeoPoints=addGeoPoints,installGeoPolygon=addGeoPolygon;
async function toggleLayer(def,enabled,checkbox){if(!def)return;state.layerRequests??=new Map();const token=(state.layerRequests.get(def.id)||0)+1;state.layerRequests.set(def.id,token);if(!enabled){clearDynamicLayer(def.id);return}const current=()=>state.layerRequests.get(def.id)===token;const addRaster=(...a)=>{if(current())installRaster(...a)},addGeoPoints=(...a)=>{if(current())installGeoPoints(...a)},addGeoPolygon=(...a)=>{if(current())installGeoPolygon(...a)};const f=selectedFilters();try{
  if(def.render==='satellite'){const s=await api(satelliteLayerPath(def.mode||'true_color'));addRaster(def.id,s.tile_url,def.mode==='true_color'?.9:.74,{maxzoom:s.max_zoom,attribution:s.attribution});toast(`${def.label} loaded from ${s.source||'satellite source'} • ${(s.observed_at||'').slice(0,10)||'latest'}`)}
  else if(def.render==='gfw'){let q=`/api/map/gfw-layer?dataset=${encodeURIComponent(def.dataset)}&confidence=${f.confidence}`;if(f.start)q+=`&start_date=${f.start}`;if(f.end)q+=`&end_date=${f.end}`;const s=await api(q);addRaster(def.id,s.tile_url,.76,{maxzoom:s.max_zoom,attribution:s.attribution});toast(`${def.label} enabled`)}
  else if(def.render==='gibs'){const d=f.end||isoDate(new Date(Date.now()-2*86400000));const s=await api(`/api/gibs/layer/${encodeURIComponent(def.gibs_layer)}?date=${encodeURIComponent(d)}`);addRaster(def.id,s.tile_url,.84,{maxzoom:s.max_zoom,attribution:s.attribution});toast(`${def.label} enabled from NASA GIBS • ${s.date}`)}
  else if(def.render==='earth_engine'){
    try{const s=await api(`/api/earth-engine/layer/${encodeURIComponent(def.ee_layer)}?lat=${state.lat}&lon=${state.lon}`);addRaster(def.id,s.tile_url,.72,{maxzoom:s.max_zoom,attribution:s.attribution});toast(s.fallback_used?`${def.label}: ${s.source||'public fallback'} active`:`${def.label} enabled via Earth Engine`)}
    catch(eeErr){
      if(['dynamic_world_trees','dynamic_world_label'].includes(def.ee_layer)){
        const s=await api('/api/map/gfw-layer?dataset=umd_tree_cover_density_2000&confidence=high');addRaster(def.id,s.tile_url,.7);toast(`${def.label}: GFW tree-cover fallback active`)
      }else if(def.ee_layer==='jrc_water_occurrence'){
        const s=await api(satelliteLayerPath('ndwi'));addRaster(def.id,s.tile_url,.75);toast('Water context: Sentinel-2 NDWI fallback active')
      }else if(def.ee_layer==='modis_burned_area'){
        const s=await api('/api/map/gfw-layer?dataset=umd_tree_cover_loss_from_fires&confidence=high');addRaster(def.id,s.tile_url,.74);toast('Fire-loss history fallback active from GFW')
      }else if(['modis_lst','chirps_rainfall'].includes(def.ee_layer)){
        const id=def.ee_layer==='modis_lst'?'modis_terra_lst_day':'imerg_precipitation_rate';const spec=await api(`/api/gibs/layer/${id}?date=${f.end||isoDate(new Date(Date.now()-2*86400000))}`);addRaster(def.id,spec.tile_url,.72,{maxzoom:spec.max_zoom,attribution:spec.attribution});toast(`${def.label}: ${spec.label} fallback • ${spec.date}`)
      }else if(['worldpop_population','human_modification'].includes(def.ee_layer)){
        const s=await api(`/api/human-pressure?lat=${state.lat}&lon=${state.lon}&radius_m=10000`);if(!s.ok)throw eeErr;const feats=(s.data?.elements||[]).map(e=>{const lat=e.lat??e.center?.lat,lon=e.lon??e.center?.lon;if(lat==null||lon==null)return null;return {type:'Feature',geometry:{type:'Point',coordinates:[Number(lon),Number(lat)]},properties:e.tags||{}}}).filter(Boolean);addGeoPoints(def.id,feats,'#f2b43a');toast(`${def.label}: OSM human-pressure fallback active`)
      }else if(['srtm_elevation','srtm_slope','srtm_aspect','gedi_agbd','wcmc_carbon_density'].includes(def.ee_layer)){
        showTab(def.ee_layer.startsWith('srtm_')?'environment':'profile');const vals=state.profile||{};const fallbackValue=def.ee_layer==='srtm_elevation'?vals.terrain?.elevation_m:def.ee_layer==='srtm_slope'?vals.terrain?.slope_deg:def.ee_layer==='srtm_aspect'?vals.terrain?.aspect_deg:def.ee_layer==='gedi_agbd'?vals.forest?.gedi_agbd_mg_per_ha:vals.forest?.carbon_density_t_per_ha_reference;if(fallbackValue!=null){addGeoPoints(def.id,[{type:'Feature',geometry:{type:'Point',coordinates:[state.lon,state.lat]},properties:{value:fallbackValue}}],'#56d893');toast(`${def.label}: available point reference ${fmt(fallbackValue,1)}`)}else{throw new Error('This layer requires an authenticated Earth Engine source; no matching data is available.')}
      }else throw eeErr
    }
  }
  else if(def.render==='firms_points'){await enableFireLayer(def.id)}
  else if(def.render==='protected_context'){const s=await api(`/api/protected-area/context?lat=${state.lat}&lon=${state.lon}`);if(!s.ok)throw new Error(s.error||'Protected-area context unavailable');const areas=s.data?.areas||[];const feats=areas.map(a=>{const c=a.center;if(c?.lat==null||c?.lon==null)return null;return {type:'Feature',geometry:{type:'Point',coordinates:[Number(c.lon),Number(c.lat)]},properties:a.tags||{}}}).filter(Boolean);addGeoPoints(def.id,feats,'#26d98b');toast(`${s.data?.inside?'Inside':'No containing'} protected area • ${s.provenance?.source||'reference source'}`)}
  else if(def.render==='overpass'){const s=await api(`/api/human-pressure?lat=${state.lat}&lon=${state.lon}&radius_m=10000`);if(!s.ok)throw new Error(s.error||'Human-pressure provider unavailable');const feats=(s.data?.elements||[]).map(e=>{const lat=e.lat??e.center?.lat,lon=e.lon??e.center?.lon;if(lat==null||lon==null)return null;return {type:'Feature',geometry:{type:'Point',coordinates:[Number(lon),Number(lat)]},properties:e.tags||{}}}).filter(Boolean);addGeoPoints(def.id,feats,'#f2b43a');toast(`${feats.length} mapped human-pressure features`)}
  else if(def.render==='metadata'||def.render==='planned_adapter'){
    const endpoint=def.id==='sentinel1'?'/api/satellite/sentinel1':def.id==='landsat'?'/api/satellite/landsat':'/api/satellite/latest';
    const s=await api(`${endpoint}?lat=${state.lat}&lon=${state.lon}&days=90`);if(!s.ok)throw new Error(s.error||'Catalogue unavailable');
    const rows=s.data?.features||[];const feats=rows.filter(x=>x.geometry).map(x=>({type:'Feature',geometry:x.geometry,properties:{id:x.id,...(x.properties||{})}}));
    addGeoPolygon(def.id,{type:'FeatureCollection',features:feats},def.id==='sentinel1'?'#4ea8ff':'#56d893');
    toast(`${def.label}: ${rows.length} catalogue scenes found`);
  }
  else if(def.render==='point_data'){
    showTab('environment');let s;
    if(['soil_type','soil_ph','soc','nitrogen','texture','bulk_density','cec'].includes(def.id))s=await api(`/api/soil?lat=${state.lat}&lon=${state.lon}`);
    else s=await api(`/api/weather?lat=${state.lat}&lon=${state.lon}`);
    if(!s.ok)throw new Error(s.error||'Point data unavailable');
    showPointDetails(def,s);
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
    if(current())state.active.set(def.id,{analysis:true});
  }
  else{showTab('analysis');toast(`${def.label} opened in its investigation/profile workflow.`)}
}catch(e){if(!current())return;if(checkbox)checkbox.checked=false;clearDynamicLayer(def.id);toast(`${def.label}: ${String(e.message).slice(0,170)}`)}finally{if(current()&&checkbox)checkbox.checked=state.active.has(def.id)}}

function showPointDetails(def,result){
  let panel=$('selectedLayerDetails');if(!panel){panel=document.createElement('div');panel.id='selectedLayerDetails';panel.className='env-card';$('environmentPanel').after(panel)}
  const data=result.data||{},rows=[];
  if(def.source==='SoilGrids'){
    const names={soil_ph:['phh2o'],soc:['soc'],nitrogen:['nitrogen'],texture:['clay','sand','silt'],bulk_density:['bdod'],cec:['cec']};
    for(const item of data.properties?.layers||[]){if(names[def.id]&&!names[def.id].includes(item.name))continue;for(const depth of item.depths||[]){const raw=depth.values?.mean,unit=item.unit_measure||{},factor=Number(unit.d_factor)||1;if(raw!=null)rows.push(`${item.name} (${depth.label||'0–5 cm'}): ${fmt(raw/factor,2)} ${unit.target_units||unit.mapped_units||''}`)}}
  }else{
    const fields={temperature:'temperature_2m',humidity:'relative_humidity_2m',rainfall:'rain',precipitation:'precipitation',wind:'wind_speed_10m',cloud_cover:'cloud_cover',soil_moisture:'soil_moisture_0_to_1cm',evapotranspiration:'et0_fao_evapotranspiration'};
    const field=fields[def.id];let value=data.current?.[field],date=data.current?.time,unit=data.current_units?.[field];
    if(value==null&&data.hourly?.[field]){const times=data.hourly.time||[],now=data.current?.time||'';let i=times.findIndex(t=>t>=now);if(i<0)i=times.length-1;value=data.hourly[field][i];date=times[i];unit=data.hourly_units?.[field]}
    if(value!=null)rows.push(`${value} ${unit||''} • ${date||'provider timestamp unavailable'}`);
  }
  if(!rows.length)throw new Error('The provider returned no value for this variable at the selected location.');
  panel.innerHTML=`<small>${esc(def.label)} • ${esc(result.provenance?.source||def.source)}</small><strong>${rows.map(esc).join('<br>')}</strong><p>Selected-point data. ${def.freshness==='REFERENCE'?'Reference surface; date filters do not apply.':'Current/forecast values; historical satellite filters do not change weather dates.'}</p>`;
}

async function quickLayer(kind){$$('.map-pill').forEach(x=>x.classList.toggle('active',x.dataset.quick===kind));try{
  if(kind==='satellite'){
    try{const mode=$('satelliteModeQuick')?.value||'true_color';const d=await api(satelliteLayerPath(mode));addRaster('quick-satellite',d.tile_url,.88,{maxzoom:d.max_zoom,attribution:d.attribution});toast(`${mode.replaceAll('_',' ').toUpperCase()} • ${d.source||'satellite'} • ${(d.observed_at||'').slice(0,10)||'latest'}`)}
    catch(primaryErr){if(($('satelliteModeQuick')?.value||'true_color')!=='true_color')throw primaryErr;const s=await api('/api/gibs/layer/viirs_snpp_true_color?date='+encodeURIComponent(selectedFilters().end||isoDate(new Date(Date.now()-86400000))));addRaster('quick-satellite',s.tile_url,.88,{maxzoom:s.max_zoom,attribution:s.attribution});toast('Requested satellite renderer unavailable • NASA real-imagery fallback loaded')}
  }
  if(kind==='ndvi'){
    try{const d=await api(satelliteLayerPath('ndvi'));addRaster('quick-ndvi',d.tile_url,.78,{maxzoom:d.max_zoom,attribution:d.attribution});toast('Sentinel-2 NDVI layer loaded')}
    catch(primaryErr){const s=await api('/api/gibs/layer/modis_terra_ndvi_8day?date='+encodeURIComponent(selectedFilters().end||isoDate(new Date(Date.now()-86400000))));addRaster('quick-ndvi',s.tile_url,.78,{maxzoom:s.max_zoom,attribution:s.attribution});toast('Sentinel-2 NDVI unavailable for filters • NASA MODIS NDVI fallback loaded')}
  }
  if(kind==='fire'){
    let pointsOk=false;try{await enableFireLayer('quick-fire');pointsOk=true}catch{}
    const thermal=findLayerBy(l=>l.id==='nasa_viirs_thermal');if(thermal){try{await toggleLayer(thermal,true,null)}catch{}}
    if(!pointsOk&& !thermal)throw new Error('Fire providers unavailable')
  }
  if(kind==='temperature'){
    showTab('environment');const cur=state.investigation?.sources?.weather?.data?.current||{};
    const eeTemp=findLayerBy(l=>(l.ee_layer||'').includes('modis')&&(l.label||'').toLowerCase().includes('temp'));
    const gibsTemp=findLayerBy(l=>l.id==='nasa_modis_lst');
    let rasterLoaded=false;
    if(eeTemp&&state.sourceHealth?.sources?.some(x=>x.source==='Google Earth Engine'&&x.ok)){try{await toggleLayer(eeTemp,true,null);rasterLoaded=true}catch{}}
    if(!rasterLoaded&&gibsTemp){try{await toggleLayer(gibsTemp,true,null);rasterLoaded=true}catch{}}
    toast(cur.temperature_2m!=null?`Air temperature ${cur.temperature_2m}°C • Open-Meteo${rasterLoaded?' • surface-temperature raster loaded':''}`:'Temperature intelligence panel opened')
  }
  if(kind==='forest'){const f=findLayerBy(l=>l.id==='tree_cover_2000')||findLayerBy(l=>l.id==='forest_loss')||findLayerBy(l=>/forest cover|dynamic world/i.test(`${l.label||''} ${l.id||''}`));if(f)await toggleLayer(f,true,null);else{showTab('analysis');toast('Forest profile opened.')}}
}catch(e){toast(String(e.message).slice(0,180))}}

async function enableFireLayer(id='fire-hotspots'){const s=await api(`/api/fire?lat=${state.lat}&lon=${state.lon}&days=1`);if(!s.ok)throw new Error(s.error||'Fire intelligence unavailable');const feats=(s.data||[]).map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[Number(r.longitude),Number(r.latitude)]},properties:r})).filter(x=>Number.isFinite(x.geometry.coordinates[0])&&Number.isFinite(x.geometry.coordinates[1]));addGeoPoints(id,feats,'#ff423d');toast(`${feats.length} fire-context points • ${s.provenance?.source||'NASA source'}`)}

async function investigate(lat,lon,place='Selected Forest Region'){
  const revision=state.locationRevision=(state.locationRevision||0)+1;state.lat=Number(lat);state.lon=Number(lon);state.place=place||'Selected Forest Region';state.evidence=null;state.alert=null;state.alertPatrol=null;clearDynamicLayer('candidate-loss');for(const def of allLayers().filter(d=>state.active.has(d.id)&&!['gfw','gibs'].includes(d.render))){clearDynamicLayer(def.id);toggleLayer(def,true,null)}
  setText('regionTitle',state.place);setText('coords',`${state.lat.toFixed(4)}, ${state.lon.toFixed(4)} • India`);setText('incidentId',incidentId());setText('mapStatus','Gathering source-backed forest intelligence…');
  ['areaAffected','aiConfidence','ndviChange','riskScore'].forEach(id=>setText(id,'…'));
  try{
    const results=await Promise.allSettled([
      api(`/api/investigate?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}`),
      api(`/api/forest-profile?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}`)
    ]);
    if(revision!==state.locationRevision)return;const inv=results[0].status==='fulfilled'?results[0].value:{sources:{}},profile=results[1].status==='fulfilled'?results[1].value:{};state.investigation=inv;state.profile=profile;renderInvestigation(inv);renderProfile(profile);renderEnvironment(inv,profile);renderNews(inv.sources?.news);await Promise.allSettled([loadEvidence(false),loadTrend(),loadInlineCompare(false),loadSourceHealth(false)]);setText('mapStatus','Latest available observations loaded • source timestamps retained');
  }catch(e){setText('mapStatus','Some providers unavailable');toast('Investigation: '+String(e.message).slice(0,170))}
}

function renderInvestigation(d){const s=d.sources||{};const reverse=s.reverse_geocode?.data||{};const addr=reverse.address||{};if(reverse.display_name){const district=addr.state_district||addr.county||addr.city||addr.town;const st=addr.state;state.regionSub=[district,st,'India'].filter(Boolean).slice(0,3).join(', ');setText('coords',state.regionSub);setText('sumRegionSub',state.regionSub)}
  const shortName=(addr.state_district||addr.county||state.place||'Selected Region').replace(/ district/i,'');setText('sumRegion',shortName);setText('regionTitle',state.place||shortName);
  const fires=s.fire?.ok?(s.fire.data||[]):[];const fireSource=s.fire?.provenance?.source||'NASA fire intelligence';const fireFresh=s.fire?.provenance?.freshness||'';const pixelNrt=/FIRMS/i.test(fireSource)&&fireFresh==='LIVE_NRT';setText('sumFire',pixelNrt?String(fires.length):'—');setText('sumFireDelta',pixelNrt?'FIRMS NRT detections':s.fire?.ok?'Context only • '+fireSource.replace('NASA ','').slice(0,22):(s.fire?.error||'Fire sources unavailable').slice(0,31));setText('navAlertBadge',pixelNrt?String(fires.length):'—');
  const cur=s.weather?.ok?s.weather.data?.current:null;if(cur){setText('regionThumb',cur.temperature_2m!=null?`${Math.round(cur.temperature_2m)}°`:'🌲')}
  renderEnvironment(d,state.profile);
  renderNews(s.news);
}

function renderProfile(p){if(!p)return;state.profile=p;const loc=p.location||{},forest=p.forest||{},env=p.environment||{},terrain=p.terrain||{},human=p.human_pressure||{},fire=p.fire||{};const conservation=p.conservation||{};const pa=conservation?.inside===true||conservation?.value===1||conservation?.inside_protected_area===true?'Inside protected area':conservation?.error?'Unavailable':conservation?.inside===false?'No containing protected area found':'Not confirmed';
  $('profilePanel').innerHTML=`<div class="profile-grid"><div><small>Location</small><b>${esc(loc.display_name||state.place)}</b></div><div><small>Latest Sentinel scene</small><b>${esc(p.satellite?.latest_scene_time||'—')}</b></div><div><small>Dynamic World tree probability</small><b>${forest.dynamic_world_tree_probability!=null?pct(forest.dynamic_world_tree_probability,1):'—'}</b></div><div><small>GEDI biomass</small><b>${forest.gedi_agbd_mg_per_ha!=null?fmt(forest.gedi_agbd_mg_per_ha,1)+' Mg/ha':'—'}</b></div><div><small>Elevation</small><b>${terrain.elevation_m!=null?fmt(terrain.elevation_m,0)+' m':'—'}</b></div><div><small>Slope</small><b>${terrain.slope_deg!=null?fmt(terrain.slope_deg,1)+'°':'—'}</b></div><div><small>Temperature</small><b>${env.temperature_c??'—'} °C</b></div><div><small>Humidity</small><b>${env.humidity_pct??'—'}%</b></div><div><small>Mapped human pressure</small><b>${human.mapped_features??'—'}</b></div><div><small>Fire detections</small><b>${fire.detections_in_window??'—'}</b></div><div><small>Protected status</small><b>${esc(pa)}</b></div><div><small>Earth Engine</small><b>${p.earth_engine?.configured?'Configured':'Credential gated'}</b></div></div>`;
}

function nearestHourlyMetric(data,field){
  const times=data?.hourly?.time||[],values=data?.hourly?.[field]||[];
  if(!times.length||!values.length)return {value:null,unit:data?.hourly_units?.[field]||'',time:null};
  const currentTime=data?.current?.time||new Date().toISOString();
  let i=times.findIndex(t=>t>=currentTime);if(i<0)i=times.length-1;
  return {value:values[i],unit:data?.hourly_units?.[field]||'',time:times[i]};
}
function soilMetric(soilResult,name){
  if(!soilResult?.ok)return {value:null,unit:'',depth:'',available:false};
  const item=(soilResult.data?.properties?.layers||[]).find(x=>x.name===name);if(!item)return {value:null,unit:'',depth:'',available:false};
  const depth=(item.depths||[])[0]||{},raw=depth.values?.mean,measure=item.unit_measure||{},factor=Number(measure.d_factor)||1;
  return {value:raw==null?null:Number(raw)/factor,unit:measure.target_units||measure.mapped_units||'',depth:depth.label||'0–5 cm',available:raw!=null};
}
function envCard(label,value,unit='',meta='',wide=false,decimals=1){
  let shown='—';
  if(value!=null&&value!==''){
    if(typeof value==='number'&&Number.isFinite(value))shown=`${fmt(value,decimals)}${unit?' '+unit:''}`;
    else shown=`${esc(value)}${unit?' '+esc(unit):''}`;
  }
  return `<article class="env-card${wide?' wide':''}"><small>${esc(label)}</small><strong>${shown}</strong>${meta?`<em>${esc(meta)}</em>`:''}</article>`;
}
function renderEnvironment(inv,profile){
  const sources=inv?.sources||{},weather=sources.weather||{},weatherData=weather.ok?weather.data||{}:{},cur=weatherData.current||{},units=weatherData.current_units||{};
  const p=profile||{},e=p.environment||{},t=p.terrain||{},soil=sources.soil||p.soil||{},fire=sources.fire||{},human=p.human_pressure||{},forest=p.forest||{},sat=p.satellite||{},conservation=p.conservation||{};
  const observed=cur.time||weather.provenance?.observed_at||weather.provenance?.fetched_at||null;
  const hourlyFields={
    precipProb:nearestHourlyMetric(weatherData,'precipitation_probability'),
    soil0:nearestHourlyMetric(weatherData,'soil_moisture_0_to_1cm'),
    soil1:nearestHourlyMetric(weatherData,'soil_moisture_1_to_3cm'),
    et0:nearestHourlyMetric(weatherData,'et0_fao_evapotranspiration')
  };
  const soilNames=[
    ['Soil pH','phh2o'],['Organic carbon','soc'],['Nitrogen','nitrogen'],['Clay','clay'],
    ['Sand','sand'],['Silt','silt'],['Bulk density','bdod'],['Cation exchange capacity','cec']
  ];
  const protectedText=conservation?.inside===true||conservation?.inside_protected_area===true?'Inside protected area':conservation?.inside===false?'No containing protected area found':sources.protected_area?.ok?'Protected-area context loaded':'Not confirmed';
  const coords=state.lat!=null&&state.lon!=null?`${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`:'—';
  const sections=[];
  sections.push('<div class="env-section-title">Selected Area & Weather</div>');
  sections.push(envCard('Selected coordinates',coords,'',state.regionSub||state.place,true,0));
  sections.push(envCard('Air temperature',cur.temperature_2m??e.temperature_c,units.temperature_2m||'°C',observed?`Observed ${observed}`:weather.provenance?.source||'Weather source',false,1));
  sections.push(envCard('Relative humidity',cur.relative_humidity_2m??e.humidity_pct,units.relative_humidity_2m||'%',weather.provenance?.source||'',false,0));
  sections.push(envCard('Rain',cur.rain??e.rain_mm,units.rain||'mm','Current interval',false,2));
  sections.push(envCard('Precipitation',cur.precipitation,units.precipitation||'mm','Current interval',false,2));
  sections.push(envCard('Cloud cover',cur.cloud_cover??e.cloud_cover_pct,units.cloud_cover||'%','Current sky cover',false,0));
  sections.push(envCard('Wind speed',cur.wind_speed_10m??e.wind_kmh,units.wind_speed_10m||'km/h','10 m wind',false,1));
  sections.push(envCard('Wind direction',cur.wind_direction_10m,units.wind_direction_10m||'°','Meteorological direction',false,0));
  sections.push(envCard('Precipitation probability',hourlyFields.precipProb.value,hourlyFields.precipProb.unit||'%',hourlyFields.precipProb.time||'Nearest forecast hour',false,0));
  sections.push(envCard('Surface soil moisture 0–1 cm',hourlyFields.soil0.value,hourlyFields.soil0.unit,hourlyFields.soil0.time||'Nearest forecast hour',false,3));
  sections.push(envCard('Soil moisture 1–3 cm',hourlyFields.soil1.value,hourlyFields.soil1.unit,hourlyFields.soil1.time||'Nearest forecast hour',false,3));
  sections.push(envCard('Reference evapotranspiration ET₀',hourlyFields.et0.value,hourlyFields.et0.unit,hourlyFields.et0.time||'Nearest forecast hour',false,2));

  sections.push('<div class="env-section-title">Soil Chemistry & Texture • SoilGrids 0–5 cm</div>');
  if(soil.ok){
    for(const [label,name] of soilNames){const m=soilMetric(soil,name);sections.push(envCard(label,m.value,m.unit,m.depth||'0–5 cm',false,name==='phh2o'?1:2))}
  }else{
    sections.push(envCard('SoilGrids status',soil.error||'Unavailable','','No soil values are fabricated when the provider fails.',true,0));
  }

  sections.push('<div class="env-section-title">Terrain, Forest & Risk Context</div>');
  sections.push(envCard('Elevation',t.elevation_m??weatherData.elevation,'m','Terrain / weather elevation',false,0));
  sections.push(envCard('Slope',t.slope_deg,'°',t.slope_deg==null?'Requires terrain source / Earth Engine':'Terrain slope',false,1));
  sections.push(envCard('Aspect',t.aspect_deg,'°',t.aspect_deg==null?'Requires terrain source / Earth Engine':'Terrain aspect',false,1));
  sections.push(envCard('Fire detections / context',fire.ok?(fire.data||[]).length:null,'',fire.ok?(fire.provenance?.source||'NASA fire intelligence'):(fire.error||'Unavailable'),false,0));
  sections.push(envCard('Protected-area status',protectedText,'',sources.protected_area?.provenance?.source||'Protected-area intelligence',false,0));
  sections.push(envCard('Mapped human-pressure features',human.mapped_features,'','OpenStreetMap / Overpass',false,0));
  sections.push(envCard('Available satellite scenes',sat.available_scenes,'',sat.latest_scene_time?`Latest ${sat.latest_scene_time}`:'Earth Search / Sentinel catalogue',false,0));
  sections.push(envCard('Dynamic World tree probability',forest.dynamic_world_tree_probability,forest.dynamic_world_tree_probability==null?'':'','Earth Engine enhancement',false,3));
  sections.push(envCard('GEDI biomass',forest.gedi_agbd_mg_per_ha,'Mg/ha','Earth Engine enhancement',false,1));
  sections.push(envCard('Carbon density reference',forest.carbon_density_t_per_ha_reference,'tC/ha','Reference layer / Earth Engine enhancement',false,1));

  sections.push('<div class="env-section-title">Source & Freshness</div>');
  sections.push(envCard('Weather provider',weather.provenance?.source||'Unavailable','',weather.provenance?.freshness||'',true,0));
  sections.push(envCard('Soil provider',soil.provenance?.source||(soil.ok?'SoilGrids':'Unavailable'),'',soil.provenance?.freshness||'REFERENCE',false,0));
  sections.push(envCard('Earth Engine',p.earth_engine?.configured?'Configured':'Optional enhancement','','Missing EE-only values remain blank rather than fabricated.',false,0));

  $('environmentPanel').innerHTML=sections.join('');
  setText('environmentUpdated',observed?`Weather ${String(observed).replace('T',' ').slice(0,16)}`:'Environmental context loaded');
}
function renderNews(n){if(!n||!n.ok){$('newsPanel').innerHTML=`<div class="empty-state">${esc(n?.error||'News context unavailable')}</div>`;return}const arts=n.data?.articles||[];$('newsPanel').innerHTML=arts.length?arts.slice(0,10).map(a=>`<article class="news-item"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title||a.url)}</a><small>${esc(a.domain||'')} • ${esc(a.seendate||'')}</small></article>`).join(''):'<div class="empty-state">No matching recent articles returned.</div>'}

async function loadEvidence(showToast=true){if(!ensureLocation())return null;const revision=state.locationRevision;const before=$('beforeDate').value,after=$('afterDate').value;try{if(showToast)toast('Running satellite change + evidence fusion…',5000);const q=`/api/analysis/evidence-chain?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}&before_date=${encodeURIComponent(before)}&after_date=${encodeURIComponent(after)}&radius_km=2`;const d=await api(q);if(revision!==state.locationRevision)return null;state.evidence=d;renderEvidence(d);if(showToast)toast('Evidence analysis completed');return d}catch(e){if(showToast)toast('Analysis: '+String(e.message).slice(0,170));renderEvidence({warning:{level:'UNKNOWN',score:null,coverage:0,factors:[]},evidence_chain:{items:[]}});return null}}

function renderEvidence(d){const c=d.change||{},w=d.warning||{},doctor=d.forest_doctor||{},carbon=d.carbon||{};const conf=c.screening_confidence;setText('areaAffected',c.candidate_area_ha!=null?`${fmt(c.candidate_area_ha,1)} ha`:'—');setText('aiConfidence',conf!=null?pct(conf,0):'—');setText('ndviChange',c.mean_ndvi_change!=null?pct(c.mean_ndvi_change,0):'—');setText('riskScore',w.score!=null?`${fmt(w.score,0)}`:'—');setText('analysisWarning',w.level||'UNKNOWN');setText('analysisCoverage',w.coverage!=null?pct(w.coverage,0):'—');setText('sumAlerts',w.score!=null?`${fmt(w.score,0)}/100`:'—');setText('sumCritical',w.level||'UNKNOWN');setText('sumAlertsDelta',w.level?`${w.level} warning`:'Evidence-normalized');setText('navAlertBadge',w.score!=null?String(Math.round(Number(w.score))):'—');
  const sev=$('severityBadge');sev.textContent=w.level||'UNKNOWN';sev.className=`severity ${(w.level||'unknown').toLowerCase()}`;
  clearDynamicLayer('candidate-loss');if(c.geojson){addGeoPolygon('candidate-loss',c.geojson,'#ff473d')}
  const drivers=doctor.probable_drivers||[];renderCauseBars(drivers);renderSignalBars(w.factors||[]);renderActionPlan(d.action_plan,d);
  const items=d.evidence_chain?.items||[];$('keyEvidence').innerHTML=items.length?items.slice(0,4).map(x=>`<div class="evidence-item"><span class="evidence-check">✓</span><span>${esc(x.statement||x.source||x.kind)}</span></div>`).join(''):'<div class="empty-state">No complete evidence items returned.</div>';
  $('evidenceChain').innerHTML=items.length?items.map(x=>`<p><b>${esc(x.kind)}</b> · ${esc(x.source)} — ${esc(x.statement)}</p>`).join(''):'<p>Evidence sources are unavailable or incomplete for the selected dates.</p>';
  setText('carbonImpact',carbon.estimated_co2e_t!=null?fmt(carbon.estimated_co2e_t,0):'—');setText('carbonImpactSub',carbon.estimated_co2e_t!=null?'tCO₂e estimated':'Requires biomass/carbon reference');
  if(d.protected_area===true){setText('protectedStatus','Inside Boundary');setText('protectedSub','WDPA / Protected Planet context')}else if(d.protected_area===false){setText('protectedStatus','Outside Boundary');setText('protectedSub','WDPA / Protected Planet context')}else{setText('protectedStatus','Unknown');setText('protectedSub','Configure Earth Engine or Protected Planet')}
  const fchange=c.fragmentation?.change||c.fragmentation_change||{};const fval=fchange.patch_count_pct??fchange.patch_density_pct??fchange.edge_density_pct??null;setText('fragmentationStatus',fval!=null?`${Number(fval)>=0?'+':''}${fmt(fval,0)}%`:'—');setText('fragmentationSub',fval!=null?'Patch isolation / edge change':'Derived when change mask exists');
  setText('changeResult',c.candidate_area_ha!=null?`${fmt(c.candidate_area_ha,2)} ha candidate vegetation loss • NDVI Δ ${fmt(c.mean_ndvi_change,3)} • warning ${w.level||'UNKNOWN'} ${w.score??'—'}/100`:'No complete before/after change result for the selected dates.');
}

function renderCauseBars(drivers){if(!drivers.length){$('causeBars').innerHTML='<div class="empty-state">Probable drivers require completed evidence analysis.</div>';return}$('causeBars').innerHTML=drivers.slice(0,4).map(x=>`<div class="cause-row"><span>${esc(x.driver)}</span><div class="cause-track"><div class="cause-fill" style="width:${clamp(Number(x.relative_support_pct)||0,0,100)}%"></div></div><b>${fmt(x.relative_support_pct,0)}%</b></div>`).join('')}
function renderSignalBars(factors){if(!factors.length){$('signalBars').innerHTML='<div class="empty-state">Run analysis to populate source-backed signals.</div>';return}$('signalBars').innerHTML=factors.slice(0,5).map((x,i)=>{const v=clamp(Number(x.contribution)||0,0,100);return `<div class="signal-row"><span>${esc(x.factor)}</span><div class="signal-track"><div class="signal-fill ${i>1?'amber':''}" style="width:${Math.max(4,v)}%"></div></div><b>${fmt(v,0)}</b></div>`}).join('')}
function renderActionPlan(plan,evidence){
  const actions=plan?.actions||[],risk=plan?.risk_before||evidence?.warning||{};
  setText('actionPlanRisk',risk.score!=null?`${risk.level||'RISK'} • ${fmt(risk.score,0)}/100`:'Insufficient evidence');
  const render=(rows,compact=false)=>rows.map((a,i)=>{
    const cls=String(a.priority||'routine').toLowerCase();
    return `<article class="action-step ${esc(cls)}"><div class="action-step-head"><b>${i+1}. ${esc(a.what)}</b><span>${esc(a.priority||'')}</span></div><p><strong>WHERE</strong> ${esc(a.where)}</p><p><strong>HOW</strong> ${esc(a.how)}</p><div class="action-step-meta"><em>⏱ ${esc(a.timeframe||'')}</em><em>WHY • ${esc(a.why||'')}</em></div><div class="expected-impact"><b>Expected impact</b><span>${esc(a.expected_impact||'')}</span><small>Success check: ${esc(a.success_metric||'')}</small></div></article>`;
  }).join('');
  $('actionPlanOverview').innerHTML=actions.length?render(actions.slice(0,3),true):'<div class="empty-state">No action plan could be generated from the available evidence.</div>';
  $('actionPlanAnalysis').innerHTML=actions.length?render(actions,false):'<div class="empty-state">No action plan could be generated from the available evidence.</div>';
  setText('actionPlanOutcome',plan?.expected_outcome||'Expected impact will appear as measurable validation targets after analysis.');
}

function validateCompareDates(before,after){if(!before||!after||before>=after)throw new Error('Choose a before date earlier than the after date.');if(before<'1982-08-22')throw new Error('Supported satellite imagery begins on 1982-08-22.');if(after>isoDate(new Date()))throw new Error('Future dates have no satellite observations.');}
function newMiniMap(container,center,zoom=11){return createEarthMap({container,center,zoom,style:{version:8,sources:{labels:baseStyle.sources.labels},layers:[baseStyle.layers[1]]},interactive:true,attributionControl:false})}
function addSceneRaster(m,id,sceneOrUrl){const scene=typeof sceneOrUrl==='string'?{tile_url:sceneOrUrl}:sceneOrUrl||{},url=scene.tile_url;if(!url)return;const draw=()=>{if(m.getLayer(id))m.removeLayer(id);if(m.getSource(id))m.removeSource(id);const src={type:'raster',tiles:[url],tileSize:256};if(Number.isFinite(Number(scene.maxzoom)))src.maxzoom=Number(scene.maxzoom);if(Number.isFinite(Number(scene.minzoom)))src.minzoom=Number(scene.minzoom);if(scene.attribution)src.attribution=scene.attribution;m.addSource(id,src);m.addLayer({id,type:'raster',source:id,paint:{'raster-opacity':1}},m.getLayer('labels')?'labels':undefined)};if(m.isStyleLoaded())draw();else m.once('load',draw)}
function syncMaps(a,b){let lock=false;a.on('move',()=>{if(lock)return;lock=true;const c=a.getCenter();b.jumpTo({center:[c.lng,c.lat],zoom:a.getZoom(),bearing:a.getBearing(),pitch:a.getPitch()});lock=false});b.on('move',()=>{if(lock)return;lock=true;const c=b.getCenter();a.jumpTo({center:[c.lng,c.lat],zoom:b.getZoom(),bearing:b.getBearing(),pitch:b.getPitch()});lock=false})}
function destroyMap(key){if(state[key]){try{state[key].remove()}catch{}state[key]=null}}
function setInlineCompareSplit(value){
  const v=Math.max(5,Math.min(95,Number(value)||50)),card=$('inlineCompareSlider')?.closest('.inline-compare-card'),wrap=$('inlineAfterWrap'),after=$('inlineAfter');
  if(!card||!wrap||!after)return;
  const width=Math.max(1,card.clientWidth);
  card.style.setProperty('--split',v+'%');
  wrap.style.left=v+'%';wrap.style.right='0';wrap.style.width='auto';
  after.style.width=width+'px';after.style.left=(-width*v/100)+'px';after.style.right='auto';
  state.inlineAfter?.resize();
}
function setModalCompareSplit(value){
  const v=Math.max(5,Math.min(95,Number(value)||50)),shell=$('compareShell'),wrap=$('compareAfterWrap'),after=$('compareAfter');
  if(!shell||!wrap||!after)return;
  const width=Math.max(1,shell.clientWidth);
  shell.style.setProperty('--split',v+'%');
  wrap.style.left='0';wrap.style.width=v+'%';
  after.style.width=width+'px';after.style.left='0';after.style.right='auto';
  state.modalAfter?.resize();
}

function sceneDateLabel(scene,requested){const actual=(scene?.observed_at||requested||'').slice(0,10),req=scene?.requested_date||requested||actual,offset=Number(scene?.date_offset_days);return actual&&req&&actual!==req?`${req} → ${actual}${Number.isFinite(offset)?` (${fmt(offset,0)}d)`:''}`:actual||req||'—'}
async function loadInlineCompare(showToast=true){if(!ensureLocation())return;const before=$('beforeDate').value,after=$('afterDate').value;if(!before||!after)return;try{validateCompareDates(before,after);if(showToast)toast('Loading dated satellite scenes (Landsat / Sentinel-2)…');const d=await api(`/api/map/compare?lat=${state.lat}&lon=${state.lon}&before_date=${before}&after_date=${after}&mode=true_color&cloud_lt=${selectedFilters().cloud}`);setupInlineCompare(d);setupPanelCompare(d);setText('beforeInlineDate',sceneDateLabel(d.before,before));setText('afterInlineDate',sceneDateLabel(d.after,after));setText('compareMeta',`Before ${sceneDateLabel(d.before,before)} • ${d.before.source||''} • cloud ${d.before.cloud_cover??'—'}% | After ${sceneDateLabel(d.after,after)} • ${d.after.source||''} • cloud ${d.after.cloud_cover??'—'}%`);if(showToast)toast('Before/after scenes loaded')}catch(e){['inlineBefore','inlineAfter','panelBefore','panelAfter'].forEach(destroyMap);setText('beforeInlineDate','—');setText('afterInlineDate','—');setText('compareMeta',String(e.message).slice(0,200));if(showToast)toast('Comparison: '+String(e.message).slice(0,160))}}
function setupInlineCompare(d){destroyMap('inlineBefore');destroyMap('inlineAfter');setInlineCompareSplit($('inlineCompareSlider')?.value||50);const center=[state.lon,state.lat],zoom=11;state.inlineBefore=newMiniMap('inlineBefore',center,zoom);state.inlineAfter=newMiniMap('inlineAfter',center,zoom);addSceneRaster(state.inlineBefore,'inline-b',d.before);addSceneRaster(state.inlineAfter,'inline-a',d.after);syncMaps(state.inlineBefore,state.inlineAfter);setTimeout(()=>{setInlineCompareSplit($('inlineCompareSlider')?.value||50);state.inlineBefore?.resize();state.inlineAfter?.resize()},300)}
function setupPanelCompare(d){destroyMap('panelBefore');destroyMap('panelAfter');const center=[state.lon,state.lat];state.panelBefore=newMiniMap('beforePanelMap',center,11);state.panelAfter=newMiniMap('afterPanelMap',center,11);addSceneRaster(state.panelBefore,'panel-b',d.before);addSceneRaster(state.panelAfter,'panel-a',d.after);syncMaps(state.panelBefore,state.panelAfter);setTimeout(()=>{state.panelBefore?.resize();state.panelAfter?.resize()},300)}
async function openFullCompare(){if(!ensureLocation())return;$('compareModal').classList.remove('hidden');$('modalBeforeDate').value=$('beforeDate').value;$('modalAfterDate').value=$('afterDate').value;await loadFullCompare()}
async function loadFullCompare(){const before=$('modalBeforeDate').value,after=$('modalAfterDate').value,mode=$('compareMode').value;try{validateCompareDates(before,after);const d=await api(`/api/map/compare?lat=${state.lat}&lon=${state.lon}&before_date=${before}&after_date=${after}&mode=${mode}&cloud_lt=${selectedFilters().cloud}`);destroyMap('modalBefore');destroyMap('modalAfter');setModalCompareSplit($('compareSlider')?.value||50);const center=[state.lon,state.lat];state.modalBefore=newMiniMap('compareBefore',center,11);state.modalAfter=newMiniMap('compareAfter',center,11);addSceneRaster(state.modalBefore,'modal-b',d.before);addSceneRaster(state.modalAfter,'modal-a',d.after);syncMaps(state.modalBefore,state.modalAfter);setText('compareModalMeta',`Before ${sceneDateLabel(d.before,before)} • After ${sceneDateLabel(d.after,after)} • ${d.before.source||''} / ${d.after.source||''} • ${mode}`);setTimeout(()=>{setModalCompareSplit($('compareSlider')?.value||50);state.modalBefore?.resize();state.modalAfter?.resize()},300)}catch(e){['modalBefore','modalAfter'].forEach(destroyMap);setText('compareModalMeta',e.message)}}

async function loadTrend(){if(!ensureLocation()||typeof echarts==='undefined')return;try{const start=isoDate(threeYearsAgo),end=isoDate(now);const d=await api(`/api/analysis/vegetation-series?lat=${state.lat}&lon=${state.lon}&start=${start}&end=${end}&max_observations=12&cloud_lt=${selectedFilters().cloud}`);const pts=d.observations||[];if(!pts.length)throw new Error('No cloud-screened scenes');if(state.trendChart)state.trendChart.dispose();state.trendChart=echarts.init($('forestTrendChart'));const dates=pts.map(x=>(x.datetime||'').slice(0,10));const ndvi=pts.map(x=>x.mean_ndvi??null);const forest=pts.map(x=>x.forest_fraction==null?null:Number(x.forest_fraction)*100);state.trendChart.setOption({animation:true,grid:{left:40,right:38,top:18,bottom:26},tooltip:{trigger:'axis'},xAxis:{type:'category',data:dates,axisLine:{lineStyle:{color:'#29414d'}},axisLabel:{color:'#91a59f',fontSize:9}},yAxis:[{type:'value',min:-1,max:1,axisLine:{show:false},splitLine:{lineStyle:{color:'#17313b'}},axisLabel:{color:'#91a59f',fontSize:9}},{type:'value',min:0,max:100,show:false}],series:[{name:'Mean NDVI',type:'line',smooth:.35,data:ndvi,symbol:'none',lineStyle:{width:2,color:'#72e57e'},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'#4fd47744'},{offset:1,color:'#4fd47700'}]}},markLine:{silent:true,lineStyle:{color:'#29414d'},data:[]}}, {name:'Forest fraction %',type:'line',smooth:.35,yAxisIndex:1,data:forest,symbol:'none',lineStyle:{width:1,color:'#a8d8a1'}}]});setText('trendSubtitle',`${state.place} • ${pts.length} Sentinel-2 observations`)}catch(e){setText('trendSubtitle','Trend unavailable: '+String(e.message).slice(0,80));if(state.trendChart){state.trendChart.clear()}}}

async function loadSourceHealth(showToast=true){try{const [h,sh]=await Promise.all([api('/api/health'),api('/api/source-health')]);state.sourceHealth=sh;const rows=sh.sources||[];const healthy=rows.filter(x=>x.ok).length,configured=rows.filter(x=>x.status!=='NOT_CONFIGURED').length;setText('sumSources',`${healthy}/${configured||rows.length}`);setText('sumSourcesDelta','Healthy/configured providers');const wanted=['Earth Search','Planetary Computer','Copernicus STAC','Sentinel-1 ASF','Open-Meteo','MET Norway','NASA GIBS','NASA POWER','NASA EONET','Google News RSS','Photon Geocoder','NASA FIRMS','Protected Planet','Earth Engine'];const selected=[];for(const name of wanted){const r=rows.find(x=>x.source===name);if(r)selected.push(r)}for(const r of rows){if(selected.length>=6)break;if(!selected.includes(r))selected.push(r)}$('sourceList').innerHTML=selected.slice(0,6).map(r=>{const cls=r.ok?'':' '+(r.status==='NOT_CONFIGURED'?'off':'err');return `<div class="source-row"><span class="source-logo">${sourceIcon(r.source)}</span><span>${esc(r.source)}</span><em class="source-status"><i class="source-dot${cls}"></i>${r.ok?(r.latency_ms!=null?`${fmt(r.latency_ms,0)} ms`:'Healthy'):(r.status==='NOT_CONFIGURED'?'Needs credential':'Unavailable')}</em></div>`}).join('');if(h.capabilities?.firms_configured===false&&$('sumFire').textContent==='—')setText('sumFireDelta','FIRMS key not configured at runtime');if(showToast)toast(`${healthy}/${configured||rows.length} configured sources healthy`);return sh}catch(e){$('sourceList').innerHTML='<div class="empty-state">Source health endpoint unavailable.</div>';if(showToast)toast('Source health unavailable');return null}}
function sourceIcon(name){name=name.toLowerCase();if(name.includes('sentinel')||name.includes('copernicus')||name.includes('earth search')||name.includes('gibs'))return '🛰';if(name.includes('firms')||name.includes('eonet'))return '🔥';if(name.includes('meteo')||name.includes('met norway')||name.includes('power'))return '☁';if(name.includes('protected'))return '🛡';if(name.includes('photon')||name.includes('nominatim'))return '⌖';if(name.includes('soil'))return '🌱';if(name.includes('news'))return '📰';if(name.includes('earth engine'))return '🌍';return '●'}

function drawSearchBoundary(hit){const g=hit?.geojson;if(!g)return;for(const id of ['search-boundary-fill','search-boundary-line'])if(map.getLayer(id))map.removeLayer(id);if(map.getSource('search-boundary'))map.removeSource('search-boundary');map.addSource('search-boundary',{type:'geojson',data:{type:'Feature',properties:{},geometry:g}});map.addLayer({id:'search-boundary-fill',type:'fill',source:'search-boundary',paint:{'fill-color':'#20d67b','fill-opacity':.06}},map.getLayer('labels')?'labels':undefined);map.addLayer({id:'search-boundary-line',type:'line',source:'search-boundary',paint:{'line-color':'#e8fff4','line-width':1.6,'line-opacity':.9}})}
async function loadDemoScenarioManifest(){
  try{
    const d=await api('/api/demo-scenarios');
    state.demoScenarios=d.scenarios||[];
    const select=$('demoScenarioSelect');
    if(!select)return;
    select.innerHTML=state.demoScenarios.map(s=>`<option value="${esc(s.id)}">${esc(s.priority==='PRIMARY'?'★ ':'')}${esc(s.name)}</option>`).join('');
    const primary=state.demoScenarios.find(s=>s.priority==='PRIMARY')||state.demoScenarios[0];
    if(primary){select.value=primary.id;renderDemoScenarioMeta(primary)}
  }catch(e){
    const select=$('demoScenarioSelect');
    if(select)select.innerHTML='<option value="">Verified scenarios unavailable</option>';
    setText('demoScenarioMeta','Scenario manifest unavailable; manual investigation remains available.');
  }
}
function renderDemoScenarioMeta(s){
  if(!s)return;
  const b=s.sentinel2?.before,a=s.sentinel2?.after,sar=s.sentinel1?.matched_pair;
  setText('demoScenarioMeta',`${b?.date||'—'} → ${a?.date||'—'} • Sentinel-2 verified${sar?' • matched SAR pair':''}`);
}
async function applyDemoScenario(){
  const id=$('demoScenarioSelect')?.value;
  const s=state.demoScenarios.find(x=>x.id===id);
  if(!s)return toast('No verified demo scenario selected');
  const before=s.sentinel2?.before?.date,after=s.sentinel2?.after?.date;
  state.place=s.name;state.regionSub=`${s.state||''}, India`;
  if(before){$('beforeDate').value=before;$('modalBeforeDate').value=before}
  if(after){$('afterDate').value=after;$('modalAfterDate').value=after}
  if($('timeStart')&&before)$('timeStart').value=before;
  if($('timeEnd')&&after)$('timeEnd').value=after;
  renderDemoScenarioMeta(s);
  map.flyTo({center:[Number(s.lon),Number(s.lat)],zoom:Number(s.zoom||10),essential:true});
  toast(`Loading verified demo inputs for ${s.name}…`,5000);
  await investigate(Number(s.lat),Number(s.lon),s.name);
  await loadInlineCompare(false);
  showTab('overview');
  toast(`${s.name}: verified scene dates loaded. Analysis remains source-computed.`,5000);
}

async function doSearch(){const q=$('searchBox').value.trim();if(!q)return;try{const g=await api('/api/geocode?q='+encodeURIComponent(q));if(g.ok&&g.data?.length){const hit=g.data[0];state.place=hit.display_name?.split(',').slice(0,2).join(',')||q;drawSearchBoundary(hit);map.flyTo({center:[Number(hit.lon),Number(hit.lat)],zoom:9.5,essential:true});await investigate(Number(hit.lat),Number(hit.lon),state.place);toast('Location resolved and investigation started');return}}catch{}try{if(!ensureLocation())return;const parsed=await api(`/api/query/live?q=${encodeURIComponent(q)}&lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}&before_date=${encodeURIComponent($('beforeDate').value)}&after_date=${encodeURIComponent($('afterDate').value)}`);toast('AI Earth query executed against live evidence');state.liveIntelligence=parsed.live_result||null;showTab('analysis');await loadEvidence(false)}catch(e){toast('Search: '+String(e.message).slice(0,160))}}

async function generateReport(){if(!ensureLocation())return;try{toast('Generating source-backed PDF report…',5000);const url=`/api/report/investigation?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}&before_date=${encodeURIComponent($('beforeDate').value)}&after_date=${encodeURIComponent($('afterDate').value)}`;const r=await fetch(url);if(!r.ok)throw new Error(`${r.status} ${await r.text()}`);const blob=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='vanrakshak-investigation-report.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1200);toast('Investigation report generated')}catch(e){toast('Report: '+String(e.message).slice(0,170))}}

function predictionMetric(label,value,sub=''){return `<article class="metric-card"><small>${esc(label)}</small><strong>${esc(value)}</strong><em>${esc(sub)}</em></article>`}
function renderPredictionResult(d,useLocation){
  const p=d.projection||d,a=p.analysis||{},observed=d.historical_risk_proxy||[],dates=d.dates||[],forecast=p.projected_values||[],future=p.forecast_dates||forecast.map((_,i)=>`Next ${i+1}`);
  const current=useLocation?(d.analysis?.current_risk_index??observed.at(-1)):a.latest_value;
  const predictionMetrics=[
    predictionMetric('Current index',fmt(current,1),useLocation?'satellite-derived':'series value'),
    predictionMetric('Forecast',fmt(a.forecast_final,1),a.risk_level||''),
    predictionMetric('Trend',a.direction||'—',`${a.strength||''} • ${fmt(p.trend_per_step,2)}/step`),
    predictionMetric('Confidence',a.confidence_pct!=null?`${fmt(a.confidence_pct,0)}%`:'—',`${a.observations||observed.length} observations`)
  ];
  if(useLocation&&d.analysis){
    predictionMetrics.push(
      predictionMetric('NDVI change',fmt(d.analysis.ndvi_change_first_to_latest,3),'first → latest'),
      predictionMetric('Forest fraction Δ',pct(d.analysis.forest_fraction_change_first_to_latest,1),'first → latest'),
      predictionMetric('Optical quality',d.analysis.optical_quality_pct!=null?`${fmt(d.analysis.optical_quality_pct,0)}%`:'—','after cloud masking'),
      predictionMetric('Latest scene',d.analysis.latest_observation||'—',`${d.analysis.scene_read_errors||0} read errors`)
    );
  }
  $('predictionSummary').innerHTML=predictionMetrics.join('');
  const pipeline=[...(d.pipeline||[]),...(p.pipeline||[])];
  $('predictionUpdates').innerHTML=pipeline.map((x,i)=>`<div class="update-row"><b>${i+1}</b><span>${esc(x)}</span></div>`).join('');
  $('predictionResult').textContent=JSON.stringify(d,null,2);
  const chart=$('predictionChart');
  if(chart&&typeof echarts!=='undefined'){
    state.predictionChart??=echarts.init(chart);
    const labels=[...dates,...future],observedLine=[...observed,...Array(forecast.length).fill(null)],forecastLine=[...Array(Math.max(0,observed.length-1)).fill(null),observed.at(-1)??null,...forecast],lower=[...Array(observed.length).fill(null),...(p.lower||[])],upper=[...Array(observed.length).fill(null),...(p.upper||[])];
    state.predictionChart.setOption({animationDuration:350,tooltip:{trigger:'axis'},grid:{left:44,right:16,top:24,bottom:34},xAxis:{type:'category',data:labels,axisLabel:{color:'#829b93',fontSize:9}},yAxis:{type:'value',min:0,max:100,axisLabel:{color:'#829b93',fontSize:9},splitLine:{lineStyle:{color:'#16303a'}}},series:[{name:'Observed',type:'line',data:observedLine,symbolSize:6,lineStyle:{width:3}},{name:'Forecast',type:'line',data:forecastLine,symbolSize:6,lineStyle:{width:3,type:'dashed'}},{name:'Lower 95%',type:'line',data:lower,symbol:'none',lineStyle:{width:1,type:'dotted'}},{name:'Upper 95%',type:'line',data:upper,symbol:'none',lineStyle:{width:1,type:'dotted'}}]});
    state.predictionChart.resize();
  }
  const interpretation=d.analysis?.interpretation||a.summary||'Prediction complete.';
  setText('predictionStatus',`${interpretation} Updated ${(d.generated_at||p.generated_at||'').replace('T',' ').slice(0,19)} UTC`);
}
async function runPrediction(useLocation=false){
  const btn=useLocation?$('runLocationPrediction'):$('runPrediction');
  try{
    btn.disabled=true;setText('predictionStatus',useLocation?'Reading Sentinel-2 observations and computing forest trend…':'Validating series and fitting robust forecast models…');$('predictionSummary').innerHTML='';$('predictionUpdates').innerHTML='<div class="update-row"><b>•</b><span>Analysis in progress…</span></div>';
    let d;
    if(!useLocation){
      const values=$('predictionValues').value.split(/[\s,]+/).filter(Boolean).map(Number);
      if(values.length<3||values.some(v=>!Number.isFinite(v)))throw new Error('Enter at least three finite numeric values.');
      d=await api('/api/intelligence/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values,steps:4,floor:0,ceiling:100})});d={...d,source:'User-entered series',historical_risk_proxy:values,dates:values.map((_,i)=>`Obs ${i+1}`)};
    }else{
      if(!ensureLocation())return;
      const start=$('timeStart')?.value||isoDate(threeYearsAgo),end=$('timeEnd')?.value||isoDate(now);
      if(start>=end)throw new Error('Prediction start date must be before end date.');
      d=await api(`/api/intelligence/predict-location?lat=${state.lat}&lon=${state.lon}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&max_observations=12`);
    }
    renderPredictionResult(d,useLocation);toast(useLocation?'Selected forest prediction updated':'Series projection updated');
  }catch(e){setText('predictionStatus','Prediction failed: '+e.message);$('predictionResult').textContent=e.message;$('predictionUpdates').innerHTML=''}finally{btn.disabled=false}
}
async function runWhatIf(){try{if(!ensureLocation())return;const before=$('beforeDate').value,after=$('afterDate').value;if(!before||!after)throw new Error('Select real before/after dates first');const qs=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after,temperature_delta_c:String(Number($('whatTemp').value||0)),rainfall_delta_pct:String(Number($('whatRain').value||0)),fire_delta:String(Number($('whatFire').value||0)),ndvi_delta:'0'});const d=await api('/api/intelligence/what-if-location?'+qs.toString());$('whatIfResult').textContent=JSON.stringify(d,null,2)}catch(e){$('whatIfResult').textContent=e.message}}

function openPatrol(){if(!ensureLocation())return;$('patrolModal').classList.remove('hidden');if(!$('patrolPoints').value.trim())$('patrolPoints').value=`${state.lat.toFixed(5)},${state.lon.toFixed(5)},95`}
function fitLineGeometry(geometry){const coords=geometry?.coordinates||[];if(!coords.length)return;let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;for(const c of coords){if(!Array.isArray(c)||c.length<2)continue;minX=Math.min(minX,c[0]);maxX=Math.max(maxX,c[0]);minY=Math.min(minY,c[1]);maxY=Math.max(maxY,c[1])}if(Number.isFinite(minX))map.fitBounds([[minX,minY],[maxX,maxY]],{padding:70,maxZoom:13,duration:700})}
function renderPatrolResult(d,useDetected){
  const o=d.ordering||{},route=o.route||[],road=d.road_route||{};
  const patrolMetrics=[predictionMetric('Stops',String(route.length),useDetected?'detected hotspots':'entered targets'),predictionMetric('Road distance',road.distance_km!=null?`${fmt(road.distance_km,1)} km`:'Unavailable',o.ordering_mode||''),predictionMetric('ETA',road.duration_min!=null?`${fmt(road.duration_min,0)} min`:'—',road.source||'fallback ordering'),predictionMetric('Mode',d.status||'—',o.ordering_mode||'')];
  if(useDetected&&d.analysis){
    patrolMetrics.push(
      predictionMetric('Candidate area',d.analysis.candidate_area_ha!=null?`${fmt(d.analysis.candidate_area_ha,2)} ha`:'—','screened change'),
      predictionMetric('Screen confidence',d.analysis.screening_confidence!=null?pct(d.analysis.screening_confidence,0):'—','multispectral'),
      predictionMetric('Warning score',fmt(d.analysis.warning_score,0),'/ 100'),
      predictionMetric('Scene period',String(d.analysis.before_observed_at||'').slice(0,10)||'—',`→ ${String(d.analysis.after_observed_at||'').slice(0,10)||'—'}`)
    );
  }
  $('patrolMetrics').innerHTML=patrolMetrics.join('');
  $('patrolStops').innerHTML=route.map((s,i)=>{const area=s.candidate_context?.area_ha;return `<article class="route-stop"><b>${i+1}</b><div><strong>${esc(s.id)}</strong><small>${fmt(s.lat,5)}, ${fmt(s.lon,5)} • priority ${fmt(s.priority,0)}/100 (${esc(s.priority_band||'')})${area!=null?` • ${fmt(area,2)} ha candidate`:''}</small><em>${esc(s.why_selected||'')}</em></div></article>`}).join('')||'<div class="empty-state">No patrol hotspots detected for this comparison.</div>';
  const steps=(road.legs||[]).flatMap((leg,li)=>(leg.steps||[]).slice(0,8).map(x=>({...x,leg:li+1})));
  $('patrolInstructions').innerHTML=steps.length?`<h3>Road Guidance</h3>${steps.map(x=>`<div class="route-step"><b>L${x.leg}</b><span>${esc(x.instruction)} <small>${fmt(x.distance_m,0)} m • ${fmt(x.duration_min,1)} min</small></span></div>`).join('')}`:'<div class="drawer-note">No turn guidance returned. The ordered stops remain available, but straight lines must not be treated as roads.</div>';
  $('patrolResult').textContent=JSON.stringify(d,null,2);
  if(d.status==='NO_PATROL_TARGETS')setText('patrolStatus','Analysis complete: no candidate-change patrol hotspots were detected, so routing was correctly skipped.');
  else setText('patrolStatus',road.geometry?`Road route ready from ${road.source}. ${fmt(road.distance_km,1)} km / ~${fmt(road.duration_min,0)} min.`:`Road service unavailable. Showing ${o.ordering_mode||'fallback'} ordering only.`);
  clearDynamicLayer('patrol-route');clearDynamicLayer('patrol-stops');
  const features=[{type:'Feature',properties:{kind:'start'},geometry:{type:'Point',coordinates:[state.lon,state.lat]}},...route.map(s=>({type:'Feature',properties:{id:s.id,priority:s.priority,order:s.order},geometry:{type:'Point',coordinates:[s.lon,s.lat]}}))];
  addGeoPoints('patrol-stops',features,'#ffd166');
  if(road.geometry){map.addSource('src-patrol-route',{type:'geojson',data:{type:'Feature',properties:{},geometry:road.geometry}});map.addLayer({id:'lyr-patrol-route',type:'line',source:'src-patrol-route',paint:{'line-color':'#37e79c','line-width':4,'line-opacity':.95}},map.getLayer('labels')?'labels':undefined);state.active.set('patrol-route',{source:'src-patrol-route',layer:'lyr-patrol-route'});fitLineGeometry(road.geometry)}else fitSelected();
}
async function runPatrol(useDetected=false){
  const btn=useDetected?$('runDetectedPatrol'):$('runPatrol');
  try{
    if(!ensureLocation())return;btn.disabled=true;setText('patrolStatus',useDetected?'Running change screening, extracting hotspots and requesting road travel matrix…':'Validating stops and requesting road travel matrix…');$('patrolMetrics').innerHTML='';$('patrolStops').innerHTML='<div class="empty-state">Building route…</div>';$('patrolInstructions').innerHTML='';
    const before=$('beforeDate').value,after=$('afterDate').value;let d;
    if(useDetected){
      if(!before||!after)throw new Error('Select real before/after dates first');
      const q=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after,max_points:'5'});d=await api('/api/patrol/live?'+q.toString());
    }else{
      const points=$('patrolPoints').value.trim().split('\n').filter(Boolean).map((row,i)=>{const v=row.split(',').map(x=>Number(x.trim()));if(v.length!==3||v.some(x=>!Number.isFinite(x))||Math.abs(v[0])>90||Math.abs(v[1])>180||v[2]<0||v[2]>100)throw new Error(`Invalid stop on line ${i+1}: use lat,lon,priority (0–100).`);return {id:String(i+1),lat:v[0],lon:v[1],priority:v[2]}});if(!points.length)throw new Error('Enter at least one patrol stop.');
      d=await api('/api/patrol/road-route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_lat:state.lat,start_lon:state.lon,points})});
    }
    if(useDetected)state.alertPatrol=d;renderPatrolResult(d,useDetected);toast(d.status==='NO_PATROL_TARGETS'?'Analysis complete: no patrol hotspots detected':d.road_route?'Road-aware patrol route loaded':'Road route unavailable; fallback ordering displayed',4500);
  }catch(e){setText('patrolStatus','Patrol route failed: '+e.message);$('patrolResult').textContent=e.message;$('patrolStops').innerHTML='';$('patrolInstructions').innerHTML=''}finally{btn.disabled=false}
}

function alertRouteAppendix(){
  const d=state.alertPatrol;if(!d)return '';
  if(d.status==='NO_PATROL_TARGETS')return '\n\nPATROL ROUTE: No candidate-change patrol hotspots were detected; routing was intentionally skipped.';
  const o=d.ordering||{},route=o.route||[],road=d.road_route||{};
  const lines=['','PATROL ROUTE'];
  lines.push(`Mode: ${o.ordering_mode||d.status||'—'}`);
  if(road.distance_km!=null)lines.push(`Road distance: ${fmt(road.distance_km,2)} km`);
  if(road.duration_min!=null)lines.push(`Estimated travel time: ${fmt(road.duration_min,1)} min`);
  if(route.length){
    lines.push('Ordered stops:');
    route.slice(0,5).forEach((x,i)=>{
      const area=x.candidate_context?.area_ha;
      lines.push(`${i+1}. ${x.id} — ${fmt(x.lat,6)}, ${fmt(x.lon,6)} — priority ${fmt(x.priority,0)}/100${area!=null?` — ${fmt(area,2)} ha candidate`:''}`);
    });
  }
  return '\n'+lines.join('\n');
}
function refreshAlertMessage(){
  if(!$('alertMessage'))return;
  $('alertMessage').value=(state.alert?.message||'')+alertRouteAppendix();
}
function renderAlert(d){
  const c=d.change||{},top=d.top_patrol_target||{},period=d.detected_period||{},metrics=[
    predictionMetric('Severity',d.severity||'UNKNOWN','field triage'),
    predictionMetric('Warning score',d.warning_score!=null?fmt(d.warning_score,0)+'/100':'—','evidence-normalized'),
    predictionMetric('Candidate area',c.candidate_area_ha!=null?fmt(c.candidate_area_ha,2)+' ha':'—',`${c.candidate_polygons??0} polygon(s)`),
    predictionMetric('Confidence',c.screening_confidence!=null?pct(c.screening_confidence,0):'—','change screening'),
    predictionMetric('NDVI change',c.mean_ndvi_change!=null?fmt(c.mean_ndvi_change,3):'—','mean before → after'),
    predictionMetric('Before',period.before||'—','satellite observation'),
    predictionMetric('After',period.after||'—','satellite observation'),
    predictionMetric('First target',top.area_ha!=null?fmt(top.area_ha,2)+' ha':'Priority point',top.lat!=null?`${fmt(top.lat,5)}, ${fmt(top.lon,5)}`:'—')
  ];
  $('alertMetrics').innerHTML=metrics.join('');
  $('alertContext').innerHTML=`<p><b>Location:</b> ${esc(d.location?.place||state.place)}</p><p><b>Coordinates:</b> ${fmt(d.location?.lat,6)}, ${fmt(d.location?.lon,6)}</p><p><b>Detected:</b> ${c.candidate_area_ha!=null?fmt(c.candidate_area_ha,2)+' ha candidate change':'No complete area'} across ${c.candidate_polygons??0} polygon(s).</p><p><b>Period:</b> ${esc(period.before||'—')} → ${esc(period.after||'—')}</p><p><b>Priority target:</b> ${top.lat!=null?`${fmt(top.lat,6)}, ${fmt(top.lon,6)}`:'Selected location'} ${top.area_ha!=null?`• ${fmt(top.area_ha,2)} ha`:''}</p>`;
  const drivers=d.probable_drivers||[];
  $('alertDrivers').innerHTML=drivers.length?drivers.map(x=>`<div class="alert-driver"><span>${esc(x.driver)}</span><b>${x.support_pct!=null?fmt(x.support_pct,0)+'%':'evidence present'}</b></div>`).join(''):'<div class="drawer-note">No cause is established from the current evidence. Patrol should verify conditions without assuming a cause.</div>';
  refreshAlertMessage();
  setText('alertStatus',`${d.severity||'UNKNOWN'} patrol brief ready • incident ${d.incident_id||'—'} • generated ${String(d.generated_at||'').replace('T',' ').slice(0,19)} UTC`);
}
async function composeCurrentAlert(){
  if($('alertModal')?.classList.contains('hidden'))return null;
  if(!ensureLocation())return null;
  const before=$('beforeDate').value,after=$('afterDate').value;
  try{
    validateCompareDates(before,after);
    setText('alertStatus','Analyzing selected forest and composing patrol message…');
    $('alertMetrics').innerHTML='';
    $('alertContext').innerHTML='<div class="empty-state">Reading source-backed forest evidence…</div>';
    $('alertDrivers').innerHTML='<div class="empty-state">Evaluating probable drivers…</div>';
    const q=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after});
    const d=await api('/api/alerts/compose?'+q.toString());
    state.alert=d;state.alertPatrol=null;renderAlert(d);toast('Patrol alert generated from current evidence');return d;
  }catch(e){
    setText('alertStatus','Alert generation failed: '+e.message);
    $('alertContext').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;
    $('alertDrivers').innerHTML='';$('alertMessage').value='';state.alert=null;return null;
  }
}
async function openAlertCenter(){
  if(!ensureLocation())return;
  $('alertModal').classList.remove('hidden');
  await composeCurrentAlert();
}
async function attachAlertPatrolRoute(){
  if($('alertModal').classList.contains('hidden'))return;
  if(!state.alert){const d=await composeCurrentAlert();if(!d)return}
  const before=$('beforeDate').value,after=$('afterDate').value;
  try{
    setText('alertRouteStatus','Building route from detected change polygons…');
    const q=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after,max_points:'5'});
    const d=await api('/api/patrol/live?'+q.toString());state.alertPatrol=d;refreshAlertMessage();
    if(d.status==='NO_PATROL_TARGETS')setText('alertRouteStatus','No patrol hotspots detected; the alert remains valid as an analysis update.');
    else setText('alertRouteStatus',d.road_route?`Attached ${(d.ordering?.route||[]).length} stops • ${fmt(d.road_route.distance_km,1)} km • ~${fmt(d.road_route.duration_min,0)} min`:'Attached priority stop order; road geometry unavailable.');
    toast('Patrol route attached to alert');
  }catch(e){setText('alertRouteStatus','Route attachment failed: '+e.message)}
}
function alertDraft(){
  return ($('alertMessage')?.value||'').trim();
}
async function copyAlertMessage(){
  if($('alertModal').classList.contains('hidden'))return;
  const text=alertDraft();if(!text)return toast('Generate the alert first');
  try{
    if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);
    else{const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove()}
    toast('Patrol alert copied');
  }catch{toast('Could not copy automatically; select the message manually')}
}
async function shareAlertMessage(){
  if($('alertModal').classList.contains('hidden'))return;
  const text=alertDraft();if(!text)return toast('Generate the alert first');
  if(navigator.share){
    try{await navigator.share({title:state.alert?.subject||'VanRakshak Patrol Alert',text});return}catch(e){if(e.name==='AbortError')return}
  }
  await copyAlertMessage();toast('Share sheet unavailable; alert copied instead');
}
function whatsappAlertMessage(){
  if($('alertModal').classList.contains('hidden'))return;
  const text=alertDraft();if(!text)return toast('Generate the alert first');
  const phone=($('alertPhone').value||'').replace(/\D/g,'');
  const url=`https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
  window.open(url,'_blank','noopener');
}
function emailAlertMessage(){
  if($('alertModal').classList.contains('hidden'))return;
  const text=alertDraft();if(!text)return toast('Generate the alert first');
  const email=($('alertEmail').value||'').trim();
  const subject=state.alert?.subject||'VanRakshak Patrol Alert';
  window.open(`mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(text)}`,'_blank','noopener');
}

async function loadTime(){if(!ensureLocation())return;if(state.timeTimer){clearInterval(state.timeTimer);state.timeTimer=null;$('playTime').textContent='▶ Play'}try{validateCompareDates($('timeStart').value,$('timeEnd').value);const d=await api(`/api/time-machine?lat=${state.lat}&lon=${state.lon}&start=${$('timeStart').value}&end=${$('timeEnd').value}&limit=70`);state.timeScenes=d.scenes||[];state.timeIndex=0;$('timeline').innerHTML=state.timeScenes.length?state.timeScenes.map((x,i)=>`<button class="timeline-item" data-scene="${i}"><b>${esc(sceneDateLabel(x,x.requested_date))}</b><small>Cloud ${x.cloud_cover??'—'}%</small></button>`).join(''):'<div class="empty-state">No suitable scenes returned.</div>';$$('[data-scene]').forEach(btn=>btn.onclick=()=>showTimeScene(Number(btn.dataset.scene)));if(state.timeScenes.length)showTimeScene(0)}catch(e){$('timeline').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`}}
function showTimeScene(i){const scene=state.timeScenes[i];if(!scene)return;state.timeIndex=i;$$('[data-scene]').forEach(x=>x.classList.toggle('active',Number(x.dataset.scene)===i));if(!state.timeMap)state.timeMap=newMiniMap('timeMap',[state.lon,state.lat],9);state.timeMap.jumpTo({center:[state.lon,state.lat],zoom:9});addSceneRaster(state.timeMap,'time-raster',scene);setText('timeCaption',`${sceneDateLabel(scene,scene.requested_date)} • cloud ${scene.cloud_cover??'—'}% • ${scene.source||'Satellite archive'}`)}
function toggleTimePlay(){if(state.timeTimer){clearInterval(state.timeTimer);state.timeTimer=null;$('playTime').textContent='▶ Play';return}if(!state.timeScenes.length)return toast('Load a timeline first');$('playTime').textContent='⏸ Pause';state.timeTimer=setInterval(()=>{state.timeIndex=(state.timeIndex+1)%state.timeScenes.length;showTimeScene(state.timeIndex)},1700)}

function openLayerDrawer(){$('layerDrawer').classList.remove('hidden');renderLayers()}

// Main interactions
$('searchBtn').onclick=doSearch;$('searchBox').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch()});$('brandHome').onclick=()=>{showTab('overview');map.flyTo({center:[78.8,22.5],zoom:4.25})};
$$('[data-quick]').forEach(b=>b.onclick=()=>quickLayer(b.dataset.quick));$('layersBtn').onclick=openLayerDrawer;$('closeLayers').onclick=()=>$('layerDrawer').classList.add('hidden');['freshnessFilter','resolutionFilter','sourceFilter','renderFilter','cloudFilter','confidenceFilter','startDate','endDate'].forEach(id=>{const el=$(id);if(el)el.onchange=scheduleLayerFilterApply});if($('cloudFilter'))$('cloudFilter').oninput=scheduleLayerFilterApply;if($('applyFilters'))$('applyFilters').onclick=applyLayerFilters;if($('resetFilters'))$('resetFilters').onclick=resetLayerFilters;if($('satelliteModeQuick'))$('satelliteModeQuick').onchange=()=>quickLayer('satellite');
$$('.right-tab').forEach(b=>b.onclick=()=>showTab(b.dataset.tab));
$('inlineCompareSlider').oninput=e=>setInlineCompareSplit(e.target.value);
$('expandCompare').onclick=openFullCompare;$('openCompareBtn').onclick=openFullCompare;$('closeCompare').onclick=()=>$('compareModal').classList.add('hidden');$('loadCompare').onclick=loadFullCompare;$('compareSlider').oninput=e=>setModalCompareSplit(e.target.value);
$('loadInlineCompare').onclick=()=>loadInlineCompare(true);$('runChangeAnalysis').onclick=()=>loadEvidence(true);$('runEvidenceAnalysis').onclick=()=>loadEvidence(true);
$('reportBtn').onclick=generateReport;$('generateReportNews').onclick=generateReport;$('reportsTop').onclick=generateReport;$('viewOnMapBtn').onclick=fitSelected;$('patrolBtn').onclick=openPatrol;$('sendAlertBtn').onclick=openAlertCenter;
$('refreshSources').onclick=()=>loadSourceHealth(true);$('healthBtn').onclick=()=>loadSourceHealth(true);$('liveDataTop').onclick=()=>{showTab('overview');const inspector=$('inspector');if(inspector)inspector.scrollTo({top:Math.max(0,$('liveDataSection').offsetTop-90),behavior:'smooth'});loadSourceHealth(true)};$('analyticsTop').onclick=async()=>{showTab('analysis');await loadEvidence(false);toast('Source-backed regional analytics loaded')};
$('aboutTop').onclick=()=>$('aboutModal').classList.remove('hidden');$('closeAbout').onclick=()=>$('aboutModal').classList.add('hidden');
$('demoScenarioSelect').onchange=()=>renderDemoScenarioMeta(state.demoScenarios.find(x=>x.id===$('demoScenarioSelect').value));$('loadDemoScenario').onclick=applyDemoScenario;
$('aiAssistantBtn').onclick=()=>{$('searchBox').focus();$('searchBox').placeholder='Ask: show fire risk near Bandipur, forest change in Kodagu…';toast('Type a forest question or place in the search bar')};
$('openLayerDrawerEnv').onclick=openLayerDrawer;
$('closeIntelligence').onclick=()=>$('intelligenceModal').classList.add('hidden');$('runPrediction').onclick=()=>runPrediction(false);$('runLocationPrediction').onclick=()=>runPrediction(true);$('runWhatIf').onclick=runWhatIf;
$('closePatrol').onclick=()=>$('patrolModal').classList.add('hidden');$('runPatrol').onclick=()=>runPatrol(false);$('runDetectedPatrol').onclick=()=>runPatrol(true);
$('closeAlert').onclick=()=>$('alertModal').classList.add('hidden');$('refreshAlert').onclick=composeCurrentAlert;$('attachAlertPatrol').onclick=attachAlertPatrolRoute;$('copyAlert').onclick=copyAlertMessage;$('shareAlert').onclick=shareAlertMessage;$('whatsappAlert').onclick=whatsappAlertMessage;$('emailAlert').onclick=emailAlertMessage;
$('openTime').onclick=()=>{$('timeModal').classList.remove('hidden');state.timeMap?.resize()};
$('closeTime').onclick=()=>{if(state.timeTimer){clearInterval(state.timeTimer);state.timeTimer=null}$('playTime').textContent='▶ Play';$('timeModal').classList.add('hidden')};$('loadTime').onclick=loadTime;$('playTime').onclick=toggleTimePlay;
$('addBhuvan').onclick=()=>{const layer=$('bhuvanLayer').value.trim();if(!layer)return toast('Enter an exact Bhuvan-published WMS layer name');addRaster('bhuvan-custom',`/api/bhuvan/tile/{z}/{x}/{y}.png?layer=${encodeURIComponent(layer)}`,.78);toast('Bhuvan layer added')};

$('[data-nav]').forEach(b=>b.onclick=async()=>{const n=b.dataset.nav;$('[data-nav]').forEach(x=>x.classList.toggle('active',x===b));if(n==='map'){showTab('overview');fitSelected()}if(n==='forest')await quickLayer('forest');if(n==='alerts')await openAlertCenter();if(n==='analysis'){showTab('analysis');await loadEvidence(false)}if(n==='weather'){showTab('environment');renderEnvironment(state.investigation,state.profile)}if(n==='fire'){await quickLayer('fire')}if(n==='soil'){showTab('environment');renderEnvironment(state.investigation,state.profile);openLayerDrawer()}if(n==='predictions')$('intelligenceModal').classList.remove('hidden');if(n==='patrol')openPatrol();if(n==='reports')generateReport()});

// Keep paired date controls synchronized.
$('beforeDate').onchange=()=>{$('modalBeforeDate').value=$('beforeDate').value};$('afterDate').onchange=()=>{$('modalAfterDate').value=$('afterDate').value};$('modalBeforeDate').onchange=()=>{$('beforeDate').value=$('modalBeforeDate').value};$('modalAfterDate').onchange=()=>{$('afterDate').value=$('modalAfterDate').value};

let resizeFrame=0;window.addEventListener('resize',()=>{if(resizeFrame)cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=0;state.trendChart?.resize();state.predictionChart?.resize();setInlineCompareSplit($('inlineCompareSlider')?.value||50);setModalCompareSplit($('compareSlider')?.value||50);[map,state.inlineBefore,state.inlineAfter,state.panelBefore,state.panelAfter,state.modalBefore,state.modalAfter,state.timeMap].forEach(m=>{try{m?.resize()}catch{}})})},{passive:true});

// Initial boot: exact dashboard layout opens on Kodagu with real source calls.
(async function boot(){
  const start=()=>{map.flyTo({center:[state.lon,state.lat],zoom:8.2,duration:1400});investigate(state.lat,state.lon,state.place)};
  if(map.isStyleLoaded())start();else map.once('load',start);
  await Promise.allSettled([loadDemoScenarioManifest(),loadLayers(),loadSourceHealth(false)]);
})();
