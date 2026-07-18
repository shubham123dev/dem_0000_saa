# Organization API contracts

## Common authorization

Every organization-scoped endpoint requires an authenticated active user, an
active membership in the exact organization, the backend-owned permission, and
an active sandbox organization.

## Existing Overview

```text
GET /workplace/organizations/{organization_id}/overview
permission: organization.profile.read
```

## Exact Nucleus account

```text
GET /workplace/organizations/{organization_id}/nucleus/account
permission: organization.account.read
```

Returns profile, contact, address, account status, creation/update metadata and
an internal optimistic version. `Password` is never returned.

## Licence

```text
GET /workplace/organizations/{organization_id}/nucleus/license
permission: organization.account.read
```

Returns `MaxUserLimit`, `LicenseStartDate`, `LicenseEndDate`, status and active
state exactly. The API does not rename `LicenseEndDate` to renewal date.

## Approval status

```text
GET /workplace/organizations/{organization_id}/nucleus/approval-status
permission: organization.account.read
```

Returns approval/rejection identifiers, dates and rejection reason.

## Entitlements

```text
GET /workplace/organizations/{organization_id}/nucleus/entitlements
permission: organization.entitlements.read
```

Returns rows from Category, Company Profile, Drug, Indication, Market,
Permission and Report access tables.

## Error behavior

The existing standard errors remain in force:

- `401 unauthenticated`
- `403 user_disabled`
- `403 organization_access_denied`
- `403 permission_denied`
- `403 production_access_blocked`
- `403 organization_suspended`
- `404 organization_not_found`
- `409 agent_action_stale`
- `422 agent_action_invalid`

No response exposes SQL, filesystem paths, stack traces, secrets or Password.
