"""Small fixed smoke benchmark, not a held-out production-quality evaluation."""
import json
import time
from app.main import catalog
from app.intelligence import SearchRequest, search

CASES = [
    ('carne de frango sem osso', 'chicken'),
    ('massa para espaguete', 'pasta'),
    ('folhas para salada', 'lettuce'),
    ('queijo para derreter', 'cheese'),
    ('pao para montar sanduiche', 'bread'),
    ('tomates frescos para molho', 'tomato'),
    ('arroz para acompanhar o almoco', 'rice'),
    ('creme para molho do estrogonofe', 'cream'),
    ('carne bovina triturada', 'beef'),
    ('grao de bico para salada', 'chickpea'),
]
report = {'dataset': '10 consultas manuais de desenvolvimento; não é teste reservado', 'simulated_catalog': True, 'methods': {}}
for method in ('lexical', 'semantic'):
    rows = []
    start = time.perf_counter()
    for query, expected in CASES:
        response = search(catalog, SearchRequest(query=query, target='products', method=method, limit=10))
        ids = list(dict.fromkeys(row['ingredient_id'] for row in response['results']))
        rows.append({'query': query, 'expected': expected, 'top_ingredients': ids[:3], 'hit_at_1': bool(ids and ids[0] == expected), 'hit_at_3': expected in ids[:3]})
    report['methods'][method] = {'hit_at_1': sum(r['hit_at_1'] for r in rows) / len(rows), 'hit_at_3': sum(r['hit_at_3'] for r in rows) / len(rows), 'total_seconds_including_first_load': round(time.perf_counter() - start, 3), 'rows': rows}
print(json.dumps(report, indent=2, ensure_ascii=False))
