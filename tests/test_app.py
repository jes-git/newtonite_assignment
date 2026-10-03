import os

import pytest
from app import app, init_db


@pytest.fixture
def client():
    app.config['TESTING'] = True
    db_path = os.path.join(os.getcwd(), 'data', 'test_app.db')
    app.config['DATABASE'] = db_path
    if os.path.exists(db_path):
        os.remove(db_path)
    with app.test_client() as client:
        init_db()
        yield client


def test_items_list_and_create(client):
    response = client.get('/api/items')
    assert response.status_code == 200
    initial = response.get_json()
    assert isinstance(initial['items'], list)

    response = client.post('/api/items', json={
        'title': 'Payment investigation',
        'description': 'Review failed settlement',
        'priority': 'High',
        'status': 'New',
        'team_id': 1,
        'assignee_id': 1,
    })
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['item']['title'] == 'Payment investigation'


def test_stale_update_rejected(client):
    # create item
    create = client.post('/api/items', json={
        'title': 'Compliance review',
        'description': 'Check customer data request',
        'priority': 'Medium',
        'status': 'New',
        'team_id': 1,
        'assignee_id': 1,
    })
    item_id = create.get_json()['item']['id']

    # stale update attempt
    response = client.post(f'/api/items/{item_id}/update', json={
        'assignee_id': 2,
        'status': 'In Progress',
        'priority': 'High',
        'version': 999,
    })
    assert response.status_code == 409
    payload = response.get_json()
    assert 'stale' in payload['error'].lower()


def test_permission_denied_for_unapproved_user(client):
    client.set_cookie('user_id', '2')
    response = client.post('/api/items', json={
        'title': 'Escalation item',
        'description': 'Only assigned team can update',
        'priority': 'High',
        'status': 'New',
        'team_id': 2,
        'assignee_id': 2,
    })
    assert response.status_code == 200
    item_id = response.get_json()['item']['id']

    # user 1 is in team 1; team 2 item should not be accessible
    client.set_cookie('user_id', '1')
    response = client.post(f'/api/items/{item_id}/update', json={
        'status': 'Closed',
        'priority': 'Low',
        'version': 1,
    })
    assert response.status_code == 403
