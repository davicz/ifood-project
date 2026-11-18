"""Read the simulated catalog from PostgreSQL or the bundled fixture."""
import logging
import os
from pathlib import Path

from fastapi import HTTPException

from .models import Catalog

demo_catalog = Catalog.model_validate_json(
    Path(__file__).with_name('catalog.json').read_text(encoding='utf-8')
)

# One statement gives all five tables the same PostgreSQL snapshot.
CATALOG_QUERY = """
select jsonb_build_object(
    'schema_version', 1,
    'simulated', true,
    'currency', 'BRL',
    'ingredients', (
        select coalesce(jsonb_agg(jsonb_build_object(
            'id', id, 'name', name, 'unit', unit, 'pack', reference_pack,
            'price', reference_price_cents / 100.0
        ) order by id), '[]')
        from prato.ingredients
    ),
    'recipes', (
        select coalesce(jsonb_agg(to_jsonb(r) || jsonb_build_object(
            'needs', (select coalesce(jsonb_object_agg(ingredient_id, quantity_per_serving), '{}')
                      from prato.recipe_ingredients where recipe_id = r.id)
        ) order by r.id), '[]')
        from prato.recipes r
    ),
    'stores', (
        select coalesce(jsonb_agg(
            (to_jsonb(s) - 'freight_cents' - 'minimum_cents') || jsonb_build_object(
                'freight', s.freight_cents / 100.0, 'minimum', s.minimum_cents / 100.0,
                'products', (select coalesce(jsonb_agg(to_jsonb(p) - 'store_id' order by ingredient_id), '[]')
                             from prato.store_products p where store_id = s.id)
            ) order by s.id
        ), '[]')
        from prato.stores s
    )
)
"""


def read_postgres_catalog(url: str) -> Catalog:
    import psycopg

    with psycopg.connect(url, connect_timeout=5) as connection:
        connection.read_only = True
        connection.execute("SET LOCAL statement_timeout = '5s'")
        row = connection.execute(CATALOG_QUERY).fetchone()
    return Catalog.model_validate(row[0])


def get_active_catalog() -> Catalog:
    url = os.environ.get('DATABASE_URL')
    if not url:
        return demo_catalog

    try:
        return read_postgres_catalog(url)
    except Exception as exc:
        # The driver can include connection details in exception messages.
        _catalog_unavailable(exc)


def _catalog_unavailable(exc: Exception):
    logging.getLogger(__name__).warning('Catálogo PostgreSQL indisponível (%s)', type(exc).__name__)
    raise HTTPException(
        status_code=503,
        detail='Não foi possível ler o catálogo PostgreSQL. Confira a conexão e as tabelas do schema prato.',
    ) from None
