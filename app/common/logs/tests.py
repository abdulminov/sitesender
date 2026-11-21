from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import RequestLog


class LogsListTest(TestCase):

    def setUp(self):
        now = timezone.now()

        self.old_log = RequestLog.objects.create(
            user_id='111',
            url='https://example.com/old',
            request_type='Video',
            status_code=200,
            execution_time=1.0,
        )

        self.new_log = RequestLog.objects.create(
            user_id='222',
            url='https://example.com/new',
            request_type='Video',
            status_code=500,
            execution_time=2.0,
        )
        
        self.middle_log = RequestLog.objects.create(
            user_id='333',
            url='https://example.com/middle',
            request_type='Video',
            status_code=500,
            execution_time=1.5,
        )


        RequestLog.objects.filter(pk=self.old_log.pk).update(
            created_at=now - timedelta(minutes=10)
        )
        RequestLog.objects.filter(pk=self.new_log.pk).update(
            created_at=now
        )
        RequestLog.objects.filter(pk=self.middle_log.pk).update(
           created_at=now - timedelta(minutes=5)
        )

    def test_logs_list_returns_200(self):
        response = self.client.get(reverse('logs_list'))

        self.assertEqual(response.status_code, 200)

    def test_logs_are_ordered_newest_first(self):
        response = self.client.get(reverse('logs_list'))
        logs = list(response.context['logs'])

        for newer, older in zip(logs, logs[1:]):
            self.assertGreaterEqual(
                newer.created_at,
                older.created_at,
            )

    def test_all_logs_are_displayed(self):
        response = self.client.get(reverse('logs_list'))
        logs = list(response.context['logs'])

        self.assertCountEqual(
            [log.pk for log in logs],
            [
                self.old_log.pk,
                self.middle_log.pk,
                self.new_log.pk,
            ],
        )

    def test_logs_can_be_filtered_by_status(self):
        response = self.client.get(reverse('logs_list'), {'status': '500'})

        logs = list(response.context['logs'])

        self.assertEqual(
            [log.pk for log in logs],
            [self.new_log.pk, self.middle_log.pk],
        )

    def test_logs_filter_returns_empty_listy_when_no_matches(self):
        response = self.client.get(reverse('logs_list'), {'status': '404'})

        logs = list(response.context['logs'])

        self.assertEqual(logs, [])


    def test_logs_are_displayed_at_html(self):
        response = self.client.get(reverse('logs_list'))

        self.assertContains(response, self.new_log.url)
