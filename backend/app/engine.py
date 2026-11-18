"""Pure purchase planning. Money is integer cents; quantities use Decimal.

Each ingredient is assigned wholly to one store. Split plans enumerate all
nonempty assignments for each store pair, retaining the cheapest valid one.
This exact algorithm is intentionally bounded by the validated demo catalogue.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from itertools import combinations
from .models import Catalog, PlanRequest


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def packs(quantity, size):
    return int((Decimal(str(quantity)) / Decimal(str(size))).to_integral_value(rounding=ROUND_CEILING))


def plan(catalog: Catalog, request: PlanRequest):
    recipe_map = {r.id: r for r in catalog.recipes}
    ingredient_map = {i.id: i for i in catalog.ingredients}
    if not set(request.recipe_ids) <= recipe_map.keys():
        raise ValueError('Prato desconhecido.')
    if not set(request.pantry_ids) <= ingredient_map.keys():
        raise ValueError('Ingrediente de despensa desconhecido.')
    quantities = {}
    for recipe_id in request.recipe_ids:
        for ingredient_id, amount in recipe_map[recipe_id].needs.items():
            quantities[ingredient_id] = quantities.get(ingredient_id, Decimal(0)) + Decimal(str(amount)) * request.servings
    needs = [{**i.model_dump(), 'quantity': float(quantities[i.id]), 'packs': packs(quantities[i.id], i.pack)} for i in catalog.ingredients if i.id in quantities]
    shopping = [i for i in needs if i['id'] not in request.pantry_ids]
    estimate = sum(cents(i['price']) * i['packs'] for i in shopping)
    options = []

    def quote(store, items):
        products = {p.ingredient_id: p for p in store.products}
        lines, missing = [], []
        for item in items:
            p = products.get(item['id'])
            count = packs(item['quantity'], p.pack) if p else 0
            if not p or p.stock < count:
                missing.append(item['name'])
                continue
            lines.append({'ingredient_id': item['id'], 'name': item['name'], 'quantity': item['quantity'], 'unit': p.unit, 'pack': p.pack, 'packs': count, 'price_cents': p.price_cents, 'line_total_cents': count * p.price_cents})
        subtotal = sum(line['line_total_cents'] for line in lines)
        return {'store_id': store.id, 'store_name': store.name, 'lines': lines, 'missing': missing, 'subtotal_cents': subtotal, 'freight_cents': cents(store.freight), 'valid': bool(items) and not missing and subtotal >= cents(store.minimum)}

    def option(id, name, initials, color, minutes, orders, minimum=0, allocation=''):
        subtotal = sum(o['subtotal_cents'] for o in orders)
        freight = sum(o['freight_cents'] for o in orders)
        return {'id': id, 'name': name, 'initials': initials, 'color': color, 'minutes': minutes, 'subtotal': subtotal / 100, 'freight': freight / 100, 'total': (subtotal + freight) / 100, 'missing': [m for o in orders for m in o['missing']], 'valid': all(o['valid'] for o in orders), 'minimum': minimum, 'allocation': allocation, 'orders': orders}

    if shopping:
        for s in catalog.stores:
            options.append(option(s.id, s.name, s.initials, s.color, s.minutes, [quote(s, shopping)], s.minimum))
        if request.split:
            for a, b in combinations(catalog.stores, 2):
                best = None
                for mask in range(1, (1 << len(shopping)) - 1):
                    groups = [[item for idx, item in enumerate(shopping) if bool(mask & (1 << idx)) == side] for side in (False, True)]
                    orders = [quote(s, items) for s, items in zip((a, b), groups)]
                    if not all(o['valid'] for o in orders):
                        continue
                    cost = sum(o['subtotal_cents'] + o['freight_cents'] for o in orders)
                    if best is None or cost < best[0]:
                        best = (cost, orders)
                if best:
                    allocation = ' · '.join(o['store_name'] + ': ' + ', '.join(line['name'] for line in o['lines']) for o in best[1])
                    options.append(option(f'{a.id}+{b.id}', f'{a.name} + {b.name}', '2×', '#323232', max(a.minutes, b.minutes), best[1], allocation=allocation))
    options.sort(key=lambda o: (not o['valid'], o['total'] if request.sort == 'price' else o['minutes'], o['id']))
    return {'simulated': True, 'currency': 'BRL', 'needs': needs, 'shopping': shopping, 'estimate': estimate / 100, 'options': options}
