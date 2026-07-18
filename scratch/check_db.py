import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.applications.models import FacultyApplication

apps = FacultyApplication.objects.filter(applicant_name_snapshot__icontains="suma")
for app in apps:
    print(f"ID: {app.pk}, Candidate: {app.applicant_name_snapshot}, Status: {app.status}, Vacancy: {app.vacancy.title if app.vacancy else 'None'}")

apps = FacultyApplication.objects.all()
print(f"Total faculty apps in DB: {apps.count()}")
