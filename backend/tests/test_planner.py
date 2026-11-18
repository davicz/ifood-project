import pytest
from fastapi.testclient import TestClient
from app.main import app, catalog
from app.engine import plan
from app.models import PlanRequest, Catalog

client = TestClient(app)

def calculate(**kwargs):
    return plan(catalog, PlanRequest(recipe_ids=['strogonoff'], **kwargs))

def test_shared_ingredients_aggregate_before_rounding():
    result = plan(catalog, PlanRequest(recipe_ids=['strogonoff', 'bowl'], servings=2))
    chicken = next(i for i in result['needs'] if i['id'] == 'chicken')
    assert chicken['quantity'] == 600
    assert chicken['packs'] == 2

def test_package_boundary_and_fractional_units():
    result = calculate(servings=10)
    assert next(i for i in result['needs'] if i['id'] == 'chicken')['packs'] == 3
    salad = plan(catalog, PlanRequest(recipe_ids=['salad'], servings=1))
    assert next(i for i in salad['needs'] if i['id'] == 'lettuce')['packs'] == 1

def test_pantry_removes_purchase_not_recipe_need():
    result = calculate(pantry_ids=['rice'])
    assert len(result['needs']) == 4 and len(result['shopping']) == 3
    assert all(i['id'] != 'rice' for i in result['shopping'])

def test_integer_money_and_missing_stock():
    result = calculate()
    a = next(o for o in result['options'] if o['id'] == 'a')
    assert a['subtotal'] == 32.5 and a['total'] == 38.4
    b = next(o for o in result['options'] if o['id'] == 'b')
    assert not b['valid'] and b['missing'] == ['Peito de frango']

def test_stock_quantity_and_per_store_package_size():
    fixture = catalog.model_copy(deep=True)
    product = fixture.stores[0].products[0]
    product.pack = 100
    product.stock = 2
    result = plan(fixture, PlanRequest(recipe_ids=['strogonoff']))
    assert 'Peito de frango' in next(o for o in result['options'] if o['id'] == 'a')['missing']
    product.stock = 3
    result = plan(fixture, PlanRequest(recipe_ids=['strogonoff']))
    line = next(o for o in result['options'] if o['id'] == 'a')['orders'][0]['lines'][0]
    assert line['packs'] == 3

def test_minimum_and_freights_on_split_orders():
    result = plan(catalog, PlanRequest(recipe_ids=['strogonoff', 'pasta'], servings=3, split=True))
    pairs = [o for o in result['options'] if len(o['orders']) == 2]
    assert pairs
    for option in pairs:
        assert option['valid']
        assert option['total'] == round(sum(o['subtotal_cents'] + o['freight_cents'] for o in option['orders']) / 100, 2)
        for order in option['orders']:
            store = next(s for s in catalog.stores if s.id == order['store_id'])
            assert order['subtotal_cents'] >= round(store.minimum * 100)
        assert option['minutes'] == max(next(s.minutes for s in catalog.stores if s.id == o['store_id']) for o in option['orders'])

def test_small_basket_cannot_meet_minimum():
    result = calculate(pantry_ids=['chicken', 'rice', 'tomato'], split=True)
    assert not any(o['valid'] for o in result['options'])

def test_empty_purchase_has_no_freight_or_options():
    result = calculate(pantry_ids=['chicken', 'rice', 'cream', 'tomato'])
    assert result['shopping'] == [] and result['options'] == [] and result['estimate'] == 0
    assert plan(catalog, PlanRequest(recipe_ids=[]))['options'] == []

def test_sorting_keeps_incomplete_last():
    result = calculate(sort='time')
    assert result['options'][0]['id'] == 'c'
    assert not result['options'][-1]['valid']

@pytest.mark.parametrize('payload', [
    {'recipe_ids':['unknown']}, {'recipe_ids':['strogonoff'], 'servings':0},
    {'recipe_ids':['strogonoff'], 'servings':1.5}, {'recipe_ids':['strogonoff'], 'servings':13},
    {'recipe_ids':['strogonoff','strogonoff']}, {'recipe_ids':[], 'pantry_ids':['unknown']},
    {'recipe_ids':[], 'sort':'invalid'}, {'recipe_ids':[], 'unexpected':True},
])
def test_api_rejects_invalid_requests(payload):
    assert client.post('/api/plan', json=payload).status_code == 422

def test_api_contract():
    assert client.get('/api/health').json()['status'] == 'ok'
    response = client.get('/api/catalog')
    assert response.status_code == 200 and response.json()['simulated']
    assert response.json()['recipes'][0]['estimate_per_person'] > 0
    response = client.post('/api/plan', json={'recipe_ids':['strogonoff']})
    assert response.status_code == 200 and len(response.json()['needs']) == 4

def test_catalog_rejects_incompatible_units():
    data = catalog.model_dump()
    data['stores'][0]['products'][0]['unit'] = 'ml'
    with pytest.raises(ValueError): Catalog.model_validate(data)
