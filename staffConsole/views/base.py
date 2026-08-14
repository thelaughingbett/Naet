from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from base.models import AcademicAppointment


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Base mixin for all staff views.

    required_role must match a profile attribute:
        'lecturer'          → user.lecturer_profile
        'deptadmin'         → user.deptadmin_profile
        'schooladmin'       → user.schooladmin_profile
        'dean'              → user.dean_profile
        'institutionadmin'  → user.institutionadmin_profile
    """
    required_role = None
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.required_role:
            profile_attr = f"{self.required_role}_profile"

            if not hasattr(request.user, profile_attr):

                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_profile(self):
        return getattr(self.request.user, f"{self.required_role}_profile", None)

    def get_context_data(self, **kwargs):

        ctx = kwargs
        ctx['active_role'] = self.required_role
        ctx['profile'] = self.get_profile()
        ctx['user'] = self.request.user
        return ctx


def get_staff_dashboard_url(user):
    """Returns the correct dashboard URL for this user's role."""
    if hasattr(user, 'institutionadmin_profile'):
        return '/staff/admin/dashboard/'
    if hasattr(user, 'dean_profile'):
        return '/staff/dean/dashboard/'
    if hasattr(user, 'schooladmin_profile'):
        return '/staff/school-admin/dashboard/'
    if hasattr(user, 'deptadmin_profile'):
        return '/staff/dept-admin/dashboard/'
    if hasattr(user, 'lecturer_profile'):
        lecturer = user.lecturer_profile
        # TODO : this is checked against role which should have a background job to keep this in track
        return f'/staff/{lecturer.role}/dashboard/'

    return '/'  # TODO : return bad request here
