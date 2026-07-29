"""
基础路由测试
"""
import json


def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert '菜品' in resp.get_data(as_text=True) or 'menu' in resp.get_data(as_text=True)


def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['status'] == 'ok'


def test_preview_no_data(client):
    resp = client.post('/preview', data={})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert 'error' in data


def test_generate_no_data(client):
    resp = client.post('/generate', data={})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert 'error' in data
