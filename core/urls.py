from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.student_profile, name='student_profile'),
    path('profile/update-picture/', 
         views.update_profile_picture, 
         name='update_profile_picture'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/users/', views.admin_users, name='admin_users'),
    path('dashboard/admin/offices/', views.admin_offices, name='admin_offices'),
    path('dashboard/admin/clearances/', views.admin_clearances, name='admin_clearances'),
    path('dashboard/admin/deans/', views.admin_deans, name='admin_deans'),
    path('dashboard/admin/courses/', views.admin_courses, name='admin_courses'),
    path('program-chair/students/', views.ManageStudentsView.as_view(), name='manage_students'),
    path('clearance/<int:clearance_id>/delete/', views.delete_clearance, name='delete_clearance'),
    path('clearance-request/<int:request_id>/update/', views.update_clearance_request, name='update_clearance_request'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/create/users/', views.create_user, name='create_user'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('program-chair/dashboard/', views.program_chair_dashboard, name='program_chair_dashboard'),
    path('generate-reports/', views.generate_reports, name='generate_reports'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('student/create-clearance-requests/', views.create_clearance_requests, name='create_clearance_requests'),
    path('student/clearance/<int:clearance_id>/', 
         views.view_clearance_details, 
         name='view_clearance_details'),
    path('profile/program-chair/', views.program_chair_profile, name='program_chair_profile'),
    path('profile/admin/', views.admin_profile, name='admin_profile'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('staff/pending-requests/', views.staff_pending_requests, name='staff_pending_requests'),
    path('approve-clearance-request/<int:request_id>/', views.approve_clearance_request, name='approve_clearance_request'),
    path('deny-clearance-request/<int:request_id>/', views.deny_clearance_request, name='deny_clearance_request'),
    path('staff/clearance-history/', views.staff_clearance_history, name='staff_clearance_history'),
    path('staff/profile/', views.staff_profile, name='staff_profile'),
    path('staff/view-request/<int:request_id>/', views.view_request, name='view_request'),
<<<<<<< HEAD
    path('program-chair/print-permit/<int:student_id>/', views.print_permit, name='print_permit'),
    path('program-chair/students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('clearance/<int:clearance_id>/', views.view_clearance_details, name='clearance_details'),
    path('export-clearances-excel/', views.export_clearances_excel, name='export_clearances_excel'),
    path('dashboard/admin/students/', views.admin_students, name='admin_students'),
    path('dashboard/admin/staff/', views.admin_staff, name='admin_staff'),
    path('dashboard/admin/staff/add/', views.admin_staff_add, name='admin_staff_add'),
    path('dashboard/admin/staff/<int:staff_id>/edit/', views.admin_staff_edit, name='admin_staff_edit'),
    path('dashboard/admin/settings/', views.admin_settings, name='admin_settings'),
=======

     # Add these new URL patterns
path('api/user-details/<int:user_id>/', views.get_user_details, name='get_user_details'),
path('api/approve-registration/<int:user_id>/', views.approve_registration, name='approve_registration'),
path('api/reject-registration/<int:user_id>/', views.reject_registration, name='reject_registration'),


>>>>>>> fe2b44eaf8609ca5b71b5756f71b0f6fa2ba8502
]








































