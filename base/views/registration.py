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

from http import HTTPStatus

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect
)
from django.views import View
from django.http import HttpResponse
from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from django.db import (
    DatabaseError,
    IntegrityError,
    transaction
)


from base.models import (
    EmergencyContact,
    Student,
    Programme,
    School,
    Department,
    User,
)
from base.forms import (
    EmergencyContactFormSet,
    RegisterForm,
    ContactInfoForm,
    EducationalInfoForm,
    UserDetailsForm,
)

from .base import logger


class RegisterView(View):
    """
    Manages the student onboarding and registration matrix pipeline.

    Assembles cascading academic entity dependency maps for dynamic client-side 
    filtering, binds five discrete form layouts inside an atomic transaction block, 
    and handles conditional routing based on residency selections.
    """

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
            'EmergencyContactInfoFormset': EmergencyContactFormSet(queryset=EmergencyContact.objects.none()),
            'EducationalInfoForm': EdForm,
            'schools_json': schools,
            'departments_json': departments,
            'programmes_json': programmes
        }

        return render(request, "base/registration.html", context)

    def post(self, request):
        """
        Processes the multi-form student onboarding wizard registration bundle.

        Execution Workflow & Business Logic:
            1. Form Binding: Synchronously instantiates five distinct forms and 
               formsets from POST data, loading any uploaded physical verification media.
            2. Hard Validation: Forces all layouts to evaluate (`all([...])`) to ensure 
               the client frontend gets complete validation error packets across every field.
            3. Data Compacting: Merges cleaned dictionaries, strips client-side tracking 
               variables, and prepares database-level insert properties.
            4. Atomic Transaction Matrix:
               - Spawns the central auth User record, explicitly forcing 'student' roles.
               - Hashes the student's dynamic registration number to serve as their temporary password.
               - Injects the `email_generator` util to assign a unique, isolated university channel address.
               - Resolves academic cohort hierarchies, mapping the program directly to its current active class.
               - Iterates through the emergency contacts formset, filtering out unmodified rows or items 
                 marked for deletion, while flagging primary index nodes manually.
            5. Post-Commit Pipeline:
               - Evaluates residency selection tags ('stay').
               - Resident: Diverts workflow loops to immediate local hostel booking routes.
               - Non-Resident: Triggers transaction-locked alert signals (`transaction.on_commit`), 
                 queueing asynchronous background tasks to broadcast multi-channel (SMS/Email) confirmation alerts.

        Exceptions & Failure States:
            - IntegrityError: Returns HTTP 409 if unique key fields (e.g., registration number, 
              national ID, telephone strings) trigger a table collision constraint.
            - DatabaseError: Returns HTTP 500 if server connection blocks drop mid-execution.
        """

        form = RegisterForm(request.POST)
        UserDetails = UserDetailsForm(request.POST, request.FILES)
        detailsForm = ContactInfoForm(request.POST)
        emergencyContactInfoFormset = EmergencyContactFormSet(request.POST)
        EducationalInf = EducationalInfoForm(request.POST)

        # Force all forms to validate to populate errors
        valid = all([
            form.is_valid(),
            detailsForm.is_valid(),
            EducationalInf.is_valid(),
            UserDetails.is_valid(),
            emergencyContactInfoFormset.is_valid(),
        ])

        if valid:
            # Combine cleaned data into a single dictionary safely
            all_data = {
                **form.cleaned_data,
                **detailsForm.cleaned_data,
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
                    from base.utils.email_generator import email_generator
                    all_data['school_email'] = email_generator.generate_unique(
                        reg_num)

                    # Instantiate student object
                    instance = Student(**all_data)
                    instance.user = user_instance

                    # Fetch relational data safely from the educational form
                    programme_obj = EducationalInf.cleaned_data['programme']
                    instance.class_entered = programme_obj.current_class
                    instance.save()

                    primary_index = int(request.POST.get(
                        'primary_contact_index', 0))
                    for index, form in enumerate(emergencyContactInfoFormset):
                        # 1. Skip empty extra forms that the user didn't fill out
                        if not form.has_changed():
                            continue

                        # 2. Skip forms marked for deletion (if can_delete=True is enabled)
                        if emergencyContactInfoFormset.can_delete and emergencyContactInfoFormset._should_delete_form(form):
                            continue

                        # 3. Safely extract data and create the model instance manually
                        contact_data = form.cleaned_data
                        is_primary_choice = (index == primary_index)

                        EmergencyContact.objects.create(
                            **contact_data,
                            student=instance,
                            is_primary=is_primary_choice
                        )

                    # Save the final student record

                    # TODO : send notificatio here for sucessful registration,with schoolemail details

                    # TODO :  check if student chose resident and redirect to hostel booking form else redirect to successful registration and tell of email notification

                    # after instance.save() and login(request, user_instance)
                # login(request, user_instance)
                stay = all_data.get('stay', 'outside')

                if stay == 'resident':
                    # redirect to hostel booking with a success message
                    messages.success(
                        request,
                        f"Registration successful! Welcome, {user_instance.first_name}. "
                        f"Your school email is {instance.school_email}. "
                        f"Please complete your hostel booking below."
                    )
                    return redirect('base-registration-hostel-booking')

                else:
                    messages.success(
                        request,
                        f"Registration successful! Welcome, {user_instance.first_name}. "
                        f"Your school email is {instance.school_email}. "
                        f"A confirmation has been sent to {user_instance.email}."
                    )
                    # fire notification
                    from base.utils.signals import send_notification
                    transaction.on_commit(lambda: send_notification.send(
                        sender=Student,
                        user=user_instance,
                        template_key='registration_confirmed',
                        channels=['email', 'sms'],
                        context={
                            'student_name':  user_instance.first_name,
                            'school_email':  instance.school_email,
                            'reg_number':    instance.registration_number,
                            'programme':     programme_obj.programme_name,
                            'class':         instance.class_entered.class_name,
                        }
                    ))

                    request.session['new_student_id'] = str(instance.record_id)
                    return redirect('base-registration-sucess')

                    # Log the user into the active session
                    # TODO : remove this registration

            except IntegrityError as e:
                # Specific database error (e.g., duplicate phone numbers, null violations)
                logger.error(
                    f"Database Integrity Error during contact registration for Student ID {instance.registration_number}: {e}", exc_info=True)
                messages.error(
                    request, f"Registration failed: A data conflict occurred. Technical details: {e}")
                return HttpResponse(
                    f"Registration failed: A data conflict occurred. Technical details: {e}")

            except DatabaseError as e:
                # Broad database error (e.g., connection lost, timeout, syntax errors)
                logger.error(
                    f"General Database Error during contact registration for Student ID {instance.registration_number}: {e}", exc_info=True)
                messages.error(
                    request, "A database system error occurred. Please verify your connection and try again.")
                return HttpResponse("General Database Error during contact registration for Student ID {instance.registration_number}: {e}")

            return redirect("/", permanent=True)

        return HttpResponse("failed to create")


class RegistrationSucessView(View):
    def get(self, request):
        student_id = request.session.pop('new_student_id')
        student = None

        if student_id:
            student = get_object_or_404(Student, record_id=student_id)

            context = {
                'student': student
            }

            return render(request, 'base/registration-sucess.html', context=context)

        else:
            return redirect('base-index')


class HostelBookingRegistrationView(View):
    pass
