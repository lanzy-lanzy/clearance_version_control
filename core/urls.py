from django.urls import path
from . import views

urlpatterns = [
    # Basic Routes
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),

    # Student Routes
    path('profile/', views.student_profile, name='student_profile'),
    path('profile/update-picture/', views.update_profile_picture, name='update_profile_picture'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/create-clearance-requests/', views.create_clearance_requests, name='create_clearance_requests'),
    path('student/clearance/<int:clearance_id>/', views.view_clearance_details, name='view_clearance_details'),
    path('request-again/<int:request_id>/', views.request_again, name='request_again'),

    # Program Chair Routes
    path('program-chair/dashboard/', views.program_chair_dashboard, name='program_chair_dashboard'),
    path('program-chair/students/', views.ManageStudentsView.as_view(), name='manage_students'),
    path('program-chair/students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('program-chair/print-permit/<int:student_id>/', views.print_permit, name='print_permit'),
    path('profile/program-chair/', views.program_chair_profile, name='program_chair_profile'),
    path('clearance/<int:clearance_id>/delete/', views.delete_clearance, name='delete_clearance'),

    # Staff Routes
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/pending-requests/', views.staff_pending_requests, name='staff_pending_requests'),
    path('staff/clearance-history/', views.staff_clearance_history, name='staff_clearance_history'),
    path('staff/profile/', views.staff_profile, name='staff_profile'),
    path('staff/view-request/<int:request_id>/', views.view_request, name='view_request'),
    path('approve-clearance-request/<int:request_id>/', views.approve_clearance_request, name='approve_clearance_request'),
    path('deny-clearance-request/<int:request_id>/', views.deny_clearance_request, name='deny_clearance_request'),
    path('clearance-request/<int:request_id>/update/', views.update_clearance_request, name='update_clearance_request'),

    # Admin Routes
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/users/', views.admin_users, name='admin_users'),
    path('dashboard/admin/offices/', views.admin_offices, name='admin_offices'),
    path('dashboard/admin/clearances/', views.admin_clearances, name='admin_clearances'),
    path('dashboard/admin/clearances/<int:clearance_id>/', views.clearance_details, name='clearance_details'),
    path('dashboard/admin/deans/', views.admin_deans, name='admin_deans'),
    path('dashboard/admin/courses/', views.admin_courses, name='admin_courses'),
    path('dashboard/admin/students/', views.admin_students, name='admin_students'),
    path('dashboard/admin/staff/', views.admin_staff, name='admin_staff'),
    path('dashboard/admin/staff/add/', views.admin_staff_add, name='admin_staff_add'),
    path('dashboard/admin/staff/<int:staff_id>/edit/', views.admin_staff_edit, name='admin_staff_edit'),
    path('dashboard/admin/settings/', views.admin_settings, name='admin_settings'),
    path('dashboard/admin/pending-approvals/', views.admin_pending_approvals, name='admin_pending_approvals'),
    path('dashboard/create/users/', views.create_user, name='create_user'),
    path('profile/admin/', views.admin_profile, name='admin_profile'),

    path('dashboard/admin/approve-student/<int:student_id>/', views.approve_student, name='approve_student'),
    path('dashboard/admin/reject-student/<int:student_id>/', views.reject_student, name='reject_student'),
    # Report Routes
    path('generate-reports/', views.generate_reports, name='generate_reports'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('export-clearances-excel/', views.export_clearances_excel, name='export_clearances_excel'),

    # API Routes
    path('api/deans/<int:dean_id>/', views.get_dean_details, name='get_dean_details'),
    path('api/offices/detail/<int:office_id>/', views.office_detail_api, name='office_detail_api'),
    path('api/staff/<int:staff_id>/delete/', views.delete_staff, name='api_staff_delete'),
    path('admin/student-details/<int:student_id>/', views.get_student_details, name='get_student_details'),
    # Add missing stats endpoint (example)
    path('dashboard/admin/get-approval-stats/', views.get_approval_stats, name='get_approval_stats'),
    path('api/courses-by-dean/<str:dean_name>/', views.get_courses_by_dean, name='courses_by_dean'),
    path('api/program-chairs/<int:dean_id>/', views.get_program_chairs, name='get_program_chairs'),
    path('api/courses/<int:dean_id>/', views.get_courses, name='get_courses'),  # Remove any login_required decorator
]
