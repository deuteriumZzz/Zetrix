import uuid
from django.test import TestCase
from .tests import WorkspaceFixture, INPUTS
from .models import Membership, PortfolioRevision, ScenarioRevision

LINE = {'supplier': 'Acme', 'country_code': 'US', 'category': 'Chips', 'monthly_cost': '100.00', 'currency': 'USD'}
HEADER = 'supplier,country_code,category,monthly_cost,currency\r\n'


class PortfolioAPITests(WorkspaceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.url = self.prefix + f'projects/{self.project}/portfolio/'

    def save_portfolio(self, lines=None):
        return self.client.post(self.url, {'lines': lines or [LINE]}, format='json')

    def test_manual_version_append_only_and_list(self):
        first = self.save_portfolio()
        self.assertEqual(first.status_code, 201, first.json())
        self.assertEqual(first.json()['data']['monthly_total'], '100.00')
        second = self.save_portfolio([{**LINE, 'monthly_cost': '200.00'}]).json()['data']
        self.assertEqual(second['number'], 2)
        self.assertEqual(len(self.client.get(self.url).json()['data']), 2)
        record = PortfolioRevision.objects.get(pk=first.json()['data']['id'])
        self.assertEqual(record.lines[0]['monthly_cost'], '100.00')
        with self.assertRaises(ValueError):
            record.save()

    def test_manual_validation(self):
        cases = [[], [LINE] * 1001, [{**LINE, 'currency': 'EUR'}],
                 [{**LINE, 'monthly_cost': 12}], [{**LINE, 'monthly_cost': '1e2'}],
                 [{**LINE, 'monthly_cost': '0.50'}], [{**LINE, 'country_code': 'usa'}],
                 [{**LINE, 'supplier': '=SUM(A1)'}], [{**LINE, 'category': '+SUM(A1)'}],
                 [{**LINE, 'extra': True}], [{**LINE, 'monthly_cost': '1000000000.00'}, LINE]]
        for lines in cases:
            with self.subTest(lines=str(lines)[:100]):
                self.assertEqual(self.client.post(self.url, {'lines': lines}, format='json').status_code, 400)

    def test_csv_quoted_newline_preview_confirm_idempotent(self):
        csv = HEADER + '"Acme, Inc\nAsia",US,Chips,100.00,USD\r\n'
        preview = self.client.post(self.url + 'preview/', {'csv': csv}, format='json')
        self.assertEqual(preview.status_code, 201, preview.json())
        self.assertEqual(PortfolioRevision.objects.count(), 0)
        data = preview.json()['data']
        self.assertEqual(data['lines'][0]['supplier'], 'Acme, Inc\nAsia')
        confirm = self.url + f'imports/{data["id"]}/confirm/'
        created = self.client.post(confirm, {}, format='json')
        self.assertEqual(created.status_code, 201, created.json())
        again = self.client.post(confirm, {}, format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(created.json()['data']['id'], again.json()['data']['id'])
        self.assertEqual(PortfolioRevision.objects.count(), 1)

    def test_csv_all_errors_and_structural_limits(self):
        invalid = HEADER + 'A,usa,Chips,no,USD\nB,US,Chips,100,EUR\n'
        response = self.client.post(self.url + 'preview/', {'csv': invalid}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.json()['error']['field_errors']['rows']), 2)
        for csv in ('', HEADER, 'supplier,supplier,category,monthly_cost,currency\nA,US,C,1,USD',
                    HEADER + 'A,US,C,1,USD,extra', HEADER + '"unterminated',
                    HEADER + 'A,US,C,1,USD\n' * 1001, 'a' * (2 * 1024 * 1024 + 1)):
            with self.subTest(csv=csv[:60]):
                self.assertEqual(self.client.post(self.url + 'preview/', {'csv': csv}, format='json').status_code, 400)

    def test_tenant_viewer_project_scoping(self):
        saved = self.save_portfolio().json()['data']
        preview = self.client.post(self.url + 'preview/', {'csv': HEADER + 'A,US,C,1,USD'}, format='json').json()['data']
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.save_portfolio().status_code, 404)
        Membership.objects.create(organization_id=self.org, user=self.other, role='viewer')
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.save_portfolio().status_code, 403)
        self.assertEqual(self.client.post(self.url + f'imports/{preview["id"]}/confirm/', {}, format='json').status_code, 403)
        self.client.force_login(self.user)
        project = self.client.post(self.prefix + 'projects/', {'title': 'Other'}, format='json').json()['data']['id']
        other_url = self.prefix + f'projects/{project}/'
        invalid = {'title': 'x', 'inputs': {**INPUTS, 'monthly_cost': '100.00'}, 'portfolio_revision_id': saved['id']}
        self.assertEqual(self.client.post(other_url + 'scenarios/', invalid, format='json').status_code, 404)
        self.assertEqual(self.client.post(other_url + f'portfolio/imports/{preview["id"]}/confirm/', {}, format='json').status_code, 404)

    def test_scenario_snapshot_selection_and_runs(self):
        saved = self.save_portfolio([LINE, {**LINE, 'supplier': 'Second', 'monthly_cost': '200.00'}]).json()['data']
        payload = {'title': 'Portfolio scenario', 'inputs': {**INPUTS, 'monthly_cost': '300.00'},
                   'portfolio_revision_id': saved['id'], 'affected_line_ids': [saved['lines'][0]['id']]}
        response = self.client.post(self.scenario_url, payload, format='json')
        self.assertEqual(response.status_code, 201, response.json())
        revision = response.json()['data']['revisions'][0]
        self.assertEqual(revision['context']['monthly_total'], '300.00')
        self.save_portfolio()
        run = self.run_scenario('portfolio-run', revision['id'])
        self.assertEqual(run.status_code, 201, run.json())
        run = run.json()['data']
        self.assertEqual(run['engine_version'], 'portfolio-cost-v1.0.0')
        self.assertEqual(run['results']['baseline_total'], '900.00')
        self.assertEqual(run['results']['additional_total'], '24.00')
        self.assertEqual(run['context'], revision['context'])
        self.assertEqual(self.run_scenario('portfolio-run', revision['id']).json()['data']['id'], run['id'])
        self.assertEqual(ScenarioRevision.objects.get(pk=revision['id']).context['lines'], saved['lines'])
        default = self.client.post(self.scenario_url, {key: value for key, value in payload.items() if key != 'affected_line_ids'}, format='json')
        self.assertEqual(len(default.json()['data']['revisions'][0]['context']['affected_line_ids']), 2)

    def test_scenario_rejects_bad_selection_and_total(self):
        saved = self.save_portfolio().json()['data']
        base = {'title': 'Invalid', 'inputs': {**INPUTS, 'monthly_cost': '100.00'}, 'portfolio_revision_id': saved['id']}
        for extra in ({'inputs': INPUTS}, {'affected_line_ids': []}, {'affected_line_ids': [str(uuid.uuid4())]},
                      {'affected_line_ids': [saved['lines'][0]['id']] * 2}):
            self.assertEqual(self.client.post(self.scenario_url, {**base, **extra}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.scenario_url, {'title': 'Bad', 'inputs': INPUTS, 'affected_line_ids': [str(uuid.uuid4())]}, format='json').status_code, 400)

    def test_evidence_snapshot_survives_withdrawal_for_scalar_and_portfolio(self):
        from django.utils import timezone
        from apps.evidence.models import Event, EventRevision
        event = Event.objects.create(created_by=self.user)
        evidence = EventRevision.objects.create(event=event, number=1, title='Reviewed event', summary='Source-backed context',
                    event_kind='trade', country_codes=['US'], effective_at=timezone.now(), provenance='Manual review',
                    sources=[{'id': str(uuid.uuid4()), 'publisher': 'Example', 'url': 'https://example.org', 'allowed_use': 'Link'}], created_by=self.user)
        payload = {'title': 'With evidence', 'inputs': INPUTS, 'evidence_revision_id': str(evidence.id)}
        self.assertEqual(self.client.post(self.scenario_url, payload, format='json').status_code, 400)
        Event.objects.filter(pk=event.id).update(published_revision=evidence)
        response = self.client.post(self.scenario_url, payload, format='json')
        self.assertEqual(response.status_code, 201, response.json())
        scalar = response.json()['data']['revisions'][0]
        saved = self.save_portfolio().json()['data']
        portfolio = {**payload, 'inputs': {**INPUTS, 'monthly_cost': '100.00'}, 'portfolio_revision_id': saved['id']}
        response = self.client.post(self.detail + 'revisions/', {key: value for key, value in portfolio.items() if key != 'title'}, format='json')
        self.assertEqual(response.status_code, 201, response.json())
        portfolio_revision = response.json()['data']
        Event.objects.filter(pk=event.id).update(published_revision=None)
        self.assertEqual(self.client.post(self.scenario_url, payload, format='json').status_code, 400)
        for index, revision in enumerate((scalar, portfolio_revision)):
            run = self.run_scenario(f'evidence-{index}', revision['id'])
            self.assertEqual(run.status_code, 201, run.json())
            self.assertEqual(run.json()['data']['context']['evidence']['title'], 'Reviewed event')
            self.assertEqual(run.json()['data']['context']['evidence']['publication_status'], 'current')

    def test_csv_bom_utf8_boundary_and_formula_validation(self):
        good = self.client.post(self.url + 'preview/', {'csv': '\ufeff' + HEADER + 'A,US,C,1,USD'}, format='json')
        self.assertEqual(good.status_code, 201)
        cases = [HEADER + '=SUM(A1),US,C,1,USD', HEADER + 'A,US,C,1000000000,USD\nB,US,C,1,USD',
                 'я' * (1024 * 1024 + 1)]
        for csv in cases:
            self.assertEqual(self.client.post(self.url + 'preview/', {'csv': csv}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url + 'preview/', {'csv': HEADER + 'A,US,C,1,USD', 'unknown': True}, format='json').status_code, 400)
        confirm = self.url + f'imports/{good.json()["data"]["id"]}/confirm/'
        self.assertEqual(self.client.post(confirm, {'lines': [LINE]}, format='json').status_code, 400)

    def test_maximum_valid_portfolio_and_preview_foreign_tenant(self):
        response = self.save_portfolio([LINE] * 1000)
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['data']['monthly_total'], '100000.00')
        preview = self.client.post(self.url + 'preview/', {'csv': HEADER + 'A,US,C,1,USD'}, format='json').json()['data']
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url + 'preview/', {'csv': HEADER + 'A,US,C,1,USD'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(self.url + f'imports/{preview["id"]}/confirm/', {}, format='json').status_code, 404)

    def test_scalar_run_fingerprint_stays_backward_compatible(self):
        import hashlib
        import json
        from .models import ScenarioRun
        response = self.run_scenario('legacy-scalar')
        canonical = json.dumps({'revision_id': self.revision, 'inputs': INPUTS}, sort_keys=True, separators=(',', ':'))
        stored = ScenarioRun.objects.get(pk=response.json()['data']['id'])
        self.assertEqual(stored.request_fingerprint, hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual(self.run_scenario('legacy-scalar').status_code, 200)
