"""Races that SQLite cannot show: real row locks need PostgreSQL (skipped elsewhere).

ZETRIX_PG_HOST=... python -m django test apps.workspaces.test_concurrency \
    --settings=config.settings.workspace_pg_test
Each call runs in its own thread and connection; a barrier releases them together.
"""
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.http import Http404
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from apps.decisions.models import Decision
from apps.decisions.services import create_decision
from apps.evidence import services as evidence
from apps.workspaces import portfolio, services
from apps.workspaces.api import Conflict
from apps.workspaces.models import AuditEvent, Membership, PortfolioRevision, ScenarioRevision, ScenarioRun
from apps.workspaces.tests import INPUTS, WorkspaceFixture

CSV = 'supplier,country_code,category,monthly_cost,currency\r\nAcme,US,Chips,100000.00,USD\r\n'


def race(*calls):
    """Run callables simultaneously; return each result or the exception it raised."""
    barrier = Barrier(len(calls))

    def go(call):
        try:
            barrier.wait(timeout=10)
            return call()
        except Exception as error:  # reported to the test, not swallowed
            return error
        finally:
            connections.close_all()

    with ThreadPoolExecutor(len(calls)) as pool:
        return list(pool.map(go, calls))


@unittest.skipUnless(connection.vendor == 'postgresql', 'row locks need PostgreSQL')
class RaceTests(WorkspaceFixture, TransactionTestCase):
    def test_parallel_revisions_get_consecutive_numbers(self):
        results = race(*[lambda: services.create_revision(
            self.org, self.project, self.scenario, self.user, {'inputs': INPUTS})] * 8)
        self.assertEqual([r for r in results if isinstance(r, Exception)], [])
        numbers = sorted(ScenarioRevision.objects.filter(scenario_id=self.scenario).values_list('number', flat=True))
        self.assertEqual(numbers, list(range(1, 10)))

    def test_parallel_runs_with_one_key_create_one_run(self):
        results = race(*[lambda: services.create_run(self.org, self.user, self.revision, 'k')] * 8)
        self.assertEqual([r for r in results if isinstance(r, Exception)], [])
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(ScenarioRun.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action='run.succeeded').count(), 1)

    def test_one_key_for_two_revisions_lets_only_one_win(self):
        other = services.create_revision(self.org, self.project, self.scenario, self.user,
                                         {'inputs': {**INPUTS, 'shock': '30.00'}})
        results = race(*[lambda: services.create_run(self.org, self.user, self.revision, 'k')] * 3,
                       *[lambda: services.create_run(self.org, self.user, str(other.id), 'k')] * 3)
        failures = [r for r in results if isinstance(r, Exception)]
        self.assertTrue(failures and all(isinstance(f, Conflict) for f in failures), failures)
        self.assertEqual(ScenarioRun.objects.count(), 1)

    def test_two_owners_cannot_remove_each_other(self):
        """Write skew: each sees two owners, so without the org lock both removals pass."""
        mine = Membership.objects.get(organization_id=self.org, user=self.user)
        theirs = Membership.objects.create(organization_id=self.org, user=self.other, role='owner')
        results = race(
            lambda: services.update_member(self.org, theirs.id, self.user, {'active': False}),
            lambda: services.update_member(self.org, mine.id, self.other, {'active': False}))
        self.assertEqual(sum(isinstance(r, Exception) for r in results), 1, results)
        self.assertTrue(all(isinstance(r, (Conflict, Http404)) for r in results if isinstance(r, Exception)))
        self.assertEqual(Membership.objects.filter(organization_id=self.org, role='owner', active=True).count(), 1)

    def test_one_csv_import_confirmed_in_parallel_makes_one_revision(self):
        preview = portfolio.preview_csv(self.org, self.project, self.user, CSV)
        results = race(*[lambda: portfolio.confirm_import(self.org, self.project, preview.id, self.user)] * 6)
        self.assertEqual([r for r in results if isinstance(r, Exception)], [])
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(PortfolioRevision.objects.count(), 1)

    def test_one_decision_key_in_parallel_makes_one_decision(self):
        run, _ = services.create_run(self.org, self.user, self.revision, 'k')
        data = {'title': 'T', 'note': 'N', 'run_ids': [run.id]}
        results = race(*[lambda: create_decision(self.org, self.user, data, 'dk')] * 6)
        self.assertEqual([r for r in results if isinstance(r, Exception)], [])
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(Decision.objects.count(), 1)


@unittest.skipUnless(connection.vendor == 'postgresql', 'row locks need PostgreSQL')
class EvidenceRaceTests(WorkspaceFixture, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.curator = get_user_model().objects.create_user('curator', is_staff=True)
        source = evidence.create_source(self.curator, {
            'publisher': 'Example', 'url': 'https://example.org/r', 'allowed_use': 'Link only'})
        self.data = {'title': 'Restriction', 'summary': 'Summary.', 'event_kind': 'trade_restriction',
                     'country_codes': ['US'], 'effective_at': datetime(2026, 10, 16, tzinfo=timezone.utc),
                     'source_ids': [source.id], 'provenance': 'Synthetic test fixture.'}
        self.event = evidence.create_event(self.curator, self.data)

    def test_parallel_event_revisions_get_consecutive_numbers(self):
        results = race(*[lambda: evidence.create_revision(self.event.id, self.curator, self.data)] * 6)
        self.assertEqual([r for r in results if isinstance(r, Exception)], [])
        self.assertEqual(sorted(self.event.revisions.values_list('number', flat=True)), list(range(1, 8)))

    def test_publish_revoke_and_scenario_use_neither_deadlock_nor_diverge(self):
        """Lock order is org then event in scenarios; curators take only the event lock."""
        revisions = [self.event.revisions.get(number=1)] + [
            evidence.create_revision(self.event.id, self.curator, self.data) for _ in range(2)]
        calls = []
        for index in range(6):
            current = revisions[index % 3]
            calls += [lambda r=current: evidence.publish(self.event.id, r.id, self.curator),
                      lambda: evidence.revoke(self.event.id, self.curator, 'withdrawn'),
                      lambda r=current: services.create_revision(
                          self.org, self.project, self.scenario, self.user,
                          {'inputs': INPUTS, 'evidence_revision_id': str(r.id)})]
        results = race(*calls)
        unexpected = [r for r in results if isinstance(r, Exception) and not isinstance(r, ValidationError)]
        self.assertEqual(unexpected, [])
        self.event.refresh_from_db()
        last = self.event.publications.order_by('-created_at', '-id').first()
        self.assertEqual(self.event.published_revision_id,
                         last.revision_id if last and last.action == 'publish' else None)
