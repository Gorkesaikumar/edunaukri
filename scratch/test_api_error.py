import os
import django
import json

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from apps.accounts.models import CollegeUser, ProfessorUser
from django.db import transaction

client = Client()
password = "TestPassword123!@#"

def run_test():
    # Clean database first in correct dependency order
    from apps.applications.models import FacultyApplication
    from apps.faculty.models import FacultyVacancy
    from apps.colleges.models import College
    FacultyApplication.objects.all().delete()
    FacultyVacancy.objects.all().delete()
    College.objects.all().delete()
    ProfessorUser.objects.filter(email="ent-fac-app-prof@test.com").delete()
    CollegeUser.objects.filter(email="ent-fac-app-college@test.com").delete()

    professor_email = "ent-fac-app-prof@test.com"
    ProfessorUser.objects.create_user(professor_email, password)
    
    # Get token
    prof_token_resp = client.post(
        "/api/v1/auth/professor/token/",
        data=json.dumps({"email": professor_email, "password": password}),
        content_type="application/json"
    )
    print("prof_token_resp status:", prof_token_resp.status_code)
    professor_token = prof_token_resp.json()["data"]["access"]
    
    # Setup profile
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {professor_token}"
    prof_profile_resp = client.post(
        "/api/v1/faculty/profiles/professor/",
        data=json.dumps({
            "first_name": "Ent",
            "last_name": "Professor",
            "phone": "9876543210",
            "highest_qualification": "PhD",
            "specialization": "Physics",
            "current_institution": "IISc",
            "current_designation": "Associate Professor",
            "publications_count": 12,
            "expected_salary": "1500000",
        }),
        content_type="application/json"
    )
    print("prof_profile_resp status:", prof_profile_resp.status_code)
    
    college_email = "ent-fac-app-college@test.com"
    CollegeUser.objects.create_user(college_email, password)
    
    college_token_resp = client.post(
        "/api/v1/auth/college/token/",
        data=json.dumps({"email": college_email, "password": password}),
        content_type="application/json"
    )
    college_token = college_token_resp.json()["data"]["access"]
    
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {college_token}"
    college_resp = client.post(
        "/api/v1/faculty/colleges/",
        data=json.dumps({"name": "Ent Faculty College", "city": "Chennai"}),
        content_type="application/json"
    )
    print("college_resp status:", college_resp.status_code)
    college_id = college_resp.json()["data"]["id"]
    
    from tests.conftest import verify_test_college
    verify_test_college(college_id)
    
    vacancy_resp = client.post(
        "/api/v1/faculty/vacancies/",
        data=json.dumps({
            "college_id": college_id,
            "title": "Professor of Physics",
            "description": "Teach UG/PG",
            "department": "Physics",
        }),
        content_type="application/json"
    )
    print("vacancy_resp status:", vacancy_resp.status_code)
    vacancy_id = vacancy_resp.json()["data"]["id"]
    
    pub_resp = client.post(f"/api/v1/faculty/vacancies/{vacancy_id}/publish/")
    print("publish status:", pub_resp.status_code)
    
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {professor_token}"
    apply_resp = client.post(
        "/api/v1/applications/faculty/",
        data=json.dumps({
            "vacancy_id": vacancy_id,
            "expected_salary": "1400000",
            "source": "direct",
            "current_institution": "IISc Bangalore",
        }),
        content_type="application/json"
    )
    print("apply_resp status:", apply_resp.status_code)
    print("apply_resp content:", apply_resp.content.decode())

try:
    with transaction.atomic():
        run_test()
except Exception as e:
    import traceback
    traceback.print_exc()
