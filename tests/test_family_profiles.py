import pytest
from app import app, PROFILES

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_api_profiles_list(client):
    res = client.get('/api/profiles')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'profiles' in data
    profiles = {p['id']: p for p in data['profiles']}
    assert 'mom' in profiles
    assert 'dad' in profiles
    assert 'wife' in profiles
    assert profiles['mom']['name'] == 'Mom'
    assert profiles['dad']['name'] == 'Dad'
    assert profiles['wife']['name'] == 'Wife'
    assert profiles['mom']['currency_symbol'] == '₹'
    assert profiles['dad']['currency_symbol'] == '₹'
    assert profiles['wife']['currency_symbol'] == '₹'

def test_switch_to_dad(client):
    res = client.post('/api/profile/switch', json={'profile_id': 'dad'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['active_profile_id'] == 'dad'
    assert data['profile']['name'] == 'Dad'
    assert data['profile']['currency_symbol'] == '₹'
    assert len(data['transactions']) > 0
    assert data['report']['currency'] == 'INR'
    assert data['report']['currency_symbol'] == '₹'

def test_switch_to_wife(client):
    res = client.post('/api/profile/switch', json={'profile_id': 'wife'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['active_profile_id'] == 'wife'
    assert data['profile']['name'] == 'Wife'
    assert data['profile']['currency_symbol'] == '₹'
    assert len(data['transactions']) > 0
    assert data['report']['currency'] == 'INR'
    assert data['report']['currency_symbol'] == '₹'

def test_switch_to_mom(client):
    res = client.post('/api/profile/switch', json={'profile_id': 'mom'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['active_profile_id'] == 'mom'
    assert data['profile']['name'] == 'Mom'
    assert data['profile']['currency_symbol'] == '₹'
    assert len(data['transactions']) > 0
    assert data['report']['currency'] == 'INR'
    assert data['report']['currency_symbol'] == '₹'

def test_profile_update_credentials(client):
    res = client.post('/api/profile/update-credentials', json={
        'profile_id': 'dad',
        'pdf_password': 'DADNEWPASSWORD123'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert PROFILES['dad']['pdf_password'] == 'DADNEWPASSWORD123'
