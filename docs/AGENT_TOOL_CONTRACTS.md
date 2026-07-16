# Agent Tool Contracts

The Workplace Agent exposes a **small, fixed** set of tools. Tools are not
arbitrary: there is no arbitrary SQL, shell, browser control, or unrestricted
HTTP. Step 0 exposes exactly one tool, and it is read-only.

---

## Tool: `get_organization_profile`

| Field | Value |
| ----- | ----- |
| **Risk** | `read_only` |
| **Permission** | `organization.profile.read` |
| **Environment** | `sandbox` |
| **Input** | `organization_id` |
| **Output** | organization profile |
| **Backing endpoint** | `GET /sandbox/organizations/{organization_id}/profile` |
| **Status** | implemented (Step 0) |

### Failure cases

| HTTP | Error code | When |
| ---- | ---------- | ---- |
| 401 | `unauthenticated` | missing/unknown `X-Mock-Employee-Id` |
| 403 | `employee_disabled` | employee account disabled |
| 403 | `organization_access_denied` | employee has no role in the organization |
| 403 | `permission_denied` | employee lacks `organization.profile.read` |
| 403 | `production_access_blocked` | organization is not `sandbox` |
| 404 | `organization_not_found` | organization does not exist |
| 500 | `internal_error` | unexpected server error |

### Side effects

- Appends one append-only audit event (`organization.profile.read`).

---

## Tool: `update_organization_display_name`

| Field | Value |
| ----- | ----- |
| **Risk** | `write` |
| **Permission** | `organization.profile.update` |
| **Environment** | `sandbox` |
| **Input** | `organization_id`, `new_display_name`, `expected_version` |
| **Output** | updated organization profile |
| **Status** | **`NOT_IMPLEMENTED_STEP_0`** |

This tool is intentionally **not implemented** in Step 0. It is listed here only
to lock its name and contract ahead of the first controlled write workflow. No
write tool is registered, exposed, or executable in Step 0.
