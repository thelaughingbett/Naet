# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import datetime
from http import HTTPStatus

from decouple import config

from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import (
    render,
    redirect
)
from django.urls import reverse
from django.views import View
from django.views.generic import (
    DetailView,
    ListView,
    DeleteView
)
from django.http import HttpResponse
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)
from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from django.db import (
    DatabaseError,
    transaction
)
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    Curriculum,
    Student,
    Programme,
    School,
    Department,
    Timetable,
    User,
    Session,
    Reporting,
    FeeStructure,
    StudentFeeAccount,
    Payment
)
from .forms import (
    RegisterForm,
    ContactInfoForm,
    EmergencyContactInfoForm,
    EducationalInfoForm,
    UserDetailsForm,
    LoginForm,
    PaymentForm
)


class StudentContextMixin:
    """Adds student + session to context automatically"""

    def get_student(self, request):
        try:
            return Student.objects.select_related(
                'class_entered__programme__department__school'
            ).get(user=request.user)
        except Student.DoesNotExist:
            return None

    def get_active_session(self):
        try:
            # TODO :  get session from student programme
            return Session.objects.get(is_active=True)
        except Session.DoesNotExist:
            return None


class StudentProfileRequiredMixin:
    """Checks if the user has a student profile before letting them view the page."""

    def dispatch(self, request, *args, **kwargs):

        if not hasattr(request.user, 'student_profile'):
            # Stop the user and show an error page
            raise PermissionDenied("You do not have a student profile.")

        return super().dispatch(request, *args, **kwargs)

# ─── Auth ────────────────────────────────────────────────────────────────


class RegisterView(View):

    def get(self, request):
        EdForm = EducationalInfoForm()
        schools = list(
            School.objects.values(
                'record_id',
                'school_name'
            )
        )

        departments = list(
            Department.objects.values(
                'record_id',
                'department_name',
                'school_id'
            )
        )

        programmes = list(
            Programme.objects.values(
                'record_id',
                'programme_name',
                'department_id'
            )
        )

        context = {
            'form': RegisterForm(),
            'userdetailsForm': UserDetailsForm(),
            'detailsForm': ContactInfoForm(),
            'EmergencyContactInfoForm': EmergencyContactInfoForm(),
            'EducationalInfoForm': EdForm,
            'schools_json': schools,
            'departments_json': departments,
            'programmes_json': programmes
        }

        return render(request, "base/registration.html", context)

    def post(self, request):
        """
        this method saves  a new instance to the database adding the required fields

        Args:
            request (_type_): _description_

        Returns:
            HTTPResponse: 
        """

        form = RegisterForm(request.POST)

        UserDetails = UserDetailsForm(request.POST, request.FILES)
        detailsForm = ContactInfoForm(request.POST)
        EmergencyContact = EmergencyContactInfoForm(request.POST)
        EducationalInf = EducationalInfoForm(request.POST)

        # Force all forms to validate to populate errors
        valid = all([
            form.is_valid(),
            detailsForm.is_valid(),
            EmergencyContact.is_valid(),
            EducationalInf.is_valid(),
            UserDetails.is_valid()
        ])

        if valid:
            # Combine cleaned data into a single dictionary safely
            all_data = {
                **form.cleaned_data,
                **detailsForm.cleaned_data,
                **EmergencyContact.cleaned_data,
                **EducationalInf.cleaned_data,
            }

            # Safely remove non-model fields
            for field in ['password_confirm', 'school', 'department', 'programme']:
                all_data.pop(field, None)

            try:
                with transaction.atomic():
                    # Create user first since Student depends on User (Foreign Key)
                    user_instance = User.objects.create(
                        **UserDetails.cleaned_data,
                        role='student'
                    )

                    # Use registration number securely as a password string
                    reg_num = str(
                        EducationalInf.cleaned_data['registration_number'])
                    user_instance.set_password(reg_num)
                    user_instance.save()

                    # Process institutional email string safely
                    from utils.email_generator import email_generator
                    all_data['school_email'] = email_generator.generate_unique(
                        reg_num)

                    # Instantiate student object
                    instance = Student(**all_data)
                    instance.user = user_instance

                    # Fetch relational data safely from the educational form
                    programme_obj = EducationalInf.cleaned_data['programme']
                    instance.class_entered = programme_obj.current_class

                    # Save the final student record
                    instance.save()

                    # Log the user into the active session
                    login(request, user_instance)

            except DatabaseError:
                return HttpResponse('A database error occurred during registration.', status=500)

            return redirect("/", permanent=True)

        return HttpResponse("failed to create")


class LoginView(
    View
):
    def get(self, request):
        form = LoginForm()
        context = {
            'form': form
        }
        return render(request, 'base/login.html', context)

    def post(self, request):
        form = LoginForm(request.POST)

        next_url = request.GET.get('next') or request.POST.get('next') or '/'

        is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            # require_https=request.is_secure() if not settings.DEBUG else '',
        )

        if form.is_valid() and is_safe:
            email = form.cleaned_data['emaile']
            password = form.cleaned_data['password']
            try:
                user = authenticate(request, username=email, password=password)
                login(request, user)
                return redirect(next_url)
            except:
                return HttpResponse('failed to login')

        return HttpResponse('error response')


class LogoutView(View):
    login_url = config("LOGIN_URL") + '?next=/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def post(self, request):
        logout(request)
        return redirect(reverse('base-login'))


class SettingsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config('LOGIN_URL') + '?next=settings'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        context = {

        }
        return render(request, 'base/settings.html', context)

# ─── Dashboard ────────────────────────────────────────────────────────────────


class IndexView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):

        student = self.get_student(request)
        session = self.get_active_session()

        fee_account = StudentFeeAccount.objects.filter(
            student=student
        ).order_by('-created_at').last()

        enrollments = Curriculum.objects.none()
        fee_balance = None
        session_progress = 0

        if student and session:
            enrollments = student.enrollments.filter(
                session=session
            ).select_related('course')

            try:
                account = StudentFeeAccount.objects.get(
                    student=student,
                    fee_structure__session=session
                )

                fee_balance = account.balance
            except StudentFeeAccount.DoesNotExist:
                fee_balance = 0.0

            if session.start_date and session.end_date:
                from django.utils import timezone
                today = timezone.now().date()
                total = (session.end_date - session.start_date).days
                elapsed = (today - session.start_date).days
                session_progress = min(
                    100, round((elapsed / total) * 100)
                ) if total > 0 else 0

        context = {
            'user': request.user,
            'fee_account': fee_account,
            'session': session,
            'student': student,
            'session': session,
            'enrollments': enrollments,
            'fee_balance': fee_balance,
            'session_progress': session_progress,
            'year': __import__('datetime').date.today().year,
        }
        return render(request, 'base/index.html', context)


# ─── Socials ──────────────────────────────────────────────────────────────────

class EventsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=socials/events/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        context = {}
        return render(request, 'base/socials/events.html', context)


class NewsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=socials/news/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        context = {}
        return render(request, 'base/socials/news.html', context)


# ─── Academics ────────────────────────────────────────────────────────────────

class CurriculumView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/curriculum/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()
        # TODO : add sessions

        curriculum = Curriculum.objects.none()
        if student and session:
            curriculum = Curriculum.objects.filter(
                Tclass=student.class_entered
            ).select_related('course', 'session')

        context = {
            'curriculum': curriculum,
            'session': session,
            'student': student,
        }

        return render(request, 'base/academics/curriculum.html', context)


class UnitRegistrationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/units/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        enrolled_ids = student.enrollments.values_list(
            'record_id', flat=True
        ) if student else []

        available = Curriculum.objects.none()
        if student and session:
            available = Curriculum.objects.filter(
                Tclass=student.class_entered,
                session=session,
                # course__type='E'  # electives only — core auto-enrolled
            ).exclude(
                record_id__in=enrolled_ids
            ).select_related('course')

        context = {
            'available': available,
            'enrolled': student.enrollments.filter(
                session=session
            ).select_related('course') if student and session else [],
            'student': student,
            'session': session,
        }
        return render(request, 'base/academics/unit_registration.html', context)

    def post(self, request):
        """Enroll in a selected elective"""
        student = self.get_student(request)
        session = self.get_active_session()
        curriculum_id = request.POST.get('curriculum_id')

        if not all([student, session, curriculum_id]):
            return HttpResponse('Invalid request', status=400)

        try:
            curriculum = Curriculum.objects.get(
                record_id=curriculum_id,
                Tclass=student.class_entered,
                session=session,
                course__type='E'
            )
            # student.enrollments.add(curriculum)
            # TODO : create enrollment here
            # TODO : make transaction atomic
        except Curriculum.DoesNotExist:
            return HttpResponse('Unit not found', status=404)

        return render(request, 'base/academics/unit_registration.html', {
            'message': 'Enrolled successfully'
        })


class ResultsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=academics/results/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        from .models import Result
        student = self.get_student(request)
        session = self.get_active_session()

        results = Result.objects.none()
        if student:
            sessions = Session.objects.filter(start_date__gte=student.enrolled)
            results = Result.objects.filter(
                student=student
            ).select_related('curricula__course').order_by('-created_at')

        context = {
            'results': results,
            'student': student,
            'session': session,
            'sessions': sessions
        }
        return render(request, 'base/academics/results.html', context)


# ─── Admissions ───────────────────────────────────────────────────────────────

class ReportingView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=admissions/reporting/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        from .forms import ReportingForm
        student = self.get_student(request)
        session = self.get_active_session()

        already_reported = False

        if student and session:
            already_reported = Reporting.objects.filter(
                student=student, session=session
            ).exists()

        context = {
            'already_reported': already_reported,
            'session': session,
            'student': student
        }
        return render(request, 'base/admissions/reporting.html', context)

    def post(self, request):
        from .forms import ReportingForm
        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('No active session', status=400)

        if Reporting.objects.filter(student=student, session=session).exists():
            return HttpResponse('Already reported for this session', status=400)

        form = ReportingForm(request.POST)
        if form.is_valid():
            reporting = form.save(commit=False)
            reporting.student = student
            reporting.session = session
            reporting.save()
            from django.shortcuts import redirect
            return redirect('base-dashboard')

        context = {
            'form': form,
            'session': session,
        }
        return render(request, 'base/admissions/reporting.html', context)


class DefermentView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=admissions/defer/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        """Confirmation page before deferring"""
        context = {
            'student': self.get_student(request)
        }
        return render(request, 'base/admissions/defer.html', context)

    def post(self, request):
        student = self.get_student(request)
        if not student:
            return HttpResponse('Student not found', status=404)

        student.deffered = True
        # TODO :  add defer record here
        student.save()
        return redirect('base-dashboard')


class HostelBookingView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=admissions/hostel/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        context = {
            'student': student,
            'current_hostel': student.hostel if student else None,
        }
        return render(request, 'base/admissions/hostel_booking.html', context)

    def post(self, request):
        student = self.get_student(request)
        hostel = request.POST.get('hostel')

        if not student or not hostel:
            return HttpResponse('Invalid request', status=400)

        student.hostel = hostel
        student.stay = 'resident'
        student.save()
        from django.shortcuts import redirect
        return redirect('base-dashboard')


# ─── Financials ───────────────────────────────────────────────────────────────

class FeeStatementView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=financials/fees/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        from .forms import PaymentForm
        from .models import Payment
        student = self.get_student(request)
        session = self.get_active_session()

        account = None
        payments = []
        structure = None

        if student and session:
            try:
                structure = FeeStructure.objects.get(
                    Tclass=student.class_entered,
                    session=session
                )
            except FeeStructure.DoesNotExist:
                structure = None

            account, _ = StudentFeeAccount.objects.get_or_create(
                student=student,
                session=session,
                defaults={'fee_structure': structure}
            ) if structure else (None, False)

            if account:
                payments = Payment.objects.filter(
                    account=account
                ).order_by('-paid_at')

        context = {
            'account': account,
            'structure': structure,
            'payments': payments,
            'form': PaymentForm(initial={'account': account}),
            'student': student,
            'session': session,
        }
        return render(request, 'base/financials/fee_statement.html', context)

    def post(self, request):
        from .forms import PaymentForm
        from .models import Payment
        from django.db import transaction, DatabaseError

        student = self.get_student(request)
        session = self.get_active_session()

        if not student or not session:
            return HttpResponse('Invalid session', status=400)

        try:
            structure = FeeStructure.objects.get(
                tclass=student.class_entered,
                session=session
            )
        except FeeStructure.DoesNotExist:
            return HttpResponse('No fee structure found', status=404)

        account, _ = StudentFeeAccount.objects.get_or_create(
            student=student,
            session=session,
            defaults={'fee_structure': structure}
        )

        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    Payment.objects.create(
                        **form.cleaned_data,
                        account=account
                    )
                from django.shortcuts import redirect
                return redirect('base-fee-statement')
            except DatabaseError:
                return HttpResponse('Database error', status=500)

        context = {
            'form': form,
            'account': account,
            'structure': structure,
        }
        return render(request, 'base/financials/fee_statement.html', context)


class PaymentView(
        LoginRequiredMixin,
        StudentProfileRequiredMixin,
        View
):
    login_url = config('LOGIN_URL') + '?next=pay-fees'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    #  TODO : check if student already as an account for session to be paid if not instatiate a new one
    # HTTPStatus

    def get(self, request):
        # check for active session
        session = Session.objects.get(is_active=True)
        student = Student.objects.get(user=request.user)

        stucture = FeeStructure.objects.get(
            session=session
        )

        try:
            studentAccount = StudentFeeAccount.objects.get(
                session=session,
                student=student
            )
        except:
            studentAccount = None

        if studentAccount is None:

            studentAccount = StudentFeeAccount.objects.create(
                student=student,
                session=session,
                fee_structure=stucture
            )

        intitial = {
            'account': studentAccount
        }

        form = PaymentForm(initial=intitial)

        context = {
            'form': form,
            'structure': stucture,
            'account': studentAccount
        }
        return render(request, 'base/payment.html', context)

    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse('invalid session')

        form = PaymentForm(request.POST)
        session = Session.objects.get(is_active=True)
        student = Student.objects.get(user=request.user)
        stucture = FeeStructure.objects.get(
            session=session,
            tclass=student.class_entered
        )

        try:
            studentAccount = StudentFeeAccount.objects.get(
                session=session,
                student=student
            )
        except:
            studentAccount = None

        if studentAccount is None:

            studentAccount = StudentFeeAccount.objects.create(
                student=student,
                session=session,
                fee_structure=stucture
            )

        if form.is_valid():
            data = {
                **form.cleaned_data
            }

            try:
                with transaction.atomic():
                    instance = Payment.objects.create(
                        **data,
                        account=studentAccount
                    )

                return HttpResponse('created  succesfully')
            except DatabaseError:
                return HttpResponse('db error')
        print(form.errors)
        return HttpResponse("Error creating")

# ─── Timetable ────────────────────────────────────────────────────────────────


class WeeklyScheduleView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=timetable/schedule/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        schedule = {}
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI']

        if student and session:
            slots = Timetable.objects.filter(
                tclass=student.class_entered,
                session=session
            ).select_related('course', 'lecturer__user').order_by('start_time')

            for day in days:
                schedule[day] = slots.filter(day=day)

        context = {
            'schedule': schedule,
            'days': days,
            'student': student,
            'session': session,
        }
        return render(request, 'base/timetable/weekly_schedule.html', context)


class ExamTimetableView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=timetable/exams/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        context = {
            'student': student,
            'session': session,
            # wire to ExamSession model when built
        }
        return render(request, 'base/timetable/exam.html', context)


# ─── Evaluations ──────────────────────────────────────────────────────────────

class CourseEvaluationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=evaluations/course/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        enrolled_courses = student.enrollments.filter(
            session=session
        ).select_related('course') if student and session else []

        context = {
            'courses': enrolled_courses,
            'student': student,
        }
        return render(request, 'base/evaluations/course.html', context)


class LecturerEvaluationView(
    LoginRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=evaluations/lecturer/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        session = self.get_active_session()

        lecturers = Curriculum.objects.filter(
            Tclass=student.class_entered,
            session=session
        ).prefetch_related(
            'professor'
        ).values(
            'professor__user__first_name',
            'professor__user__last_name',
            'professor__record_id',
            'course__course_name'
        ) if student and session else []

        context = {
            'lecturers': lecturers,
            'student': student,
        }
        return render(request, 'base/evaluations/lecturer.html', context)


class HostelEvaluationView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    login_url = config("LOGIN_URL") + '?next=evaluations/hostel/'
    redirect_field_name = config("REDIRECT_FIELD_NAME")

    def get(self, request):
        student = self.get_student(request)
        # TODO : check if hostel records exist else redirect to referer
        context = {
            'student': student,
            'hostel': student if student else None,
        }
        return render(request, 'base/evaluations/hostel.html', context)
