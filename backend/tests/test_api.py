from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200 and r.json()['ok'] is True

def test_layers():
    r=client.get('/api/layers'); assert r.status_code==200 and len(r.json()['groups'])>=10

def test_features_37():
    r=client.get('/api/features'); assert r.json()['count']==37

def test_query_parser():
    r=client.get('/api/query',params={'q':'Show forests in Karnataka with high heat and recent canopy loss'}); assert r.status_code==200; assert r.json()['filters']['state']=='Karnataka'
