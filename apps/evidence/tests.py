from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

BASE = '/api/v2/evidence/'


class EvidenceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = get_user_model().objects.create_user('curator', is_staff=True)
        self.user = get_user_model().objects.create_user('customer')
        self.client = APIClient()
        self.client.force_login(self.staff)
        response = self.client.post(BASE + 'sources/', {
            'publisher': 'Example publisher', 'url': 'https://example.org/report',
            'allowed_use': 'Link and original curator summary only',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.source_id = response.json()['data']['id']
        self.payload = {'title': 'Illustrative restriction', 'summary': 'Curator-written summary.',
                        'event_kind': 'trade_restriction', 'country_codes': ['US'],
                        'effective_at': '2026-10-16T00:00:00Z', 'source_ids': [self.source_id],
                        'provenance': 'Manually checked reference; illustrative test fixture.'}
        response = self.client.post(BASE + 'events/', self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.event = response.json()['data']
        self.url = BASE + f"events/{self.event['id']}/"
        self.revision = self.event['latest_revision']['id']

    def publish(self, revision=None):
        return self.client.post(self.url + 'publish/', {'revision_id': revision or self.revision}, format='json')

    def test_anonymous_and_corporate_owner_cannot_curate(self):
        from apps.workspaces.models import Organization, Membership
        org = Organization.objects.create(name='Customer')
        Membership.objects.create(organization=org, user=self.user, role='owner')
        self.client.logout()
        self.assertEqual(self.client.get(BASE + 'events/').status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.publish().status_code, 403)
        self.assertEqual(self.client.post(BASE + 'sources/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.post(self.url + 'revisions/', self.payload, format='json').status_code, 403)

    def test_draft_hidden_and_revision_does_not_change_published_event(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(BASE + 'events/').json()['data'], [])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.staff)
        self.assertEqual(self.publish().status_code, 200)
        changed = {**self.payload, 'title': 'Unapproved changed title'}
        self.assertEqual(self.client.post(self.url + 'revisions/', changed, format='json').status_code, 201)
        self.client.force_login(self.user)
        data = self.client.get(self.url).json()['data']
        self.assertEqual(data['published_revision']['title'], self.payload['title'])
        self.assertNotIn('latest_revision', data)
        revisions = self.client.get(self.url + 'revisions/').json()['data']
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]['publication_status'], 'current')

    def test_revoke_history_and_snapshot(self):
        from .services import get_published_snapshot
        from rest_framework.exceptions import ValidationError
        self.publish()
        snapshot = get_published_snapshot(self.revision)
        self.assertEqual(snapshot['sources'][0]['url'], 'https://example.org/report')
        result = self.client.post(self.url + 'revoke/', {'reason': 'Source correction required'}, format='json')
        self.assertEqual(result.status_code, 200)
        with self.assertRaises(ValidationError):
            get_published_snapshot(self.revision)
        self.client.force_login(self.user)
        listed = self.client.get(BASE + 'events/').json()['data']
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]['id'], self.event['id'])
        self.assertIsNone(listed[0]['published_revision'])
        self.assertEqual(listed[0]['historical_revision']['publication_status'], 'withdrawn')
        history = self.client.get(self.url + 'revisions/').json()['data']
        self.assertEqual(history[0]['publication_status'], 'withdrawn')

    def test_foreign_revision_and_unknown_source_rejected(self):
        other = self.client.post(BASE + 'events/', self.payload, format='json').json()['data']
        self.assertEqual(self.publish(other['latest_revision']['id']).status_code, 404)
        import uuid
        bad = {**self.payload, 'source_ids': [str(uuid.uuid4())]}
        self.assertEqual(self.client.post(self.url + 'revisions/', bad, format='json').status_code, 400)

    def test_source_and_revision_validation(self):
        for url in ('javascript:alert(1)', 'file:///etc/passwd', 'ftp://example.org/report'):
            result = self.client.post(BASE + 'sources/', {'publisher': 'x', 'url': url, 'allowed_use': 'x'}, format='json')
            self.assertEqual(result.status_code, 400)
        for change in ({'country_codes': ['USA']}, {'country_codes': ['US', 'US']},
                       {'source_ids': []}, {'title': 'x' * 201}, {'unknown': True}):
            self.assertEqual(self.client.post(self.url + 'revisions/', {**self.payload, **change}, format='json').status_code, 400)

    def test_append_only_and_superseded(self):
        from .models import EvidenceSource, EventRevision, Publication
        self.publish()
        second = self.client.post(self.url + 'revisions/', {**self.payload, 'title': 'Updated'}, format='json').json()['data']
        self.assertEqual(self.publish(second['id']).status_code, 200)
        self.client.force_login(self.user)
        revisions = self.client.get(self.url + 'revisions/').json()['data']
        self.assertEqual([row['publication_status'] for row in revisions], ['current', 'superseded'])
        for model in (EvidenceSource, EventRevision, Publication):
            with self.assertRaises(ValueError):
                model.objects.first().save()
            with self.assertRaises(ValueError):
                model.objects.all().delete()

    def test_pagination_bounds_and_no_mutation_routes(self):
        self.assertEqual(self.client.get(BASE + 'events/?offset=-1').status_code, 400)
        self.assertEqual(self.client.get(BASE + 'sources/?limit=999').json()['meta']['limit'], 50)
        self.assertEqual(self.client.patch(self.url, {'title': 'x'}, format='json').status_code, 405)

    def test_publish_exact_revision_and_snapshot_history_remains_unchanged(self):
        from .services import get_published_snapshot
        from .models import Publication
        from rest_framework.exceptions import ValidationError
        self.publish()
        snapshot = get_published_snapshot(self.revision)
        second = self.client.post(self.url + 'revisions/', {**self.payload, 'title': 'Updated title'}, format='json').json()['data']
        self.assertEqual(self.publish(second['id']).status_code, 200)
        self.assertEqual(snapshot['title'], self.payload['title'])
        self.assertEqual(snapshot['publication_status'], 'current')
        with self.assertRaises(ValidationError):
            get_published_snapshot(self.revision)
        self.publish(second['id'])
        self.assertEqual(Publication.objects.filter(event_id=self.event['id']).count(), 2)
        self.client.post(self.url + 'revoke/', {'reason': 'Correction'}, format='json')
        self.publish(second['id'])
        self.assertEqual(get_published_snapshot(second['id'])['publication_status'], 'current')

    def test_invalid_source_credentials_and_decisions(self):
        from .services import get_published_snapshot
        from rest_framework.exceptions import ValidationError
        import uuid
        response = self.client.post(BASE + 'sources/', {
            'publisher': 'Publisher', 'url': 'https://user:password@example.org/', 'allowed_use': 'Link only',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(self.url + 'revoke/', {'reason': 'No publication'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url + 'publish/', {'revision_id': 'invalid'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url + 'revoke/', {'reason': ''}, format='json').status_code, 400)
        with self.assertRaises(ValidationError):
            get_published_snapshot(uuid.uuid4())

    def test_session_csrf_required_for_curator_writes(self):
        strict = APIClient(enforce_csrf_checks=True)
        strict.force_login(self.staff)
        self.assertEqual(strict.post(BASE + 'events/', self.payload, format='json').status_code, 403)
        self.assertEqual(strict.get(BASE + 'events/').status_code, 200)

    def test_service_mutations_reject_nonstaff_even_without_views(self):
        from . import services
        from rest_framework.exceptions import PermissionDenied
        for action in (
            lambda: services.create_source(self.user, {}),
            lambda: services.create_event(self.user, {}),
            lambda: services.create_revision(self.event['id'], self.user, {}),
            lambda: services.publish(self.event['id'], self.revision, self.user),
            lambda: services.revoke(self.event['id'], self.user, 'Reason'),
        ):
            with self.assertRaises(PermissionDenied):
                action()

    def test_staff_can_read_draft_revision_history(self):
        response = self.client.get(self.url + 'revisions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'][0]['publication_status'], 'draft')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url + 'revisions/').status_code, 404)
