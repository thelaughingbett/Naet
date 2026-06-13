from django.urls import path

from base.views import CourseEvaluationView, LecturerEvaluationView, HostelEvaluationView

urlpatterns = [
    path('course/',   CourseEvaluationView.as_view(),   name='base-course-evaluation'),
    path('lecturer/', LecturerEvaluationView.as_view(), name='base-lecturer-evaluation'),
    path('hostel/',   HostelEvaluationView.as_view(),   name='base-hostel-evaluation'),
]
