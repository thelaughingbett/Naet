from django.test import TestCase, Client
from django.test import TestCase
from django.urls import reverse

from ..models import School, Department, Programme, Tclass, User

# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.test import Client, TestCase
from django.urls import reverse

from .factories import UserFactory


class AuthViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('some-protected-view'))
        self.assertRedirects(
            response, f"/login/?next={reverse('some-protected-view')}")

    def test_authenticated_gets_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('some-protected-view'))
        self.assertEqual(response.status_code, 200)

    def test_post_creates_object(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('some-create-view'),
            data={'field': 'value'},
        )
        self.assertEqual(response.status_code, 302)  # redirect on success


class ViewsTestCase(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            school_name="Education"
        )

        self.department = Department.objects.create(
            department_name='English and Literature',
            school=self.school
        )

        self.programme = Programme.objects.create(
            programme_name='B.A in English and Literature',
            department=self.department
        )

        self.tclass = Tclass.objects.create(
            class_name='LIT/26',
            programme=self.programme
        )

        self.programme.current_class = self.tclass
        self.programme.save()

        self.user = User.objects.create_user(
            email='exampl@email.com',
            password='lit/046/22',
            first_name='Brett',
            last_name='Travis',
            role='student',
            gender='M',
        )

        self.registration_data = {
            'first_name': 'Brett',
            'last_name': 'Travis',
            'surname': 'coleman',
            'gender': 'M',
            'email': 'example@email.com',
            'national_id': '12345678',
            'religion': 'christian',
            'nationality': 'kenyan',
            'marital_status': 'U',
            'ethnicity': 'kikuyu',
            'date_of_birth': '2004-01-12',
            'place_of_birth': 'roysambu',
            'telephone_no': '0712345678',
            'county': 'Muranga',
            'domicile': 'kenya',
            'sub_county': 'muranga',
            'location': 'muranga',
            'division': 'muranga',
            'constituency': 'muranga',
            'home_adress': 'home-addr-56',
            'emergency_contact_name': 'jaohn seymour',
            'emergency_contact_phone': '0712345678',
            'emergency_contact_email': 'email@example.com',
            'emergency_contact_relationship': 'guardian',
            'emergency_contact_address': 'emergency-addrs',
            'registration_number': 'lit/046/22',
            'school': str(self.programme.department.school.school_id),
            'department': str(self.programme.department.department_id),
            'programme': str(self.programme.programme_id),
            'stay': 'outside',
            'hostel': 'a',
        }

    def test_registration(self):
        "tests registration of a new user"

        response = self.client.post(
            reverse('base-register'),
            self.registration_data
        )

        self.assertEqual(
            response.status_code,
            301
        )

    def test_dashboard_access(self):
        self.client.login(
            username='exampl@email.com',
            password='lit/046/22'
        )

        logged_in = self.client.login(
            username='exampl@email.com',
            password='lit/046/22'
        )

        self.assertTrue(
            logged_in, "Login failed — check credentials or USERNAME_FIELD"
        )

        response = self.client.get(
            reverse('base-index')
        )

        self.assertEqual(
            response.status_code,
            200
        )


class StudentViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='admin123',
        )

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse('student-list'))
        self.assertEqual(response.status_code, 302)  # redirects to login

    def test_authenticated_access(self):
        self.client.login(email='admin@test.com', password='admin123')
        response = self.client.get(reverse('student-list'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_admin_view(self):
        self.client.login(email='student@test.com', password='testpass123')
        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.status_code, 403)
