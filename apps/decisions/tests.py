import csv
import io
from copy import deepcopy

from django.test import TestCase
from apps.workspaces.models import AuditEvent, Membership, ScenarioRun
from apps.workspaces.tests import WorkspaceFixture, INPUTS


class DecisionAPITests(WorkspaceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.run = self.run_scenario().json()['data']
        self.url = self.prefix + 'decisions/'
        self.payload = {'title': 'Procurement decision', 'note': 'Request alternative quotes.',
                        'run_ids': [self.run['id']]}

    def create(self, data=None, key='decision-1'):
        return self.client.post(self.url, data or self.payload, format='json', HTTP_IDEMPOTENCY_KEY=key)

    def second_run(self, changes=None, project_url=None):
        response = self.client.post(project_url or self.scenario_url,
                                    {'title': 'Alternative', 'inputs': {**INPUTS, **(changes or {})}}, format='json')
        revision = response.json()['data']['revisions'][0]['id']
        return self.run_scenario(key=str(revision), revision=revision).json()['data']

    def test_create_snapshot_read_and_idempotency(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        item = response.json()['data']
        self.assertEqual(item['snapshots'][0]['results'], self.run['results'])
        self.assertEqual(item['project_id'], self.project)
        self.assertEqual(self.create().status_code, 200)
        self.assertEqual(self.create().json()['data']['id'], item['id'])
        self.assertEqual(self.create({**self.payload, 'note': 'Different'}).status_code, 409)
        self.assertEqual(self.client.get(self.url + item['id'] + '/').json()['data'], item)
        self.assertEqual(self.client.get(self.url + '?limit=1').json()['meta']['count'], 1)
        self.assertEqual(AuditEvent.objects.filter(action='decision.created').count(), 1)

    def test_tenant_and_viewer_permissions(self):
        item = self.create().json()['data']
        self.client.force_login(self.other)
        self.assertEqual(self.create().status_code, 404)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.get(self.url + item['id'] + '/').status_code, 404)
        Membership.objects.create(organization_id=self.org, user=self.other, role='viewer')
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.create().status_code, 403)

    def test_inputs_and_required_key(self):
        for changes in ({'title': ''}, {'title': 12}, {'note': ''}, {'note': 'a' * 4001},
                        {'note': 12}, {'title': 'a' * 161}, {'extra': True}, {'run_ids': []},
                        {'run_ids': [self.run['id']] * 2}, {'run_ids': ['invalid']},
                        {'run_ids': [self.run['id']] * 4}):
            self.assertEqual(self.create({**self.payload, **changes}).status_code, 400, changes)
        for key in ('', 'space key', 'a' * 129):
            self.assertEqual(self.create(key=key).status_code, 400)

    def test_comparison_contract(self):
        compatible = self.second_run({'shock': '30.00'})
        response = self.create({**self.payload, 'run_ids': [self.run['id'], compatible['id']]})
        self.assertEqual(response.status_code, 201, response.content)
        for changes in ({'months': 6}, {'monthly_cost': '90000.00'}, {'kind': 'energy'}):
            different = self.second_run(changes)
            result = self.create({**self.payload, 'run_ids': [self.run['id'], different['id']]}, key=different['id'])
            self.assertEqual(result.status_code, 400, result.content)
        project = self.client.post(self.prefix + 'projects/', {'title': 'Other'}, format='json').json()['data']['id']
        different = self.second_run(project_url=self.prefix + f'projects/{project}/scenarios/')
        self.assertEqual(self.create({**self.payload, 'run_ids': [self.run['id'], different['id']]}, key='other-project').status_code, 400)

    def test_foreign_run_and_append_only(self):
        from apps.decisions.models import Decision
        from apps.workspaces.models import Organization
        org = Organization.objects.create(name='Second')
        Membership.objects.create(organization=org, user=self.user, role='owner')
        response = self.client.post(f'/api/v2/organizations/{org.id}/decisions/', self.payload,
                                    format='json', HTTP_IDEMPOTENCY_KEY='foreign')
        self.assertEqual(response.status_code, 404)
        item = self.create().json()['data']
        decision = Decision.objects.get(pk=item['id'])
        for mutate in (lambda: decision.save(), lambda: decision.delete(),
                       lambda: Decision.objects.filter(pk=decision.pk).update(note='Changed'),
                       lambda: Decision.objects.filter(pk=decision.pk).delete()):
            with self.assertRaises(ValueError):
                mutate()
        self.assertEqual(self.client.patch(self.url + item['id'] + '/', {'note': 'New'}).status_code, 405)
        self.second_run({'shock': '60.00'})
        self.assertEqual(self.client.get(self.url + item['id'] + '/').json()['data']['snapshots'], item['snapshots'])


class CSVExportTests(WorkspaceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.run = self.run_scenario().json()['data']
        self.url = self.prefix + f"runs/{self.run['id']}/csv/"

    def test_export_exact_stored_values_and_authorization(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertIn(['result', 'additional_total', '24000.00'], rows)
        self.assertIn(['input', 'monthly_cost', '100000.00'], rows)
        self.assertTrue(AuditEvent.objects.filter(action='run.csv_exported').exists())
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        Membership.objects.create(organization_id=self.org, user=self.other, role='viewer')
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_csv_formula_and_control_prefixes(self):
        from apps.decisions.services import safe_cell
        for unsafe in ('=1+2', '+1', '-2', '@SUM(A1)', '  =1', '\tHello', '\nHello', '\rHello', ' \t=1'):
            self.assertEqual(safe_cell(unsafe), "'" + unsafe)
        self.assertEqual(safe_cell('123.40'), '123.40')
        self.assertEqual(safe_cell('Ordinary supplier'), 'Ordinary supplier')

    def test_portfolio_report_uses_snapshots(self):
        from apps.decisions.services import render_csv
        run = ScenarioRun.objects.get(pk=self.run['id'])
        run.context = {'portfolio_revision_id': 'old-version', 'lines': [
            {'id': 'line-1', 'supplier': '=HYPERLINK("evil")', 'country_code': 'US',
             'category': '\t@bad', 'monthly_cost': '100000.00', 'currency': 'USD'}],
             'evidence': {'title': 'Stored event', 'id': 'event-version'}}
        run.results = {**deepcopy(run.results), 'line_impacts': [
            {'line_id': 'line-1', 'affected': True, 'baseline_total': '300000.00',
             'additional_total': '24000.00', 'scenario_total': '324000.00'}]}
        rows = list(csv.reader(io.StringIO(render_csv(run))))
        joined = str(rows)
        self.assertIn("'=HYPERLINK", joined)
        self.assertIn('324000.00', joined)
        self.assertIn('old-version', joined)
