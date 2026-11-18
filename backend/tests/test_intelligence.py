import json
import pytest
from app.main import catalog, app
from app.intelligence import local_interpret, bedrock_interpret, validate_interpretation, Interpretation
from fastapi.testclient import TestClient

client = TestClient(app)

def test_local_rules_extract_explicit_recipe_and_portions():
    data = local_interpret(catalog, 'Estrogonofe para quatro pessoas')
    assert data['provider'] == 'local_rules'
    assert data['interpretation']['recipe_ids'] == ['strogonoff']
    assert data['interpretation']['servings'] == 4
    assert not data['interpretation']['clarification']

@pytest.mark.parametrize('text', ['Não quero estrogonofe', 'Estrogonofe sem lactose para quatro pessoas', 'Estrogonofe para 3 pessoas e salada para 6 pessoas', 'Quero sushi', 'Estrogonofe para 99 pessoas', 'Estrogonofe, tenho 50g de arroz'])
def test_local_ambiguities_require_review(text):
    assert local_interpret(catalog, text)['interpretation']['clarification']

def test_no_pantry_or_portion_assumptions():
    result = local_interpret(catalog, 'Quero bolonhesa')['interpretation']
    assert result['servings'] is None and result['pantry_ids'] == []

@pytest.mark.parametrize('data', [{'recipe_ids':['invented']}, {'pantry_ids':['invented']}, {'recipe_ids':['pasta','pasta']}, {'servings':0}, {'price':99}])
def test_llm_output_is_untrusted(data):
    with pytest.raises(ValueError): validate_interpretation(catalog, data)

class FakeBedrock:
    def __init__(self, data): self.data = data
    def converse(self, **kwargs):
        assert kwargs['messages'][0]['role'] == 'user'
        assert 'Catálogo' in kwargs['system'][0]['text']
        return {'output':{'message':{'content':[{'text':json.dumps(self.data)}]}}, 'usage':{'inputTokens':10,'outputTokens':20}}

def test_bedrock_adapter_and_usage(monkeypatch):
    monkeypatch.setenv('BEDROCK_MODEL_ID', 'test-model')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    result = bedrock_interpret(catalog, 'pedido', FakeBedrock({'recipe_ids':['strogonoff'], 'servings':4}))
    assert result['provider'] == 'bedrock' and result['requires_confirmation']
    assert result['usage']['inputTokens'] == 10

def test_unconfigured_bedrock_is_explicit(monkeypatch):
    monkeypatch.delenv('BEDROCK_MODEL_ID', raising=False)
    response = client.post('/api/interpret',json={'text':'Quero estrogonofe', 'provider':'bedrock'})
    assert response.status_code == 503

def test_interpret_api():
    assert client.post('/api/interpret',json={'text':'Estrogonofe para 4 pessoas'}).json()['interpretation']['servings'] == 4
    assert client.post('/api/interpret',json={'text':'x'}).status_code == 422
    assert client.post('/api/search',json={'query':'frango','unit':'kg'}).status_code == 422

def test_lexical_search_returns_grounded_products_and_unit_filter():
    response = client.post('/api/search', json={'query':'frango', 'target':'products', 'method':'lexical', 'unit':'g'})
    assert response.status_code == 200
    rows = response.json()['results']
    assert rows[0]['ingredient_id'] == 'chicken'
    assert all(r['unit'] == 'g' for r in rows)
    assert {r['stock'] for r in rows} == {0, 100}
    for row in rows:
        store = next(s for s in catalog.stores if s.id == row['store_id'])
        product = next(p for p in store.products if p.ingredient_id == row['ingredient_id'])
        assert row['price_cents'] == product.price_cents

def test_llm_invalid_json_rejected(monkeypatch):
    monkeypatch.setattr('app.main.bedrock_interpret', lambda *_: (_ for _ in ()).throw(ValueError('bad JSON')))
    response = client.post('/api/interpret', json={'text':'quero estrogonofe', 'provider':'bedrock'})
    assert response.status_code == 502

@pytest.mark.parametrize(('message', 'expected'), [
    ('The security token has expired', 'expirou'),
    ('The request is denied because of missing AWS Marketplace subscription', 'Marketplace'),
    ('The bearer token is invalid', 'Bearer Token'),
    ('User is not authorized to perform bedrock:InvokeModel', 'bedrock:InvokeModel'),
])
def test_provider_diagnostics_do_not_disclose_aws_message(monkeypatch, message, expected):
    from botocore.exceptions import ClientError
    secret_marker = 'secret-sensitive-identifier'
    def denied(*_):
        raise ClientError({'Error': {'Code': 'AccessDeniedException', 'Message': message + ' ' + secret_marker}}, 'Converse')
    monkeypatch.setattr('app.main.bedrock_interpret', denied)
    response = client.post('/api/interpret', json={'text': 'quero estrogonofe', 'provider': 'bedrock'})
    assert response.status_code == 503
    assert expected in response.json()['detail']
    assert secret_marker not in response.text
