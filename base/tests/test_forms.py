# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.test import TestCase


class SomeFormTest(TestCase):

    def test_valid_data(self):
        from base.forms import SomeForm
        form = SomeForm(data={'field': 'value'})
        self.assertTrue(form.is_valid())

    def test_missing_required_field(self):
        from base.forms import SomeForm
        form = SomeForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('field', form.errors)

    def test_invalid_data(self):
        from base.forms import SomeForm
        form = SomeForm(data={'field': ''})
        self.assertFalse(form.is_valid())
