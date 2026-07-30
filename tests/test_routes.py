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


def test_nutrition_page(client):
    resp = client.get('/nutrition')
    assert resp.status_code == 200
    assert '精准营养素计算' in resp.get_data(as_text=True)


def test_nutrition_calculation(client):
    food = {'name': '测试米饭', 'state': '熟', 'source': '测试权威库',
            'source_id': 'TEST-001', 'source_version': '2026',
            'carbs_basis': '总碳水', 'fiber_basis': '总膳食纤维', 'energy': 100,
            'protein': 2, 'fat': 1, 'carbs': 20, 'fiber': 0.5,
            'sodium': 5, 'potassium': 10, 'calcium': 3, 'cholesterol': 0}
    resp = client.post('/api/nutrition/calculate', json={
        'foods': [food], 'items': [{'name': '测试米饭', 'state': '熟', 'weight': 250, 'waste': 0}]})
    assert resp.status_code == 200
    assert resp.get_json()['totals']['energy'] == 250.0
    assert resp.get_json()['details'][0]['source_id'] == 'TEST-001'


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
