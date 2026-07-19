# Social Auth

## Purpose
Google, LinkedIn, Microsoft, and GitHub OAuth 2.0 authentication integration.

- OAuth initiation (returns provider authorization URL)
- Callback handling (code → token exchange → user-info → account linking)
- Social account management (link, unlink, list)

## Domain
shared

## Architecture
Follows Clean Architecture + SOLID principles inside a Modular Monolith:

- **Views** — thin; no business logic; delegate to services.
- **Services** — contain all business logic, OAuth orchestration, and account linking.
- **Selectors** — read-side queries; no writes.
- **Serializers** — request/response mapping only.
- **Permissions** — DRF permission classes.
- **Constants** — `ProviderConfig` dataclasses and provider registry.
- **Exceptions** — domain-specific exception classes.

## Providers
| Provider    | Scope                         |
|-------------|-------------------------------|
| Google      | openid, email, profile        |
| LinkedIn    | openid, email, profile        |
| Microsoft   | openid, email, profile, User.Read |
| GitHub      | read:user, user:email         |

## Dependencies
See `docs/PROJECT_SKELETON.md` dependency matrix.

## Phase 1 Scope
Skeleton only — no OAuth implementation yet.

## Future Expansion
See app README in architecture blueprint.
