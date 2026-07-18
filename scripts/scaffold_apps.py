"""
One-time scaffold generator for Edunaukri enterprise app skeleton.
Run: python scripts/scaffold_apps.py
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "apps"

APP_DEFINITIONS = {
    "authentication": {
        "label": "Authentication",
        "purpose": "Login, registration, logout, password reset, and email verification flows.",
        "domain": "shared",
    },
    "common": {
        "label": "Common",
        "purpose": "Cross-domain shared helpers, base classes, and mixins not belonging to core kernel.",
        "domain": "shared",
    },
    "it_recruitment": {
        "label": "IT Recruitment",
        "purpose": "IT domain orchestration, coordination, and domain-specific business rules.",
        "domain": "it",
    },
    "academic_recruitment": {
        "label": "Academic Recruitment",
        "purpose": "Faculty domain orchestration, coordination, and domain-specific business rules.",
        "domain": "faculty",
    },
    "companies": {
        "label": "Companies",
        "purpose": "IT employer company profiles, verification, and membership.",
        "domain": "it",
    },
    "colleges": {
        "label": "Colleges",
        "purpose": "Faculty institution profiles, verification, and membership.",
        "domain": "faculty",
    },
    "jobs": {
        "label": "Jobs",
        "purpose": "IT job posting lifecycle, skills, and publication.",
        "domain": "it",
    },
    "faculty": {
        "label": "Faculty Vacancies",
        "purpose": "Faculty vacancy posting lifecycle and departments.",
        "domain": "faculty",
    },
    "applications": {
        "label": "Applications",
        "purpose": "Job and faculty application submission, tracking, and status history.",
        "domain": "both",
    },
    "documents": {
        "label": "Documents",
        "purpose": "File upload metadata, storage adapters, resume/CV/certificate handling.",
        "domain": "shared",
    },
    "billing": {
        "label": "Billing",
        "purpose": "Placement fees, fee schedules, and billing orchestration.",
        "domain": "shared",
    },
    "invoices": {
        "label": "Invoices",
        "purpose": "Invoice generation, line items, and payment recording.",
        "domain": "shared",
    },
    "guarantee_claims": {
        "label": "Guarantee Claims",
        "purpose": "Guarantee claim filing, review, and resolution.",
        "domain": "shared",
    },
    "reports": {
        "label": "Reports",
        "purpose": "Analytics, exports, and aggregated reporting.",
        "domain": "shared",
    },
    "dashboard": {
        "label": "Dashboard",
        "purpose": "Server-rendered dashboard routing and context for all actor types.",
        "domain": "shared",
    },
    "notifications": {
        "label": "Notifications",
        "purpose": "Phase 2 notification foundation — outbox consumers, preference stubs.",
        "domain": "shared",
    },
    "search": {
        "label": "Search",
        "purpose": "Search orchestration, filtering, sorting, and pagination contracts.",
        "domain": "shared",
    },
    "audit": {
        "label": "Audit",
        "purpose": "Immutable audit event logging and compliance trail.",
        "domain": "shared",
    },
}

STANDARD_DIRS = [
    "models",
    "views",
    "serializers",
    "services",
    "repositories",
    "selectors",
    "permissions",
    "validators",
    "managers",
    "forms",
    "constants",
    "filters",
    "urls",
    "api/v1",
    "tests/unit",
    "tests/integration",
    "tests/api",
    "tests/factories",
    "tests/fixtures",
    "templates",
    "static",
    "migrations",
]

INIT_DOC = '''"""
{label} — {folder}
{description}
"""
'''

FOLDER_DESCRIPTIONS = {
    "models": "Django ORM models (Phase 1 implementation). One module per aggregate root.",
    "views": "Django template views and DRF view classes. Delegate to services only.",
    "serializers": "DRF serializers for request/response mapping. No business logic.",
    "services": "Business logic, transactions, and orchestration.",
    "repositories": "Write-side data access. Persistence operations only.",
    "selectors": "Read-side optimized queries. No writes.",
    "permissions": "DRF and Django permission classes for this app.",
    "validators": "Domain-specific validation rules.",
    "managers": "Custom model managers and querysets.",
    "forms": "Django forms for server-rendered UI.",
    "constants": "Enums, status codes, and configuration constants.",
    "filters": "django-filter FilterSet classes for list endpoints.",
    "urls": "Web URL routing (Django template views).",
    "api/v1": "REST API v1 endpoints mounted under /api/v1/.",
    "tests/unit": "Unit tests for services, validators, and utilities.",
    "tests/integration": "Integration tests with database.",
    "tests/api": "API endpoint tests.",
    "tests/factories": "factory_boy model factories.",
    "tests/fixtures": "Test fixture data files.",
    "templates": "Django HTML templates (Phase 1 UI).",
    "static": "App-scoped static assets (CSS/JS).",
    "migrations": "Django database migrations.",
}


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def scaffold_app(app_name: str, meta: dict) -> None:
    app_dir = BASE / app_name
    label = meta["label"]
    purpose = meta["purpose"]

    write_if_missing(
        app_dir / "apps.py",
        f'''from django.apps import AppConfig


class {app_name.title().replace("_", "")}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{app_name}"
    verbose_name = "{label}"
''',
    )

    write_if_missing(app_dir / "__init__.py", f'"""{label} application package."""\n')

    write_if_missing(
        app_dir / "admin.py",
        f'"""Django Admin registrations for {label}. Phase 1 implementation."""\n',
    )

    write_if_missing(
        app_dir / "signals.py",
        f'"""Domain signals for {label}. Connect in apps.py ready(). Phase 1 implementation."""\n',
    )

    write_if_missing(
        app_dir / "tasks.py",
        f'"""Celery tasks for {label}. Phase 2 activation."""\n',
    )

    for folder in STANDARD_DIRS:
        folder_path = app_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        desc = FOLDER_DESCRIPTIONS.get(folder, purpose)
        init_path = folder_path / "__init__.py"
        write_if_missing(
            init_path,
            INIT_DOC.format(label=label, folder=folder, description=desc),
        )

    # api urls stub
    write_if_missing(
        app_dir / "api" / "urls.py",
        f'"""API URL router for {label}. Mounted at /api/v1/{app_name.replace("_", "-")}/."""\n\nurlpatterns = []\n',
    )

    write_if_missing(
        app_dir / "api" / "v1" / "urls.py",
        f'"""{label} API v1 endpoints. Phase 1 implementation."""\n\nurlpatterns = []\n',
    )

    write_if_missing(
        app_dir / "urls" / "web.py",
        f'"""Web URL routes for {label}. Phase 1 implementation."""\n\nurlpatterns = []\n',
    )

    write_if_missing(
        app_dir / "constants" / "enums.py",
        f'"""Status enums and constants for {label}. Phase 1 implementation."""\n',
    )

    write_if_missing(
        app_dir / "services" / "base.py",
        f'"""Base service class for {label}. Extend apps.core.services.BaseService."""\n',
    )

    write_if_missing(
        app_dir / "repositories" / "base.py",
        f'"""Base repository class for {label}. Extend apps.core.repositories.BaseRepository."""\n',
    )

    # templates/static gitkeep
    write_if_missing(app_dir / "templates" / app_name / ".gitkeep", "")
    write_if_missing(app_dir / "static" / app_name / ".gitkeep", "")

    # README per app
    write_if_missing(
        app_dir / "README.md",
        f"""# {label}

## Purpose
{purpose}

## Domain
{meta["domain"]}

## Dependencies
See `docs/PROJECT_SKELETON.md` dependency matrix.

## Phase 1 Scope
Skeleton only — no business logic implemented.

## Future Expansion
See app README in architecture blueprint.
""",
    )


def extend_existing_apps() -> None:
    """Add missing folders to existing foundation apps."""
    for app_name in ("core", "accounts", "api", "health"):
        meta = {
            "label": app_name.replace("_", " ").title(),
            "purpose": "Existing foundation app — extended structure.",
        }
        app_dir = BASE / app_name
        if not app_dir.exists():
            continue
        for folder in STANDARD_DIRS:
            if folder in ("migrations",) and app_name == "api":
                continue
            folder_path = app_dir / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            desc = FOLDER_DESCRIPTIONS.get(folder, meta["purpose"])
            write_if_missing(
                folder_path / "__init__.py",
                INIT_DOC.format(label=meta["label"], folder=folder, description=desc),
            )


def create_media_structure() -> None:
    media_root = BASE.parent / "media"
    dirs = [
        "it/resumes",
        "it/companies/logos",
        "faculty/cvs",
        "faculty/certificates",
        "faculty/colleges/logos",
        "billing/invoices",
        "billing/claims",
        "admin/exports",
    ]
    for d in dirs:
        (media_root / d).mkdir(parents=True, exist_ok=True)
        write_if_missing(media_root / d / ".gitkeep", "")


def main() -> None:
    for app_name, meta in APP_DEFINITIONS.items():
        scaffold_app(app_name, meta)
    extend_existing_apps()
    create_media_structure()
    print(f"Scaffolded {len(APP_DEFINITIONS)} apps under {BASE}")


if __name__ == "__main__":
    main()
