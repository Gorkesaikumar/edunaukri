from django.db import models


class MatchMode(models.TextChoices):
    CONTAINS = "contains", "Contains"
    EXACT = "exact", "Exact"
    STARTSWITH = "startswith", "Starts With"


class PaginationMode(models.TextChoices):
    PAGE = "page", "Page Number"
    OFFSET = "offset", "Offset"
    CURSOR = "cursor", "Cursor"


class SearchResource(models.TextChoices):
    JOBS = "jobs", "Jobs"
    FACULTY = "faculty", "Faculty Vacancies"
    VACANCIES = "vacancies", "Vacancies"
    COMPANIES = "companies", "Companies"
    COLLEGES = "colleges", "Colleges"
    APPLICATIONS = "applications", "Applications"
    INVOICES = "invoices", "Invoices"
    GUARANTEES = "guarantees", "Guarantee Claims"
    JOB_SEEKERS = "job_seekers", "Job Seekers"
    RECRUITERS = "recruiters", "Recruiters"
    PROFESSORS = "professors", "Professors"
    ADMIN = "admin", "Admin Global"
