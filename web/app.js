const API='';
const $=(id)=>document.getElementById(id);
const state={lat:null,lon:null,place:'India',investigation:null,layers:null};

function toast(msg){const t=$('toast');t.textContent=msg;t.classList.remove('hidden');setTimeout(()=>t.classList.add('hidden'),2600)}
async function api(path,opts={}){const r=await fetch(API+path,opts); if(!r.ok) throw new Error(`${r.status} ${await r.text()}`); return r.json()}

const map=new maplibregl.Map({container:'map',center:[78.9,22.8],zoom:4.2,style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'osm',type:'raster',source:'osm',paint:{'raster-saturation':-.15,'raster-brightness-min':.18,'raster-brightness-max':.75,'raster-contrast':.08}}]}});
map.addControl(new maplibregl.NavigationControl(),'top-right');
map.on('click',e=>investigate(e.lngLat.lat,e.lngLat.lng,state.place));

async function loadLayers(){
  const data=await api('/api/layers'); state.layers=data.groups; renderLayers();
}
function renderLayers(){
 const fresh=$('freshnessFilter').value,res=Number($('resolutionFilter').value||0);
 $('layerGroups').innerHTML=state.layers.map(g=>{
  const rows=g.layers.filter(l=>(!fresh||l.freshness===fresh)&&(!res||!l.resolution_m||l.resolution_m<=res)).map(l=>`<div class="layer-row"><label><input type="checkbox" data-layer="${l.id}"> ${l.label}</label><span class="layer-meta">${l.source}<br>${l.resolution_m?l.resolution_m+' m':''} ${l.freshness||''}</span></div>`).join('');
  return rows?`<div class="layer-group"><h3>${g.icon||''} ${g.label}</h3>${rows}</div>`:'';
 }).join('');
 document.querySelectorAll('[data-layer]').forEach(x=>x.addEventListener('change',()=>toast(`${x.checked?'Enabled':'Disabled'} ${x.dataset.layer}. Raster rendering adapters are source-dependent.`)));
}

async function investigate(lat,lon,place='India'){
 state.lat=lat;state.lon=lon;state.place=place||'India';
 $('inspector').classList.remove('hidden');$('coords').textContent=`${lat.toFixed(5)}, ${lon.toFixed(5)}`;$('regionTitle').textContent=place||'Selected Region';$('mapStatus').textContent='Gathering real source data…';
 ['mSatellite','mTemp','mFire','mSoil'].forEach(id=>$(id).textContent='Checking…');
 try{
  const d=await api(`/api/investigate?lat=${lat}&lon=${lon}&place=${encodeURIComponent(place||'India')}`); state.investigation=d; renderInvestigation(d); $('mapStatus').textContent='Investigation loaded — source freshness shown in evidence';
 }catch(e){toast('Investigation error: '+e.message);$('mapStatus').textContent='Some sources unavailable';}
}

function renderInvestigation(d){
 const s=d.sources;
 const sat=s.satellite; const features=sat.ok?(sat.data.features||[]):[]; $('mSatellite').textContent=sat.ok?(features.length?`${features.length} scenes`:'No scene'):'Unavailable';
 $('mSatelliteSub').textContent=sat.ok?`${sat.provenance.resolution_m||10}m • ${sat.provenance.freshness}`:(sat.error||'Source unavailable');
 const cur=s.weather.ok?s.weather.data.current:null; $('mTemp').textContent=cur&&cur.temperature_2m!=null?`${cur.temperature_2m}°C`:'Unavailable'; $('mWeatherSub').textContent=cur?`${cur.relative_humidity_2m??'—'}% RH • ${s.weather.provenance.freshness}`:(s.weather.error||'Open-Meteo unavailable');
 const fires=s.fire.ok?(s.fire.data||[]):[]; $('mFire').textContent=s.fire.ok?`${fires.length} detections`:'Not configured'; $('mFireSub').textContent=s.fire.ok?s.fire.provenance.freshness:(s.fire.error||'FIRMS unavailable');
 $('mSoil').textContent=s.soil.ok?'Available':'Unavailable'; $('mSoilSub').textContent=s.soil.ok?'250m modeled reference':(s.soil.error||'SoilGrids unavailable');
 const ev=[];
 if(sat.ok&&features.length){const f=features[0];ev.push(`Latest suitable Sentinel-2 scene: ${f.properties?.datetime||'timestamp present in STAC item'}; cloud ${f.properties?.['eo:cloud_cover']??'—'}%`)} else ev.push('Sentinel-2 scene metadata unavailable for this request');
 if(cur) ev.push(`Current weather: ${cur.temperature_2m??'—'}°C, humidity ${cur.relative_humidity_2m??'—'}%, cloud ${cur.cloud_cover??'—'}%`);
 if(s.fire.ok) ev.push(`${fires.length} FIRMS detections returned in the configured search window`); else ev.push('FIRMS source requires a free MAP_KEY; no fire count fabricated');
 if(s.human_pressure.ok) ev.push(`${(s.human_pressure.data.elements||[]).length} mapped road/settlement/industrial features found within search radius`);
 if(s.soil.ok) ev.push('SoilGrids modeled soil properties retrieved; treat as reference estimates, not field samples');
 $('evidenceChain').innerHTML=ev.map(x=>`<p>${escapeHtml(x)}</p>`).join('');
 $('evidenceRaw').textContent=JSON.stringify(d,null,2);
 $('environmentPanel').innerHTML=renderEnvironment(s);
 $('newsPanel').innerHTML=renderNews(s.news);
}

function renderEnvironment(s){
 const cur=s.weather.ok?s.weather.data.current||{}:{};
 return `<h3>Environmental profile</h3><div class="evidence-list"><p>Temperature: ${cur.temperature_2m??'Unavailable'}°C</p><p>Humidity: ${cur.relative_humidity_2m??'Unavailable'}%</p><p>Rain: ${cur.rain??'Unavailable'} mm</p><p>Cloud cover: ${cur.cloud_cover??'Unavailable'}%</p><p>Wind: ${cur.wind_speed_10m??'Unavailable'} km/h</p><p>Soil source: ${s.soil.ok?'SoilGrids reference estimates':'Unavailable'}</p></div>`;
}
function renderNews(n){
 if(!n||!n.ok) return `<h3>News intelligence</h3><p>${escapeHtml(n?.error||'Unavailable')}</p><small>News is contextual evidence only and never proof of causation.</small>`;
 const arts=n.data?.articles||[]; if(!arts.length) return '<h3>News intelligence</h3><p>No matching recent articles returned.</p>';
 return `<h3>News intelligence</h3>${arts.slice(0,8).map(a=>`<p><a target="_blank" rel="noopener" href="${a.url}">${escapeHtml(a.title||a.url)}</a><br><small>${escapeHtml(a.domain||'')} ${escapeHtml(a.seendate||'')}</small></p>`).join('')}<small>Supporting context only; correlation is not causation.</small>`;
}
function escapeHtml(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}

$('layersBtn').onclick=()=>$('layerDrawer').classList.remove('hidden');$('closeLayers').onclick=()=>$('layerDrawer').classList.add('hidden');$('freshnessFilter').onchange=renderLayers;$('resolutionFilter').onchange=renderLayers;
$('closeInspector').onclick=()=>$('inspector').classList.add('hidden');
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.tab-panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('tab-'+b.dataset.tab).classList.add('active')});
$('healthBtn').onclick=async()=>{try{const h=await api('/api/health');toast(`${h.service}: operational • ${h.environment}`)}catch(e){toast('System health failed')}};
$('riskDemoBtn').onclick=async()=>{try{const payload={ndvi_drop:.25,temp_anomaly_c:1.5,rainfall_deficit_pct:25,fire_signal:0,protected_area:false,fragmentation_change:.15,human_pressure:.3,model_confidence:.8};const r=await api('/api/intelligence/risk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});$('evidenceChain').innerHTML=`<p><b>${r.level}</b> — ${r.score}/100 (AI estimate)</p>`+r.factors.slice(0,5).map(f=>`<p>${escapeHtml(f.factor)}: +${f.contribution}</p>`).join('');toast('Explainable risk model completed')}catch(e){toast(e.message)}};
$('reportBtn').onclick=async()=>{if(!state.investigation)return toast('Select a region first');const r=await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:'VanRakshak Investigation Report',location:state.investigation.location,sources:state.investigation.sources})});const blob=await r.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='vanrakshak-report.pdf';a.click();URL.revokeObjectURL(a.href)};
$('searchBtn').onclick=()=>{const q=$('searchBox').value.trim();if(!q)return;state.place=q;api('/api/query?q='+encodeURIComponent(q)).then(x=>toast('Query parsed: '+JSON.stringify(x.filters))).catch(e=>toast(e.message));if(state.lat!=null)investigate(state.lat,state.lon,q)};
$('searchBox').addEventListener('keydown',e=>{if(e.key==='Enter')$('searchBtn').click()});
loadLayers().catch(e=>toast('Layer registry failed: '+e.message));
