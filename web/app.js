const API='';
const $=(id)=>document.getElementById(id);
const $$=(sel)=>Array.from(document.querySelectorAll(sel));
const state={
  lat:12.3375,lon:75.8069,place:'Kodagu Forest Region',regionSub:'Karnataka, India',
  investigation:null,profile:null,evidence:null,layers:[],active:new Map(),sourceHealth:null,
  inlineBefore:null,inlineAfter:null,panelBefore:null,panelAfter:null,modalBefore:null,modalAfter:null,
  timeMap:null,timeScenes:[],timeIndex:0,timeTimer:null,trendChart:null,predictionChart:null,alert:null,alertPatrol:null,patrolMap:null,patrolRouteGeometry:null,patrolEvidenceUrls:[]
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
  $$('.right-tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));
  $$('.right-panel-view').forEach(x=>x.classList.toggle('active',x.id===`tab-${name}`));
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

const QUICK_LEGENDS={
  satellite:{title:'Satellite',meta:'true color / imagery',className:'satellite-gradient',ticks:['Natural','Earth imagery'],status:'Satellite imagery • selected rendering mode'},
  forest:{title:'Forest Cover',meta:'tree cover / probability',className:'forest-gradient',ticks:['0%','25%','50%','75%','100%'],status:'Forest-cover layer • green = denser tree cover'},
  ndvi:{title:'NDVI',meta:'vegetation index',className:'ndvi-gradient',ticks:['-1','-0.5','0','0.5','1'],status:'NDVI • brown/red = sparse/stressed • green = healthy vegetation'},
  fire:{title:'Fire & Heat',meta:'thermal / hotspot intensity',className:'fire-gradient',ticks:['Low','Moderate','High','Very High','Critical'],status:'Fire layer only • red hotspot points + VIIRS thermal anomalies'},
  temperature:{title:'Temperature',meta:'surface / air temperature',className:'temperature-gradient',ticks:['Cool','Mild','Warm','Hot','Very Hot'],status:'Temperature layer • blue = cooler • red = hotter'}
};
function setQuickLegend(kind,metaOverride=''){
  const spec=QUICK_LEGENDS[kind]||QUICK_LEGENDS.satellite;
  setText('mapLegendTitle',spec.title);
  setText('mapLegendMeta',`(${metaOverride||spec.meta})`);
  const g=$('mapLegendGradient');if(g)g.className=`legend-gradient ${spec.className}`;
  const ticks=$('mapLegendTicks');if(ticks)ticks.innerHTML=spec.ticks.map(x=>`<span>${esc(x)}</span>`).join('');
  setText('mapStatus',spec.status);
}
function clearQuickOverlays(){
  ['quick-satellite','quick-ndvi','quick-fire'].forEach(clearDynamicLayer);
  if(state.quickManagedLayers){for(const id of state.quickManagedLayers)clearDynamicLayer(id)}
  state.quickManagedLayers=new Set();
}
function trackQuickLayer(id){state.quickManagedLayers??=new Set();if(id)state.quickManagedLayers.add(id)}

async function quickLayer(kind){
  $$('.map-pill').forEach(x=>x.classList.toggle('active',x.dataset.quick===kind));
  const revision=state.quickLayerRevision=(state.quickLayerRevision||0)+1;
  const current=()=>state.quickLayerRevision===revision;
  clearQuickOverlays();
  setQuickLegend(kind,kind==='satellite'?($('satelliteModeQuick')?.value||'true_color').replaceAll('_',' '):'');
  try{
    if(kind==='satellite'){
      try{
        const mode=$('satelliteModeQuick')?.value||'true_color';
        const d=await api(satelliteLayerPath(mode));
        if(!current())return;
        addRaster('quick-satellite',d.tile_url,.88,{maxzoom:d.max_zoom,attribution:d.attribution});
        setQuickLegend('satellite',mode.replaceAll('_',' '));
        toast(`${mode.replaceAll('_',' ').toUpperCase()} • ${d.source||'satellite'} • ${(d.observed_at||'').slice(0,10)||'latest'}`);
      }catch(primaryErr){
        if(($('satelliteModeQuick')?.value||'true_color')!=='true_color')throw primaryErr;
        const fallback=await api('/api/gibs/layer/viirs_snpp_true_color?date='+encodeURIComponent(selectedFilters().end||isoDate(new Date(Date.now()-86400000))));
        if(!current())return;
        addRaster('quick-satellite',fallback.tile_url,.88,{maxzoom:fallback.max_zoom,attribution:fallback.attribution});
        setQuickLegend('satellite','NASA true color');
        toast('Requested satellite renderer unavailable • NASA real-imagery fallback loaded');
      }
    }
    if(kind==='ndvi'){
      try{
        const d=await api(satelliteLayerPath('ndvi'));
        if(!current())return;
        addRaster('quick-ndvi',d.tile_url,.78,{maxzoom:d.max_zoom,attribution:d.attribution});
        toast('Sentinel-2 NDVI layer loaded');
      }catch(primaryErr){
        const fallback=await api('/api/gibs/layer/modis_terra_ndvi_8day?date='+encodeURIComponent(selectedFilters().end||isoDate(new Date(Date.now()-86400000))));
        if(!current())return;
        addRaster('quick-ndvi',fallback.tile_url,.78,{maxzoom:fallback.max_zoom,attribution:fallback.attribution});
        setQuickLegend('ndvi','MODIS NDVI fallback');
        toast('Sentinel-2 NDVI unavailable for filters • NASA MODIS NDVI fallback loaded');
      }
    }
    if(kind==='fire'){
      let pointsOk=false;
      try{await enableFireLayer('quick-fire',true);if(!current()){clearDynamicLayer('quick-fire');return}pointsOk=true}catch{}
      const thermal=findLayerBy(l=>l.id==='nasa_viirs_thermal');
      let thermalOk=false;
      if(thermal){try{await toggleLayer(thermal,true,null);if(!current()){clearDynamicLayer(thermal.id);return}trackQuickLayer(thermal.id);thermalOk=true}catch{}}
      if(!pointsOk&&!thermalOk)throw new Error('Fire providers unavailable');
      if(current())setQuickLegend('fire',pointsOk&&thermalOk?'FIRMS + VIIRS thermal':pointsOk?'FIRMS hotspots':'VIIRS thermal');
    }
    if(kind==='temperature'){
      showTab('environment');
      const cur=state.investigation?.sources?.weather?.data?.current||{};
      const eeTemp=findLayerBy(l=>(l.ee_layer||'').includes('modis')&&(l.label||'').toLowerCase().includes('temp'));
      const gibsTemp=findLayerBy(l=>l.id==='nasa_modis_lst');
      let rasterLoaded=false;
      if(eeTemp&&state.sourceHealth?.sources?.some(x=>x.source==='Google Earth Engine'&&x.ok)){
        try{await toggleLayer(eeTemp,true,null);if(!current()){clearDynamicLayer(eeTemp.id);return}trackQuickLayer(eeTemp.id);rasterLoaded=true}catch{}
      }
      if(!rasterLoaded&&gibsTemp){
        try{await toggleLayer(gibsTemp,true,null);if(!current()){clearDynamicLayer(gibsTemp.id);return}trackQuickLayer(gibsTemp.id);rasterLoaded=true}catch{}
      }
      if(current())setQuickLegend('temperature',rasterLoaded?'surface temperature + air temperature':'air temperature');
      toast(cur.temperature_2m!=null?`Air temperature ${cur.temperature_2m}°C • Open-Meteo${rasterLoaded?' • surface-temperature raster loaded':''}`:'Temperature intelligence panel opened');
    }
    if(kind==='forest'){
      const forest=findLayerBy(l=>l.id==='forest_cover')||findLayerBy(l=>l.id==='tree_cover_2000')||findLayerBy(l=>/forest cover|tree probability|dynamic world/i.test(`${l.label||''} ${l.id||''}`));
      if(forest){await toggleLayer(forest,true,null);if(!current()){clearDynamicLayer(forest.id);return}trackQuickLayer(forest.id);setQuickLegend('forest',forest.source||'forest source')}
      else{showTab('analysis');toast('Forest profile opened.')}
    }
  }catch(e){
    if(!current())return;
    setText('mapStatus',`${QUICK_LEGENDS[kind]?.title||'Layer'} unavailable • ${String(e.message).slice(0,110)}`);
    toast(String(e.message).slice(0,180));
  }
}

async function enableFireLayer(id='fire-hotspots',silent=false){const s=await api(`/api/fire?lat=${state.lat}&lon=${state.lon}&days=1`);if(!s.ok)throw new Error(s.error||'Fire intelligence unavailable');const feats=(s.data||[]).map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[Number(r.longitude),Number(r.latitude)]},properties:r})).filter(x=>Number.isFinite(x.geometry.coordinates[0])&&Number.isFinite(x.geometry.coordinates[1]));addGeoPoints(id,feats,'#ff423d');if(!silent)toast(`${feats.length} fire-context points • ${s.provenance?.source||'NASA source'}`)}

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

function renderDataIntegrity(){
  const invSources=state.investigation?.sources||{},evidenceSources=state.evidence?.sources||{};
  const merged=new Map();
  for(const [key,row] of Object.entries({...invSources,...evidenceSources})){
    if(!row||typeof row!=='object')continue;
    const prov=row.provenance||{};
    const source=prov.source||key.replaceAll('_',' ');
    const existing=merged.get(source);
    if(!existing||(!existing.ok&&row.ok))merged.set(source,{key,row,prov,source});
  }
  const rows=[...merged.values()];
  const healthy=rows.filter(x=>x.row.ok===true&&x.row.data!=null);
  const unavailable=rows.filter(x=>x.row.ok===false||x.row.data==null);
  const suspicious=rows.filter(x=>/demo|mock|synthetic|placeholder|fake/i.test(String(x.source)+' '+String(x.prov.notes||'')));
  const fallbacks=rows.filter(x=>x.row.fallback_used||x.row.provider_fallback_used||/fallback/i.test(String(x.prov.notes||'')));
  const badge=$('dataModeBadge');
  if(badge){
    badge.textContent=suspicious.length
      ?'DATA INTEGRITY WARNING'
      :fallbacks.length
        ?'REAL SOURCES + '+fallbacks.length+' LABELED FALLBACK'+(fallbacks.length===1?'':'S')
        :'REAL SOURCES • '+healthy.length+' ACTIVE';
    badge.className='data-mode-badge'+(suspicious.length?' warning':fallbacks.length?' fallback':'');
  }
  setText('dataIntegritySummary',healthy.length+' available • '+unavailable.length+' unavailable • '+fallbacks.length+' labeled fallback'+(fallbacks.length===1?'':'s'));
  const panel=$('dataIntegrityPanel');
  if(!panel)return;
  panel.innerHTML=rows.length?rows.sort((a,b)=>(b.row.ok===true)-(a.row.ok===true)).map(x=>{
    const observed=x.prov.observed_at||x.prov.fetched_at||'timestamp unavailable';
    const freshness=x.prov.freshness||'UNCLASSIFIED';
    const fallback=x.row.fallback_used||x.row.provider_fallback_used||/fallback/i.test(String(x.prov.notes||''));
    const status=x.row.ok===true&&x.row.data!=null?'AVAILABLE':'UNAVAILABLE';
    const cls=status==='AVAILABLE'?(fallback?'fallback':'ok'):'off';
    const note=x.prov.notes||x.row.error||'';
    return '<div class="data-source-row '+cls+'"><div><b>'+esc(x.source)+'</b><small>'+esc(freshness)+' • '+esc(String(observed).replace('T',' ').slice(0,19))+'</small></div><span>'+(fallback?'REAL FALLBACK':status)+'</span>'+(note?'<em>'+esc(String(note).slice(0,180))+'</em>':'')+'</div>';
  }).join(''):'<div class="empty-state">No provider provenance has loaded yet.</div>';
}

function renderInvestigation(d){const s=d.sources||{};const reverse=s.reverse_geocode?.data||{};const addr=reverse.address||{};if(reverse.display_name){const district=addr.state_district||addr.county||addr.city||addr.town;const st=addr.state;state.regionSub=[district,st,'India'].filter(Boolean).slice(0,3).join(', ');setText('coords',state.regionSub);setText('sumRegionSub',state.regionSub)}
  const shortName=(addr.state_district||addr.county||state.place||'Selected Region').replace(/ district/i,'');setText('sumRegion',shortName);setText('regionTitle',state.place||shortName);
  const fires=s.fire?.ok?(s.fire.data||[]):[];const fireSource=s.fire?.provenance?.source||'NASA fire intelligence';const fireFresh=s.fire?.provenance?.freshness||'';const pixelNrt=/FIRMS/i.test(fireSource)&&fireFresh==='LIVE_NRT';setText('sumFire',pixelNrt?String(fires.length):'—');setText('sumFireDelta',pixelNrt?'FIRMS NRT detections':s.fire?.ok?'Context only • '+fireSource.replace('NASA ','').slice(0,22):(s.fire?.error||'Fire sources unavailable').slice(0,31));setText('navAlertBadge',pixelNrt?String(fires.length):'—');
  const cur=s.weather?.ok?s.weather.data?.current:null;if(cur){setText('regionThumb',cur.temperature_2m!=null?`${Math.round(cur.temperature_2m)}°`:'🌲')}
  renderEnvironment(d,state.profile);
  renderAnalysisIntelligence();
  renderDataIntegrity();
  renderNews(s.news);
}

function renderProfile(p){
  if(!p)return;
  state.profile=p;
  const loc=p.location||{},forest=p.forest||{},env=p.environment||{},terrain=p.terrain||{},human=p.human_pressure||{},fire=p.fire||{},availability=p.availability||{};
  const conservation=p.conservation||{},evidence=state.evidence||{},change=evidence.change||{},carbon=evidence.carbon||{};
  const latestObs=(state.vegetationSeries||[]).at(-1)||{};
  const protectedSource=p.provenance?.protected_area?.source||p.raw_sources?.protected_area?.provenance?.source||'Protected-area intelligence';
  const pa=conservation?.inside===true||conservation?.value===1||conservation?.inside_protected_area===true
    ?'Inside protected area'
    :conservation?.error?'Unavailable'
    :conservation?.inside===false?'No containing protected area found'
    :'Not confirmed';
  const ndviDelta=change.mean_ndvi_change;
  const vegetation=ndviDelta!=null
    ?(Number(ndviDelta)<=-0.10?'Strong decline':Number(ndviDelta)<=-0.03?'Declining':Number(ndviDelta)<0.03?'Stable':'Improving / greening')
    :(latestObs.mean_ndvi!=null?'Current Sentinel vegetation observation':'Awaiting Sentinel analysis');
  const fragChange=change.fragmentation?.change||change.fragmentation_change||{};
  const frag=fragChange.patch_count_pct??fragChange.patch_density_pct??fragChange.edge_density_pct??null;
  const dynamicValue=forest.dynamic_world_tree_probability;
  const sentinelForest=latestObs.forest_fraction;
  const dynamicDisplay=dynamicValue!=null
    ?pct(dynamicValue,1)
    :sentinelForest!=null
      ?pct(sentinelForest,1)+' Sentinel forest fraction'
      :'Unavailable';
  const dynamicMeta=dynamicValue!=null
    ?'Dynamic World / Earth Engine'
    :sentinelForest!=null
      ?'Credential-free Sentinel-2 forest-mask fallback'
      :(availability.dynamic_world_tree_probability?.reason||'Dynamic World source unavailable');
  const gediDisplay=forest.gedi_agbd_mg_per_ha!=null?fmt(forest.gedi_agbd_mg_per_ha,1)+' Mg/ha':'Unavailable';
  const gediMeta=forest.gedi_agbd_mg_per_ha!=null?'NASA GEDI biomass':(availability.gedi_biomass?.reason||'GEDI layer unavailable');
  const slopeDisplay=terrain.slope_deg!=null?fmt(terrain.slope_deg,1)+'°':'Unavailable';
  const slopeMeta=terrain.slope_deg!=null?'SRTM terrain':(availability.slope?.reason||'Slope source unavailable');
  const carbonRef=evidence.carbon_reference||{};
  const carbonDisplay=carbon.estimated_co2e_t!=null?fmt(carbon.estimated_co2e_t,1)+' tCO₂e':'Local carbon unavailable';
  const carbonMeta=carbon.estimated_co2e_t!=null
    ?`${carbon.density_source||carbon.estimate_class||'Location-specific mapped reference'} • selected-area estimate`
    :carbonRef.estimated_co2e_t!=null
      ?`IPCC regional context only: ${fmt(carbonRef.estimated_co2e_t,1)} tCO₂e • not a local measurement`
      :'No location-specific biomass/carbon source available';
  const humanDisplay=human.mapped_features!=null?String(human.mapped_features):'Unavailable';
  const humanMeta=human.source||p.provenance?.human_pressure?.source||'OpenStreetMap / Overpass';
  const candidate=change.candidate_area_ha!=null?fmt(change.candidate_area_ha,2)+' ha':'Not measured';
  const latestNdvi=latestObs.mean_ndvi!=null?fmt(latestObs.mean_ndvi,3):'—';
  const eeStatus=p.earth_engine?.configured?'Configured':'Optional enhancement not configured';

  const cell=(label,value,meta='',tone='')=>`<div class="profile-cell ${esc(tone)}"><small>${esc(label)}</small><b>${esc(value==null?'—':String(value))}</b>${meta?`<em>${esc(meta)}</em>`:''}</div>`;

  $('profilePanel').innerHTML=`<div class="profile-grid enhanced-profile">
    ${cell('Location',loc.display_name||state.place,state.regionSub||'Reverse geocoded selected area','wide')}
    ${cell('Latest Sentinel scene',p.satellite?.latest_scene_time||'Unavailable',`${p.satellite?.available_scenes??'—'} catalogue scene(s) • ${p.satellite?.resolution_m||10} m`)}
    ${cell('Current Sentinel NDVI',latestNdvi,latestObs.datetime?`Observed ${String(latestObs.datetime).slice(0,10)}`:'Loads from vegetation trend')}
    ${cell('Forest cover / tree signal',dynamicDisplay,dynamicMeta)}
    ${cell('Vegetation condition',vegetation,ndviDelta!=null?`Before/after NDVI Δ ${fmt(ndviDelta,3)}`:'Based on latest available Sentinel observation',ndviDelta!=null&&Number(ndviDelta)<-0.03?'danger':'ok')}
    ${cell('Candidate affected area',candidate,change.screening_confidence!=null?`Screening confidence ${pct(change.screening_confidence,0)}`:'Run before/after analysis')}
    ${cell('GEDI biomass',gediDisplay,gediMeta)}
    ${cell('Carbon impact',carbonDisplay,carbonMeta)}
    ${cell('Elevation',terrain.elevation_m!=null?fmt(terrain.elevation_m,0)+' m':'Unavailable','Source-backed terrain/weather elevation')}
    ${cell('Slope',slopeDisplay,slopeMeta)}
    ${cell('Temperature',env.temperature_c!=null?fmt(env.temperature_c,1)+' °C':'Unavailable','Current weather observation')}
    ${cell('Humidity',env.humidity_pct!=null?fmt(env.humidity_pct,0)+'%':'Unavailable','Current weather observation')}
    ${cell('Mapped human pressure',humanDisplay,humanMeta)}
    ${cell('Fire detections / context',fire.detections_in_window!=null?String(fire.detections_in_window):'Unavailable',fire.source||'NASA fire intelligence')}
    ${cell('Protected status',pa,protectedSource)}
    ${cell('Fragmentation',frag!=null?`${Number(frag)>=0?'+':''}${fmt(frag,1)}%`:'Not measured',frag!=null?'Derived from before/after forest mask patch/edge change':'Run before/after evidence analysis')}
    ${cell('Earth Engine',eeStatus,p.earth_engine?.configured?'Higher-value layers enabled':'Credential-free fallbacks remain active')}
  </div>`;
  renderAnalysisIntelligence();
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
  const climate=state.evidence?.climate||{};
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

  sections.push('<div class="env-section-title">Climate Stress • Recent Window vs Historical Baseline</div>');
  sections.push(envCard('Temperature anomaly',climate.temperature_anomaly_c,'°C',climate.window?`${climate.window.start} → ${climate.window.end}`:'Runs with source-backed analysis',false,2));
  sections.push(envCard('Recent mean temperature',climate.temperature_mean_c,'°C',climate.baseline_years?`${climate.baseline_years}-year comparison window`:'Historical/reanalysis',false,2));
  sections.push(envCard('Baseline temperature',climate.temperature_baseline_c,'°C','Historical baseline',false,2));
  sections.push(envCard('Rainfall in recent window',climate.rainfall_sum_mm,'mm',climate.window?`${climate.window.days} days`:'Historical/reanalysis',false,1));
  sections.push(envCard('Baseline rainfall',climate.rainfall_baseline_mm,'mm','Historical baseline',false,1));
  sections.push(envCard('Rainfall deficit',climate.rainfall_deficit_pct,'%',climate.source||'Computed after evidence analysis',false,1));

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

function analysisValue(label,value,meta='',tone=''){
  const shown=value==null||value===''?'—':String(value);
  return `<div class="analysis-value ${esc(tone)}"><small>${esc(label)}</small><b>${esc(shown)}</b>${meta?`<em>${esc(meta)}</em>`:''}</div>`;
}
function situationRow(icon,title,text,tone=''){
  return `<div class="situation-row ${esc(tone)}"><span>${icon}</span><div><b>${esc(title)}</b><p>${esc(text)}</p></div></div>`;
}
function impactTarget(label,current,target,meta=''){
  return `<div class="impact-target"><small>${esc(label)}</small><b>${esc(current||'—')}</b><span>Target → ${esc(target)}</span>${meta?`<em>${esc(meta)}</em>`:''}</div>`;
}
function renderAnalysisIntelligence(){
  const area=$('analysisAreaGrid'),situation=$('currentSituationPanel'),workflow=$('vanrakshakWorkflow'),impact=$('analysisImpactSummary');
  if(!area||!situation||!workflow||!impact)return;

  const inv=state.investigation||{},sources=inv.sources||{},profile=state.profile||{},evidence=state.evidence||{};
  const weather=sources.weather||{},weatherData=weather.ok?weather.data||{}:{},cur=weatherData.current||{},units=weatherData.current_units||{};
  const forest=profile.forest||{},terrain=profile.terrain||{},human=profile.human_pressure||{},sat=profile.satellite||{},conservation=profile.conservation||{};
  const soil=sources.soil||profile.soil||{},fireSource=sources.fire||{},change=evidence.change||{},warning=evidence.warning||{},climate=evidence.climate||{},plan=evidence.action_plan||{};
  const ph=soilMetric(soil,'phh2o'),soc=soilMetric(soil,'soc'),nitrogen=soilMetric(soil,'nitrogen'),clay=soilMetric(soil,'clay'),sand=soilMetric(soil,'sand'),silt=soilMetric(soil,'silt');
  const soilMoist=nearestHourlyMetric(weatherData,'soil_moisture_0_to_1cm');
  const coords=state.lat!=null&&state.lon!=null?`${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`:'—';
  const observed=cur.time||weather.provenance?.observed_at||weather.provenance?.fetched_at||null;
  const fireCount=fireSource.ok?(fireSource.data||[]).length:null;
  const ndviDelta=change.mean_ndvi_change;
  const candidateArea=change.candidate_area_ha;
  const confidence=change.screening_confidence;
  const treeProb=forest.dynamic_world_tree_probability;

  let vegetationState='Awaiting satellite analysis',vegetationTone='';
  if(ndviDelta!=null){
    const n=Number(ndviDelta);
    if(n<=-0.10){vegetationState='Strong declining vegetation signal';vegetationTone='danger'}
    else if(n<=-0.03){vegetationState='Declining vegetation signal';vegetationTone='warn'}
    else if(n<0.03){vegetationState='Broadly stable vegetation signal';vegetationTone='ok'}
    else{vegetationState='Greening / increasing vegetation signal';vegetationTone='ok'}
  }

  let soilClass='Soil pH unavailable';
  if(ph.value!=null){
    soilClass=ph.value<5.5?'Acidic soil reference':ph.value<=7.5?'Near-neutral / mildly acidic soil reference':'Alkaline soil reference';
  }

  const protectedText=conservation?.inside===true||conservation?.inside_protected_area===true?'Inside protected area':conservation?.inside===false?'Outside mapped protected-area boundary':'Not confirmed';

  area.innerHTML=[
    analysisValue('Selected area',state.place||profile.location?.display_name||'Selected region',state.regionSub||'', 'wide'),
    analysisValue('Coordinates',coords,'Selected AOI center'),
    analysisValue('Air temperature',cur.temperature_2m!=null?`${fmt(cur.temperature_2m,1)} ${units.temperature_2m||'°C'}`:'—',observed?`Observed ${String(observed).replace('T',' ').slice(0,16)}`:'Weather source'),
    analysisValue('Humidity',cur.relative_humidity_2m!=null?`${fmt(cur.relative_humidity_2m,0)} ${units.relative_humidity_2m||'%'}`:'—',weather.provenance?.source||''),
    analysisValue('Current rain',cur.rain!=null?`${fmt(cur.rain,2)} ${units.rain||'mm'}`:'—','Current interval'),
    analysisValue('Soil pH',ph.value!=null?fmt(ph.value,1):'—',soilClass),
    analysisValue('Surface soil moisture',soilMoist.value!=null?`${fmt(soilMoist.value,3)} ${soilMoist.unit||''}`:'—',soilMoist.time||'0–1 cm forecast/reanalysis'),
    analysisValue('Soil organic carbon',soc.value!=null?`${fmt(soc.value,2)} ${soc.unit}`:'—',soc.depth||'SoilGrids 0–5 cm'),
    analysisValue('Soil nitrogen',nitrogen.value!=null?`${fmt(nitrogen.value,2)} ${nitrogen.unit}`:'—',nitrogen.depth||'SoilGrids 0–5 cm'),
    analysisValue('Soil texture',clay.value!=null||sand.value!=null||silt.value!=null?`Clay ${clay.value!=null?fmt(clay.value,1):'—'} • Sand ${sand.value!=null?fmt(sand.value,1):'—'} • Silt ${silt.value!=null?fmt(silt.value,1):'—'}`:'—',clay.unit||sand.unit||silt.unit||'SoilGrids'),
    analysisValue('Vegetation condition',vegetationState,ndviDelta!=null?`NDVI Δ ${fmt(ndviDelta,3)}`:'Requires before/after analysis',vegetationTone),
    analysisValue('Tree probability',treeProb!=null?pct(treeProb,1):'—','Dynamic World / enhancement'),
    analysisValue('Candidate affected area',candidateArea!=null?`${fmt(candidateArea,2)} ha`:'—',confidence!=null?`Screening confidence ${pct(confidence,0)}`:'Satellite screening'),
    analysisValue('Biomass reference',forest.gedi_agbd_mg_per_ha!=null?`${fmt(forest.gedi_agbd_mg_per_ha,1)} Mg/ha`:'—','GEDI enhancement'),
    analysisValue('Terrain',terrain.elevation_m!=null?`${fmt(terrain.elevation_m,0)} m elevation`:'—',terrain.slope_deg!=null?`Slope ${fmt(terrain.slope_deg,1)}°`:'Slope unavailable'),
    analysisValue('Fire context',fireCount!=null?`${fireCount} returned points`:'—',fireSource.provenance?.source||'Fire provider'),
    analysisValue('Human pressure',human.mapped_features!=null?`${human.mapped_features} mapped features`:'—','Road / settlement / quarry context'),
    analysisValue('Protected-area context',protectedText,sources.protected_area?.provenance?.source||'Conservation context'),
    analysisValue('Latest satellite scene',sat.latest_scene_time||'—',sat.available_scenes!=null?`${sat.available_scenes} available scenes`:'Satellite catalogue')
  ].join('');

  const changeText=candidateArea!=null
    ?`${fmt(candidateArea,2)} ha is flagged as candidate vegetation change; NDVI change is ${ndviDelta!=null?fmt(ndviDelta,3):'unavailable'}.`
    :'No complete before/after candidate-area result is available yet.';
  const climateText=climate.temperature_anomaly_c!=null||climate.rainfall_deficit_pct!=null
    ?`Temperature anomaly ${climate.temperature_anomaly_c!=null?fmt(climate.temperature_anomaly_c,2)+'°C':'—'}; rainfall deficit ${climate.rainfall_deficit_pct!=null?fmt(climate.rainfall_deficit_pct,1)+'%':'—'} over the analysis window.`
    :'Climate anomaly analysis is not complete yet.';
  const soilText=ph.value!=null||soilMoist.value!=null
    ?`${soilClass}. Surface soil moisture is ${soilMoist.value!=null?fmt(soilMoist.value,3)+' '+(soilMoist.unit||''):'unavailable'}; organic carbon and nitrogen are shown above when SoilGrids returns them.`
    :'Soil provider data is currently unavailable; VanRakshak does not fabricate soil values.';
  const fireText=fireCount!=null
    ?`${fireCount} fire-context points were returned by ${fireSource.provenance?.source||'the fire provider'}. These are context signals and require source-aware verification.`
    :'Live fire context is unavailable for this request.';
  const pressureText=human.mapped_features!=null
    ?`${human.mapped_features} mapped human-pressure features are present in the area context. This supports patrol prioritization but does not prove causation.`
    :'Human-pressure mapping is unavailable or returned no count.';
  const riskText=warning.score!=null
    ?`Current warning is ${warning.level||'UNKNOWN'} at ${fmt(warning.score,0)}/100 with ${warning.coverage!=null?pct(warning.coverage,0):'unknown'} evidence coverage.`
    :'A complete evidence-normalized warning score has not been produced yet.';

  situation.innerHTML=[
    situationRow('🌿','Vegetation / forest change',changeText,ndviDelta!=null&&Number(ndviDelta)<-0.03?'danger':''),
    situationRow('🌦','Climate stress',climateText,climate.rainfall_deficit_pct!=null&&Number(climate.rainfall_deficit_pct)>=25?'warn':''),
    situationRow('🧪','Soil condition',soilText,''),
    situationRow('🔥','Fire & heat context',fireText,fireCount>0?'warn':''),
    situationRow('⌂','Human-pressure context',pressureText,human.mapped_features>0?'warn':''),
    situationRow('⚠','Overall warning',riskText,warning.level==='CRITICAL'||warning.level==='WARNING'?'danger':warning.level==='WATCH'?'warn':'')
  ].join('');

  workflow.innerHTML=[
    ['1','Detect','Before/After + NDVI/NDMI/NBR identify candidate forest change.'],
    ['2','Verify','Evidence Chain checks satellite, climate, fire, soil and mapped pressure together.'],
    ['3','Prioritize','Forest Doctor + warning score rank the most urgent locations and likely drivers.'],
    ['4','Route','Patrol Planner sends teams first to candidate polygons and access points.'],
    ['5','Alert & document','Patrol Alert + investigation report preserve coordinates, timestamps and evidence.'],
    ['6','Recheck','Time Machine / next satellite scene validates whether the disturbance stopped or expanded.']
  ].map(x=>`<div class="workflow-step"><span>${x[0]}</span><b>${x[1]}</b><p>${x[2]}</p></div>`).join('');

  const fchange=change.fragmentation?.change||change.fragmentation_change||{};
  const frag=fchange.patch_count_pct??fchange.patch_density_pct??fchange.edge_density_pct??null;
  const actions=plan.actions||[];
  const firstUrgent=actions.find(a=>a.priority==='URGENT'||a.priority==='HIGH');
  impact.innerHTML=[
    impactTarget('Change footprint',candidateArea!=null?`${fmt(candidateArea,2)} ha candidate`:'Not measured','Stable or smaller on the next suitable observation','Validates that the disturbance is not expanding.'),
    impactTarget('Vegetation signal',ndviDelta!=null?`NDVI Δ ${fmt(ndviDelta,3)}`:'Not measured','NDVI stable or improving relative to this baseline','Recheck with cloud-screened satellite imagery.'),
    impactTarget('Fire signal',fireCount!=null?`${fireCount} context points`:'Unavailable','No new verified thermal detections in the AOI','Context detections must be verified before declaring an active fire.'),
    impactTarget('Fragmentation',frag!=null?`${Number(frag)>=0?'+':''}${fmt(frag,1)}%`:'Not measured','No worsening of patch / edge fragmentation','Compare the same geometry after intervention.'),
    impactTarget('Field response',firstUrgent?.timeframe||'Pending plan','Highest-priority locations verified and documented',firstUrgent?.where||'Selected AOI'),
    impactTarget('Overall outcome',warning.score!=null?`${warning.level||'RISK'} ${fmt(warning.score,0)}/100`:'Pending','Lower or stable risk with no unexplained new change',plan.expected_outcome||'Measured on repeat observations.')
  ].join('');

  setText('analysisAreaFreshness',observed?`Weather ${String(observed).replace('T',' ').slice(0,16)}`:'Area intelligence loaded');
}

function renderNews(n){if(!n||!n.ok){$('newsPanel').innerHTML=`<div class="empty-state">${esc(n?.error||'News context unavailable')}</div>`;return}const arts=n.data?.articles||[];$('newsPanel').innerHTML=arts.length?arts.slice(0,10).map(a=>`<article class="news-item"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title||a.url)}</a><small>${esc(a.domain||'')} • ${esc(a.seendate||'')}</small></article>`).join(''):'<div class="empty-state">No matching recent articles returned.</div>'}

function selectedAreaAlertCount(d){
  const c=d?.change||{},cl=d?.climate||{},src=d?.sources||{},carbon=d?.carbon||{};
  let n=0;
  if(Number(c.candidate_area_ha||0)>0)n++;
  if(c.mean_ndvi_change!=null&&Number(c.mean_ndvi_change)<=-0.03)n++;
  const fire=src.fire||{};if(fire.ok&&(fire.data||[]).length>0)n++;
  if((cl.rainfall_deficit_pct!=null&&Number(cl.rainfall_deficit_pct)>=25)||(cl.temperature_anomaly_c!=null&&Number(cl.temperature_anomaly_c)>=1.5))n++;
  const fc=c.fragmentation?.change||c.fragmentation_change||{};const fv=fc.patch_count_pct??fc.patch_density_pct??fc.edge_density_pct??null;if(fv!=null&&Math.abs(Number(fv))>=5)n++;
  if(d?.protected_area===true)n++;
  const hp=src.human_pressure?.data||{};const hc=hp.count??(Array.isArray(hp.elements)?hp.elements.length:null);if(hc!=null&&Number(hc)>0)n++;
  if(Number(carbon.estimated_co2e_t||0)>0)n++;
  return n;
}

async function loadEvidence(showToast=true){if(!ensureLocation())return null;const revision=state.locationRevision;const before=$('beforeDate').value,after=$('afterDate').value;try{if(showToast)toast('Running satellite change + evidence fusion…',5000);const q=`/api/analysis/evidence-chain?lat=${state.lat}&lon=${state.lon}&place=${encodeURIComponent(state.place)}&before_date=${encodeURIComponent(before)}&after_date=${encodeURIComponent(after)}&radius_km=2`;const d=await api(q);if(revision!==state.locationRevision)return null;state.evidence=d;renderEvidence(d);if(showToast)toast('Evidence analysis completed');return d}catch(e){if(showToast)toast('Analysis: '+String(e.message).slice(0,170));renderEvidence({warning:{level:'UNKNOWN',score:null,coverage:0,factors:[]},evidence_chain:{items:[]}});return null}}

function renderEvidence(d){const c=d.change||{},w=d.warning||{},doctor=d.forest_doctor||{},carbon=d.carbon||{},carbonRef=d.carbon_reference||{};const conf=c.screening_confidence;setText('areaAffected',c.candidate_area_ha!=null?`${fmt(c.candidate_area_ha,1)} ha`:'—');setText('aiConfidence',conf!=null?pct(conf,0):'—');setText('ndviChange',c.mean_ndvi_change!=null?pct(c.mean_ndvi_change,0):'—');setText('riskScore',w.score!=null?`${fmt(w.score,0)}`:'—');setText('analysisWarning',w.level||'UNKNOWN');setText('analysisCoverage',w.coverage!=null?pct(w.coverage,0):'—');setText('sumAlerts',w.score!=null?`${fmt(w.score,0)}/100`:'—');setText('sumCritical',w.level||'UNKNOWN');setText('sumAlertsDelta',w.level?`${w.level} warning`:'Evidence-normalized');setText('navAlertBadge',String(selectedAreaAlertCount(d)));
  const sev=$('severityBadge');sev.textContent=w.level||'UNKNOWN';sev.className=`severity ${(w.level||'unknown').toLowerCase()}`;
  clearDynamicLayer('candidate-loss');if(c.geojson){addGeoPolygon('candidate-loss',c.geojson,'#ff473d')}
  const drivers=doctor.probable_drivers||[];renderCauseBars(drivers);renderSignalBars(w.factors||[]);renderActionPlan(d.action_plan,d);renderEnvironment(state.investigation,state.profile);renderAnalysisIntelligence();renderDataIntegrity();
  const items=d.evidence_chain?.items||[];$('keyEvidence').innerHTML=items.length?items.slice(0,4).map(x=>`<div class="evidence-item"><span class="evidence-check">✓</span><span>${esc(x.statement||x.source||x.kind)}</span></div>`).join(''):'<div class="empty-state">No complete evidence items returned.</div>';
  $('evidenceChain').innerHTML=items.length?items.map(x=>`<p><b>${esc(x.kind)}</b> · ${esc(x.source)} — ${esc(x.statement)}</p>`).join(''):'<p>Evidence sources are unavailable or incomplete for the selected dates.</p>';
  setText('carbonImpact',carbon.estimated_co2e_t!=null?fmt(carbon.estimated_co2e_t,0):'Local unavailable');setText('carbonImpactSub',carbon.estimated_co2e_t!=null?`tCO₂e • ${carbon.estimate_class||'location-specific mapped reference'}`:carbonRef.estimated_co2e_t!=null?`IPCC context ${fmt(carbonRef.estimated_co2e_t,0)} tCO₂e • NOT local measurement`:'No location-specific biomass source');
  const protectedSource=d.sources?.protected_area?.provenance?.source||'Protected-area intelligence';
  if(d.protected_area===true){setText('protectedStatus','Inside Boundary');setText('protectedSub',protectedSource)}else if(d.protected_area===false){setText('protectedStatus','Outside Boundary');setText('protectedSub',protectedSource)}else{setText('protectedStatus','Unknown');setText('protectedSub','Protected-area source unavailable')}
  const ndviNow=c.mean_ndvi_after??null,ndviDelta=c.mean_ndvi_change??null;
  const vegLabel=ndviDelta==null?'Not measured':Number(ndviDelta)<=-0.10?'Strong Decline':Number(ndviDelta)<=-0.03?'Declining':Number(ndviDelta)<0.03?'Stable':'Improving';
  setText('vegetationStatus',vegLabel);setText('vegetationSub',ndviDelta!=null?`NDVI ${ndviNow!=null?fmt(ndviNow,3):'—'} • Δ ${fmt(ndviDelta,3)}`:'Run before/after Sentinel analysis');
  const fchange=c.fragmentation?.change||c.fragmentation_change||{};const fval=fchange.patch_count_pct??fchange.patch_density_pct??fchange.edge_density_pct??null;setText('fragmentationStatus',fval!=null?`${Number(fval)>=0?'+':''}${fmt(fval,0)}%`:'—');setText('fragmentationSub',fval!=null?'Sentinel-derived patch / edge change':'Run before/after analysis');
  setText('changeResult',c.candidate_area_ha!=null?`${fmt(c.candidate_area_ha,2)} ha candidate vegetation loss • NDVI Δ ${fmt(c.mean_ndvi_change,3)} • warning ${w.level||'UNKNOWN'} ${w.score??'—'}/100`:'No complete before/after change result for the selected dates.');
  if(state.profile)renderProfile(state.profile);
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

async function loadTrend(){if(!ensureLocation()||typeof echarts==='undefined')return;try{const start=isoDate(threeYearsAgo),end=isoDate(now);const d=await api(`/api/analysis/vegetation-series?lat=${state.lat}&lon=${state.lon}&start=${start}&end=${end}&max_observations=12&cloud_lt=${selectedFilters().cloud}`);const pts=d.observations||[];state.vegetationSeries=pts;if(!pts.length)throw new Error('No cloud-screened scenes');if(state.trendChart)state.trendChart.dispose();state.trendChart=echarts.init($('forestTrendChart'));const dates=pts.map(x=>(x.datetime||'').slice(0,10));const ndvi=pts.map(x=>x.mean_ndvi??null);const forest=pts.map(x=>x.forest_fraction==null?null:Number(x.forest_fraction)*100);state.trendChart.setOption({animation:true,grid:{left:40,right:38,top:18,bottom:26},tooltip:{trigger:'axis'},xAxis:{type:'category',data:dates,axisLine:{lineStyle:{color:'#29414d'}},axisLabel:{color:'#91a59f',fontSize:9}},yAxis:[{type:'value',min:-1,max:1,axisLine:{show:false},splitLine:{lineStyle:{color:'#17313b'}},axisLabel:{color:'#91a59f',fontSize:9}},{type:'value',min:0,max:100,show:false}],series:[{name:'Mean NDVI',type:'line',smooth:.35,data:ndvi,symbol:'none',lineStyle:{width:2,color:'#72e57e'},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'#4fd47744'},{offset:1,color:'#4fd47700'}]}},markLine:{silent:true,lineStyle:{color:'#29414d'},data:[]}}, {name:'Forest fraction %',type:'line',smooth:.35,yAxisIndex:1,data:forest,symbol:'none',lineStyle:{width:1,color:'#a8d8a1'}}]});setText('trendSubtitle',`${state.place} • ${pts.length} Sentinel-2 observations`);if(state.profile)renderProfile(state.profile)}catch(e){setText('trendSubtitle','Trend unavailable: '+String(e.message).slice(0,80));if(state.trendChart){state.trendChart.clear()}}}

async function loadSourceHealth(showToast=true){try{const [h,sh]=await Promise.all([api('/api/health'),api('/api/source-health')]);state.sourceHealth=sh;const rows=sh.sources||[];const healthy=rows.filter(x=>x.ok).length,configured=rows.filter(x=>x.status!=='NOT_CONFIGURED').length;setText('sumSources',`${healthy}/${configured||rows.length}`);setText('sumSourcesDelta','Healthy/configured providers');const wanted=['Earth Search','Planetary Computer','Copernicus STAC','Sentinel-1 ASF','Open-Meteo','MET Norway','NASA GIBS','NASA POWER','NASA EONET','Google News RSS','Photon Geocoder','NASA FIRMS','Protected Planet','Earth Engine'];const selected=[];for(const name of wanted){const r=rows.find(x=>x.source===name);if(r)selected.push(r)}for(const r of rows){if(selected.length>=6)break;if(!selected.includes(r))selected.push(r)}$('sourceList').innerHTML=selected.slice(0,6).map(r=>{const cls=r.ok?'':' '+(r.status==='NOT_CONFIGURED'?'off':'err');return `<div class="source-row"><span class="source-logo">${sourceIcon(r.source)}</span><span>${esc(r.source)}</span><em class="source-status"><i class="source-dot${cls}"></i>${r.ok?(r.latency_ms!=null?`${fmt(r.latency_ms,0)} ms`:'Healthy'):(r.status==='NOT_CONFIGURED'?'Needs credential':'Unavailable')}</em></div>`}).join('');if(h.capabilities?.firms_configured===false&&$('sumFire').textContent==='—')setText('sumFireDelta','FIRMS key not configured at runtime');if(showToast)toast(`${healthy}/${configured||rows.length} configured sources healthy`);return sh}catch(e){$('sourceList').innerHTML='<div class="empty-state">Source health endpoint unavailable.</div>';if(showToast)toast('Source health unavailable');return null}}
function sourceIcon(name){name=name.toLowerCase();if(name.includes('sentinel')||name.includes('copernicus')||name.includes('earth search')||name.includes('gibs'))return '🛰';if(name.includes('firms')||name.includes('eonet'))return '🔥';if(name.includes('meteo')||name.includes('met norway')||name.includes('power'))return '☁';if(name.includes('protected'))return '🛡';if(name.includes('photon')||name.includes('nominatim'))return '⌖';if(name.includes('soil'))return '🌱';if(name.includes('news'))return '📰';if(name.includes('earth engine'))return '🌍';return '●'}

function drawSearchBoundary(hit){const g=hit?.geojson;if(!g)return;for(const id of ['search-boundary-fill','search-boundary-line'])if(map.getLayer(id))map.removeLayer(id);if(map.getSource('search-boundary'))map.removeSource('search-boundary');map.addSource('search-boundary',{type:'geojson',data:{type:'Feature',properties:{},geometry:g}});map.addLayer({id:'search-boundary-fill',type:'fill',source:'search-boundary',paint:{'fill-color':'#20d67b','fill-opacity':.06}},map.getLayer('labels')?'labels':undefined);map.addLayer({id:'search-boundary-line',type:'line',source:'search-boundary',paint:{'line-color':'#e8fff4','line-width':1.6,'line-opacity':.9}})}
function predictionMetric(label,value,sub=''){return `<article class="metric-card"><small>${esc(label)}</small><strong>${esc(value)}</strong><em>${esc(sub)}</em></article>`}
function predictionExplainRow(title,text,meta=''){
  return `<div class="prediction-explain-row"><b>${esc(title)}</b><p>${esc(text||'Unavailable')}</p>${meta?`<small>${esc(meta)}</small>`:''}</div>`;
}
function predictionActionRow(a,i){
  return `<div class="prediction-action-row"><span>${i+1}</span><div><b>${esc(a.what||a.priority||'Action')}</b><p>${esc(a.how||a.plan||'Review source-backed evidence and verify conditions.')}</p>${a.where?`<small>WHERE • ${esc(a.where)}</small>`:''}${a.why?`<small>WHY • ${esc(a.why)}</small>`:''}${a.timeframe?`<small>WHEN • ${esc(a.timeframe)}</small>`:''}</div></div>`;
}
function predictionImpactRow(x){
  return `<div class="prediction-impact-row"><div><b>${esc(x.metric||x.label||'Impact target')}</b><small>${esc(x.current==null?'Current value unavailable':String(x.current))}</small></div><p>${esc(x.target||x.expected_impact||'Stable or improving on follow-up verification.')}</p>${x.success_check?`<em>Success check • ${esc(x.success_check)}</em>`:''}</div>`;
}
function resetPredictionNarrative(message='Run Analyze Selected Forest to generate operational prediction intelligence.'){
  ['predictionWhat','predictionWhy','predictionActions','predictionImpact','predictionConfidence'].forEach(id=>{const el=$(id);if(el)el.innerHTML=`<div class="empty-state">${esc(message)}</div>`});
}
function renderPredictionIntelligence(d,useLocation){
  const p=d.projection||d,a=p.analysis||{},fi=d.forecast_intelligence||{},ev=state.evidence||{},evChange=ev.change||{},warning=ev.warning||{};
  const what=$('predictionWhat'),why=$('predictionWhy'),actionsEl=$('predictionActions'),impactEl=$('predictionImpact'),confidenceEl=$('predictionConfidence');
  if(!what||!why||!actionsEl||!impactEl||!confidenceEl)return;

  if(!useLocation){
    const latest=a.latest_value,final=a.forecast_final;
    what.innerHTML=predictionExplainRow(
      'Numerical series projection',
      a.summary||`The supplied series is ${String(a.direction||'stable').toLowerCase()} and projects from ${latest??'—'} to ${final??'—'}.`,
      'This mode only understands the numbers you entered; it has no forest, climate, fire or field context.'
    );
    why.innerHTML=[
      predictionExplainRow('Trend direction',`${a.direction||'UNKNOWN'} • ${a.strength||'UNKNOWN'} strength`,`Trend ${p.trend_per_step!=null?fmt(p.trend_per_step,3):'—'} per step`),
      predictionExplainRow('Model agreement',`Confidence ${a.confidence_pct!=null?fmt(a.confidence_pct,0)+'%':'—'} across ${a.observations||0} observations.`,'Confidence is model quality, not event probability.')
    ].join('');
    actionsEl.innerHTML=predictionActionRow({what:'Use a real selected-forest analysis before operational action',how:'Run Analyze Selected Forest so VanRakshak can use Sentinel-2 observations and current evidence context.',why:'A user-entered number series cannot establish environmental cause or patrol priority.'},0);
    impactEl.innerHTML=predictionImpactRow({metric:'Series projection',current:latest??'—',target:'Use only as a mathematical trend scenario',success_check:'Validate against measured forest observations before decisions.'});
    confidenceEl.innerHTML=predictionExplainRow('Limitation','No geographic or environmental evidence is attached to this custom series.','Operational recommendations are intentionally withheld until a selected forest is analyzed.');
    return;
  }

  const currentRisk=d.analysis?.current_risk_index;
  const projectedRisk=d.analysis?.projected_risk_index;
  const changeText=evChange.candidate_area_ha!=null
    ? `Current evidence also screens ${fmt(evChange.candidate_area_ha,2)} ha of candidate change with NDVI Δ ${evChange.mean_ndvi_change!=null?fmt(evChange.mean_ndvi_change,3):'—'}.`
    : 'No complete candidate-change area is available from the current evidence window.';
  what.innerHTML=[
    predictionExplainRow('Forecast situation',fi.what_is_happening||d.analysis?.interpretation||a.summary||'Prediction complete.',`Current risk ${currentRisk!=null?fmt(currentRisk,1)+'/100':'—'} • projected ${projectedRisk!=null?fmt(projectedRisk,1)+'/100':'—'}`),
    predictionExplainRow('Current selected-area evidence',changeText,warning.score!=null?`Evidence warning ${warning.level||'UNKNOWN'} • ${fmt(warning.score,0)}/100`:'Evidence warning unavailable')
  ].join('');

  const reasons=(fi.why_model_is_flagging_it||[]).map(x=>predictionExplainRow(x.factor||'Model factor',x.observation||'',x.meaning||''));
  const contextual=(ev.forest_doctor?.probable_drivers||[]).slice(0,3).map(x=>predictionExplainRow(
    `Probable context: ${x.driver||'Unknown'}`,
    x.relative_support_pct!=null?`${fmt(x.relative_support_pct,0)}% relative support in the evidence model.`:'Evidence present.',
    'Context for verification only — not proof of causation.'
  ));
  const climate=ev.climate||{};
  if(climate.rainfall_deficit_pct!=null||climate.temperature_anomaly_c!=null){
    contextual.push(predictionExplainRow(
      'Climate context',
      `Temperature anomaly ${climate.temperature_anomaly_c!=null?fmt(climate.temperature_anomaly_c,2)+'°C':'—'} • rainfall deficit ${climate.rainfall_deficit_pct!=null?fmt(climate.rainfall_deficit_pct,1)+'%':'—'}.`,
      'Used as environmental context; it does not prove the cause of vegetation change.'
    ));
  }
  why.innerHTML=[...reasons,...contextual].join('')||'<div class="empty-state">The forecast completed, but no explanatory factors were returned.</div>';

  const evidenceActions=(ev.action_plan?.actions||[]).slice(0,4);
  const forecastActions=fi.recommended_actions||[];
  const chosenActions=evidenceActions.length?evidenceActions:forecastActions;
  actionsEl.innerHTML=chosenActions.length
    ?chosenActions.map((x,i)=>predictionActionRow(x,i)).join('')
    :predictionActionRow({what:'Verify before escalation',how:'Re-run before/after evidence analysis, inspect the newest satellite scene and field-verify any candidate hotspot.',why:'A forecast is a screening signal rather than proof.'},0);

  const impactTargets=[...(fi.expected_impacts||[])];
  if(ev.carbon?.estimated_co2e_t!=null){
    impactTargets.push({metric:'Local carbon exposure baseline',current:`${fmt(ev.carbon.estimated_co2e_t,1)} tCO₂e • location-specific mapped reference`,target:'Prevent further candidate-area expansion',success_check:'Recompute only after a verified area change and replace with field inventory when available.'});
  }else if(ev.carbon_reference?.estimated_co2e_t!=null){
    impactTargets.push({metric:'Carbon reference context',current:`${fmt(ev.carbon_reference.estimated_co2e_t,1)} tCO₂e • IPCC regional reference`,target:'Do not present as local carbon loss',success_check:'Use only as context until a location-specific biomass/carbon source is available.'});
  }
  const frag=evChange.fragmentation?.change||evChange.fragmentation_change||{};
  const fragValue=frag.patch_count_pct??frag.patch_density_pct??frag.edge_density_pct??null;
  if(fragValue!=null){
    impactTargets.push({metric:'Fragmentation',current:`${Number(fragValue)>=0?'+':''}${fmt(fragValue,1)}%`,target:'No further worsening of patch / edge fragmentation',success_check:'Compare the same AOI on the next suitable observation.'});
  }
  impactEl.innerHTML=impactTargets.length
    ?impactTargets.slice(0,6).map(predictionImpactRow).join('')
    :'<div class="empty-state">No measurable impact targets were returned.</div>';

  const uncertainty=fi.uncertainty||{};
  const interval=uncertainty.final_interval||{};
  const backtest=uncertainty.backtest||d.analysis?.temporal_backtest||{};
  const next=fi.verification_next||[];
  confidenceEl.innerHTML=[
    predictionExplainRow(
      'Model confidence',
      `${uncertainty.confidence_pct??d.analysis?.model_confidence_pct??a.confidence_pct??'—'}% model confidence • optical quality ${d.analysis?.optical_quality_pct!=null?fmt(d.analysis.optical_quality_pct,0)+'%':'—'}.`,
      uncertainty.note||'Confidence describes fit and data quality, not the probability of deforestation.'
    ),
    predictionExplainRow(
      'Real temporal holdout backtest',
      backtest.available
        ?`MAE ${fmt(backtest.mae,2)} • RMSE ${fmt(backtest.rmse,2)} • interval coverage ${fmt(backtest.interval_coverage_pct,0)}% across ${backtest.holdout_observations} held-out observation(s).`
        :`Unavailable: ${backtest.reason||'not enough real observations'}`,
      backtest.note||'Backtest evaluates held-out Sentinel-derived screening-risk values; it is not ground-truth deforestation classification accuracy.'
    ),
    predictionExplainRow(
      'Forecast uncertainty',
      interval.lower!=null&&interval.upper!=null?`Final forecast interval ${fmt(interval.lower,1)}–${fmt(interval.upper,1)} on the 0–100 screening index.`:'Forecast interval unavailable.',
      p.uncertainty_sigma!=null?`Residual uncertainty σ ${fmt(p.uncertainty_sigma,2)}`:''
    ),
    ...next.map((x,i)=>predictionExplainRow(`Verify next ${i+1}`,x,'')),
    predictionExplainRow('Causation warning',fi.causation_note||d.warning||'The prediction explains the model signal; real-world cause requires evidence-chain and field verification.','')
  ].join('');
}
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
  renderPredictionIntelligence(d,useLocation);
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
    btn.disabled=true;setText('predictionStatus',useLocation?'Reading Sentinel-2 observations and computing forest trend…':'Validating series and fitting robust forecast models…');$('predictionSummary').innerHTML='';resetPredictionNarrative('Prediction analysis in progress…');$('predictionUpdates').innerHTML='<div class="update-row"><b>•</b><span>Analysis in progress…</span></div>';
    let d;
    if(!useLocation){
      const values=$('predictionValues').value.split(/[\s,]+/).filter(Boolean).map(Number);
      if(values.length<3||values.some(v=>!Number.isFinite(v)))throw new Error('Enter at least three finite numeric values.');
      d=await api('/api/intelligence/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values,steps:4,floor:0,ceiling:100})});d={...d,source:'User-entered series',historical_risk_proxy:values,dates:values.map((_,i)=>`Obs ${i+1}`)};
    }else{
      if(!ensureLocation())return;
      const start=$('timeStart')?.value||isoDate(threeYearsAgo),end=$('timeEnd')?.value||isoDate(now);
      if(start>=end)throw new Error('Prediction start date must be before end date.');
      if(!state.evidence)await loadEvidence(false);
      d=await api(`/api/intelligence/predict-location?lat=${state.lat}&lon=${state.lon}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&max_observations=12`);
    }
    renderPredictionResult(d,useLocation);toast(useLocation?'Selected forest prediction updated':'Series projection updated');
  }catch(e){setText('predictionStatus','Prediction failed: '+e.message);$('predictionResult').textContent=e.message;$('predictionUpdates').innerHTML='<div class="update-row"><b>!</b><span>Prediction could not be completed. Check the date range and source availability.</span></div>';resetPredictionNarrative('Prediction unavailable: '+String(e.message).slice(0,140))}finally{btn.disabled=false}
}
async function runWhatIf(){try{if(!ensureLocation())return;const before=$('beforeDate').value,after=$('afterDate').value;if(!before||!after)throw new Error('Select real before/after dates first');const qs=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after,temperature_delta_c:String(Number($('whatTemp').value||0)),rainfall_delta_pct:String(Number($('whatRain').value||0)),fire_delta:String(Number($('whatFire').value||0)),ndvi_delta:'0'});const d=await api('/api/intelligence/what-if-location?'+qs.toString());$('whatIfResult').textContent=JSON.stringify(d,null,2)}catch(e){$('whatIfResult').textContent=e.message}}

function openPatrol(){
  if(!ensureLocation())return;
  $('patrolModal').classList.remove('hidden');
  $('patrolScroll')?.scrollTo({top:0,behavior:'auto'});
  if(!$('patrolPoints').value.trim())$('patrolPoints').value=`${state.lat.toFixed(5)},${state.lon.toFixed(5)},95`;
  setTimeout(()=>{try{state.patrolMap?.resize()}catch{}},60);
}
function closePatrol(){
  $('patrolModal').classList.add('hidden');
}
function fitLineGeometry(geometry,targetMap=map){
  const coords=geometry?.coordinates||[];
  if(!coords.length)return;
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const c of coords){
    if(!Array.isArray(c)||c.length<2)continue;
    minX=Math.min(minX,c[0]);maxX=Math.max(maxX,c[0]);minY=Math.min(minY,c[1]);maxY=Math.max(maxY,c[1]);
  }
  if(Number.isFinite(minX))targetMap.fitBounds([[minX,minY],[maxX,maxY]],{padding:60,maxZoom:14,duration:650});
}
function patrolFallbackGeometry(route){
  const coords=[[state.lon,state.lat],...(route||[]).map(x=>[Number(x.lon),Number(x.lat)]).filter(x=>x.every(Number.isFinite))];
  return coords.length>1?{type:'LineString',coordinates:coords}:null;
}
function drawPatrolOnMainMap(route,road){
  clearDynamicLayer('patrol-route');clearDynamicLayer('patrol-stops');
  const features=[{type:'Feature',properties:{kind:'start',label:'Start'},geometry:{type:'Point',coordinates:[state.lon,state.lat]}},...route.map((s,i)=>({type:'Feature',properties:{id:s.id,priority:s.priority,order:s.order||i+1,label:`Stop ${i+1}`},geometry:{type:'Point',coordinates:[s.lon,s.lat]}}))];
  addGeoPoints('patrol-stops',features,'#ffd166');
  const geometry=road?.geometry||patrolFallbackGeometry(route);
  state.patrolRouteGeometry=geometry;
  if(!geometry){fitSelected();return}
  const fallback=!road?.geometry;
  map.addSource('src-patrol-route',{type:'geojson',data:{type:'Feature',properties:{fallback},geometry}});
  map.addLayer({id:'lyr-patrol-route',type:'line',source:'src-patrol-route',paint:{
    'line-color':fallback?'#f2bd4b':'#37e79c',
    'line-width':fallback?4:6,
    'line-opacity':.98,
    'line-dasharray':fallback?[2,2]:[1,0.01]
  }},map.getLayer('labels')?'labels':undefined);
  state.active.set('patrol-route',{source:'src-patrol-route',layer:'lyr-patrol-route'});
  fitLineGeometry(geometry,map);
}
function renderPatrolMiniMap(route,road){
  const el=$('patrolRouteMap'),fallbackEl=$('patrolMapFallback');
  if(!el||typeof maplibregl==='undefined')return;
  try{state.patrolMap?.remove()}catch{}
  const geometry=road?.geometry||patrolFallbackGeometry(route);
  if(!geometry){if(fallbackEl)fallbackEl.textContent='No route geometry is available for this patrol.';return}
  if(fallbackEl)fallbackEl.textContent=road?.geometry?'Road/track geometry from the routing provider.':'Road geometry unavailable — dashed line shows stop order only and must not be treated as drivable.';
  state.patrolMap=new maplibregl.Map({container:el,style:baseStyle,center:[state.lon,state.lat],zoom:11,attributionControl:false});
  state.patrolMap.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');
  state.patrolMap.on('load',()=>{
    const fallback=!road?.geometry;
    state.patrolMap.addSource('patrol-route-mini',{type:'geojson',data:{type:'Feature',properties:{fallback},geometry}});
    state.patrolMap.addLayer({id:'patrol-route-mini-line',type:'line',source:'patrol-route-mini',paint:{'line-color':fallback?'#f2bd4b':'#37e79c','line-width':5,'line-opacity':.98,'line-dasharray':fallback?[2,2]:[1,0.01]}});
    const pointFeatures=[
      {type:'Feature',properties:{order:0},geometry:{type:'Point',coordinates:[state.lon,state.lat]}},
      ...route.map((x,i)=>({type:'Feature',properties:{order:i+1},geometry:{type:'Point',coordinates:[x.lon,x.lat]}}))
    ];
    state.patrolMap.addSource('patrol-stops-mini',{type:'geojson',data:{type:'FeatureCollection',features:pointFeatures}});
    state.patrolMap.addLayer({id:'patrol-stops-mini-circles',type:'circle',source:'patrol-stops-mini',paint:{'circle-radius':7,'circle-color':'#ffd166','circle-stroke-color':'#08151c','circle-stroke-width':2}});
    fitLineGeometry(geometry,state.patrolMap);
  });
}
function renderPatrolBrief(d,route){
  const brief=d.operational_brief||{},analysis=d.analysis||{};
  const drivers=brief.probable_drivers||[];
  const actions=brief.recommended_actions||[];
  const sceneBefore=brief.before_scene||{},sceneAfter=brief.after_scene||{};
  const rows=[];
  rows.push(`<div class="patrol-brief-block"><small>SITUATION</small><p>${esc(brief.situation||`${route.length} ordered patrol stop(s) prepared.`)}</p></div>`);
  if(sceneBefore.id||sceneAfter.id){
    rows.push(`<div class="patrol-brief-block"><small>REAL SATELLITE EVIDENCE</small><p>Before: ${esc(sceneBefore.id||analysis.before_scene||'—')} • ${esc(String(sceneBefore.datetime||analysis.before_observed_at||'').slice(0,19)||'—')}</p><p>After: ${esc(sceneAfter.id||analysis.after_scene||'—')} • ${esc(String(sceneAfter.datetime||analysis.after_observed_at||'').slice(0,19)||'—')}</p><button id="openPatrolSatelliteEvidence" class="small-secondary">View Before / After Satellite Evidence</button></div>`);
  }
  if(drivers.length){
    rows.push(`<div class="patrol-brief-block"><small>WHAT TO VERIFY — NOT CONFIRMED CAUSES</small>${drivers.slice(0,4).map(x=>`<p>• ${esc(x.driver||x.name||'Context signal')} ${x.relative_support_pct!=null?`• ${fmt(x.relative_support_pct,0)}% relative support`:''}</p>`).join('')}</div>`);
  }
  if(actions.length){
    rows.push(`<div class="patrol-brief-block"><small>VANRAKSHAK ACTION PLAN</small>${actions.slice(0,5).map((x,i)=>`<p><b>${i+1}. ${esc(x.what||'Action')}</b> — ${esc(x.how||'Verify in the field.')} ${x.timeframe?`<em>${esc(x.timeframe)}</em>`:''}</p>`).join('')}</div>`);
  }
  rows.push(`<div class="patrol-brief-block"><small>EXPECTED IMPACT</small><p>${esc(brief.expected_impact||'Create a verified field record and prevent unverified satellite screening from being treated as confirmed ground truth.')}</p></div>`);
  rows.push(`<div class="patrol-brief-block caution"><small>FIELD RULE</small><p>${esc(brief.field_rule||d.warning||'Verify field accessibility and do not infer cause from satellite screening alone.')}</p></div>`);
  $('patrolBrief').innerHTML=rows.join('');
  const evidence=brief.evidence_required||route.flatMap(x=>x.evidence_required?Object.values(x.evidence_required):[]).filter(Boolean);
  $('patrolEvidenceRequirements').innerHTML=evidence.length?evidence.map((x,i)=>`<div class="evidence-requirement"><b>${i+1}</b><span>${esc(x)}</span></div>`).join(''):'<div class="drawer-note">Capture geotagged overview media, close-up disturbance evidence and factual notes at each stop.</div>';
  const satelliteBtn=$('openPatrolSatelliteEvidence');
  if(satelliteBtn)satelliteBtn.onclick=()=>{closePatrol();showTab('before');$('inspector')?.scrollTo({top:0,behavior:'smooth'});};
}
function renderPatrolEvidenceFiles(files){
  for(const u of state.patrolEvidenceUrls||[])try{URL.revokeObjectURL(u)}catch{}
  state.patrolEvidenceUrls=[];
  const rows=[];
  for(const file of Array.from(files||[]).slice(0,12)){
    const url=URL.createObjectURL(file);state.patrolEvidenceUrls.push(url);
    const meta=`${file.name} • ${(file.size/1024/1024).toFixed(1)} MB • ${new Date(file.lastModified||Date.now()).toLocaleString()}`;
    if(file.type.startsWith('video/'))rows.push(`<article class="field-media-item"><video src="${url}" controls preload="metadata"></video><small>${esc(meta)}</small><b>Real field video attachment • metadata must match stop/location/time.</b></article>`);
    else if(file.type.startsWith('image/'))rows.push(`<article class="field-media-item"><img src="${url}" alt="Patrol field evidence preview"><small>${esc(meta)}</small><b>Real field photo attachment • metadata must match stop/location/time.</b></article>`);
    else rows.push(`<article class="field-media-item"><small>${esc(meta)}</small><b>Attached evidence file</b></article>`);
  }
  $('patrolEvidencePreview').innerHTML=rows.length?rows.join(''):'<div class="drawer-note">No field media attached yet.</div>';
}
function renderPatrolResult(d,useDetected){
  const o=d.ordering||{},route=o.route||[],road=d.road_route||{};
  const patrolMetrics=[
    predictionMetric('Stops',String(route.length),useDetected?'detected hotspots':'entered targets'),
    predictionMetric('Road distance',road.distance_km!=null?`${fmt(road.distance_km,1)} km`:'Unavailable',o.ordering_mode||''),
    predictionMetric('ETA',road.duration_min!=null?`${fmt(road.duration_min,0)} min`:'—',road.source||'fallback ordering'),
    predictionMetric('Route source',road.source||'Priority order only',road.geometry?'road geometry':'no road geometry')
  ];
  if(useDetected&&d.analysis){
    patrolMetrics.push(
      predictionMetric('Candidate area',d.analysis.candidate_area_ha!=null?`${fmt(d.analysis.candidate_area_ha,2)} ha`:'—','screened change'),
      predictionMetric('Screen confidence',d.analysis.screening_confidence!=null?pct(d.analysis.screening_confidence,0):'—','multispectral'),
      predictionMetric('Warning score',fmt(d.analysis.warning_score,0),'/ 100'),
      predictionMetric('Scene period',String(d.analysis.before_observed_at||'').slice(0,10)||'—',`→ ${String(d.analysis.after_observed_at||'').slice(0,10)||'—'}`)
    );
  }
  $('patrolMetrics').innerHTML=patrolMetrics.join('');
  $('patrolStops').innerHTML=route.map((stop,i)=>{
    const area=stop.candidate_context?.area_ha,tasks=stop.field_tasks||[];
    return `<article class="route-stop precise-stop"><b>${i+1}</b><div><strong>${esc(stop.id)}</strong><small>${fmt(stop.lat,5)}, ${fmt(stop.lon,5)} • priority ${fmt(stop.priority,0)}/100 (${esc(stop.priority_band||'')})${area!=null?` • ${fmt(area,2)} ha candidate`:''}</small><em>${esc(stop.why_selected||'Evidence-ranked patrol target.')}</em>${tasks.length?`<details><summary>Exact field checks</summary>${tasks.map(x=>`<p>• ${esc(x)}</p>`).join('')}</details>`:''}</div></article>`;
  }).join('')||'<div class="empty-state">No patrol hotspots detected for this comparison.</div>';
  const steps=(road.legs||[]).flatMap((leg,li)=>(leg.steps||[]).slice(0,12).map(x=>({...x,leg:li+1})));
  $('patrolInstructions').innerHTML=steps.length?`<h3>Road Guidance</h3>${steps.map(x=>`<div class="route-step"><b>L${x.leg}</b><span>${esc(x.instruction)} <small>${fmt(x.distance_m,0)} m • ${fmt(x.duration_min,1)} min</small></span></div>`).join('')}`:'<div class="drawer-note">No turn guidance returned. The ordered stops remain available, but dashed straight-line ordering must not be treated as a drivable road.</div>';
  $('patrolResult').textContent=JSON.stringify(d,null,2);
  renderPatrolBrief(d,route);
  drawPatrolOnMainMap(route,road);
  renderPatrolMiniMap(route,road);
  $('showPatrolMainMap').disabled=!state.patrolRouteGeometry;
  if(d.status==='NO_PATROL_TARGETS')setText('patrolStatus','Analysis complete: no candidate-change patrol hotspots were detected. No route was fabricated.');
  else setText('patrolStatus',road.geometry?`Road route ready from ${road.source}. ${fmt(road.distance_km,1)} km / ~${fmt(road.duration_min,0)} min. Verify forest-track accessibility before deployment.`:`Road geometry unavailable. Showing ${o.ordering_mode||'priority'} stop ordering only; dashed lines are not roads.`);
}
async function runPatrol(useDetected=false){
  const btn=useDetected?$('runDetectedPatrol'):$('runPatrol');
  try{
    if(!ensureLocation())return;
    btn.disabled=true;
    setText('patrolStatus',useDetected?'Running real change screening, extracting hotspots and requesting road travel matrix…':'Validating stops and requesting road travel matrix…');
    $('patrolMetrics').innerHTML='';
    $('patrolStops').innerHTML='<div class="empty-state">Building precise route…</div>';
    $('patrolBrief').innerHTML='<div class="empty-state">Building operational field brief…</div>';
    $('patrolEvidenceRequirements').innerHTML='<div class="empty-state">Loading evidence requirements…</div>';
    $('patrolInstructions').innerHTML='';
    $('showPatrolMainMap').disabled=true;
    const before=$('beforeDate').value,after=$('afterDate').value;
    let d;
    if(useDetected){
      if(!before||!after)throw new Error('Select real before/after dates first');
      const q=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after,max_points:'5'});
      d=await api('/api/patrol/live?'+q.toString());
    }else{
      const points=$('patrolPoints').value.trim().split('\n').filter(Boolean).map((row,i)=>{
        const v=row.split(',').map(x=>Number(x.trim()));
        if(v.length!==3||v.some(x=>!Number.isFinite(x))||Math.abs(v[0])>90||Math.abs(v[1])>180||v[2]<0||v[2]>100)throw new Error(`Invalid stop on line ${i+1}: use lat,lon,priority (0–100).`);
        return {id:String(i+1),lat:v[0],lon:v[1],priority:v[2]};
      });
      if(!points.length)throw new Error('Enter at least one patrol stop.');
      d=await api('/api/patrol/road-route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_lat:state.lat,start_lon:state.lon,points})});
      d.operational_brief={
        situation:`${points.length} manually entered patrol stop(s) ordered using road travel time where available.`,
        evidence_required:[
          'Geotagged overview photo at every stop.',
          'Continuous 15–30 second video showing site condition and access route.',
          'Close-up photos of any physical disturbance indicators.',
          'GPS coordinates, timestamp, stop ID, patrol member and factual observation note.'
        ],
        field_rule:'Manual priorities are user-entered. Verify site conditions and never treat the route itself as evidence of disturbance.',
        expected_impact:'Create a consistent field-verification record across all manually selected stops.'
      };
    }
    if(useDetected)state.alertPatrol=d;
    renderPatrolResult(d,useDetected);
    $('patrolScroll')?.scrollTo({top:0,behavior:'smooth'});
    toast(d.status==='NO_PATROL_TARGETS'?'Analysis complete: no patrol hotspots detected':d.road_route?'Road-aware patrol route loaded on both maps':'Road route unavailable; priority ordering displayed',4500);
  }catch(e){
    setText('patrolStatus','Patrol route failed: '+e.message);
    $('patrolResult').textContent=e.message;
    $('patrolStops').innerHTML='';
    $('patrolBrief').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;
    $('patrolEvidenceRequirements').innerHTML='';
    $('patrolInstructions').innerHTML='';
    $('showPatrolMainMap').disabled=true;
  }finally{btn.disabled=false}
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
function alertSeverityClass(level){
  const v=String(level||'INFO').toUpperCase();
  if(['CRITICAL','URGENT'].includes(v))return 'urgent';
  if(['HIGH','WARNING'].includes(v))return 'high';
  if(['WATCH','MEDIUM'].includes(v))return 'watch';
  return 'info';
}
function renderAlertQueue(alerts){
  const weight={CRITICAL:100,URGENT:95,HIGH:80,WARNING:75,WATCH:55,MEDIUM:50,INFO:20};
  const rows=[...(alerts||[])].sort((a,b)=>(weight[String(b.severity||'INFO').toUpperCase()]||0)-(weight[String(a.severity||'INFO').toUpperCase()]||0));
  state.alertQueue=rows;
  setText('alertCount',`${rows.length} alert${rows.length===1?'':'s'}`);
  setText('navAlertBadge',String(rows.length));
  if(!rows.length){
    $('alertQueue').innerHTML='<div class="empty-state">No active selected-area alert signals were generated from the available evidence.</div>';
    $('alertSelectedPlan').innerHTML='<div class="drawer-note">No actionable alert is currently supported by the available selected-area evidence. Continue monitoring and rerun after new observations.</div>';
    return;
  }
  $('alertQueue').innerHTML=rows.map((a,i)=>`<button class="alert-queue-item ${alertSeverityClass(a.severity)}${i===0?' active':''}" data-alert-item="${esc(a.id)}"><span class="alert-queue-severity">${esc(a.severity||'INFO')}</span><div><b>${esc(a.title||a.kind||'Alert')}</b><small>${esc(a.when||'Time unavailable')}</small><p>${esc(a.summary||'')}</p></div><span class="alert-queue-arrow">›</span></button>`).join('');
  $$('[data-alert-item]').forEach(btn=>btn.onclick=()=>showAlertDetail(btn.dataset.alertItem));
  showAlertDetail(rows[0].id);
}
function showAlertDetail(id){
  const a=(state.alertQueue||[]).find(x=>String(x.id)===String(id));
  if(!a)return;
  $$('[data-alert-item]').forEach(x=>x.classList.toggle('active',x.dataset.alertItem===String(id)));
  $('alertSelectedPlan').innerHTML=`<article class="detail-card selected-alert-detail ${alertSeverityClass(a.severity)}">
    <div class="selected-alert-head"><div><small>${esc(a.kind||'ALERT')} • ${esc(a.when||'Time unavailable')}</small><h3>${esc(a.title||'Selected alert')}</h3></div><span>${esc(a.severity||'INFO')}</span></div>
    <div class="selected-alert-grid">
      <div><small>WHAT IS HAPPENING</small><p>${esc(a.summary||'No summary returned.')}</p></div>
      <div><small>EVIDENCE</small><p>${esc(a.evidence||'No evidence description returned.')}</p></div>
      <div><small>VANRAKSHAK PLAN</small><p>${esc(a.plan||'Field-verify before escalation.')}</p></div>
      <div><small>EXPECTED IMPACT</small><p>${esc(a.expected_impact||'Validate that the condition does not worsen on the next observation.')}</p></div>
    </div>
  </article>`;
}
function renderAlert(d){
  const c=d.change||{},top=d.top_patrol_target||{},period=d.detected_period||{},impact=d.impact_summary||{},metrics=[
    predictionMetric('Active alerts',String((d.alerts||[]).length),'selected area'),
    predictionMetric('Severity',d.severity||'UNKNOWN','field triage'),
    predictionMetric('Warning score',d.warning_score!=null?fmt(d.warning_score,0)+'/100':'—','evidence-normalized'),
    predictionMetric('Candidate area',c.candidate_area_ha!=null?fmt(c.candidate_area_ha,2)+' ha':'—',`${c.candidate_polygons??0} polygon(s)`),
    predictionMetric('Confidence',c.screening_confidence!=null?pct(c.screening_confidence,0):'—','change screening'),
    predictionMetric('NDVI change',c.mean_ndvi_change!=null?fmt(c.mean_ndvi_change,3):'—','vegetation signal'),
    predictionMetric('Before',period.before||'—','satellite observation'),
    predictionMetric('After',period.after||'—','satellite observation')
  ];
  $('alertMetrics').innerHTML=metrics.join('');
  renderAlertQueue(d.alerts||[]);
  $('alertContext').innerHTML=`<p><b>Location:</b> ${esc(d.location?.place||state.place)}</p><p><b>Coordinates:</b> ${fmt(d.location?.lat,6)}, ${fmt(d.location?.lon,6)}</p><p><b>Detected:</b> ${c.candidate_area_ha!=null?fmt(c.candidate_area_ha,2)+' ha candidate change':'No complete area'} across ${c.candidate_polygons??0} polygon(s).</p><p><b>Period:</b> ${esc(period.before||'—')} → ${esc(period.after||'—')}</p><p><b>Priority target:</b> ${top.lat!=null?`${fmt(top.lat,6)}, ${fmt(top.lon,6)}`:'Selected location'} ${top.area_ha!=null?`• ${fmt(top.area_ha,2)} ha`:''}</p><p><b>Carbon impact:</b> ${impact.carbon?.estimated_co2e_t!=null?fmt(impact.carbon.estimated_co2e_t,1)+' tCO₂e estimated':'Not calculated'}</p><p><b>Protected context:</b> ${impact.protected_area===true?'Inside returned protected-area boundary':impact.protected_area===false?'Outside returned protected-area boundary':'Not confirmed'}</p><p><b>Vegetation:</b> ${esc(impact.vegetation?.condition||'unknown')}</p>`;
  const drivers=d.probable_drivers||[];
  $('alertDrivers').innerHTML=drivers.length?drivers.map(x=>`<div class="alert-driver"><span>${esc(x.driver)}</span><b>${x.support_pct!=null?fmt(x.support_pct,0)+'%':'evidence present'}</b></div>`).join(''):'<div class="drawer-note">No cause is established from the current evidence. Patrol should verify conditions without assuming a cause.</div>';
  refreshAlertMessage();
  setText('alertStatus',`${(d.alerts||[]).length} selected-area alert(s) • ${d.severity||'UNKNOWN'} overall • incident ${d.incident_id||'—'} • generated ${String(d.generated_at||'').replace('T',' ').slice(0,19)} UTC`);
}
async function composeCurrentAlert(){
  if($('alertModal')?.classList.contains('hidden'))return null;
  if(!ensureLocation())return null;
  const before=$('beforeDate').value,after=$('afterDate').value;
  try{
    validateCompareDates(before,after);
    setText('alertStatus','Analyzing selected forest and composing patrol message…');
    $('alertMetrics').innerHTML='';
    setText('alertCount','Analyzing…');
    $('alertQueue').innerHTML='<div class="empty-state">Building selected-area alert queue from forest change, vegetation, fire, climate, fragmentation, protected-area and human-pressure evidence…</div>';
    $('alertSelectedPlan').innerHTML='<div class="empty-state">Waiting for alert evidence and response plan…</div>';
    $('alertContext').innerHTML='<div class="empty-state">Reading source-backed forest evidence…</div>';
    $('alertDrivers').innerHTML='<div class="empty-state">Evaluating probable drivers…</div>';
    const q=new URLSearchParams({lat:String(state.lat),lon:String(state.lon),place:state.place,before_date:before,after_date:after});
    const d=await api('/api/alerts/compose?'+q.toString());
    state.alert=d;state.alertPatrol=null;renderAlert(d);toast('Patrol alert generated from current evidence');return d;
  }catch(e){
    setText('alertStatus','Alert generation failed: '+e.message);
    $('alertQueue').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;setText('alertCount','0 alerts');
    $('alertSelectedPlan').innerHTML='<div class="drawer-note">Alert analysis could not be completed. No incident status is inferred from missing data.</div>';
    $('alertContext').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;
    $('alertDrivers').innerHTML='';$('alertMessage').value='';state.alert=null;state.alertQueue=[];return null;
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
$('aiAssistantBtn').onclick=()=>{$('searchBox').focus();$('searchBox').placeholder='Ask: show fire risk near Bandipur, forest change in Kodagu…';toast('Type a forest question or place in the search bar')};
$('openLayerDrawerEnv').onclick=openLayerDrawer;
$('closeIntelligence').onclick=()=>$('intelligenceModal').classList.add('hidden');$('runPrediction').onclick=()=>runPrediction(false);$('runLocationPrediction').onclick=()=>runPrediction(true);$('runWhatIf').onclick=runWhatIf;
$('closePatrol').onclick=closePatrol;$('runPatrol').onclick=()=>runPatrol(false);$('runDetectedPatrol').onclick=()=>runPatrol(true);
$('showPatrolMainMap').onclick=()=>{closePatrol();showTab('overview');if(state.patrolRouteGeometry)fitLineGeometry(state.patrolRouteGeometry,map);else fitSelected();toast('Patrol route shown on main map')};
$('patrolEvidenceFiles').onchange=e=>renderPatrolEvidenceFiles(e.target.files);
$('patrolModal').addEventListener('click',e=>{if(e.target===$('patrolModal'))closePatrol()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('patrolModal').classList.contains('hidden'))closePatrol()});
$('closeAlert').onclick=()=>$('alertModal').classList.add('hidden');$('refreshAlert').onclick=composeCurrentAlert;$('attachAlertPatrol').onclick=attachAlertPatrolRoute;$('copyAlert').onclick=copyAlertMessage;$('shareAlert').onclick=shareAlertMessage;$('whatsappAlert').onclick=whatsappAlertMessage;$('emailAlert').onclick=emailAlertMessage;
$('openTime').onclick=()=>{$('timeModal').classList.remove('hidden');state.timeMap?.resize()};
$('closeTime').onclick=()=>{if(state.timeTimer){clearInterval(state.timeTimer);state.timeTimer=null}$('playTime').textContent='▶ Play';$('timeModal').classList.add('hidden')};$('loadTime').onclick=loadTime;$('playTime').onclick=toggleTimePlay;
$('addBhuvan').onclick=()=>{const layer=$('bhuvanLayer').value.trim();if(!layer)return toast('Enter an exact Bhuvan-published WMS layer name');addRaster('bhuvan-custom',`/api/bhuvan/tile/{z}/{x}/{y}.png?layer=${encodeURIComponent(layer)}`,.78);toast('Bhuvan layer added')};

$$('[data-nav]').forEach(b=>b.onclick=async()=>{const n=b.dataset.nav;$$('[data-nav]').forEach(x=>x.classList.toggle('active',x===b));if(n==='map'){showTab('overview');fitSelected()}if(n==='forest')await quickLayer('forest');if(n==='alerts')await openAlertCenter();if(n==='analysis'){showTab('analysis');await loadEvidence(false)}if(n==='weather'){showTab('environment');renderEnvironment(state.investigation,state.profile)}if(n==='fire'){await quickLayer('fire')}if(n==='soil'){showTab('environment');renderEnvironment(state.investigation,state.profile);openLayerDrawer()}if(n==='predictions')$('intelligenceModal').classList.remove('hidden');if(n==='patrol')openPatrol();if(n==='reports')generateReport()});

// Keep paired date controls synchronized.
$('beforeDate').onchange=()=>{$('modalBeforeDate').value=$('beforeDate').value};$('afterDate').onchange=()=>{$('modalAfterDate').value=$('afterDate').value};$('modalBeforeDate').onchange=()=>{$('beforeDate').value=$('modalBeforeDate').value};$('modalAfterDate').onchange=()=>{$('afterDate').value=$('modalAfterDate').value};

let resizeFrame=0;window.addEventListener('resize',()=>{if(resizeFrame)cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=0;state.trendChart?.resize();state.predictionChart?.resize();setInlineCompareSplit($('inlineCompareSlider')?.value||50);setModalCompareSplit($('compareSlider')?.value||50);[map,state.inlineBefore,state.inlineAfter,state.panelBefore,state.panelAfter,state.modalBefore,state.modalAfter,state.timeMap,state.patrolMap].forEach(m=>{try{m?.resize()}catch{}})})},{passive:true});

// Initial boot: exact dashboard layout opens on Kodagu with real source calls.
(async function boot(){
  const start=()=>{map.flyTo({center:[state.lon,state.lat],zoom:8.2,duration:1400});investigate(state.lat,state.lon,state.place)};
  if(map.isStyleLoaded())start();else map.once('load',start);
  await Promise.allSettled([loadLayers(),loadSourceHealth(false)]);
})();
