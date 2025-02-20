import logging
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from io import BytesIO
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.views.decorators.http import require_POST
from django.db.models import Count

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import json

# Excel Generation
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# Local imports
from django.db import models
from core.models import (
    ClearanceRequest, Clearance, Staff, Student, 
    Office, ProgramChair, User, Dean, Course,
    UserProfile, SEMESTER_CHOICES
)

# Set up logging
logger = logging.getLogger(__name__)

# Basic Views

def user_logout(request):
    logout(request)
    return redirect('login')
def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'programchair'):
            return redirect('program_chair_dashboard')
        elif hasattr(request.user, 'student'):
            return redirect('student_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_dashboard')
    return render(request, 'home.html')

def user_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'programchair'):
            return redirect('program_chair_dashboard')
        elif hasattr(request.user, 'staff'):  # Add staff check
            return redirect('staff_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account is not yet approved. Please wait for admin approval.')
                return redirect('login')
            
            login(request, user)
            
            # Redirect based on user type
            if hasattr(user, 'student'):
                return redirect('student_dashboard')
            elif hasattr(user, 'programchair'):
                return redirect('program_chair_dashboard')
            elif hasattr(user, 'staff'):  # Add staff redirect
                return redirect('staff_dashboard')
            elif user.is_superuser:
                return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    context = {
        'program_chairs': ProgramChair.objects.all(),
        'dormitory_owners': Staff.objects.filter(is_dormitory_owner=True)
    }
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        student_id = request.POST.get('student_id')
        program_chair_id = request.POST.get('program_chair')
        course_code = request.POST.get('course')
        year_level = request.POST.get('year_level')
        is_boarder = request.POST.get('is_boarder') == 'on'
        dormitory_owner_id = request.POST.get('dormitory_owner')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register')
            
        try:
            # Create inactive user (pending approval)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False  # Set user as inactive by default
            )
            
            # Get related objects
            program_chair = ProgramChair.objects.get(id=program_chair_id)
            course = Course.objects.get(code=course_code)
            dormitory_owner = None
            if is_boarder and dormitory_owner_id:
                dormitory_owner = Staff.objects.get(id=dormitory_owner_id)
            
            # Create student profile
            Student.objects.create(
                user=user,
                student_id=student_id,
                course=course,
                program_chair=program_chair,
                year_level=year_level,
                is_boarder=is_boarder,
                dormitory_owner=dormitory_owner,
                is_approved=False  # Set as not approved by default
            )
            
            messages.success(
                request, 
                'Registration successful! Please wait for admin approval before logging in.'
            )
            return redirect('login')
            
        except Exception as e:
            # If there's an error, delete the user if it was created
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error during registration: {str(e)}')
            return redirect('register')
    
    return render(request, 'registration/register.html', context)

@login_required
def student_dashboard(request):
    try:
        student = request.user.student
        clearances = Clearance.objects.filter(student=student).order_by('-school_year', '-semester')
        
        context = {
            'student_info': student,
            'clearances': clearances,
        }
        return render(request, 'core/student_dashboard.html', context)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('home')

@login_required
def student_profile(request):
    """
    Display and manage student profile information.
    """
    try:
        student = request.user.student
        return render(request, 'core/student_profile.html', {
            'student': student
        })
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('home')

@login_required
def delete_clearance(request, clearance_id):
    clearance = get_object_or_404(Clearance, id=clearance_id)
    if request.method == 'POST':
        clearance.delete()
        messages.success(request, 'Clearance deleted successfully.')
    return redirect('program_chair_dashboard')

@login_required
def update_clearance_request(request, request_id):
    """
    Allows a staff member to approve or deny a clearance request.
    Staff can only handle clearance requests for their assigned office.
    Special handling for dormitory clearances.
    """
    clearance_request = get_object_or_404(ClearanceRequest, pk=request_id)
    
    try:
        staff_member = request.user.staff
        
        # Check if staff member belongs to the office of the clearance request
        if staff_member.office != clearance_request.office:
            messages.error(
                request, 
                f"You don't have permission to handle clearance requests for {clearance_request.office.name}. "
                f"You can only handle requests for {staff_member.office.name}."
            )
            return redirect('office_dashboard')

        # Special handling for dormitory clearances
        if clearance_request.office.name == "DORMITORY":
            if not staff_member.is_dormitory_owner:
                messages.error(request, "Only dormitory owners can handle dormitory clearances.")
                return redirect('office_dashboard')
            if clearance_request.student.dormitory_owner != staff_member:
                messages.error(request, "You can only handle clearances for your assigned students.")
                return redirect('office_dashboard')

        # Special handling for SSB offices
        if clearance_request.office.name.startswith('SSB'):
            # Check if the student belongs to the correct school
            student_dean = clearance_request.student.course.dean
            if clearance_request.office.affiliated_dean != student_dean:
                messages.error(
                    request, 
                    "You can only handle SSB clearances for students from your school."
                )
                return redirect('office_dashboard')

    except Staff.DoesNotExist:
        messages.error(request, "Staff access required.")
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        
        try:
            if action == 'approve':
                clearance_request.approve(staff_member)
                messages.success(
                    request, 
                    f"Clearance request approved for {clearance_request.student.full_name}"
                )
            elif action == 'deny':
                if not remarks:
                    messages.error(request, "Remarks are required when denying a clearance request.")
                    return redirect('office_dashboard')
                clearance_request.deny(staff_member, remarks)
                messages.success(
                    request, 
                    f"Clearance request denied for {clearance_request.student.full_name}"
                )
            else:
                messages.error(request, "Invalid action specified.")
                return redirect('office_dashboard')

        except PermissionError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
        
        # Refresh the student's overall clearance status
        clearance = Clearance.objects.get(
            student=clearance_request.student,
            school_year=clearance_request.school_year,
            semester=clearance_request.semester
        )
        clearance.check_clearance()

    return redirect('office_dashboard')

# Class-based Views
class ManageStudentsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Student
    template_name = 'core/manage_students.html'
    context_object_name = 'students'
    paginate_by = 10

    def test_func(self):
        return hasattr(self.request.user, 'programchair')

    def get_queryset(self):
        program_chair = self.request.user.programchair
        queryset = Student.objects.filter(
            course__dean=program_chair.dean
        ).select_related(
            'user', 
            'course'
        ).prefetch_related(
            'clearances'
        )

        # Apply search filter if present
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(student_id__icontains=search_query)
            )

        # Apply year level filter if present
        year_level = self.request.GET.get('year_level')
        if year_level:
            queryset = queryset.filter(year_level=year_level)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program_chair = self.request.user.programchair
        current_year = timezone.now().year
        school_year = f"{current_year}-{current_year + 1}"
        semester = "1ST"

        context.update({
            'program_chair': program_chair,
            'current_school_year': school_year,
            'current_semester': semester,
        })
        return context

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('home')

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        student_id = request.POST.get('student_id')
        
        try:
            student = Student.objects.get(id=student_id)
            
            if action == 'delete':
                student.user.delete()  # This will cascade delete the student profile
                messages.success(request, 'Student deleted successfully.')
            elif action == 'approve':
                student.is_approved = True
                student.approval_date = timezone.now()
                student.approval_admin = request.user
                student.save()
                messages.success(request, 'Student approved successfully.')
                
        except Student.DoesNotExist:
            messages.error(request, 'Student not found.')
            
        return redirect('manage_students')

class StudentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Student
    template_name = 'core/student_detail.html'
    context_object_name = 'student'

    def test_func(self):
        return hasattr(self.request.user, 'programchair')

    def get_queryset(self):
        # Ensure program chairs can only view their students
        return Student.objects.filter(
            course__dean=self.request.user.programchair.dean
        ).select_related(
            'user',
            'course',
            'program_chair',
            'program_chair__user'
        )

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_deans(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name')
            description = request.POST.get('description')
            logo = request.FILES.get('logo')
            
            dean = Dean.objects.create(
                name=name,
                description=description,
                logo=logo if logo else None
            )
            messages.success(request, f'Dean {name} added successfully.')
            
        elif action == 'edit':
            dean_id = request.POST.get('dean_id')
            try:
                dean = Dean.objects.get(id=dean_id)
                dean.name = request.POST.get('name')
                dean.description = request.POST.get('description')
                
                # Handle logo update
                if 'logo' in request.FILES:
                    # Delete old logo if it exists
                    if dean.logo:
                        dean.logo.delete(save=False)
                    dean.logo = request.FILES['logo']
                
                dean.save()
                messages.success(request, f'Dean {dean.name} updated successfully.')
            except Dean.DoesNotExist:
                messages.error(request, 'Dean not found.')
                
        elif action == 'delete':
            dean_id = request.POST.get('dean_id')
            try:
                dean = Dean.objects.get(id=dean_id)
                # Delete the logo file when deleting the dean
                if dean.logo:
                    dean.logo.delete(save=False)
                dean.delete()
                messages.success(request, f'Dean {dean.name} deleted successfully.')
            except Dean.DoesNotExist:
                messages.error(request, 'Dean not found.')
            
    deans = Dean.objects.all()
    return render(request, 'admin/deans.html', {'deans': deans})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    # Get pending student registrations
    pending_approvals = Student.objects.filter(
        is_approved=False,
        user__is_active=False
    ).select_related('user', 'course').order_by('-user__date_joined')

    context = {
        'total_students': Student.objects.count(),
        'total_staff': Staff.objects.count(),
        'total_program_chairs': ProgramChair.objects.count(),
        'clearance_stats': {
            'total': Clearance.objects.count(),
            'pending': ClearanceRequest.objects.filter(status='pending').count(),
            'approved': ClearanceRequest.objects.filter(status='approved').count(),
            'denied': ClearanceRequest.objects.filter(status='denied').count(),
        },
        'recent_clearances': Clearance.objects.select_related('student')[:5],
        'offices': Office.objects.annotate(
            staff_count=Count('staff'),
            pending_requests=Count('clearance_requests', filter=Q(clearance_requests__status='pending'))
        ),
        'pending_approvals': pending_approvals,
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_pending_approvals(request):
    # Get all pending student registrations
    pending_students = Student.objects.filter(user__is_active=False)
    
    context = {
        'pending_students': pending_students,
        'total_pending': pending_students.count(),
    }
    
    return render(request, 'admin/pending_approvals.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_users(request):
    context = {
        'students': Student.objects.select_related('user', 'course').all(),
        'staff': Staff.objects.select_related('user', 'office').all(),
        'program_chairs': ProgramChair.objects.select_related('user').all(),
    }
    return render(request, 'admin/users.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_offices(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name')
            description = request.POST.get('description')
            location = request.POST.get('location')
            contact_number = request.POST.get('contact_number')
            email = request.POST.get('email')
            
            try:
                Office.objects.create(
                    name=name,
                    description=description,
                    location=location,
                    contact_number=contact_number,
                    email=email
                )
                messages.success(request, f'Office "{name}" added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding office: {str(e)}')
        
        elif action == 'edit':
            office_id = request.POST.get('office_id')
            try:
                office = Office.objects.get(id=office_id)
                office.name = request.POST.get('name')
                office.description = request.POST.get('description')
                office.location = request.POST.get('location')
                office.contact_number = request.POST.get('contact_number')
                office.email = request.POST.get('email')
                office.save()
                messages.success(request, f'Office "{office.name}" updated successfully.')
            except Office.DoesNotExist:
                messages.error(request, 'Office not found.')
            except Exception as e:
                messages.error(request, f'Error updating office: {str(e)}')
        
        elif action == 'delete':
            office_id = request.POST.get('office_id')
            try:
                office = Office.objects.get(id=office_id)
                office_name = office.name
                office.delete()
                messages.success(request, f'Office "{office_name}" deleted successfully.')
            except Office.DoesNotExist:
                messages.error(request, 'Office not found.')
            except Exception as e:
                messages.error(request, f'Error deleting office: {str(e)}')
    
    # Get offices with related statistics
    offices = Office.objects.annotate(
        staff_count=Count('staff'),
        pending_requests=Count('clearance_requests', 
                             filter=Q(clearance_requests__status='pending')),
        completed_requests=Count('clearance_requests', 
                               filter=Q(clearance_requests__status='completed')),
        total_requests=Count('clearance_requests')
    ).order_by('name')
    
    context = {
        'offices': offices,
        'total_offices': offices.count(),
        'total_staff': Staff.objects.count(),
        'total_pending_requests': sum(office.pending_requests for office in offices),
    }
    return render(request, 'admin/offices.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_clearances(request):
    clearances = Clearance.objects.select_related('student').all().order_by('-school_year', '-semester')
    
    # Get clearance statistics
    clearance_stats = {
        'pending': ClearanceRequest.objects.filter(status='PENDING').count(),
        'approved': ClearanceRequest.objects.filter(status='APPROVED').count(),
        'denied': ClearanceRequest.objects.filter(status='DENIED').count(),
    }
    
    # Get recent clearances
    recent_clearances = Clearance.objects.select_related('student').order_by('-created_at')[:5]
    
    context = {
        'clearances': clearances,
        'clearance_stats': clearance_stats,
        'recent_clearances': recent_clearances,
    }
    return render(request, 'admin/clearances.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_courses(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            code = request.POST.get('code')
            name = request.POST.get('name')
            dean_id = request.POST.get('dean')
            
            dean = get_object_or_404(Dean, id=dean_id)
            Course.objects.create(code=code, name=name, dean=dean)
            messages.success(request, f'Course {code} added successfully.')
            
        elif action == 'delete':
            course_id = request.POST.get('course_id')
            course = get_object_or_404(Course, id=course_id)
            course.delete()
            messages.success(request, f'Course {course.code} deleted successfully.')
            
        elif action == 'edit':
            course_id = request.POST.get('course_id')
            course = get_object_or_404(Course, id=course_id)
            course.code = request.POST.get('code')
            course.name = request.POST.get('name')
            course.dean = get_object_or_404(Dean, id=request.POST.get('dean'))
            course.save()
            messages.success(request, f'Course {course.code} updated successfully.')
            
        return redirect('admin_courses')

    # Annotate courses with student count
    courses = Course.objects.annotate(
        student_count=Count('student')
    ).select_related('dean').all()
    
    total_students = Student.objects.count()
    deans = Dean.objects.all()

    context = {
        'courses': courses,
        'deans': deans,
        'total_students': total_students,
    }
    
    return render(request, 'admin/courses.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_user(request):
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        try:
            # Create base user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )

            if user_type == 'student':
                student_id = request.POST.get('student_id')
                course_id = request.POST.get('course')
                program_chair_id = request.POST.get('program_chair')
                year_level = request.POST.get('year_level')
                
                course = Course.objects.get(id=course_id)
                program_chair = ProgramChair.objects.get(id=program_chair_id)
                
                Student.objects.create(
                    user=user,
                    student_id=student_id,
                    course=course,
                    program_chair=program_chair,
                    year_level=year_level,
                    is_approved=True,
                    approval_date=timezone.now(),
                    approval_admin=request.user
                )
            
            elif user_type == 'staff':
                office_id = request.POST.get('office')
                is_dormitory_owner = request.POST.get('is_dormitory_owner') == 'on'
                
                office = Office.objects.get(id=office_id)
                Staff.objects.create(
                    user=user,
                    office=office,
                    is_dormitory_owner=is_dormitory_owner
                )
            
            elif user_type == 'program_chair':
                dean_id = request.POST.get('dean')
                dean = Dean.objects.get(id=dean_id)
                ProgramChair.objects.create(
                    user=user,
                    dean=dean
                )

            messages.success(request, f'User {username} created successfully.')
            return redirect('admin_users')

        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('create_user')

    context = {
        'courses': Course.objects.all(),
        'offices': Office.objects.all(),
        'program_chairs': ProgramChair.objects.all(),
        'deans': Dean.objects.all(),
    }
    return render(request, 'admin/create_user.html', context)

@login_required
def get_program_chairs(request, dean_id):
    program_chairs = ProgramChair.objects.filter(dean_id=dean_id).select_related('user')
    data = [{
        'id': pc.id,
        'user': {
            'full_name': f"{pc.user.first_name} {pc.user.last_name}"
        }
    } for pc in program_chairs]
    return JsonResponse(data, safe=False)

@login_required
def get_courses(request, dean_id):
    courses = Course.objects.filter(dean_id=dean_id)
    data = [{
        'id': course.id,
        'code': course.code
    } for course in courses]
    return JsonResponse(data, safe=False)

@login_required
def get_offices(request, dean_id):
    offices = Office.objects.filter(affiliated_dean_id=dean_id)
    data = [{
        'id': office.id,
        'name': office.name
    } for office in offices]
    return JsonResponse(data, safe=False)
def is_program_chair(user):
    return hasattr(user, 'programchair')

@login_required
@user_passes_test(is_program_chair)
def program_chair_dashboard(request):
    program_chair = request.user.programchair
    students = Student.objects.filter(course__dean=program_chair.dean)
    
    # Get current school year and semester
    current_year = timezone.now().year
    school_year = f"{current_year}-{current_year + 1}"
    semester = "1ST"  # You might want to make this dynamic
    
    # Count statistics
    total_students = students.count()
    cleared_students = students.filter(
        clearances__is_cleared=True,  # Changed from clearance to clearances
        clearances__school_year=school_year,
        clearances__semester=semester
    ).count()
    
    pending_clearances = students.filter(
        clearances__is_cleared=False,
        clearances__school_year=school_year,
        clearances__semester=semester
    ).count()
    
    # Get students with pagination
    paginator = Paginator(students, 10)  # Show 10 students per page
    page = request.GET.get('page')
    students_page = paginator.get_page(page)
    
    context = {
        'program_chair': program_chair,
        'students': students_page,
        'total_students': total_students,
        'cleared_students': cleared_students,
        'pending_clearances': pending_clearances,
        'school_year': school_year,
        'semester': semester,
        'page_obj': students_page,  # For pagination
    }
    return render(request, 'core/program_chair_dashboard.html', context)

@login_required
def generate_reports(request):
    if request.method == 'POST':
        # Handle report generation logic here
        pass
    
    context = {
        'school_years': get_school_years(),
        'semesters': SEMESTER_CHOICES,
    }
    return render(request, 'core/generate_reports.html', context)

@login_required
def generate_report(request):
    if request.method == 'POST':
        school_year = request.POST.get('school_year')
        semester = request.POST.get('semester')
        report_type = request.POST.get('report_type')
        
        # Add your report generation logic here
        if report_type == 'pdf':
            # Generate PDF report
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="clearance_report_{school_year}_{semester}.pdf"'
            # Add PDF generation logic here
            return response
            
        elif report_type == 'excel':
            # Generate Excel report
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="clearance_report_{school_year}_{semester}.xlsx"'
            # Add Excel generation logic here
            return response
            
        messages.success(request, 'Report generated successfully')
        
    return redirect('generate_reports')

def get_school_years():
    current_year = timezone.now().year
    return [f"{year}-{year + 1}" for year in range(current_year - 2, current_year + 1)]

@login_required
def create_clearance_requests(request):
    """
    View for students to create clearance requests for a specific semester.
    Handles both GET and POST requests, with validation and detailed error handling.
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, "Access denied. Student profile required.")
        return redirect('home')
    
    try:
        student = request.user.student
        
        if request.method == 'POST':
            school_year = request.POST.get('school_year')
            semester = request.POST.get('semester')
            
            if not all([school_year, semester]):
                messages.error(request, "Please provide both school year and semester.")
                return redirect('create_clearance_requests')

            # Check for existing clearance
            existing_clearance = Clearance.objects.filter(
                student=student,
                school_year=school_year,
                semester=semester
            ).exists()

            if existing_clearance:
                messages.error(
                    request, 
                    f"A clearance request already exists for {school_year} {semester} semester."
                )
                return redirect('student_dashboard')

            # Check student's eligibility
            if not student.is_approved:
                messages.error(
                    request, 
                    "Your student account must be approved before creating clearance requests."
                )
                return redirect('student_dashboard')

            # Create main clearance record
            clearance = Clearance.objects.create(
                student=student,
                school_year=school_year,
                semester=semester,
                is_cleared=False
            )

            # Get required offices based on student's school
            required_offices = Office.objects.filter(
                Q(office_type='OTHER') |
                Q(office_type=student.course.dean.name)
            )

            # Create clearance requests for each required office
            for office in required_offices:
                ClearanceRequest.objects.create(
                    student=student,
                    clearance=clearance,  # Link to main clearance record
                    office=office,
                    school_year=school_year,
                    semester=semester,
                    status='pending'
                )

            messages.success(request, f"Clearance requests created for {school_year} {semester} semester.")
            return redirect('view_clearance_details', clearance_id=clearance.id)

        # GET request - show form
        context = {
            'school_years': get_school_years(),
            'semesters': SEMESTER_CHOICES,
            'student': student
        }
        
        return render(request, 'core/create_clearance_requests.html', context)

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        logger.error(f"Error creating clearance requests for student {request.user.username}: {str(e)}", exc_info=True)
        return redirect('student_dashboard')

@login_required
def view_clearance_details(request, clearance_id):
    clearance = get_object_or_404(Clearance, id=clearance_id)
    
    # Check permissions based on user type
    if request.user.is_superuser:
        # Admins can view all clearances
        pass
    elif hasattr(request.user, 'programchair'):
        # Program chairs can only view their students' clearances
        if clearance.student.course.dean != request.user.programchair.dean:
            messages.error(request, "You don't have permission to view this clearance.")
            return redirect('program_chair_dashboard')
    elif hasattr(request.user, 'staff'):
        # Staff can only view clearances where they have pending/approved/denied requests
        if not ClearanceRequest.objects.filter(
            clearance=clearance,
            office=request.user.staff.office
        ).exists():
            messages.error(request, "You don't have permission to view this clearance.")
            return redirect('staff_dashboard')
    elif hasattr(request.user, 'student'):
        # Students can only view their own clearances
        if request.user.student != clearance.student:
            messages.error(request, "You don't have permission to view this clearance.")
            return redirect('student_dashboard')
    else:
        messages.error(request, "You don't have permission to view this clearance.")
        return redirect('home')
    
    # Get all clearance requests for this clearance
    clearance_requests = ClearanceRequest.objects.filter(
        clearance=clearance
    ).select_related('office', 'reviewed_by')
    
    context = {
        'clearance': clearance,
        'clearance_requests': clearance_requests,
        'user_type': 'admin' if request.user.is_superuser else (
            'program_chair' if hasattr(request.user, 'programchair') else (
            'staff' if hasattr(request.user, 'staff') else 'student'
        ))
    }
    return render(request, 'core/clearance_details.html', context)

@login_required
@require_POST
def update_profile_picture(request):
    try:
        if 'profile_picture' not in request.FILES:
            messages.error(request, 'No image file provided')
            return redirect('home')

        # Handle different user types
        if hasattr(request.user, 'student'):
            profile = request.user.student
        elif hasattr(request.user, 'programchair'):
            profile = request.user.programchair
        elif hasattr(request.user, 'staff'):  # Add staff handling
            profile = request.user.staff
        elif request.user.is_superuser:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
        else:
            messages.error(request, 'Invalid user type')
            return redirect('home')
        
        # Delete old profile picture if it exists
        if profile.profile_picture:
            profile.profile_picture.delete(save=False)
        
        # Save new profile picture
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()

        messages.success(request, 'Profile picture updated successfully')
        
        # Redirect based on user type
        if hasattr(request.user, 'student'):
            return redirect('student_profile')
        elif hasattr(request.user, 'programchair'):
            return redirect('program_chair_profile')
        elif hasattr(request.user, 'staff'):  # Add staff redirect
            return redirect('staff_profile')
        else:
            return redirect('admin_profile')

    except Exception as e:
        messages.error(request, f'Error updating profile picture: {str(e)}')
        return redirect('home')
@login_required
@user_passes_test(is_program_chair)
def program_chair_profile(request):
    """
    Display and manage program chair profile information.
    """
    try:
        program_chair = request.user.programchair
        return render(request, 'core/program_chair_profile.html', {
            'program_chair': program_chair
        })
    except ProgramChair.DoesNotExist:
        messages.error(request, "Program chair profile not found.")
        return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_profile(request):
    """
    Display and manage administrator profile information.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('home')
    
    # Get or create UserProfile for admin
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'core/admin_profile.html', {
        'admin_user': request.user,
        'profile': profile
    })

def get_current_school_year():
    current_date = datetime.now()
    # If current month is January-May, school year is previous year-current year
    # If current month is June-December, school year is current year-next year
    if current_date.month <= 5:
        return f"{current_date.year - 1}-{current_date.year}"
    else:
        return f"{current_date.year}-{current_date.year + 1}"

def get_current_semester():
    current_month = datetime.now().month
    # First semester: August-December
    # Second semester: January-May
    # Summer: June-July
    if 1 <= current_month <= 5:
        return "Second"
    elif 6 <= current_month <= 7:
        return "Summer"
    else:
        return "First"

@login_required
def staff_dashboard(request):
    try:
        staff = request.user.staff
        current_semester = get_current_semester()
        
        # Get recent requests for this staff's office
        recent_requests = ClearanceRequest.objects.filter(
            office=staff.office
        ).select_related(
            'student__user'
        ).order_by('-request_date')[:10]  # Get last 10 requests
        
        # Get counts for statistics
        pending_requests_count = ClearanceRequest.objects.filter(
            office=staff.office,
            status='pending'
        ).count()
        
        approved_today_count = ClearanceRequest.objects.filter(
            office=staff.office,
            status='approved',
            reviewed_date__date=timezone.now().date()
        ).count()
        
        total_processed = ClearanceRequest.objects.filter(
            office=staff.office,
            status__in=['approved', 'denied']
        ).count()

        context = {
            'current_semester': current_semester,
            'recent_requests': recent_requests,
            'pending_requests_count': pending_requests_count,
            'approved_today_count': approved_today_count,
            'total_processed': total_processed,
        }
        
        return render(request, 'core/staff_dashboard.html', context)
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('home')

@login_required
def staff_pending_requests(request):
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    school_year = request.GET.get('school_year', '')
    semester = request.GET.get('semester', '')
    sort_by = request.GET.get('sort', 'request_date')

    # Define semester choices
    SEMESTER_CHOICES = [
        ('First', 'First Semester'),
        ('Second', 'Second Semester'),
        ('Summer', 'Summer'),
    ]

    # Start with all pending requests for the staff's office
    pending_requests = ClearanceRequest.objects.filter(
        office=request.user.staff.office,
        status='pending'
    )

    # Apply filters
    if search_query:
        pending_requests = pending_requests.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )

    if school_year:
        pending_requests = pending_requests.filter(school_year=school_year)

    if semester:
        pending_requests = pending_requests.filter(semester=semester)

    # Apply sorting
    if sort_by == 'student_name':
        pending_requests = pending_requests.order_by('student__user__last_name', 'student__user__first_name')
    elif sort_by == 'course':
        pending_requests = pending_requests.order_by('student__course__code')
    else:  # default to request_date
        pending_requests = pending_requests.order_by('-request_date')

    # Get unique school years for the filter dropdown
    school_years = ClearanceRequest.objects.values_list('school_year', flat=True).distinct()

    context = {
        'pending_requests': pending_requests,
        'school_years': school_years,
        'SEMESTER_CHOICES': SEMESTER_CHOICES,
        'current_filters': {
            'search': search_query,
            'school_year': school_year,
            'semester': semester,
            'sort': sort_by,
        },
        'office': request.user.staff.office,
        'school_year': get_current_school_year(),
        'current_semester': get_current_semester(),
    }

    return render(request, 'core/staff_pending_requests.html', context)
@login_required
@require_POST
def approve_clearance_request(request, request_id):
    """Handle approval of a clearance request."""
    try:
        staff = request.user.staff
        clearance_request = get_object_or_404(ClearanceRequest, id=request_id)
        
        # Check if staff member belongs to the office of the clearance request
        if staff.office != clearance_request.office:
            messages.error(
                request,
                f"You don't have permission to handle clearance requests for {clearance_request.office.name}"
            )
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

        # Check if request is already processed
        if clearance_request.status != 'pending':
            messages.error(request, 'This request has already been processed')
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))
        
        # Approve the request
        clearance_request.approve(staff)
        
        # Update the student's overall clearance status
        clearance = Clearance.objects.get(
            student=clearance_request.student,
            school_year=clearance_request.school_year,
            semester=clearance_request.semester
        )
        clearance.check_clearance()
        
        messages.success(
            request,
            f'Successfully approved clearance request for {clearance_request.student.full_name}'
        )
        
    except Staff.DoesNotExist:
        messages.error(request, 'Staff access required')
    except Exception as e:
        messages.error(request, f'Error processing request: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

@login_required
@require_POST
def deny_clearance_request(request, request_id):
    """Handle denial of a clearance request."""
    try:
        staff = request.user.staff
        clearance_request = get_object_or_404(ClearanceRequest, id=request_id)
        
        # Check if staff member belongs to the office of the clearance request
        if staff.office != clearance_request.office:
            messages.error(
                request,
                f"You don't have permission to handle clearance requests for {clearance_request.office.name}"
            )
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

        # Check if request is already processed
        if clearance_request.status != 'pending':
            messages.error(request, 'This request has already been processed')
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))
        
        # Get reason from either JSON or POST data
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            reason = data.get('reason', '')
        else:
            reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'A reason must be provided for denial')
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))
        
        # Deny the request
        clearance_request.deny(staff, reason)
        
        # Update the student's overall clearance status
        clearance = Clearance.objects.get(
            student=clearance_request.student,
            school_year=clearance_request.school_year,
            semester=clearance_request.semester
        )
        clearance.check_clearance()
        
        messages.success(
            request,
            f'Successfully denied clearance request for {clearance_request.student.full_name}'
        )
        
    except Staff.DoesNotExist:
        messages.error(request, 'Staff access required')
    except Exception as e:
        messages.error(request, f'Error processing request: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

@login_required
def staff_clearance_history(request):
    """View for staff to see history of processed clearance requests."""
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        return redirect('login')

    # Get filter parameters from request
    status = request.GET.get('status', '')
    school_year = request.GET.get('school_year', '')
    semester = request.GET.get('semester', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    clearance_requests = ClearanceRequest.objects.filter(
        office=staff.office,
        status__in=['approved', 'denied']
    ).select_related(
        'student',
        'student__user',
        'student__course',
        'reviewed_by'
    ).order_by('-reviewed_date')

    # Apply filters
    if status:
        clearance_requests = clearance_requests.filter(status=status)
    if school_year:
        clearance_requests = clearance_requests.filter(clearance__school_year=school_year)
    if semester:
        clearance_requests = clearance_requests.filter(clearance__semester=semester)
    if search_query:
        clearance_requests = clearance_requests.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(clearance_requests, 10)  # Show 10 requests per page
    page = request.GET.get('page')
    try:
        clearance_requests = paginator.page(page)
    except PageNotAnInteger:
        clearance_requests = paginator.page(1)
    except EmptyPage:
        clearance_requests = paginator.page(paginator.num_pages)

    # Get list of school years for filter dropdown
    current_year = timezone.now().year
    school_years = [f"{year}-{year + 1}" for year in range(current_year - 2, current_year + 1)]

    context = {
        'clearance_requests': clearance_requests,
        'school_years': school_years,
        'current_filters': {
            'status': status,
            'school_year': school_year,
            'semester': semester,
            'search': search_query,
        },
        'office': staff.office,
        'SEMESTER_CHOICES': SEMESTER_CHOICES,
    }

    return render(request, 'core/staff_clearance_history.html', context)  # Updated path
@login_required
def staff_profile(request):
    """
    Display and manage staff profile information.
    """
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('home')

    if request.method == 'POST':
        # Handle profile updates
        if 'update_role' in request.POST:
            new_role = request.POST.get('role')
            staff.role = new_role
            staff.save()
            messages.success(request, 'Role updated successfully')
            return redirect('staff_profile')

    context = {
        'staff': staff,
        'office': staff.office,
        'user': request.user,
        'is_dormitory_owner': staff.is_dormitory_owner,
        'assigned_students': staff.students_dorm.all() if staff.is_dormitory_owner else None,
    }

    return render(request, 'core/staff_profile.html', context)  # Updated template path

@login_required
def view_request(request, request_id):
    try:
        staff = request.user.staff
        request_obj = get_object_or_404(ClearanceRequest, id=request_id, office=staff.office)
        
        context = {
            'request_obj': request_obj,
        }
        
        return render(request, 'core/staff_view_request.html', context)
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('home')

@login_required
def print_permit(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    context = {
        'student': student,
        'logo_url': 'images/logo.png',  # Adjust path as needed
    }
    return render(request, 'core/print_permit.html', context)

def export_clearances_excel(request):
    # Create a new workbook and select the active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Clearance Report"

    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="44B78B", end_color="44B78B", fill_type="solid")
    
    # Write headers
    headers = [
        'Student ID',
        'Student Name',
        'Course',
        'Year Level',
        'School Year',
        'Semester',
        'Clearance Status',
        'Date Cleared'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[cell.column_letter].width = 15

    # Get all clearances
    clearances = Clearance.objects.select_related(
        'student', 
        'student__course'
    ).order_by('-school_year', '-semester', 'student__student_id')

    # Write data
    for row, clearance in enumerate(clearances, 2):
        student = clearance.student
        ws.cell(row=row, column=1, value=student.student_id)
        ws.cell(row=row, column=2, value=student.full_name)
        ws.cell(row=row, column=3, value=student.course.code)
        ws.cell(row=row, column=4, value=student.year_level)
        ws.cell(row=row, column=5, value=clearance.school_year)
        ws.cell(row=row, column=6, value=dict(SEMESTER_CHOICES)[clearance.semester])
        ws.cell(row=row, column=7, value="Cleared" if clearance.is_cleared else "Pending")
        
        if clearance.cleared_date:
            cleared_date = clearance.cleared_date.strftime("%Y-%m-%d")
            ws.cell(row=row, column=8, value=cleared_date)
        else:
            ws.cell(row=row, column=8, value="N/A")

    # Apply styles to data cells
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.alignment = Alignment(horizontal='center')

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=clearance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    # Save the workbook to the response
    wb.save(response)
    return response
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_students(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        action = request.POST.get('action')
        
        if action == 'approve':
            try:
                student = Student.objects.get(id=student_id)
                student.is_approved = True
                student.approval_date = timezone.now()
                student.approval_admin = request.user
                student.save()
                
                # Also activate the user account
                student.user.is_active = True
                student.user.save()
                
                messages.success(request, f'Student {student.user.get_full_name()} has been approved.')
            except Student.DoesNotExist:
                messages.error(request, 'Student not found.')
    
    # Get all students with related user and course data
    students = Student.objects.select_related('user', 'course').all()
    courses = Course.objects.all()
    
    context = {
        'students': students,
        'courses': courses,
    }
    return render(request, 'admin/students.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_staff(request):
    """View for managing staff members in admin dashboard."""
    # Get all staff members with related user and office data
    staff = Staff.objects.select_related(
        'user',
        'office'
    ).all().order_by('office__name', 'user__first_name')

    # Calculate statistics
    total_staff = staff.count()
    active_staff = staff.filter(user__is_active=True).count()
    total_offices = Office.objects.count()
    staff_by_office = Office.objects.annotate(
        staff_count=Count('staff')
    )

    context = {
        'staff': staff,
        'statistics': {
            'total_staff': total_staff,
            'active_staff': active_staff,
            'total_offices': total_offices,
            'staff_by_office': staff_by_office,
        }
    }
    
    return render(request, 'admin/staff.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_staff_add(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        office_id = request.POST.get('office')
        role = request.POST.get('role')
        is_dormitory_owner = request.POST.get('is_dormitory_owner') == 'on'

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )

            # Create staff profile
            Staff.objects.create(
                user=user,
                office_id=office_id,
                role=role,
                is_dormitory_owner=is_dormitory_owner
            )

            messages.success(request, 'Staff member added successfully.')
            return redirect('admin_staff')

        except Exception as e:
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error adding staff member: {str(e)}')
            return redirect('admin_staff_add')

    # GET request - show form
    offices = Office.objects.all()
    context = {
        'offices': offices,
    }
    return render(request, 'admin/staff_add.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_staff_edit(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    
    if request.method == 'POST':
        try:
            # Update user information
            staff.user.username = request.POST.get('username')
            staff.user.email = request.POST.get('email')
            staff.user.first_name = request.POST.get('first_name')
            staff.user.last_name = request.POST.get('last_name')
            
            # Update password if provided
            new_password = request.POST.get('password')
            if new_password:
                staff.user.set_password(new_password)
            
            staff.user.is_active = request.POST.get('is_active') == 'on'
            staff.user.save()
            
            # Update staff information
            staff.office_id = request.POST.get('office')
            staff.role = request.POST.get('role')
            staff.is_dormitory_owner = request.POST.get('is_dormitory_owner') == 'on'
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                staff.profile_picture = request.FILES['profile_picture']
            
            staff.save()
            
            messages.success(request, 'Staff member updated successfully.')
            return redirect('admin_staff')
            
        except Exception as e:
            messages.error(request, f'Error updating staff member: {str(e)}')
            return redirect('admin_staff_edit', staff_id=staff_id)
    
    # GET request - show form
    offices = Office.objects.all()
    context = {
        'staff_member': staff,
        'offices': offices,
    }
    return render(request, 'admin/staff_edit.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_settings(request):
    if request.method == 'POST':
        # Handle settings updates here
        pass
    
    context = {
        'current_school_year': timezone.now().year,
        'current_semester': get_current_semester(),
        # Add other settings as needed
    }
    return render(request, 'admin/settings.html', context)

@login_required
def request_again(request, request_id):
    """
    Allow students to request clearance again after denial
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    try:
        # Get the original request
        clearance_request = get_object_or_404(ClearanceRequest, id=request_id)
        
        # Security checks
        if clearance_request.student.user != request.user:
            messages.error(request, "You don't have permission to perform this action.")
            return redirect('student_dashboard')
            
        if clearance_request.status != 'denied':
            messages.error(request, "You can only request again for denied clearances.")
            return redirect('clearance_details', clearance_id=clearance_request.clearance.id)
        
        # Update the existing request instead of creating a new one
        clearance_request.status = 'pending'
        clearance_request.reviewed_date = None
        clearance_request.reviewed_by = None
        clearance_request.notes = None
        clearance_request.request_date = timezone.now()
        clearance_request.save()
        
        messages.success(
            request, 
            f"Successfully resubmitted clearance request for {clearance_request.office.name}"
        )
        
    except Exception as e:
        messages.error(request, f"Error processing request: {str(e)}")
    
    return redirect('clearance_details', clearance_id=clearance_request.clearance.id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def get_dean_details(request, dean_id):
    try:
        dean = Dean.objects.get(id=dean_id)
        data = {
            'name': dean.name,
            'description': dean.description,
            'logo_url': dean.logo.url if dean.logo else None
        }
        return JsonResponse(data)
    except Dean.DoesNotExist:
        return JsonResponse({'error': 'Dean not found'}, status=404)

def office_detail_api(request, office_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    office = get_object_or_404(Office, id=office_id)
    
    # Only include the basic fields that definitely exist
    data = {
        'name': office.name,
    }
    
    # Optionally add description if it exists
    if hasattr(office, 'description'):
        data['description'] = office.description
    
    return JsonResponse(data)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def get_user_details(request, user_id):
    try:
        student = Student.objects.select_related('user', 'course').get(user_id=user_id)
        data = {
            'full_name': student.user.get_full_name(),
            'student_id': student.student_id,
            'course': student.course.name if student.course else 'N/A',
            'date_joined': student.user.date_joined.strftime('%B %d, %Y'),
            'email': student.user.email,
        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_staff(request, staff_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        staff = Staff.objects.get(id=staff_id)
        user = staff.user
        staff.delete()
        user.delete()  # This will cascade delete the staff profile and user
        return JsonResponse({'success': True})
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'Staff not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def approve_student(request, student_id):
    try:
        student = Student.objects.get(id=student_id)
        student.approve_student(request.user)
        return JsonResponse({'success': True})
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_student_details(request, student_id):
    try:
        student = Student.objects.select_related('user', 'course').get(id=student_id)
        data = {
            'id': student.id,
            'full_name': f"{student.user.first_name} {student.user.last_name}",
            'student_id': student.student_id,
            'email': student.user.email,
            'course': student.course.code,
            'year_level': student.year_level,
            'date_applied': student.user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'is_boarder': student.is_boarder,
            'profile_picture_url': student.get_profile_picture_url(),
        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def reject_student(request, student_id):
    try:
        data = json.loads(request.body)
        reason = data.get('reason')
        if not reason:
            return JsonResponse({'error': 'Rejection reason is required'}, status=400)
        
        student = Student.objects.get(id=student_id)
        student.reject_student(request.user, reason)
        return JsonResponse({'success': True})
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
