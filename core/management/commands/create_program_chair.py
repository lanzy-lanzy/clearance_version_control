from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Staff, Office  # Use your actual app name if it's different


class Command(BaseCommand):
    help = "Create a Program Chair user account."

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help="Email of the Program Chair")
        parser.add_argument('password', type=str, help="Password for the Program Chair")

    def handle(self, *args, **kwargs):
        email = kwargs['email']
        password = kwargs['password']
        username = email.split('@')[0]  # Use part of the email as the username

        # Check if a Program Chair office exists
        office, created = Office.objects.get_or_create(name="Program Chair", defaults={"description": "Handles final clearance approval"})

        # Check if the user already exists
        user, user_created = User.objects.get_or_create(username=username, email=email)
        if user_created:
            user.set_password(password)
            user.is_staff = True  # Allow admin panel access
            user.is_superuser = False
            user.save()

            # Assign user as a Program Chair in Staff table
            Staff.objects.create(user=user, office=office, role="Program Chair")
            self.stdout.write(self.style.SUCCESS(f"✅ Program Chair {email} created successfully!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Program Chair {email} already exists."))
