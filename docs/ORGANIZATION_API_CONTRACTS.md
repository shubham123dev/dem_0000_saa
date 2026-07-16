# Organization API Contracts

Contracts for the organization adapter. Step 0 implements only the read
operation. The update operation is documented as **provisional / future** and
is **not** implemented or exposed in Step 0.

---

## Current (Step 0): read organization profile

- **Adapter method:** `OrganizationGateway.get_profile(organization_id: str) -> OrganizationProfile`
- **HTTP endpoint:** `GET /sandbox/organizations/{organization_id}/profile`
- **Required permission:** `organization.profile.read`
- **Environment constraint:** organization `environment` must be `sandbox`

### Validation

- `X-Mock-Employee-Id` header must be present and resolve to an active employee.
- Organization must exist (else `organization_not_found` / 404).
- Organization must be `environment = sandbox` (else `production_access_blocked` / 403).
- Employee must have a role in the organization (else `organization_access_denied` / 403).
- Employee's role(s) must grant `organization.profile.read` (else `permission_denied` / 403).

### Verification

- The response returns the **exact persisted organization state**.
- A read audit event (`organization.profile.read`, `outcome=success`) is
  appended before returning.

### Rollback

- Reads are non-mutating; there is nothing to roll back. Audit events are
  append-only and are never rewritten.

### Response shape

```json
{
  "organization": {
    "id": "org_sandbox_001",
    "display_name": "Demo Enterprise Sandbox",
    "legal_name": "Demo Enterprise Private Limited",
    "contact_email": "operations@example.test",
    "environment": "sandbox",
    "status": "active",
    "version": 1
  },
  "access": {
    "employee_id": "emp_admin_001",
    "permission": "organization.profile.read"
  }
}
```

---

## Provisional (future): update organization display name

> **NOT implemented in Step 0.** Documented to lock the contract for the first
> controlled write workflow.

- **Adapter method (future):** `update_display_name(organization_id, new_display_name, expected_version) -> OrganizationProfile`
- **Required permission:** `organization.profile.update`
- **Environment constraint:** `sandbox` only.

### Validation (future)

- Authenticated + active employee with `organization.profile.update`.
- New display name is non-empty and length-bounded.
- Optimistic concurrency via `expected_version` matching the stored `version`.

### Verification (future)

- Re-read the profile after write and confirm the new value and incremented
  `version`.
- Append a write audit event capturing before/after values.

### Rollback (future)

- The controlled write workflow (inspect → propose → approve → update →
  re-read → verify → audit → rollback) must be able to restore the prior value
  using the recorded before-state if verification fails.

---

## Expected permissions summary

| Operation | Permission | Status |
| --------- | ---------- | ------ |
| read profile | `organization.profile.read` | implemented (Step 0) |
| update display name | `organization.profile.update` | future, not implemented |
