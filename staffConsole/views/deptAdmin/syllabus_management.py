from django.views import View
from django.shortcuts import render

from base.models import (
    Session,
    Curriculum,
)


from staffConsole.views.base import RoleRequiredMixin


from rest_framework.serializers import ModelSerializer, SerializerMethodField


class SyllabusSerializer(ModelSerializer):
    lecturers = SerializerMethodField()
    session = SerializerMethodField()
    class_name = SerializerMethodField()
    course_code = SerializerMethodField()
    course_name = SerializerMethodField()
    course_type = SerializerMethodField()
    enrolled = SerializerMethodField()
    status = SerializerMethodField()
    weekly_slots = SerializerMethodField()
    id = SerializerMethodField()

    class Meta:
        model = Curriculum

        exclude = [
            'record_id',
            'created_at',
            'updated_at',
            'professor',
            'syllabus',
            'Tclass',
            'weekly_allocated_slots'
        ]

    def get_lecturers(self, obj):
        lecturers = []
        from base.models import LecturerAssignment
        qs = LecturerAssignment.objects.filter(
            curriculum=obj
        )
        for lecturer in qs:
            role = "Primary" if lecturer.is_primary else "Assistant"
            name = f"{lecturer.lecturer.name}({role})"
            lecturers.append(name)
        return lecturers

    def get_session(self, obj):
        return f"{obj.session}"

    def get_class_name(self, obj):
        return f"{obj.Tclass}"

    def get_course_code(self, obj):
        return obj.syllabus.course.course_code

    def get_course_name(self, obj):
        return obj.syllabus.course.course_name

    def get_course_type(self, obj):
        return obj.syllabus.course.course_type

    def get_enrolled(self, obj):
        return len(obj.enrollment_records.all())

    def get_status(self, obj):
        return "Confirmed"

    def get_weekly_slots(self, obj):
        return obj.weekly_allocated_slots

    def get_id(self, obj):
        return f"{obj.Tclass} - {obj.syllabus.course.course_code} "


class SyllabusManagementView(RoleRequiredMixin, View):
    required_role = 'lecturer'
    template_name = 'staffConsole/deptadmin/hod_syllabus_management.html'

    def get(self, request):
        admin = self.get_profile()  # NOTE : Possible problem with adminstrative staff
        session = Session.objects.filter(is_active=True).first()

        sessions = Session.objects.all().order_by('-end_date')[:12]

        dept = admin.department

        qs = Curriculum.objects.filter(
            syllabus__course__department=dept,
            session=session
        )

        syllabus_data = SyllabusSerializer(qs, many=True).data

        context = {
            'syllabus_data': syllabus_data,
            'sessions': sessions
        }

        return render(request, self.template_name, context)
