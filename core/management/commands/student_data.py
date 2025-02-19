from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Office, Staff, Student, ClearanceRequest, Clearance

class Command(BaseCommand):
    help = 'Populate database with initial sample student data'

    def handle(self, *args, **kwargs):
        # Create sample students
        students_data = [
            {
                "username": "student1",
                "password": "student123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@student.edu",
                "student_id": "2023-0001",
                "course": "Computer Science",
                "year_level": 3,
                "is_boarder": True
            },
            {
                "username": "student2",
                "password": "student123",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@student.edu",
                "student_id": "2023-0002",
                "course": "Engineering",
                "year_level": 2,
                "is_boarder": False
            },
            {
                "username": "student3",
                "password": "student123",
                "first_name": "Mike",
                "last_name": "Johnson",
                "email": "mike.johnson@student.edu",
                "student_id": "2023-0003",
                "course": "Business Administration",
                "year_level": 4,
                "is_boarder": True
            }
        ]

        for student_info in students_data:
            # Create or get the user account
            user, created = User.objects.get_or_create(
                username=student_info["username"],
                defaults={
                    "first_name": student_info["first_name"],
                    "last_name": student_info["last_name"],
                    "email": student_info["email"]
                }
            )
            if created:
                user.set_password(student_info["password"])
                user.save()

            # Create or get the student profile
            student, created = Student.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": student_info["student_id"],
                    "course": student_info["course"],
                    "year_level": student_info["year_level"],
                    "is_boarder": student_info["is_boarder"]
                }
            )

            if created:
                # Create clearance requests for the student based on all required offices.
                student.create_clearance_requests()
                
                # Create an initial clearance record for the student.
                Clearance.objects.get_or_create(student=student)

                self.stdout.write(self.style.SUCCESS(
                    f"Created student: {student.user.get_full_name()} ({student.student_id})"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Student exists: {student.user.get_full_name()} ({student.student_id})"
                ))

        self.stdout.write(self.style.SUCCESS("Successfully populated student data"))