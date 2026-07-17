from django.contrib.auth.models import Permission


class CanApproveDeferments(BasePermission):
    def has_permission(self, request):
        user = request.user
        return (
            hasattr(user, 'deptadmin_profile') or
            hasattr(user, 'schooladmin_profile') or
            user.is_superuser
        )


class CanViewStudentRecords(BasePermission):
    def has_permission(self, request):
        user = request.user
        return any([
            hasattr(user, 'lecturer_profile'),
            hasattr(user, 'deptadmin_profile'),
            hasattr(user, 'schooladmin_profile'),
            user.is_superuser,
        ])


class CanManageITTickets(BasePermission):
    def has_permission(self, request):
        return hasattr(request.user, 'itstaff_profile')
