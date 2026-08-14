from django.urls import path
from staffConsole.views.deptAdmin import DeptAdminDashboardView, DeptAdminFAcultyDirectoryView, DeptAdminTeachingLoadView, LeaveApprovalView, CourseCatalogView, SyllabusManagementView


urlpatterns = [
    path(
        'dashboard/',
        DeptAdminDashboardView.as_view(),
        name='hod-dashboard'
    ),
    path(
        'faculty-directory',
        DeptAdminFAcultyDirectoryView.as_view(),
        name='hod-faculty-directory'
    ),
    path(
        'teaching-load-allocation',
        DeptAdminTeachingLoadView.as_view(),
        name='hod-teaching-load'
    ),
    path(
        'leave-approval',
        LeaveApprovalView.as_view(),
        name='hod-leave-approvals'
    ),
    path(
        'course-catalog',
        CourseCatalogView.as_view(),
        name='hod-course-catalog'
    ),
    path(
        'syllabus-management',
        SyllabusManagementView.as_view(),
        name='hod-syllabus-management'
    )
]
