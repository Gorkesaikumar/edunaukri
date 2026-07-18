# Core Shared Infrastructure

Production-ready reusable primitives for every domain app. **Import from `apps.core` — never duplicate.**

## Models (`apps.core.models`)

| Class | Use when |
|-------|----------|
| `BaseModel` | Default domain entity (UUID + timestamps + soft delete) |
| `AuditedBaseModel` | Entity needs `created_by_id` / `updated_by_id` / `deleted_by_id` |
| `UUIDModel` / `TimeStampedModel` / `SoftDeleteModel` | Alias mixins for partial composition |
| `AuditModel` | Audit columns only |
| `StatusModel` | Entity has shared `RecordStatus` lifecycle |
| `OwnershipModel` | Resource scoped by `owner_type` + `owner_id` |

## Managers (`apps.core.managers`)

| Class | Use when |
|-------|----------|
| `ActiveManager` | Default manager excluding soft-deleted rows |
| `SoftDeleteManager` | Access all rows including deleted |
| `BaseManager` / `BaseQuerySet` | Shared queryset helpers (`active()`, `with_status()`) |

## Repositories (`apps.core.repositories`) — write side

| Class | Use when |
|-------|----------|
| `ReadRepository` | Read-only persistence |
| `FilteringRepository` | Add `filter_by()` / `search()` |
| `PaginationRepository` | Add `paginate()` |
| `CRUDRepository` | Full create/update/soft-delete/restore |

Set `model` on subclass. **No business rules in repositories.**

## Selectors (`apps.core.selectors`) — read side

| Class | Use when |
|-------|----------|
| `ReadSelector` | Views need lists/details without ORM in views |

## Services (`apps.core.services`)

| Class | Use when |
|-------|----------|
| `BaseService` | All domain services; use `@BaseService.atomic` for transactions |
| `CRUDService` | Generic CRUD orchestration with repository injection |
| `ValidationService` | Centralize validator execution → `ValidationException` |
| `TransactionService` | `atomic`, `on_commit`, `rollback` |
| `StorageService` | Byte storage via local/S3 backend abstraction |
| `BusinessRule` / `BusinessRuleSet` | Composable domain rules |
| `OutboxService` | Transactional outbox events |

## Exceptions (`apps.core.exceptions`)

| Layer | Classes |
|-------|---------|
| Domain (services) | `ValidationException`, `BusinessLogicException`, `PermissionDeniedException`, `ResourceNotFoundException`, `ConflictException` |
| API (DRF views) | `ValidationAPIError`, `NotFoundAPIError`, etc. |

Handler: `custom_exception_handler` — uniform `{success, error}` envelope.

## API responses (`apps.core.api.responses`)

Use `success_response`, `error_response`, `validation_error_response`, `paginated_response` or extend `EnvelopeAPIView`.

## Pagination (`apps.core.pagination`)

| Class | Page size |
|-------|-----------|
| `StandardResultsSetPagination` | 20 (default) |
| `LargeResultsSetPagination` | 50 |
| `SmallResultsSetPagination` | 10 |
| `StandardCursorPagination` | cursor-based lists |

## Filters (`apps.core.filters`)

| Class | Purpose |
|-------|---------|
| `BaseFilterSet` | Date range + include_deleted |
| `StandardSearchFilter` | `?search=` |
| `StandardOrderingFilter` | `?ordering=` |

## Validators (`apps.core.validators`)

`validate_email`, `validate_phone`, `validate_url`, `validate_gst`, `validate_password_strength`, `validate_file_upload`, `validate_image_upload`

## Utils (`apps.core.utils`)

Date/time, files, strings, UUID, permissions, pagination, validation helpers — see package `__init__.py` exports.

## Constants & enums (`apps.core.constants`)

Shared enums: `DomainType`, `PlatformRole`, `ApplicationStatus`, `InvoiceStatus`, `GuaranteeStatus`, `DocumentType`, `RecordStatus`.

## Middleware (`apps.core.middleware`)

| Middleware | Purpose |
|------------|---------|
| `RequestIDMiddleware` | Correlation ID (`X-Request-ID`) |
| `TimezoneMiddleware` | `X-Timezone` activation |
| `RequestLoggingMiddleware` | Structured request logging |
| `AuditContextMiddleware` | Thread-local audit actor |
| `SecurityHeadersMiddleware` | Security response headers |
| `ExceptionMiddleware` | JSON 500 for unhandled errors |

## Storage (`apps.core.storage`)

| Backend | Config |
|---------|--------|
| `LocalStorageBackend` | `STORAGE_BACKEND=local` |
| `S3StorageBackend` | `STORAGE_BACKEND=s3` (hook — configure django-storages) |

## Permissions (`apps.core.permissions`)

| Class | Role |
|-------|------|
| `IsPlatformAdmin` / `IsAdmin` | Platform admin |
| `IsJobSeeker`, `IsRecruiter` | IT RBAC |
| `IsProfessor`, `IsCollege` | Academic identity |
| `IsOwner` | Object-level ownership |
| `DomainPermissionBase` | Domain + IT role checks |

## Logging (`apps.core.logging.logger`)

`get_logger(__name__)` adds `request_id` to log records.

## Architecture rules

1. **Views** orchestrate only — call services/selectors.
2. **Services** contain business logic and transactions.
3. **Repositories** persist writes; **selectors** perform reads.
4. **Never** query models directly in views.
5. Raise **domain exceptions** in services; map to HTTP in the exception handler.

## Domain modules (Phase 1)

Each business app follows repositories (writes) + selectors (reads). Views extend `EnvelopeAPIView`.

| App | Selectors | Repositories |
|-----|-----------|--------------|
| `it_recruitment` | `JobSeekerProfileSelector`, `RecruiterProfileSelector` | profile repos |
| `companies` | `CompanySelector` | `CompanyRepository` |
| `jobs` | `JobPostingSelector`, `JobSearchSelector` | `JobRepository` |
| `colleges` | `CollegeSelector`, `CollegeMemberSelector` | `CollegeRepository` |
| `faculty` | `FacultyVacancySelector`, `VacancySearchSelector` | `VacancyRepository` |
| `applications` | `JobApplicationSelector`, `FacultyApplicationSelector` | application + status history repos |
| `billing` | `FeeScheduleSelector`, `PlacementFeeSelector` | fee repos |
| `invoices` | `InvoiceSelector` | invoice, line item, payment repos |
| `guarantee_claims` | `GuaranteeClaimSelector` | `GuaranteeClaimRepository` |
| `documents` | `StoredFileSelector` | `StoredFileRepository` |
| `notifications` | `NotificationSelector` | `NotificationRepository` |
| `audit` | `AuditEventSelector` | `AuditEventRepository` |
| `authentication` | `UserContextSelector` | `DomainUserRepository`, `AuthTokenRepository`, `LoginAttemptRepository` |
| `core` | `OutboxEventSelector` | `OutboxEventRepository` |
| `search` | delegates to domain search selectors | — |

## Outbox & email

- `OutboxService` publishes domain events transactionally.
- `python manage.py process_outbox` runs `OutboxProcessorService`.
- Auth emails (`AUTH_EMAIL_DELIVERY_ENABLED=true`) and in-app notifications share the outbox pipeline.
