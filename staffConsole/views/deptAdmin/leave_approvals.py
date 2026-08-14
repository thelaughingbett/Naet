from django.views import View
from django.shortcuts import render
import json

from staffConsole.views.base import RoleRequiredMixin
from base.models import (
    Session,
    Lecturer,
    LecturerAssignment,
    Curriculum,
    Syllabus,
    LeaveRequest
)

from rest_framework.serializers import ModelSerializer, SerializerMethodField


class LeaveRequestSerializer(ModelSerializer):
    leave_name = SerializerMethodField()
    days = SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            'name',
            'leave_name',
            'start_date',
            'end_date',
            'status',
            'reason',
            'days'
        ]

    def get_leave_name(self, obj):
        return obj.leave_type.name

    def get_days(self, obj):
        return (obj.start_date - obj.end_date).days


class LeaveApprovalView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/deptadmin/hod_leave_approvals.html'

    def get(self, request):
        admin = self.get_profile()  # NOTE : Possible problem with adminstrative staff
        session = Session.objects.filter(is_active=True).first()
        dept = admin.department
        faculty = Lecturer.objects.filter(
            department=dept
        ).select_related('user')

        # --- Leave Requests ---
        user_dept = []

        for member in faculty:
            if member == admin:
                continue
            user_dept.append(member.user)

        leave_requests = LeaveRequest.objects.filter(
            applicant__in=user_dept,
        )
        # NOTE : order by start_date to a reasonable range and get only recent leaves
        # Serialization
        data = []
        for request in leave_requests:
            row = {
                'name': request.name,
                'leave_name': request.leave_type.name,
                'start_date': request.start_date,
                'end_date': request.end_date,
                'status': request.status,
                'reason': request.reason,
                'days': (request.start_date - request.end_date).days
            }

            data.append(row)

        leave_data = LeaveRequestSerializer(leave_requests, many=True).data

        context = {
            'leave_data': leave_data,
            'data': data,
            'faculty': faculty
        }
        return render(request, self.template_name, context)
