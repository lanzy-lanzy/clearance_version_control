from django.urls import path
from . import views
from .views import approve_student, reject_student, get_student_details

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
    path('program-chair/print-permit/<int:student_id>/', views.print_permit, name='print_permit'),
    path('program-chair/students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('clearance/<int:clearance_id>/', views.view_clearance_details, name='clearance_details'),
    path('export-clearances-excel/', views.export_clearances_excel, name='export_clearances_excel'),
    path('dashboard/admin/students/', views.admin_students, name='admin_students'),
    path('dashboard/admin/staff/', views.admin_staff, name='admin_staff'),
    path('dashboard/admin/staff/add/', views.admin_staff_add, name='admin_staff_add'),
    path('dashboard/admin/staff/<int:staff_id>/edit/', views.admin_staff_edit, name='admin_staff_edit'),
    path('dashboard/admin/settings/', views.admin_settings, name='admin_settings'),
    path('request-again/<int:request_id>/', views.request_again, name='request_again'),
    path('api/deans/<int:dean_id>/', views.get_dean_details, name='get_dean_details'),
   path('api/offices/detail/<int:office_id>/', views.office_detail_api, name='office_detail_api'),
      path('dashboard/admin/pending-approvals/', views.admin_pending_approvals, name='admin_pending_approvals'),
    path('admin/approve-student/<int:student_id>/', approve_student, name='approve_student'),
    path('admin/reject-student/<int:student_id>/', reject_student, name='reject_student'),
    path('api/staff/<int:staff_id>/delete/', views.delete_staff, name='api_staff_delete'),
    path('admin/student-details/<int:student_id>/', get_student_details, name='get_student_details'),
]


















