from pathlib import Path
from fastapi import FastAPI, HTTPException
from .models import Catalog, PlanRequest
from .engine import plan, cents

catalog = Catalog.model_validate_json(Path(__file__).with_name('catalog.json').read_text())
app = FastAPI(title='Prato API', version='0.1.0', description='Planejamento de compras com catálogo de demonstração. Todos os valores são simulados.')

@app.get('/api/health')
def health():
    return {'status': 'ok', 'simulated': True}

@app.get('/api/catalog')
def get_catalog():
    result = catalog.model_dump()
    result['recipes'] = [{**r.model_dump(), 'estimate_per_person': round(sum(cents(next(i for i in catalog.ingredients if i.id == key).price) * amount / next(i for i in catalog.ingredients if i.id == key).pack for key, amount in r.needs.items()) / 100, 2)} for r in catalog.recipes]
    return result

@app.post('/api/plan')
def create_plan(request: PlanRequest):
    try:
        return plan(catalog, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

from .intelligence import SearchRequest, InterpretRequest, AIUnavailable, search, local_interpret, bedrock_interpret

@app.get('/api/ai/status')
def ai_status():
    import os
    return {'local_interpretation': 'rules_only', 'semantic_model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', 'bedrock_configured': bool(os.environ.get('BEDROCK_MODEL_ID') and os.environ.get('AWS_REGION'))}

@app.post('/api/search')
def search_catalog(request: SearchRequest):
    try:
        return search(catalog, request)
    except AIUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

@app.post('/api/interpret')
def interpret_request(request: InterpretRequest):
    try:
        return local_interpret(catalog, request.text) if request.provider == 'local' else bedrock_interpret(catalog, request.text)
    except AIUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=502, detail='A resposta do modelo não passou na validação. Revise seu pedido e tente novamente.') from error
    except Exception as error:
        import logging
        from botocore.exceptions import ClientError
        detail = 'Não foi possível acessar o provedor de IA. Confira a configuração do backend.'
        if isinstance(error, ClientError):
            aws_error = error.response.get('Error', {})
            code = str(aws_error.get('Code', ''))
            message = str(aws_error.get('Message', '')).lower()
            if 'expired' in message or code in ('ExpiredTokenException', 'ExpiredToken', 'RequestExpired'):
                detail = 'A credencial AWS expirou. Gere uma chave temporária nova e reinicie o backend.'
            elif 'marketplace' in message or 'subscription' in message or 'agreement' in message:
                detail = 'A AWS recusou o acesso relacionado à assinatura do modelo. Confira a ativação no Bedrock e as permissões do Marketplace.'
            elif 'use case' in message or 'use-case' in message or code == 'FTUFormNotFilled':
                detail = 'A AWS informou que os detalhes de primeiro uso do modelo estão ausentes ou pendentes.'
            elif 'bearer' in message or 'api key' in message or 'token' in message:
                detail = 'A AWS recusou a credencial ou seu uso com Bearer Token. Confira a chave, a região e as permissões da identidade.'
            elif code in ('AccessDeniedException', 'UnauthorizedOperation', 'NotAuthorized'):
                detail = 'A AWS negou acesso ao modelo ou à operação. Confira a permissão bedrock:InvokeModel e o perfil de inferência da identidade.'
            elif code in ('ValidationException', 'ResourceNotFoundException'):
                detail = 'A AWS não aceitou o modelo ou a solicitação. Confira o identificador do perfil e a região.'
            elif code in ('ThrottlingException', 'ServiceUnavailableException'):
                detail = 'O Bedrock está temporariamente indisponível ou com limite de chamadas. Tente novamente em alguns instantes.'
        logging.getLogger(__name__).warning('Falha no provedor: %s; diagnóstico: %s', type(error).__name__, detail)
        raise HTTPException(status_code=503, detail=detail) from error
