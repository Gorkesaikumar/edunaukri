from django.test import Client, TestCase
from django.urls import reverse

from apps.colleges.models import College
from apps.companies.models import Company


class InstitutionMarketplaceWebTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(
            name="Acme IT Solutions",
            slug="acme-it-solutions",
            is_active=True,
            is_deleted=False,
        )
        self.college = College.objects.create(
            name="National Institute of Technology",
            slug="national-institute-of-technology",
            is_active=True,
            is_deleted=False,
        )

    def test_institutions_browse_view_returns_200(self):
        url = reverse("institutions_browse")
        response = self.client.get(url, HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Institutions Marketplace")
        self.assertContains(response, "Acme IT Solutions")
        self.assertContains(response, "National Institute of Technology")

    def test_institution_detail_view_returns_200(self):
        url = reverse("institution_detail", kwargs={"slug": self.college.slug})
        response = self.client.get(url, HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "National Institute of Technology")
