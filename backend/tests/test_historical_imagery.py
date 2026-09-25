import asyncio
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.adapters.base import AdapterError
from app.adapters.planetary_computer import PlanetaryComputerAdapter
from app.adapters.earth_search import EarthSearchAdapter
from app.services import historical_imagery as history
from app.main import app


def dt(year):
    return datetime(year, 6, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize('year', [1987, 2001, 2011])
def test_archive_year_uses_landsat_and_retains_capture_date(year):
    earth, pc = EarthSearchAdapter(), PlanetaryComputerAdapter()
    earth.closest_scene = AsyncMock(side_effect=AssertionError('Do not search Sentinel before launch'))
    pc.search_optical = AsyncMock(return_value={'features':[{'id':f'L-{year}', 'collection':'landsat-c2-l2', 'properties':{'datetime':dt(year).isoformat()}}]})
    pc.tile_spec = AsyncMock(return_value={'item_id':f'L-{year}', 'observed_at':dt(year).isoformat(), 'tile_url':'https://example.test/{z}/{x}/{y}.png'})
    result = asyncio.run(history.dated_scene(earth,pc,12,75,dt(year),'true_color',35,60))
    assert pc.search_optical.call_args.args[-1] == 'landsat-c2-l2'
    assert result['observed_at'].startswith(str(year))
    assert result['requested_date'] == f'{year}-06-01'


def test_provider_failure_is_503_not_internal_server_error(monkeypatch):
    from app import main
    monkeypatch.setattr(main.earth,'closest_scene',AsyncMock(side_effect=AdapterError('Catalogue timeout')))
    monkeypatch.setattr(main.pc,'search_optical',AsyncMock(side_effect=AdapterError('Archive timeout')))
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
        asyncio.run(history.compare(None,None,12,75,dt(2020),dt(2021),'true_color',35,60))


def test_landsat_tile_request_uses_correct_collection_and_reflectance_offset(monkeypatch):
    pc=PlanetaryComputerAdapter()
    pc.get_json=AsyncMock(return_value={'tiles':['https://example.test/{z}/{x}/{y}.png']})
    spec=asyncio.run(pc.tile_spec({'id':'L5','collection':'landsat-c2-l2','properties':{'datetime':'1987-06-01'}},'ndvi'))
    q=parse_qs(urlparse(pc.get_json.call_args.args[0]).query)
    assert q['collection']==['landsat-c2-l2']
    assert q['assets']==['nir08','red']
    assert '-0.4' in q['expression'][0]
    assert spec['resolution_m']==30
    assert 'Landsat' in spec['source']


def test_long_timeline_samples_entire_requested_range():
    pc=PlanetaryComputerAdapter()
    pc.search_optical=AsyncMock(return_value={'features':[]})
    result=asyncio.run(history.timeline(None,pc,12,75,dt(1987),dt(2011),60,12))
    calls=pc.search_optical.call_args_list
    assert calls[0].args[2]==dt(1987)
    assert calls[-1].args[3]==dt(2011)
    assert all(c.args[-1]=='landsat-c2-l2' for c in calls)
    assert result['count']==0
    assert result['label']=='HISTORICAL'
