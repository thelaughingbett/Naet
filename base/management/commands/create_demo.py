import datetime
import random
from django.core.management.base import BaseCommand
from faker import Faker

from base.models import (
    Course, Curriculum, Department, FeeStructure, Payment, Programme,
    School, Session, Student, StudentFeeAccount, Tclass, User
)

from ..factories.demo_factory import (
    DepartmentFactory, DeptAdminFactory, LecturerFactory, ProgrammeFactory,
    SchoolAdminFactory, SchoolFactory, SessionFactory, StudentFactory,
    TclassFactory, UserFactory
)

# to run py manage.py create_demo --noinput


class Command(BaseCommand):
    help = 'Creates realistic demo data for the live showcase using factories and Faker'

    def handle(self, *args, **kwargs):
        fake = Faker()

        self.stdout.write('Clearing existing demo data safely...')

        User.objects.filter(
            email__in=['demo@portal.ac.ke', 'admin@portal.ac.ke']
        ).delete()

        self.stdout.write('Generating baseline infrastructure...')

        # Get the current calendar year
        current_year = datetime.now().year
        last_year = current_year - 1

        dynamic_academic_year = f"{last_year}/{current_year}"

        session = Session.objects.create(
            academic_year=dynamic_academic_year,
            semester=1,
            is_active=True
        )

        # 2. Create Core Academic Structure using Factories
        school = SchoolFactory(name='School of Engineering & Architecture')

        dept = DepartmentFactory(
            name='Department of Computer Science',
            school=school
        )
        prog = ProgrammeFactory(
            programme_name='Bachelor of Science in Computer Science',
            department=dept
        )
        tclass = TclassFactory(
            class_name='COM/26',
            programme=prog
        )

        # Link current class to programme
        prog.current_class = tclass
        prog.save()

        # 3. Create Static Demo Staff for Testing logins
        admin_user = User.objects.create_user(
            email='admin@portal.ac.ke',
            password='demo1234',
            first_name='System',
            last_name='Administrator',
            is_staff=True,
            is_superuser=True
        )

        # 4. Create the Static Demo Student (Fixed Credentials)
        demo_user = User.objects.create_user(
            email='demo@portal.ac.ke',
            password='demo1234',
            first_name='Jane',
            last_name='Doe',
        )

        # Explicitly configure student profile with realistic regional fake data
        student = Student.objects.create(
            user=demo_user,
            registration_number='COM/001/26',
            class_entered=tclass,
            school_email='demo@portal.ac.ke',
            national_id=str(fake.random_number(digits=8, fix_len=True)),
            telephone_no=(
                '07' + str(fake.random_number(digits=8, fix_len=True))
            ),
            name_of_secondary_school=f"{fake.city()} High School",
            address_of_secondary_school=fake.city()
        )

        # create emergency Contact
        # create parent guardian records

        # 5. Financial Configuration (Fee Structure & Account)
        structure = FeeStructure.objects.create(
            Tclass=tclass,
            session=session,
            breakdown={
                'tuition': 45000.00,
                'registration': 5000.00,
                'hostel': 12000.00,
                'library': 3000.00
            }
        )

        StudentFeeAccount.objects.create(
            student=student,
            fee_structure=structure,
            amount_paid=25000.00
        )

        # 6. Generate Bulk Background Noise (Makes charts/lists look realistic)
        self.stdout.write('Generating 15 random classmates and staff items...')

        # Generate random lecturers for the department
        LecturerFactory.create_batch(3, department=dept)

        # Generate random classmates in the same class
        for _ in range(15):
            student_profile = StudentFactory(class_entered=tclass)
            # Provision automatic fee accounts for classmates
            StudentFeeAccount.objects.create(
                student=student_profile,
                fee_structure=structure,
                amount_paid=random.choice([0.00, 20000.00, 65000.00])
            )

        # Print clean dashboard credentials
        self.stdout.write(
            self.style.SUCCESS(
                '\n🚀 Demo Showcase Environment Successfully Initialized!\n\n'
                '📌 STUDENT DASHBOARD:\n'
                '   URL:       /login/\n'
                '   Username:  demo@portal.ac.ke\n'
                '   Password:  demo1234\n\n'
                '📌 STAFF ADMIN PANEL:\n'
                '   URL:       /admin/\n'
                '   Username:  admin@portal.ac.ke\n'
                '   Password:  demo1234\n'
            )
        )
