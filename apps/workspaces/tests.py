from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditEvent, Membership, Organization, ScenarioRevision

INPUTS = {'kind': 'trade', 'monthly_cost': '100000.00', 'exposure': '40.00',
          'shock': '20.00', 'months': 3, 'currency': 'USD'}
BASE = '/api/v2/'


class WorkspaceFixture:
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user('owner', password='test-secret')
        self.other = get_user_model().objects.create_user('other', password='test-secret')
        self.client = APIClient()
        self.client.force_login(self.user)
        response = self.client.post(BASE + 'organizations/', {'name': 'Acme'}, format='json')
        self.org = response.json()['data']['id']
        self.prefix = BASE + f'organizations/{self.org}/'
        self.project = self.client.post(self.prefix + 'projects/', {'title': 'Supply'}, format='json').json()['data']['id']
        self.scenario_url = self.prefix + f'projects/{self.project}/scenarios/'
        response = self.client.post(self.scenario_url, {'title': 'Restriction', 'inputs': INPUTS}, format='json')
        self.scenario = response.json()['data']['id']
        self.detail = self.scenario_url + self.scenario + '/'
        self.revision = response.json()['data']['revisions'][0]['id']

    def run_scenario(self, key='run-1', revision=None):
        return self.client.post(self.prefix + 'runs/', {'revision_id': revision or self.revision},
                                format='json', HTTP_IDEMPOTENCY_KEY=key)


class WorkspaceAPITests(WorkspaceFixture, TestCase):
    def test_anonymous_and_cross_tenant_are_denied(self):
        self.client.logout()
        self.assertEqual(self.client.get(BASE + 'organizations/').status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(BASE + 'organizations/').json()['data'], [])
        self.assertEqual(self.client.get(self.detail).status_code, 404)
        self.assertEqual(self.run_scenario().status_code, 404)

    def test_organization_owner_and_mutation_audit(self):
        self.assertTrue(Membership.objects.filter(organization_id=self.org, user=self.user, role='owner').exists())
        self.assertEqual(AuditEvent.objects.filter(organization_id=self.org).count(), 3)

    def test_viewer_cannot_mutate(self):
        Membership.objects.create(organization_id=self.org, user=self.other, role='viewer')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.detail).status_code, 200)
        self.assertEqual(self.run_scenario().status_code, 403)
        self.assertEqual(self.client.post(self.prefix + 'projects/', {'title': 'Forbidden'}, format='json').status_code, 403)

    def test_revision_history_is_append_only(self):
        response = self.client.post(self.detail + 'revisions/', {'inputs': {**INPUTS, 'shock': '30.00'}}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['number'], 2)
        self.assertEqual(ScenarioRevision.objects.get(pk=self.revision).inputs['shock'], '20.00')
        self.assertEqual(self.client.patch(self.detail, {'title': 'Update'}).status_code, 405)

    def test_run_idempotency_conflict_and_export(self):
        first = self.run_scenario()
        self.assertEqual(first.status_code, 201)
        run = first.json()['data']
        self.assertEqual(run['status'], 'succeeded')
        again = self.run_scenario()
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()['data']['id'], run['id'])
        revision = self.client.post(self.detail + 'revisions/', {'inputs': INPUTS}, format='json').json()['data']['id']
        self.assertEqual(self.run_scenario(revision=revision).status_code, 409)
        export = self.client.get(self.prefix + f"runs/{run['id']}/export/")
        self.assertEqual(export.status_code, 200)
        self.assertIn('attachment;', export['Content-Disposition'])
        self.assertEqual(export.json()['data']['inputs'], INPUTS)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.prefix + f"runs/{run['id']}/export/").status_code, 404)

    def test_invalid_input_and_foreign_revision(self):
        bad = self.client.post(self.scenario_url, {'title': 'Invalid', 'inputs': {**INPUTS, 'shock': '-1'}}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(bad.json()['success'])
        self.assertEqual(self.client.post(self.prefix + 'runs/', {'revision_id': self.revision}, format='json').status_code, 400)
        second = Organization.objects.create(name='Other')
        Membership.objects.create(organization=second, user=self.user, role='owner')
        response = self.client.post(BASE + f'organizations/{second.id}/runs/', {'revision_id': self.revision}, format='json', HTTP_IDEMPOTENCY_KEY='x')
        self.assertEqual(response.status_code, 404)

    def test_inactive_membership_has_no_access(self):
        Membership.objects.filter(organization_id=self.org, user=self.user).update(active=False)
        self.assertEqual(self.client.get(self.detail).status_code, 404)

    def test_strict_fields_and_pagination(self):
        self.assertEqual(self.client.post(self.prefix + 'projects/', {'title': 'X', 'organization': self.org}, format='json').status_code, 400)
        result = self.client.get(self.prefix + 'projects/?limit=500').json()
        self.assertEqual(result['meta']['limit'], 50)
        self.assertEqual(self.client.get(self.prefix + 'projects/?offset=-1').status_code, 400)

    def test_member_roles_and_last_owner(self):
        response = self.client.post(self.prefix + 'members/', {'username': 'other', 'role': 'analyst'}, format='json')
        self.assertEqual(response.status_code, 201)
        own = Membership.objects.get(organization_id=self.org, user=self.user)
        self.assertEqual(self.client.patch(self.prefix + f'members/{own.id}/', {'role': 'viewer'}, format='json').status_code, 409)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.prefix + 'members/').status_code, 200)
        self.assertEqual(self.client.post(self.prefix + 'members/', {'username': 'owner', 'role': 'owner'}, format='json').status_code, 403)


class SessionSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user('alice', password='test-secret')
        self.client = APIClient(enforce_csrf_checks=True)

    def test_login_and_logout_require_csrf(self):
        payload = {'username': 'alice', 'password': 'test-secret'}
        self.assertEqual(self.client.post(BASE + 'auth/login/', payload, format='json').status_code, 403)
        csrf = self.client.get(BASE + 'auth/csrf/').json()['data']['csrf_token']
        response = self.client.post(BASE + 'auth/login/', payload, format='json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(BASE + 'auth/me/').json()['data']['username'], 'alice')
        self.assertEqual(self.client.post(BASE + 'auth/logout/').status_code, 403)
        csrf = self.client.get(BASE + 'auth/csrf/').json()['data']['csrf_token']
        self.assertEqual(self.client.post(BASE + 'auth/logout/', HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        self.assertEqual(self.client.get(BASE + 'auth/me/').status_code, 403)

    def test_bad_credentials_origin_and_throttle(self):
        csrf = self.client.get(BASE + 'auth/csrf/').json()['data']['csrf_token']
        payload = {'username': 'alice', 'password': 'incorrect'}
        denied = self.client.post(BASE + 'auth/login/', payload, format='json', HTTP_X_CSRFTOKEN=csrf,
                                  HTTP_ORIGIN='https://untrusted.example')
        self.assertEqual(denied.status_code, 403)
        response = self.client.post(BASE + 'auth/login/', payload, format='json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_failed')
        for _ in range(9):
            response = self.client.post(BASE + 'auth/login/', payload, format='json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 429)

    def test_authenticated_mutations_require_csrf(self):
        self.client.force_login(get_user_model().objects.get(username='alice'))
        self.assertEqual(self.client.post(BASE + 'organizations/', {'name': 'No csrf'}, format='json').status_code, 403)
        token = self.client.get(BASE + 'auth/csrf/').json()['data']['csrf_token']
        response = self.client.post(BASE + 'organizations/', {'name': 'With csrf'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)


class AdditionalWorkspaceTests(WorkspaceFixture, TestCase):
    """Exercise role changes, history reads and rejected boundary inputs."""
    def test_read_routes_and_append_only_records(self):
        run = self.run_scenario().json()['data']
        urls = [self.prefix, self.prefix + 'projects/', self.prefix + f'projects/{self.project}/',
                self.scenario_url, self.detail, self.detail + 'revisions/',
                self.prefix + 'runs/', self.prefix + f"runs/{run['id']}/", self.prefix + 'members/']
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['success'])
                self.assertEqual(response['Cache-Control'], 'no-store')
        revision = ScenarioRevision.objects.get(pk=self.revision)
        with self.assertRaises(ValueError):
            revision.save()
        with self.assertRaises(ValueError):
            revision.delete()
        with self.assertRaises(ValueError):
            ScenarioRevision.objects.filter(pk=revision.pk).update(inputs={})
        with self.assertRaises(ValueError):
            ScenarioRevision.objects.filter(pk=revision.pk).delete()
        self.client.force_login(self.other)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_owner_transfer_and_admin_boundaries(self):
        target = self.client.post(self.prefix + 'members/', {'username': 'other', 'role': 'admin'}, format='json').json()['data']
        own = Membership.objects.get(organization_id=self.org, user=self.user)
        self.client.force_login(self.other)
        self.assertEqual(self.client.patch(self.prefix + f'members/{own.id}/', {'active': False}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(self.prefix + f"members/{target['id']}/", {'role': 'owner'}, format='json').status_code, 403)
        self.client.force_login(self.user)
        response = self.client.patch(self.prefix + f"members/{target['id']}/", {'role': 'owner'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.patch(self.prefix + f'members/{own.id}/', {'active': False}, format='json').status_code, 200)
        self.assertEqual(self.client.get(self.prefix).status_code, 404)

    def test_member_input_boundaries(self):
        self.assertEqual(self.client.post(self.prefix + 'members/', {'username': 'missing', 'role': 'viewer'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.prefix + 'members/', {'username': 'owner', 'role': 'owner'}, format='json').status_code, 409)
        member = Membership.objects.get(organization_id=self.org, user=self.user)
        self.assertEqual(self.client.patch(self.prefix + f'members/{member.id}/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.prefix + f'members/{member.id}/', {'role': 'superuser'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.prefix + 'projects/', {'title': '', 'currency': 'EUR'}, format='json').status_code, 400)

    def test_analyst_can_write_and_viewer_cannot_export(self):
        member = Membership.objects.create(organization_id=self.org, user=self.other, role='analyst')
        self.client.force_login(self.other)
        run = self.run_scenario().json()['data']
        self.assertEqual(self.client.post(self.prefix + 'projects/', {'title': 'Analyst project'}, format='json').status_code, 201)
        Membership.objects.filter(pk=member.pk).update(role='viewer')
        response = self.client.get(self.prefix + f"runs/{run['id']}/export/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post(self.detail + 'revisions/', {'inputs': INPUTS}, format='json').status_code, 403)

    def test_transaction_rollback_on_audit_failure(self):
        from unittest.mock import patch
        from .services import create_organization
        before = Organization.objects.count()
        with patch('apps.workspaces.services.audit', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                create_organization(self.user, {'name': 'Rolled back'})
        self.assertEqual(Organization.objects.count(), before)

    def test_error_envelope_and_request_id(self):
        from unittest.mock import patch
        response = self.client.post(self.prefix + 'projects/', {'title': ''}, format='json')
        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn('title', body['error']['field_errors'])
        self.assertEqual(body['meta']['request_id'], response['X-Request-ID'])
        with patch('apps.workspaces.services.create_project', side_effect=RuntimeError('internal database detail')):
            with self.assertLogs('apps.workspaces.api', level='ERROR'):
                response = self.client.post(self.prefix + 'projects/', {'title': 'Valid'}, format='json')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('internal database detail', response.content.decode())
        self.assertEqual(response.json()['error']['code'], 'internal_error')

    def test_unknown_route_and_json_number_contract(self):
        for path in ['unknown/', 'organizations/not-a-uuid/', '']:
            response = self.client.get(BASE + path)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()['error']['code'], 'not_found')
        response = self.client.post(self.scenario_url, {'title': 'Numeric input',
            'inputs': {**INPUTS, 'monthly_cost': 100000}}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_reconstructed_instance_cannot_overwrite_history(self):
        original = ScenarioRevision.objects.get(pk=self.revision)
        replacement = ScenarioRevision(id=original.id, scenario=original.scenario,
                                       number=original.number, inputs={**INPUTS, 'shock': '99.00'},
                                       created_by=self.user)
        with self.assertRaises(ValueError):
            replacement.save(force_update=True)
        original.refresh_from_db()
        self.assertEqual(original.inputs, INPUTS)
