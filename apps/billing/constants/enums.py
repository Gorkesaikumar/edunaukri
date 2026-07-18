from django.db import models


class FeeScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    COMPANY = "company", "Company"
    COLLEGE = "college", "College"
    ROLE = "role", "Role"
    DESIGNATION = "designation", "Designation"
    RECRUITER = "recruiter", "Recruiter"


class FeeType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed Amount"


class PlacementFeeStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    INVOICED = "invoiced", "Invoiced"
    WAIVED = "waived", "Waived"
    CANCELLED = "cancelled", "Cancelled"
