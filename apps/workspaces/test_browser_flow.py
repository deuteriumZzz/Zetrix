"""Exercise the same session and CSRF path used by the cabinet in a browser."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient


class CabinetSessionFlowTests(TestCase):
    def test_login_portfolio_scenario_decision_and_export(self):
        cache.clear()
        get_user_model().objects.create_user('pilot', password='test-only-password')
        client = APIClient(enforce_csrf_checks=True)
        base = '/api/v2/'

        csrf = client.get(base + 'auth/csrf/').json()['data']['csrf_token']
        login = client.post(base + 'auth/login/',
                            {'username': 'pilot', 'password': 'test-only-password'},
                            format='json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(login.status_code, 200, login.content)
        csrf = login.json()['data']['csrf_token']
        headers = {'HTTP_X_CSRFTOKEN': csrf}

        org = client.post(base + 'organizations/', {'name': 'Pilot team'},
                          format='json', **headers)
        self.assertEqual(org.status_code, 201, org.content)
        prefix = base + f"organizations/{org.json()['data']['id']}/"
        project = client.post(prefix + 'projects/', {'title': 'Procurement'},
                              format='json', **headers)
        self.assertEqual(project.status_code, 201, project.content)
        project_path = prefix + f"projects/{project.json()['data']['id']}/"

        csv = 'supplier,country_code,category,monthly_cost,currency\nAcme,US,Chips,100.00,USD\n'
        preview = client.post(project_path + 'portfolio/preview/', {'csv': csv},
                              format='json', **headers)
        self.assertEqual(preview.status_code, 201, preview.content)
        import_id = preview.json()['data']['id']
        confirmed = client.post(project_path + f'portfolio/imports/{import_id}/confirm/',
                                {}, format='json', **headers)
        self.assertEqual(confirmed.status_code, 201, confirmed.content)
        portfolio_id = confirmed.json()['data']['id']

        scenario = client.post(project_path + 'scenarios/', {
            'title': 'Restriction',
            'inputs': {'kind': 'trade', 'monthly_cost': '100.00', 'exposure': '40.00',
                       'shock': '20.00', 'months': 3, 'currency': 'USD'},
            'portfolio_revision_id': portfolio_id,
        }, format='json', **headers)
        self.assertEqual(scenario.status_code, 201, scenario.content)
        revision_id = scenario.json()['data']['revisions'][0]['id']
        run = client.post(prefix + 'runs/', {'revision_id': revision_id}, format='json',
                          HTTP_IDEMPOTENCY_KEY='cabinet-flow-1', **headers)
        self.assertEqual(run.status_code, 201, run.content)
        run_id = run.json()['data']['id']
        self.assertEqual(run.json()['data']['context']['portfolio_revision_id'], portfolio_id)

        decision = client.post(prefix + 'decisions/', {
            'title': 'Review suppliers', 'note': 'Request an alternative quote.',
            'run_ids': [run_id],
        }, format='json', HTTP_IDEMPOTENCY_KEY='cabinet-decision-1', **headers)
        self.assertEqual(decision.status_code, 201, decision.content)
        exported = client.get(prefix + f'runs/{run_id}/csv/')
        self.assertEqual(exported.status_code, 200, exported.content)
        self.assertIn('text/csv', exported['Content-Type'])

        self.assertEqual(client.post(base + 'auth/logout/', {}, format='json',
                                     **headers).status_code, 200)
        self.assertEqual(client.get(prefix + 'runs/').status_code, 403)
