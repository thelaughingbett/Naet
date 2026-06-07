from django.test import TestCase
from django.urls import reverse

from ..models import School, Department, Programme, Tclass, User


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
