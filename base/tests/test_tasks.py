# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.test import TestCase

from .factories import UserFactory


class CeleryTaskTest(TestCase):
    """
    Call tasks directly (no broker needed) using .apply() or just calling
    the function — keeps tests fast and broker-free.
    """

    def test_task_runs_successfully(self):
        from base.tasks import some_task

        user = UserFactory()
        result = some_task.apply(args=[user.pk])  # runs synchronously
        self.assertTrue(result.successful())

    def test_task_result(self):
        from base.tasks import some_task

        user = UserFactory()
        result = some_task.apply(args=[user.pk])
        self.assertEqual(result.get(), 'expected value')

    def test_task_handles_missing_object(self):
        from base.tasks import some_task

        result = some_task.apply(args=[999999])  # non-existent pk
        self.assertTrue(result.failed())
