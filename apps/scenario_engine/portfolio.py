"""Exact USD line-cost engine with deterministic cent reconciliation."""
from decimal import Context, Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext
from .engine import _decimal, calculate

ENGINE_VERSION = 'portfolio-cost-v1.0.0'
ASSUMPTIONS = (
    'Детерминированная модель затрат по выбранным строкам; не прогноз вероятности события.',
    'Портфель и параметры заданы пользователем и закреплены неизменяемыми снимками.',
    'Одинаковые доля воздействия и удорожание применяются только к выбранным строкам.',
    'Объёмы и параметры постоянны на горизонте; только USD, без FX и вторичных эффектов.',
    'Дополнительные затраты = сумма выбранных месячных затрат × доля / 100 × удорожание / 100 × месяцы.',
    'Итог округляется ROUND_HALF_UP; центы строк распределяются по убыванию дробного остатка, при равенстве — по порядку строк.',
)
CENT = Decimal('0.01')


def _lines(context, monthly):
    lines = context.get('lines')
    selected = context.get('affected_line_ids')
    if not isinstance(lines, list) or not 1 <= len(lines) <= 1000:
        raise ValueError('Portfolio requires 1–1000 lines.')
    if any(not isinstance(line, dict) or not isinstance(line.get('id'), str) for line in lines):
        raise ValueError('Portfolio line IDs must be strings.')
    ids = [line['id'] for line in lines]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate portfolio line IDs.')
    if (not isinstance(selected, list) or not selected or
            any(not isinstance(value, str) for value in selected) or
            len(selected) != len(set(selected)) or not set(selected).issubset(ids)):
        raise ValueError('Invalid selected line IDs.')
    costs = [_decimal(line.get('monthly_cost'), 'monthly_cost', 1, 10**9) for line in lines]
    if sum(costs) != monthly:
        raise ValueError('Portfolio sum must equal monthly_cost.')
    return lines, costs, set(selected)


def _allocate(values):
    """Largest remainder allocation conserves rounded aggregate down to the cent."""
    floors = [value.quantize(CENT, rounding=ROUND_DOWN) for value in values]
    target = sum(values).quantize(CENT)
    remainder_count = int((target - sum(floors)) / CENT)
    order = sorted(range(len(values)), key=lambda index: (-(values[index] - floors[index]), index))
    recipients = set(order[:remainder_count])
    return [value + (CENT if index in recipients else 0) for index, value in enumerate(floors)]


def calculate_portfolio(inputs, context):
    calculate(inputs)  # Preserve strict scalar contract validation.
    if not isinstance(context, dict):
        raise ValueError('Portfolio context must be an object.')
    with localcontext(Context(prec=40, rounding=ROUND_HALF_UP)):
        monthly = Decimal(inputs['monthly_cost'])
        lines, costs, selected = _lines(context, monthly)
        months = inputs['months']
        exposure, shock = Decimal(inputs['exposure']), Decimal(inputs['shock'])
        affected = sum(cost for line, cost in zip(lines, costs) if line['id'] in selected)
        additional = affected * exposure * shock / 10000
        deltas = _allocate([cost * exposure * shock * months / 10000 if line['id'] in selected else Decimal(0)
                            for line, cost in zip(lines, costs)])
        baseline = monthly * months
        values = {'exposed_monthly': affected * exposure / 100, 'additional_monthly': additional,
                  'additional_total': additional * months, 'baseline_total': baseline,
                  'scenario_total': baseline + additional * months,
                  'increase_percent': additional / monthly * 100}
        return {
            **{key: format(value.quantize(CENT), '.2f') for key, value in values.items()},
            'currency': 'USD', 'engine_version': ENGINE_VERSION, 'assumptions': list(ASSUMPTIONS),
            'line_impacts': [
                {'line_id': line['id'], 'affected': line['id'] in selected,
                 'baseline_total': format(cost * months, '.2f'),
                 'additional_total': format(delta, '.2f'),
                 'scenario_total': format(cost * months + delta, '.2f')}
                for line, cost, delta in zip(lines, costs, deltas)
            ],
        }
