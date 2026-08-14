from django.views import View
from django.shortcuts import render
import json

from staffConsole.views.base import RoleRequiredMixin
from base.models import (
    Session,
    Course
)

from rest_framework.serializers import ModelSerializer


class CourseSerializer(ModelSerializer):
    class Meta:
        model = Course
        exclude = [
            'record_id',
            'created_at',
            'updated_at'
        ]


class CourseCatalogView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/deptadmin/hod_course_catalog.html'

    def get(self, request):
        admin = self.get_profile()  # NOTE : Possible problem with adminstrative staff
        session = Session.objects.filter(is_active=True).first()
        dept = admin.department

        qs = Course.objects.filter(
            department=dept
        )
        course_catalog = CourseSerializer(qs, many=True).data
        context = {
            'course_catalog': course_catalog
        }
        return render(request, self.template_name, context)
