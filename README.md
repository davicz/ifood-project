# prato. — Da ideia à sua mesa

Planejador de compras por receitas: React + TypeScript no frontend, Python + FastAPI no backend. Projeto independente de portfólio, sem vínculo com o iFood. Catálogo, preços, estoques e prazos são simulados.

## Executar localmente

Requisitos: Node.js 20.19+ e Python 3.11+ (validado com Python 3.14).

Na raiz do repositório, prepare o backend:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock.txt
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Em outro terminal, na mesma pasta:

```bash
npm install
npm run dev
```

Site: http://127.0.0.1:5173 · Documentação interativa: http://127.0.0.1:8000/docs

O Vite encaminha `/api` para a porta 8000. Para implantação, configurar o servidor/reverse proxy para encaminhar `/api` ao FastAPI. `dist/` sozinho não contém o backend.

## Verificar

```bash
backend/.venv/bin/python -m pytest -q
npm run build
```

43 testes automatizados (incluindo interpretação, contrato Bedrock simulado e busca lexical): agregação de ingredientes, embalagens, unidades fracionárias, despensa, centavos, estoque insuficiente, tamanho de embalagem por loja, mínimos, dois fretes, prazo da última entrega, cesta vazia, ordenação, validação HTTP e integridade do catálogo. Build TypeScript/Vite e fluxo de compra no navegador verificados. O ambiente atual emite um aviso de depreciação do TestClient para httpx; os testes passam.

## API

- `GET /api/health`: saúde da aplicação.
- `GET /api/catalog`: receitas e catálogo validado, incluindo estimativa de consumo por pessoa.
- `POST /api/plan`: ingredientes agregados, lista de compras e opções de mercado com linhas detalhadas de cada pedido.

Exemplo de corpo:

```json
{
  "recipe_ids": ["strogonoff", "pasta"],
  "servings": 3,
  "pantry_ids": ["rice"],
  "split": true,
  "sort": "price"
}
```

`sort`: `price` ou `time`. Porções inteiras entre 1 e 12. IDs desconhecidos, repetidos e campos inesperados retornam 422. Despensa significa que o usuário possui toda a quantidade necessária daquele ingrediente.

## Regras do cálculo

- Receitas expressam quantidades por pessoa nas unidades canônicas `g`, `ml` ou `un.`.
- Ingredientes comuns são somados antes de arredondar para embalagens.
- Cada mercado declara explicitamente embalagem, unidade, preço em centavos e estoque em número de embalagens.
- Quantidades usam Decimal; valores monetários são calculados em centavos inteiros. Valores de apresentação em reais são derivados no retorno.
- Produtos indisponíveis ou sem estoque suficiente tornam a opção incompleta. Não há substituição automática nem inclusão de produtos para atingir mínimos.
- Cada pedido deve atingir seu mínimo com o subtotal dos produtos, sem frete.
- Cestas vazias não geram opções nem frete.
- Divisão entre duas lojas enumera atribuições de ingredientes e mantém a de menor custo por par, incluindo os dois fretes e mínimos. Todas as embalagens de um ingrediente ficam em uma única loja.
- Prazo dividido é o maior prazo das lojas, assumindo pedidos simultâneos. Ordenação por prazo compara as opções geradas; não otimiza a divisão internamente por tempo.
- O algoritmo exato é limitado a 16 ingredientes no catálogo validado. Para catálogo maior, substituir a enumeração por um solver/estratégia apropriada.
- A referência dos produtos no resumo e o custo consumido por pessoa não são o preço final de qualquer mercado. O total final usa as embalagens e preços da loja escolhida.

## Estrutura

- `backend/app/catalog.json`: fonte única dos dados simulados, com versão de esquema e moeda.
- `backend/app/models.py`: modelos e validação de dados/requisições.
- `backend/app/engine.py`: motor puro de planejamento, independente de HTTP e React.
- `backend/app/main.py`: endpoints FastAPI; catálogo validado ao iniciar.
- `backend/tests/test_planner.py`: testes de domínio, dados e API.
- `src/api.ts`: cliente HTTP.
- `src/data.ts`: tipos e helpers de apresentação, sem catálogo duplicado.
- `src/main.tsx`: telas e estado, consumindo os resultados da API. Requisições anteriores são canceladas; falhas oferecem nova tentativa.

`requirements.lock.txt` registra as versões usadas na validação; os outros requirements declaram as dependências diretas.

## Limites e próximos passos

Sem autenticação, banco persistente, checkout ou integração com mercados reais. Embeddings locais estão integrados; o adaptador LLM Bedrock exige configuração e validação de acesso. A busca de pratos é textual e o estado da sessão é reiniciado ao atualizar a página. Receitas simplificadas para demonstração, sem instruções culinárias completas. Fotos ilustrativas do Unsplash e fontes do Google Fonts exigem internet.

A busca semântica oferece candidatos do catálogo para revisão. O motor de compras ainda usa associações canônicas por ID; não transforma similaridade em substituição automática. Próxima etapa: validar Bedrock real e ampliar a avaliação com exemplos reservados e catálogo mais rico.


## Assistente e busca semântica

Use Python 3.11 para o ambiente de IA (o ambiente básico anterior permanece disponível):

```bash
python3.11 -m venv backend/.venv-ai
backend/.venv-ai/bin/pip install -r backend/requirements-ai.lock.txt
PYTHONPATH=backend backend/.venv-ai/bin/python backend/scripts/prepare_model.py
backend/.venv-ai/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

A preparação baixa o modelo público `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` uma vez. Nas requisições, o carregamento é local, somente CPU e sem download automático. Pesos ficam em `backend/.cache/`, ignorado no Git. A primeira busca carrega os pesos e pode ser mais lenta.

Na página inicial, o painel abaixo das receitas permite:

- Interpretar nomes explícitos e porções por regras locais gratuitas, identificadas como regras (sem LLM).
- Revisar uma proposta antes de substituir os pratos e a despensa atuais. Pedidos ambíguos/negativos detectados pelo modo local exigem revisão manual.
- Buscar pratos e produtos por embeddings. Resultados mostram dados reais do catálogo simulado, inclusive produtos sem estoque. Similaridade não é confiança nem garantia de compatibilidade.

### Bedrock opcional

Configure autenticação no ambiente com AWS CLI/SSO ou credenciais de serviço adequadas. Não coloque chaves no frontend ou no repositório. O backend usa a cadeia padrão do boto3. Escolha um modelo/inference profile com suporte a Converse e habilitado na sua região, com permissão `bedrock:InvokeModel`.

```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=seu-modelo-ou-inference-profile
backend/.venv-ai/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

`.env.example` é apenas uma referência; o servidor não carrega `.env` automaticamente. Reinicie o backend e recarregue a página após configurar. A opção Bedrock só habilita quando as duas variáveis existem; isso não comprova acesso ao serviço. A chamada real depende de permissões, disponibilidade regional e faturamento da sua conta. A integração foi validada com uma chamada real ao Claude Haiku 4.5, com confirmação do fluxo completo no navegador. Chamadas ao Bedrock podem gerar cobrança.

`POST /api/interpret`: texto (3–2000 caracteres) e provider `local` ou `bedrock`. A saída inclui proposta, provedor/modelo, uso de tokens retornado pela AWS e confirmação obrigatória. O prompt é limitado ao catálogo e a saída passa por validação de esquema, IDs, duplicações e porções. Não há parser de prosa como fallback disfarçado de LLM. Preços não vêm do modelo. Falhas do provedor e respostas inválidas não alteram o carrinho.

`POST /api/search`: query, target (`recipes`/`products`), method (`semantic`/`lexical`), limit e filtro opcional de unidade canônica. Vetores dos documentos são mantidos em cache em memória. Busca lexical usa TF-IDF. O filtro de unidade não constitui verificação de atributos dietéticos ou culinários.

`GET /api/ai/status`: configuração declarada do adaptador, sem consultar credenciais.

### Avaliação inicial

```bash
backend/.venv-ai/bin/python -m pytest -q
PYTHONPATH=backend backend/.venv-ai/bin/python backend/scripts/evaluate_search.py > backend/search-evaluation.json
```

O relatório registra 10 consultas manuais de desenvolvimento em um catálogo pequeno e sintético. Deduplica resultados por ingrediente para medir Hit@1/Hit@3; não é um conjunto reservado nem representa qualidade em produção. Resultado observado: lexical 70%/70%, semântica 40%/50%. A busca semântica fica experimental, sem decisão automática de compra. Os tempos incluem a primeira carga, portanto não são benchmark de latência em regime estável. Não ajustamos o modelo para melhorar os resultados desse conjunto.

Os testes automatizados de Bedrock usam um cliente falso: validam contrato, prompt, validação e uso de tokens. Além disso, uma chamada real ao Claude Haiku 4.5 foi verificada manualmente; isso não constitui uma avaliação abrangente de qualidade. Fontes técnicas: [Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html) e [modelo de embeddings](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).

### Iniciar Bedrock com chave temporária

No terminal da máquina, execute `./scripts/start-bedrock.sh`. Cole a chave temporária no prompt oculto e pressione Enter. O script mantém a chave apenas no ambiente do processo; não a imprime nem salva em arquivo. A região e o modelo padrão correspondem ao Quickstart (podem ser alterados com `AWS_REGION` e `BEDROCK_MODEL_ID`). Se a porta 8000 estiver em uso, pare o servidor anterior antes. Credenciais temporárias expiram; após expirar, gere outra e reinicie o servidor. Não compartilhe credenciais no chat ou no Git.
