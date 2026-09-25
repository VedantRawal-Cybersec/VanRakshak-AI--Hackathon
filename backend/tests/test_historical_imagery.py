import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.adapters.base import AdapterError
from app.adapters.planetary_computer import PlanetaryComputerAdapter
from app.adapters.earth_search import EarthSearchAdapter
from app.adapters.gcp_landsat import GCPLandsatAdapter
from app.services.historical_landsat_tiles import parse_mtl
from app.services import historical_imagery as history
from app.main import app


def dt(year):
    return datetime(year, 6, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize('year', [1987, 2001, 2011])
def test_archive_year_prefers_official_usgs_and_public_gcp_mirror(year):
    earth, pc = EarthSearchAdapter(), PlanetaryComputerAdapter()
    earth.closest_scene = AsyncMock(side_effect=AssertionError('Do not search Sentinel before launch'))
    pc.search_optical = AsyncMock(side_effect=AssertionError('Planetary Computer should be fallback only'))
    usgs=AsyncMock()
    usgs.closest_scene=AsyncMock(return_value={
        'id':f'LT05_L2SP_145051_{year}0601_20200101_02_T1_SR',
        'properties':{'datetime':dt(year).isoformat(),'eo:cloud_cover':12},
        '_vanrakshak_archive':{'requested_date':f'{year}-06-01','window_used_days':90,'date_offset_days':0},
    })
    gcp=AsyncMock()
    gcp.resolve_item=AsyncMock(return_value=f'LT05_L1TP_145051_{year}0601_20170101_01_T1')
    gcp.tile_spec=lambda item,product,mode,requested_date=None: {
        'item_id':item['id'],'observed_at':item['properties']['datetime'],
        'requested_date':requested_date,'tile_url':'/api/historical/test/{z}/{x}/{y}.png',
        'source':'USGS Landsat archive / Google public Landsat mirror',
    }
    result=asyncio.run(history.dated_scene(earth,pc,12,75,dt(year),'true_color',35,60,usgs,gcp))
    assert result['observed_at'].startswith(str(year))
    assert result['requested_date']==f'{year}-06-01'
    assert 'USGS Landsat' in result['source']
    usgs.closest_scene.assert_awaited_once()
    gcp.resolve_item.assert_awaited_once()



def test_gcp_wrs2_candidates_cover_verified_kodagu_archive_pathrow():
    # Production diagnostics verified real LT05 scenes in 144/051 and 144/052.
    # The orbital estimate must include that overlap neighbourhood.
    candidates=GCPLandsatAdapter.wrs2_candidates(12.3375,75.8069)
    assert (144,51) in candidates
    assert (144,52) in candidates
    assert len(candidates)<=9


def test_gcp_direct_archive_discovery_returns_real_capture_metadata(monkeypatch):
    gcp=GCPLandsatAdapter()
    product='LT05_L1TP_144051_19880119_20170210_01_T1'
    gcp._discover_products=AsyncMock(return_value=[(232.0,product)])
    gcp.metadata=AsyncMock(return_value='''CLOUD_COVER = 12.0
CORNER_UL_LAT_PRODUCT = 13.5
CORNER_UR_LAT_PRODUCT = 13.5
CORNER_LL_LAT_PRODUCT = 11.0
CORNER_LR_LAT_PRODUCT = 11.0
CORNER_UL_LON_PRODUCT = 74.5
CORNER_UR_LON_PRODUCT = 77.0
CORNER_LL_LON_PRODUCT = 74.5
CORNER_LR_LON_PRODUCT = 77.0
''')
    item=asyncio.run(gcp.closest_scene(12.3375,75.8069,datetime(1987,6,1,tzinfo=timezone.utc),90,100,550))
    assert item['id']==product
    assert item['properties']['datetime'].startswith('1988-01-19')
    assert item['_vanrakshak_archive']['date_offset_days']==232.0
    assert item['_vanrakshak_catalog_source'].startswith('Google Cloud')


def test_historical_loader_uses_gcp_direct_discovery_when_usgs_has_gap():
    earth=EarthSearchAdapter(); pc=PlanetaryComputerAdapter()
    pc.search_optical=AsyncMock(side_effect=AssertionError('Planetary fallback should not run'))
    usgs=AsyncMock(); usgs.closest_scene=AsyncMock(return_value=None)
    gcp=AsyncMock()
    product='LT05_L1TP_144051_19880119_20170210_01_T1'
    gcp.closest_scene=AsyncMock(return_value={
        'id':product,
        'properties':{'datetime':'1988-01-19T00:00:00Z','eo:cloud_cover':12},
        '_gcp_product_id':product,
        '_vanrakshak_catalog_source':'Google Cloud public Landsat Collection 1',
        '_vanrakshak_archive':{'requested_date':'1987-06-01','window_used_days':232,'date_offset_days':232.0},
    })
    gcp.resolve_item=AsyncMock(return_value=product)
    gcp.tile_spec=lambda item,product,mode,requested_date=None: {
        'item_id':item['id'],'observed_at':item['properties']['datetime'],
        'requested_date':requested_date,'date_offset_days':232.0,
        'tile_url':'/api/historical/test/{z}/{x}/{y}.png',
        'source':'Google Cloud public Landsat Collection 1 archive',
    }
    result=asyncio.run(history.dated_scene(earth,pc,12.3375,75.8069,datetime(1987,6,1,tzinfo=timezone.utc),'true_color',90,100,usgs,gcp))
    assert result['observed_at'].startswith('1988-01-19')
    assert result['date_offset_days']==232.0
    gcp.closest_scene.assert_awaited_once()


def test_historical_falls_back_to_planetary_when_public_mirror_missing():
    earth=EarthSearchAdapter(); pc=PlanetaryComputerAdapter()
    usgs=AsyncMock(); usgs.closest_scene=AsyncMock(return_value={'id':'LT05_L2SP_145051_20010601_20200101_02_T1_SR','properties':{'datetime':'2001-06-01T00:00:00+00:00'}})
    gcp=AsyncMock(); gcp.resolve_item=AsyncMock(return_value=None)
    pc.search_optical=AsyncMock(return_value={'features':[{'id':'PC-2001','collection':'landsat-c2-l2','properties':{'datetime':'2001-06-01T00:00:00+00:00'}}]})
    pc.tile_spec=AsyncMock(return_value={'item_id':'PC-2001','observed_at':'2001-06-01T00:00:00+00:00','tile_url':'https://example/{z}/{x}/{y}.png','source':'Landsat'})
    result=asyncio.run(history.dated_scene(earth,pc,12,75,dt(2001),'true_color',35,60,usgs,gcp))
    assert result['item_id']=='PC-2001'


def test_provider_failure_is_503_not_internal_server_error(monkeypatch):
    from app import main
    monkeypatch.setattr(main.earth,'closest_scene',AsyncMock(side_effect=AdapterError('Catalogue timeout')))
    monkeypatch.setattr(main.pc,'search_optical',AsyncMock(side_effect=AdapterError('Archive timeout')))
    monkeypatch.setattr(main.usgs_landsat,'closest_scene',AsyncMock(side_effect=AdapterError('USGS timeout')))
    monkeypatch.setattr(main.gcp_landsat,'closest_scene',AsyncMock(side_effect=AdapterError('Google archive timeout')))
    r=TestClient(app).get('/api/map/compare',params={'lat':12,'lon':75,'before_date':'2020-01-01','after_date':'2021-01-01'})
    assert r.status_code == 503
    assert r.json()['status'] == 'PROVIDER_UNAVAILABLE'


@pytest.mark.parametrize('before,after', [('2011-01-01','2001-01-01'),('2001-01-01','2001-01-01'),('1970-01-01','2001-01-01'),('2001-01-01','2999-01-01'),('invalid','2020-01-01')])
def test_invalid_comparison_dates_rejected_before_provider_calls(before,after):
    r=TestClient(app).get('/api/map/compare',params={'lat':12,'lon':75,'before_date':before,'after_date':after})
    assert r.status_code == 422


def test_same_observation_is_not_a_change_comparison(monkeypatch):
    monkeypatch.setattr(history,'dated_scene',AsyncMock(return_value={'item_id':'same','observed_at':'2020-06-01'}))
    with pytest.raises(ValueError,match='same or reversed'):
        asyncio.run(history.compare(None,None,12,75,dt(2020),dt(2021),'true_color',35,60,None,None))


def test_gcp_public_product_resolution_prefers_tier1():
    gcp=GCPLandsatAdapter()
    gcp.get_json=AsyncMock(return_value={'items':[
        {'name':'LT05/01/145/051/LT05_L1TP_145051_19870601_20170101_01_T2/LT05_L1TP_145051_19870601_20170101_01_T2_B1.TIF'},
        {'name':'LT05/01/145/051/LT05_L1TP_145051_19870601_20170102_01_T1/LT05_L1TP_145051_19870601_20170102_01_T1_B1.TIF'},
    ]})
    item={'id':'LT05_L2SP_145051_19870601_20200101_02_T1_SR','properties':{'datetime':'1987-06-01T00:00:00Z'}}
    product=asyncio.run(gcp.resolve_item(item))
    assert product.endswith('_T1')
    urls=gcp.asset_urls(product)
    assert urls['red'].endswith('_B3.TIF')
    assert urls['nir'].endswith('_B4.TIF')
    assert urls['swir22'].endswith('_B7.TIF')


def test_landsat8_public_band_mapping():
    gcp=GCPLandsatAdapter()
    product='LC08_L1TP_145051_20140601_20170101_01_T1'
    urls=gcp.asset_urls(product)
    assert urls['red'].endswith('_B4.TIF')
    assert urls['nir'].endswith('_B5.TIF')
    assert urls['swir16'].endswith('_B6.TIF')


def test_mtl_parser_keeps_reflectance_coefficients():
    meta=parse_mtl('REFLECTANCE_MULT_BAND_3 = 2.0E-05\nREFLECTANCE_ADD_BAND_3 = -0.1\nSUN_ELEVATION = 45.0')
    assert meta['REFLECTANCE_MULT_BAND_3']=='2.0E-05'
    assert meta['REFLECTANCE_ADD_BAND_3']=='-0.1'


def test_long_timeline_samples_entire_requested_range_with_unified_scene_loader(monkeypatch):
    calls=[]
    async def fake(*args,**kwargs):
        target=args[4]; calls.append(target)
        return {'item_id':target.date().isoformat(),'observed_at':target.isoformat(),'tile_url':'x','source':'archive'}
    monkeypatch.setattr(history,'dated_scene',fake)
    result=asyncio.run(history.timeline(None,None,12,75,dt(1987),dt(2011),60,12,None,None))
    assert calls[0]==dt(1987)
    assert calls[-1]==dt(2011)
    assert result['count']==12
    assert result['label']=='HISTORICAL'
