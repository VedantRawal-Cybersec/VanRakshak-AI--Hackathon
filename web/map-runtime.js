/* Real 2D raster/GeoJSON fallback for devices without a WebGL context.
 * Leaflet 1.9.4: https://github.com/Leaflet/Leaflet (BSD-2-Clause).
 */
class RasterMap {
  constructor(options) {
    this.sources = new Map(); this.layers = new Map(); this.removed = false;
    this.map = L.map(options.container, {zoomControl:false, attributionControl:options.attributionControl!==false, minZoom:options.minZoom??0, maxZoom:options.maxZoom??18});
    this.map.setView([options.center[1],options.center[0]],options.zoom);
    for(const [id,source] of Object.entries(options.style.sources||{}))this.addSource(id,source);
    for(const layer of options.style.layers||[])this.addLayer(layer);
  }
  on(event,cb){if(event==='load'){queueMicrotask(()=>{if(!this.removed)cb()});return this}this.map.on(event,e=>cb(event==='click'?{...e,lngLat:{lat:e.latlng.lat,lng:e.latlng.lng}}:e));return this}
  once(event,cb){if(event==='load'||event==='idle'){queueMicrotask(()=>{if(!this.removed)cb()});return this}this.map.once(event,cb);return this}
  loaded(){return !this.removed} isStyleLoaded(){return !this.removed}
  addControl(){L.control.zoom({position:'topright'}).addTo(this.map);return this}
  addSource(id,source){this.sources.set(id,source);return this}
  getSource(id){return this.sources.get(id)}
  removeSource(id){this.sources.delete(id);return this}
  getLayer(id){return this.layers.get(id)}
  removeLayer(id){const layer=this.layers.get(id);if(layer)this.map.removeLayer(layer);this.layers.delete(id);return this}
  addLayer(spec,before){
    const source=this.sources.get(spec.source),p=spec.paint||{};
    if(!source)throw new Error('Map source missing: '+spec.source);
    let layer;
    if(source.type==='raster'){
      const template=source.tiles[0];
      const options={tileSize:source.tileSize||256,opacity:p['raster-opacity']??1,maxZoom:22,minZoom:source.minzoom??0,maxNativeZoom:source.maxzoom??19,attribution:source.attribution||''};
      if(template.includes('{bbox-epsg-3857}')){
        const projected=L.TileLayer.extend({getTileUrl(coords){const n=2**coords.z,span=40075016.68557849/n,left=-20037508.342789244+coords.x*span,top=20037508.342789244-coords.y*span;return template.replace('{bbox-epsg-3857}',[left,top-span,left+span,top].join(','))}});
        layer=new projected('',options);
      }else layer=L.tileLayer(template,options);
      layer.on('tileerror',()=>this.map.fire('error',{error:new Error('Raster tile unavailable')}));
    }else{
      layer=L.geoJSON(source.data,{style:{color:p['line-color']||p['fill-color']||'#56d893',weight:p['line-width']??1,fillOpacity:spec.type==='line'?0:(p['fill-opacity']??0.3)},pointToLayer:(f,ll)=>L.circleMarker(ll,{radius:5,color:p['circle-stroke-color']||'#fff',weight:1,fillColor:p['circle-color']||'#4ea8ff',fillOpacity:0.9})});
    }
    layer.addTo(this.map);this.layers.set(spec.id,layer);
    if(before)this.layers.get(before)?.bringToFront?.();
    return this;
  }
  getCenter(){return this.map.getCenter()} getZoom(){return this.map.getZoom()}
  getBearing(){return 0} getPitch(){return 0}
  jumpTo(o){const c=o.center||[this.getCenter().lng,this.getCenter().lat];this.map.setView([c[1],c[0]],o.zoom??this.getZoom(),{animate:false});return this}
  flyTo(o){return this.jumpTo(o)}
  resize(){if(!this.removed)this.map.invalidateSize({pan:false});return this}
  remove(){this.removed=true;this.map.remove()}
}
let useRasterFallback = false;
function createEarthMap(options){
  if(!useRasterFallback && typeof maplibregl!=='undefined'){
    try{
      // Probe before creating MapLibre so unsupported WebGL cannot abort boot.
      const canvas=document.createElement('canvas');
      const gl=canvas.getContext('webgl2')||canvas.getContext('webgl');
      if(!gl)throw new Error('WebGL unavailable');
      gl.getExtension('WEBGL_lose_context')?.loseContext();
      return new maplibregl.Map(options);
    }catch(e){useRasterFallback=true;document.getElementById(options.container)?.replaceChildren()}
  }
  useRasterFallback=true;
  if(typeof L==='undefined')throw new Error('Map libraries could not load. Reload with an internet connection.');
  return new RasterMap(options);
}
