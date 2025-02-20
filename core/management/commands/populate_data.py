from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
import random
from core.models import (
    Dean, Course, Office, Staff, Student, 
    ProgramChair, Clearance, ClearanceRequest
)


class Command(BaseCommand):
    help = 'Populate database with initial sample data including completed clearance requests'

    def handle(self, *args, **kwargs):
        # Get or set current school year and semester
        current_year = timezone.now().year
        school_year = f"{current_year}-{current_year + 1}"
        semester = "1ST"  # You can modify this as needed: "1ST", "2ND", or "SUM"

        self.stdout.write(self.style.SUCCESS("\nCreating Admin User..."))
        # Create superuser/admin account
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "User"
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user"))
        else:
            self.stdout.write(self.style.WARNING("Admin user already exists"))

        # Create Deans
        self.stdout.write(self.style.SUCCESS("\nCreating Deans..."))
        deans_data = [
            {
                "name": "SET DEAN",
                "description": "School of Engineering and Technology"
            },
            {
                "name": "STE DEAN",
                "description": "School of Teacher Education"
            },
            {
                "name": "SOCJE DEAN",
                "description": "School of Criminal Justice Education"
            },
            {
                "name": "SAFES DEAN",
                "description": "School of Agriculture, Forestry and Environmental Sciences"
            }
        ]

        deans = []
        for dean_data in deans_data:
            dean, created = Dean.objects.get_or_create(
                name=dean_data["name"],
                defaults={"description": dean_data["description"]}
            )
            deans.append(dean)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} dean: {dean.name}"))

        # Create Courses
        self.stdout.write(self.style.SUCCESS("\nCreating Courses..."))
        courses_data = [
            {"code": "BSIT", "name": "Bachelor of Science in Information Technology", "dean": deans[0]},
            {"code": "BSCS", "name": "Bachelor of Science in Computer Science", "dean": deans[0]},
            {"code": "BEED", "name": "Bachelor of Elementary Education", "dean": deans[1]},
            {"code": "BSED", "name": "Bachelor of Secondary Education", "dean": deans[1]},
            {"code": "BSCrim", "name": "Bachelor of Science in Criminology", "dean": deans[2]},
            {"code": "BSAF", "name": "Bachelor of Science in Agroforestry", "dean": deans[3]},
            {"code": "BSA", "name": "Bachelor of Science in Agriculture", "dean": deans[3]}
        ]

        courses = []
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                code=course_data["code"],
                defaults={
                    "name": course_data["name"],
                    "dean": course_data["dean"]
                }
            )
            courses.append(course)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} course: {course.code}"))

        self.stdout.write(self.style.SUCCESS("\nCreating Offices..."))
        self.create_offices()

        # Get the dormitory office reference after creation
        dormitory_office = Office.objects.get(name="DORMITORY")

        self.stdout.write(self.style.SUCCESS("\nCreating Staff Members..."))
        staff_data = [
            {
                "username": "osa_staff",
                "password": "staff123",
                "first_name": "OSA",
                "last_name": "Staff",
                "email": "osa.staff@example.com",
                "office": "OSA",
                "role": "OSA Officer",
                "is_active": True  # Make sure staff is active
            },
            {
                "username": "library_staff",
                "password": "staff123",
                "first_name": "Library",
                "last_name": "Staff",
                "email": "library.staff@example.com",
                "office": "LIBRARY",
                "role": "Librarian"
            },
            {
                "username": "accounting_staff",
                "password": "staff123",
                "first_name": "Accounting",
                "last_name": "Staff",
                "email": "accounting.staff@example.com",
                "office": "ACCOUNTING OFFICE",
                "role": "Accounting Officer"
            },
            {
                "username": "registrar_staff",
                "password": "staff123",
                "first_name": "Registrar",
                "last_name": "Staff",
                "email": "registrar.staff@example.com",
                "office": "REGISTRAR OFFICE",
                "role": "Registrar Officer"
            },
            {
                "username": "guidance_staff",
                "password": "staff123",
                "first_name": "Guidance",
                "last_name": "Staff",
                "email": "guidance.staff@example.com",
                "office": "Guidance Office",
                "role": "Guidance Counselor"
            },
            {
                "username": "laboratory_staff",
                "password": "staff123",
                "first_name": "Laboratory",
                "last_name": "Staff",
                "email": "lab.staff@example.com",
                "office": "LABORATORY",
                "role": "Laboratory Technician"
            }
        ]

        for staff_info in staff_data:
            # Create User
            user, created = User.objects.get_or_create(
                username=staff_info["username"],
                defaults={
                    "first_name": staff_info["first_name"],
                    "last_name": staff_info["last_name"],
                    "email": staff_info["email"],
                    "is_active": True
                }
            )
            if created:
                user.set_password(staff_info["password"])
                user.save()
            else:
                # Update existing user's password if needed
                user.set_password(staff_info["password"])
                user.save()

            # Get office
            office = Office.objects.get(name=staff_info["office"])

            # Create Staff
            staff, created = Staff.objects.get_or_create(
                user=user,
                defaults={
                    "office": office,
                    "role": staff_info["role"],
                    "is_dormitory_owner": False
                }
            )

            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Found'} staff member: {staff.user.get_full_name()} ({staff.office.name})"
            ))

        self.stdout.write(self.style.SUCCESS("\nCreating BH Owners..."))
        # Create multiple BH owners
        bh_owners_data = [
            {
                "username": "bh_owner1",
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@bh.com",
                "role": "BH Owner 1"
            },
            {
                "username": "bh_owner2",
                "first_name": "Mary",
                "last_name": "Johnson",
                "email": "mary.johnson@bh.com",
                "role": "BH Owner 2"
            }
        ]

        bh_owners = []
        for owner_data in bh_owners_data:
            user, created = User.objects.get_or_create(
                username=owner_data["username"],
                defaults={
                    "first_name": owner_data["first_name"],
                    "last_name": owner_data["last_name"],
                    "email": owner_data["email"],
                    "is_active": True
                }
            )
            if created:
                user.set_password("bhowner123")
                user.save()

            staff, created = Staff.objects.get_or_create(
                user=user,
                defaults={
                    "office": dormitory_office,
                    "role": owner_data["role"],
                    "is_dormitory_owner": True
                }
            )
            bh_owners.append(staff)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} BH Owner: {staff.user.get_full_name()}"))

        self.stdout.write(self.style.SUCCESS("\nCreating Program Chairs..."))
        program_chair_data = [
            {
                "username": "pc_set",
                "first_name": "Zenon A.",
                "last_name": "Matos, MIT",
                "email": "pc_set@example.com",
                "dean": deans[0]  # SET Dean
            },
            {
                "username": "pc_ste",
                "first_name": "Star Clyde",
                "last_name": "Sebial, Ph.D",
                "email": "pc_ste@example.com",
                "dean": deans[1]  # STE Dean
            },
            {
                "username": "pc_socje",
                "first_name": "Mark E.",
                "last_name": "Patalinghug, Ph.D",
                "email": "pc_socje@example.com",
                "dean": deans[2]  # SOCJE Dean
            },
            {
                "username": "pc_safes",
                "first_name": "Teonita Y.",
                "last_name": "Velasco, Ed.D",
                "email": "pc_safes@example.com",
                "dean": deans[3]  # SAFES Dean
            }
        ]

        program_chairs = []
        for pc_info in program_chair_data:
            user, created = User.objects.get_or_create(
                username=pc_info["username"],
                defaults={
                    "first_name": pc_info["first_name"],
                    "last_name": pc_info["last_name"],
                    "email": pc_info["email"],
                    "is_active": True,
                }
            )
            if created:
                user.set_password("pc_pass123")
                user.save()

            # Create the Program Chair entry
            pc, created = ProgramChair.objects.get_or_create(
                user=user,
                defaults={
                    "dean": pc_info["dean"]
                }
            )
            program_chairs.append(pc)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} Program Chair: {pc.user.get_full_name()}"))

        self.stdout.write(self.style.SUCCESS("\nCreating Sample Students with Completed Clearances..."))
        students_data = [
            {
                "username": "set_student1",
                "password": "student123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@student.edu",
                "student_id": "2023-SET-001",
                "course": Course.objects.get(code="BSIT"),
                "year_level": 3,
                "is_boarder": True,
                "is_approved": True
            },
            {
                "username": "ste_student1",
                "password": "student123",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@student.edu",
                "student_id": "2023-STE-001",
                "course": Course.objects.get(code="BSED"),
                "year_level": 2,
                "is_boarder": True,
                "is_approved": False,
                "rejection_reason": "Incomplete requirements"
            },
            {
                "username": "cleared_student",
                "password": "student123",
                "first_name": "Mark",
                "last_name": "Wilson",
                "email": "mark.wilson@student.edu",
                "student_id": "2023-SET-002",
                "course": Course.objects.get(code="BSIT"),
                "year_level": 3,
                "is_boarder": False,
                "is_approved": True
            }
        ]

        for student_info in students_data:
            try:
                # Create User
                user, created = User.objects.get_or_create(
                    username=student_info["username"],
                    defaults={
                        "first_name": student_info["first_name"],
                        "last_name": student_info["last_name"],
                        "email": student_info["email"],
                        "is_active": student_info["is_approved"]
                    }
                )
                if created:
                    user.set_password(student_info["password"])
                    user.save()

                # Create Student
                student, created = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        "student_id": student_info["student_id"],
                        "course": student_info["course"],
                        "year_level": student_info["year_level"],
                        "is_boarder": student_info["is_boarder"],
                        "is_approved": student_info["is_approved"],
                        "rejection_reason": student_info.get("rejection_reason", None)
                    }
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created student: {student.user.get_full_name()} ({student.student_id})"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error creating student {student_info['username']}: {str(e)}"
                    )
                )

        self.stdout.write(self.style.SUCCESS("\nData population completed successfully!"))

    def create_offices(self):
        created_count = 0
        offices = [
            # Base offices that all students must pass
            {
                "name": "OSA",
                "description": "Office of Student Affairs",
                "office_type": "OTHER"
            },
            {
                "name": "DSA",
                "description": "Dean of Student Affairs",
                "office_type": "OTHER"
            },
            {
                "name": "SSC",
                "description": "Student Services Center",
                "office_type": "OTHER"
            },
            {
                "name": "LIBRARY",
                "description": "University Library",
                "office_type": "OTHER"
            },
            {
                "name": "LABORATORY",
                "description": "Laboratory Services",
                "office_type": "OTHER"
            },
            {
                "name": "ACCOUNTING OFFICE",
                "description": "University Accounting Office",
                "office_type": "OTHER"
            },
            {
                "name": "REGISTRAR OFFICE",
                "description": "University Registrar",
                "office_type": "OTHER"
            },
            {
                "name": "Guidance Office",
                "description": "University Guidance Office",
                "office_type": "OTHER"
            },
            {
                "name": "DORMITORY",
                "description": "University Dormitory",
                "office_type": "OTHER"
            },
            # School-specific SSB offices
            {
                "name": "SSB SET",
                "description": "Student Services Bureau - School of Engineering and Technology",
                "office_type": "SET"
            },
            {
                "name": "SSB STE",
                "description": "Student Services Bureau - School of Teacher Education",
                "office_type": "STE"
            },
            {
                "name": "SSB SOCJE",
                "description": "Student Services Bureau - School of Criminal Justice Education",
                "office_type": "SOCJE"
            },
            {
                "name": "SSB SAFES",
                "description": "Student Services Bureau - School of Agriculture, Forestry and Environmental Sciences",
                "office_type": "SAFES"
            }
        ]

        # Get all deans for office affiliation
        deans = {dean.name: dean for dean in Dean.objects.all()}

        for office_data in offices:
            # Determine the affiliated dean based on office type
            affiliated_dean = None
            if office_data["office_type"] in ["SET", "STE", "SOCJE", "SAFES"]:
                dean_name = f"{office_data['office_type']} DEAN"
                affiliated_dean = deans.get(dean_name)

            office, created = Office.objects.get_or_create(
                name=office_data["name"],
                defaults={
                    "description": office_data["description"],
                    "office_type": office_data["office_type"],
                    "affiliated_dean": affiliated_dean
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created office: {office.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Office exists: {office.name}"))

        self.stdout.write(self.style.SUCCESS(f"\nCreated {created_count} new offices"))

    def create_student_clearances(self, student, school_year, semester):
        try:
            # First create the main clearance record
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

            # Create clearance requests for each office
            for office in required_offices:
                ClearanceRequest.objects.create(
                    student=student,
                    office=office,
                    clearance=clearance,  # Add the clearance reference
                    school_year=school_year,
                    semester=semester,
                    status='pending'
                )

            return clearance

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error creating clearance for student {student.user.username}: {str(e)}"
                )
            )
            return None

    def create_students(self, school_year, semester):
        self.stdout.write(self.style.SUCCESS("\nCreating Students..."))
        
        # Example student data
        students_data = [
            {
                "username": "set_student1",
                "password": "student123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "student_id": "2023-0001",
                "course": "BSIT",
                "year_level": "1",
                "is_boarder": False
            },
            {
                "username": "ste_student1",
                "password": "student123",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com",
                "student_id": "2023-0002",
                "course": "BEED",
                "year_level": "2",
                "is_boarder": True
            }
            # Add more student data as needed
        ]

        for student_data in students_data:
            try:
                # Create user
                user = User.objects.create_user(
                    username=student_data["username"],
                    password=student_data["password"],
                    email=student_data["email"],
                    first_name=student_data["first_name"],
                    last_name=student_data["last_name"],
                    is_active=True
                )

                # Get course
                course = Course.objects.get(code=student_data["course"])
                
                # Get program chair
                program_chair = ProgramChair.objects.filter(dean=course.dean).first()

                # Create student
                student = Student.objects.create(
                    user=user,
                    student_id=student_data["student_id"],
                    course=course,
                    program_chair=program_chair,
                    year_level=student_data["year_level"],
                    is_boarder=student_data["is_boarder"],
                    is_approved=True
                )

                # Create clearance records
                self.create_student_clearances(student, school_year, semester)

                self.stdout.write(self.style.SUCCESS(f"Created student: {student.user.username}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating student {student_data['username']}: {str(e)}"))
                # Clean up if user was created
                if 'user' in locals():
                    user.delete()
