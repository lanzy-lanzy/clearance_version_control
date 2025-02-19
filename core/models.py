from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver 
from django.db.models.signals import post_save
from django.utils import timezone
import os
from django.conf import settings
from django.templatetags.static import static

SEMESTER_CHOICES = [
    ('1ST', 'First Semester'),
    ('2ND', 'Second Semester'),
    ('SUM', 'Summer')
]

class Dean(models.Model):
    """
    Represents a dean (or school head) who can be assigned to courses.
    This model can be managed dynamically via Django Admin.
    """
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='dean_logos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)  # e.g., BSIT, BPED
    name = models.CharField(max_length=100)  # e.g., Bachelor of Science in Information Technology
    dean = models.ForeignKey(Dean, on_delete=models.CASCADE, related_name='courses')
    is_active = models.BooleanField(default=True)  # To mark if course is currently offered
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

class Office(models.Model):
    """Represents different offices handling clearance."""
    OFFICE_TYPES = [
        ('SET', 'SET'),
        ('STE', 'STE'),
        ('SOCJE', 'SOCJE'),
        ('SAFES', 'SAFES'),
        ('SSB SET', 'SSB SET'),
        ('SSB STE', 'SSB STE'),
        ('SSB SOCJE', 'SSB SOCJE'),
        ('SSB SAFES', 'SSB SAFES'),
        ('OTHER', 'OTHER'),
    ]
    name = models.CharField(max_length=255, unique=True)
    office_type = models.CharField(max_length=50, choices=OFFICE_TYPES, default='OTHER')
    # New field: associate an office to a specific program (dean)
    affiliated_dean = models.ForeignKey(Dean, on_delete=models.SET_NULL, null=True, blank=True, help_text="Associate this office with a specific dean (program)")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Staff(models.Model):
    """Represents staff members assigned to different offices."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='staff')
    role = models.CharField(max_length=100)
    is_dormitory_owner = models.BooleanField(default=False)  # For dormitory (BH) manager
    profile_picture = models.ImageField(
        upload_to='staff_profiles/',
        null=True,
        blank=True
    )

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return static('img/default-profile.png')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.office.name}"

class ProgramChair(models.Model):
    """Represents a program chair (dean) user responsible for final clearance approval."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dean = models.ForeignKey(Dean, on_delete=models.SET_NULL, null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='program_chair_profiles/',
        null=True,
        blank=True
    )

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return static('img/default-profile.png')

    @property
    def is_program_chair(self):
        return True

class UserProfile(models.Model):
    """Represents additional profile information for admin users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(
        upload_to='admin_profiles/',
        null=True,
        blank=True
    )

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return static('img/default-profile.png')

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Add a signal to create UserProfile automatically when a superuser is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.is_superuser:
        if not hasattr(instance, 'userprofile'):
            UserProfile.objects.create(user=instance)

class Student(models.Model):
    """Represents students requesting clearance."""
    student_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    year_level = models.IntegerField()
    is_boarder = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    program_chair = models.ForeignKey(ProgramChair, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    dormitory_owner = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="students_dorm", limit_choices_to={'is_dormitory_owner': True})
    is_approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_students')
    profile_picture = models.ImageField(
        upload_to='student_profiles/',
        null=True,
        blank=True
    )

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return static('img/default-profile.png')

    @property
    def full_name(self):
        return self.user.get_full_name()

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"
    
    def approve_student(self, admin_user):
        """Approve a student's registration."""
        self.is_approved = True
        self.approval_date = timezone.now()
        self.approval_admin = admin_user
        self.save()

    def create_clearance_requests(self, school_year, semester):
        """
        Creates clearance requests for a specific semester and school year.
        """
        from core.models import ClearanceRequest, Clearance  # to avoid circular import
        
        # Base offices that all students must pass
        base_offices = [
            'OSA', 'DSA', 'SSC', 'LIBRARY', 'LABORATORY',
            'ACCOUNTING OFFICE', 'REGISTRAR OFFICE', 'Guidance Office'
        ]

        # Add dean-specific offices based on student's program chair
        # Note: Dean offices are not included in clearance requests
        # They are only for permit printing purposes
        if self.program_chair and self.program_chair.dean:
            dean_name = self.program_chair.dean.name
            if 'SET' in dean_name:
                # For SET students, add SSB SET to their clearance requirements
                base_offices.append('SSB SET')
            elif 'STE' in dean_name:
                # For STE students, add SSB STE to their clearance requirements
                base_offices.append('SSB STE')
            elif 'SOCJE' in dean_name:
                # For SOCJE students, add SSB SOCJE to their clearance requirements
                base_offices.append('SSB SOCJE')
            elif 'SAFES' in dean_name:
                # For SAFES students, add SSB SAFES to their clearance requirements
                base_offices.append('SSB SAFES')

        required_offices = Office.objects.filter(name__in=base_offices)
        
        # Add dormitory clearance if student is a boarder
        if self.is_boarder:
            try:
                dorm_office = Office.objects.get(name='DORMITORY')
                required_offices = list(required_offices)
                required_offices.append(dorm_office)
            except Office.DoesNotExist:
                print("Dormitory office not found.")

        # Create or get clearance record for this semester
        clearance, _ = Clearance.objects.get_or_create(
            student=self,
            school_year=school_year,
            semester=semester,
            defaults={'is_cleared': False}
        )

        # Create clearance requests for each required office
        for office in required_offices:
            ClearanceRequest.objects.get_or_create(
                student=self,
                office=office,
                school_year=school_year,
                semester=semester,
                defaults={'status': 'pending'}
            )

    def has_complete_clearance(self):
        """Check if student has completed all clearance requests for the latest clearance."""
        latest_clearance = self.clearances.order_by('-school_year', '-semester').first()
        if not latest_clearance:
            return False
        return latest_clearance.is_cleared

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    # Automatic student profile creation is disabled as it is managed in view logic.
    pass

class ClearanceRequest(models.Model):
    """Represents clearance requests for students dynamically per office."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='clearance_requests')
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='clearance_requests')
    clearance = models.ForeignKey('Clearance', on_delete=models.CASCADE, related_name='requests')  # Fixed line
    school_year = models.CharField(max_length=9)  # Format: 2023-2024
    semester = models.CharField(max_length=3, choices=SEMESTER_CHOICES)
    status_choices = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='pending')
    remarks = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True, help_text="Reasons for pending or denied clearance.")

    class Meta:
        unique_together = ['student', 'office', 'school_year', 'semester']
        ordering = ['-school_year', '-semester', '-request_date']

    def __str__(self):
        return f"{self.student} - {self.office} - {self.school_year} {self.get_semester_display()} ({self.status})"

    def validate_staff_permission(self, staff):
        """Validates if a staff member can handle this clearance request."""
        if staff.office != self.office:
            raise PermissionError(
                f"You don't have permission to handle clearance requests for {self.office.name}. "
                f"You can only handle requests for {staff.office.name}."
            )

        # Special handling for dormitory clearances
        if self.office.name == "DORMITORY":
            if not staff.is_dormitory_owner:
                raise PermissionError("Only dormitory owners can handle dormitory clearances.")
            if self.student.dormitory_owner != staff:
                raise PermissionError("You can only handle clearances for your assigned students.")

        # Special handling for SSB offices
        if self.office.name.startswith('SSB'):
            student_dean = self.student.course.dean
            if self.office.affiliated_dean != student_dean:
                raise PermissionError(
                    "You can only handle SSB clearances for students from your school."
                )

    def approve(self, staff):
        """Approve a clearance request."""
        self.validate_staff_permission(staff)
        
        self.status = "approved"
        self.reviewed_by = staff
        self.reviewed_date = timezone.now()
        self.save()

        # Check if all clearances for this semester are complete
        clearance = Clearance.objects.get(
            student=self.student,
            school_year=self.school_year,
            semester=self.semester
        )
        clearance.check_clearance()

    def deny(self, staff, reason):
        """Deny a clearance request with a reason."""
        if not reason:
            raise ValueError("A reason must be provided when denying a clearance request.")
        
        self.validate_staff_permission(staff)
        
        self.status = "denied"
        self.reviewed_by = staff
        self.notes = reason
        self.reviewed_date = timezone.now()
        self.save()

    def can_be_handled_by(self, staff):
        """Check if a staff member can handle this clearance request."""
        try:
            self.validate_staff_permission(staff)
            return True
        except PermissionError:
            return False

class Clearance(models.Model):
    """Represents the final clearance status of a student."""
    SEMESTER_CHOICES = SEMESTER_CHOICES  # Reference the module-level choices
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='clearances')
    school_year = models.CharField(max_length=9)  # Format: 2023-2024
    semester = models.CharField(max_length=3, choices=SEMESTER_CHOICES)
    is_cleared = models.BooleanField(default=False)
    cleared_date = models.DateTimeField(null=True, blank=True)
    program_chair_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'school_year', 'semester']
        ordering = ['-school_year', '-semester']

    def check_clearance(self):
        # Check clearance requests for this specific semester and school year
        pending_requests = self.student.clearance_requests.filter(
            school_year=self.school_year,
            semester=self.semester,
            status='pending'
        ).exists()
        denied_requests = self.student.clearance_requests.filter(
            school_year=self.school_year,
            semester=self.semester,
            status='denied'
        ).exists()
        
        if not pending_requests and not denied_requests:
            self.is_cleared = True
            self.cleared_date = timezone.now()
            self.save()

    def unlock_permit(self):
        if self.is_cleared:
            self.program_chair_approved = True
            self.save()

    def __str__(self):
        status = 'Cleared' if self.is_cleared else 'Not Cleared'
        permit_status = 'Permit Unlocked' if self.program_chair_approved else 'Permit Locked'
        return f"{self.student} - {self.school_year} {self.get_semester_display()} - {status} - {permit_status}"
