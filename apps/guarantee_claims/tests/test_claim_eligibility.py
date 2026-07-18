import pytest
from datetime import timedelta
from django.utils import timezone
from apps.guarantee_claims.services.eligibility_service import GuaranteeClaimEligibilityService
from apps.core.constants.enums import ApplicationStatus
from apps.invoices.models import Invoice

class MockApplication:
    def __init__(self, pk, status, joined_date=None, is_faculty=True):
        self.pk = pk
        self.status = status
        self.joined_date = joined_date
        self.actual_joining_date = joined_date
        self.is_faculty = is_faculty

@pytest.mark.django_db
class TestGuaranteeClaimEligibilityService:
    def setup_method(self):
        self.service = GuaranteeClaimEligibilityService()
        self.today = timezone.now().date()
        self.invoice = Invoice.objects.create(
            placement_fee_id="11111111-1111-1111-1111-111111111111",
            total_amount=10000.00
        )

    def test_ineligible_not_joined(self):
        app = MockApplication(pk="11111111-1111-1111-1111-111111111111", status=ApplicationStatus.OFFERED)
        result = self.service.check_eligibility(app, self.today)
        assert not result["eligible"]
        assert "not reached JOINED status" in result["reason"]

    def test_ineligible_no_joining_date(self):
        app = MockApplication(pk="11111111-1111-1111-1111-111111111111", status=ApplicationStatus.JOINED, joined_date=None)
        result = self.service.check_eligibility(app, self.today)
        assert not result["eligible"]
        assert "Joining date is not confirmed" in result["reason"]

    def test_ineligible_past_90_days(self):
        joining_date = self.today - timedelta(days=95)
        exit_date = self.today
        app = MockApplication(pk="11111111-1111-1111-1111-111111111111", status=ApplicationStatus.JOINED, joined_date=joining_date)
        result = self.service.check_eligibility(app, exit_date)
        assert not result["eligible"]
        assert "outside the 90-day guarantee window" in result["reason"]

    def test_ineligible_exit_before_joining(self):
        joining_date = self.today - timedelta(days=10)
        exit_date = self.today - timedelta(days=12)
        app = MockApplication(pk="11111111-1111-1111-1111-111111111111", status=ApplicationStatus.JOINED, joined_date=joining_date)
        result = self.service.check_eligibility(app, exit_date)
        assert not result["eligible"]
        assert "cannot be before the joining date" in result["reason"]

    def test_eligible_within_90_days(self):
        joining_date = self.today - timedelta(days=80)
        exit_date = self.today - timedelta(days=5)
        app = MockApplication(pk="11111111-1111-1111-1111-111111111111", status=ApplicationStatus.JOINED, joined_date=joining_date)
        result = self.service.check_eligibility(app, exit_date)
        assert result["eligible"] is True
        assert result["invoice"] == self.invoice
