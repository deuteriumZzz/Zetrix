from decimal import Decimal
from unittest import TestCase

from .portfolio import calculate_portfolio


class PortfolioEngineTests(TestCase):
    def test_reconciliation_preserves_exact_total_and_unchanged_lines(self):
        inputs = {'kind': 'trade', 'monthly_cost': '3.00', 'exposure': '50.00',
                  'shock': '1.00', 'months': 1, 'currency': 'USD'}
        lines = [{'id': str(index), 'monthly_cost': '1.00'} for index in range(3)]
        context = {'lines': lines, 'monthly_total': '3.00', 'affected_line_ids': ['0', '1', '2']}
        result = calculate_portfolio(inputs, context)
        self.assertEqual(result['additional_total'], '0.02')
        self.assertEqual([row['additional_total'] for row in result['line_impacts']], ['0.01', '0.01', '0.00'])
        self.assertEqual(sum(Decimal(row['additional_total']) for row in result['line_impacts']), Decimal('0.02'))
        selected = calculate_portfolio(inputs, {**context, 'affected_line_ids': ['0']})
        self.assertEqual(selected['additional_total'], '0.01')
        self.assertEqual(selected['line_impacts'][1]['additional_total'], '0.00')
        self.assertEqual(context['lines'], lines)

    def test_rejects_bad_context(self):
        inputs = {'kind': 'trade', 'monthly_cost': '3.00', 'exposure': '50.00',
                  'shock': '1.00', 'months': 1, 'currency': 'USD'}
        for context in ({}, {'lines': [], 'affected_line_ids': []},
                        {'lines': [{'id': 'a', 'monthly_cost': '3.00'}], 'affected_line_ids': ['b']}):
            with self.subTest(context=context), self.assertRaises(ValueError):
                calculate_portfolio(inputs, context)
