# Workplace Agent sandbox requirements

## Current scope

- SQLite remains the sandbox database.
- The eight supplied Nucleus tables use exact names and columns without `dbo`.
- Existing Overview, user, seat, report, action and audit behavior remains.
- Stable Workplace contracts isolate chat/frontend code from raw persistence.
- All synthetic rows are deterministic and idempotently seeded.

## Required safety behavior

- No arbitrary SQL, URL, shell or browser tool.
- No production credentials or real employee data.
- Password is never exposed.
- Reads require membership plus resource permission.
- Writes are dry-run proposals until separately approved and executed.
- High-risk OrganizationPermission changes require two independent approvers.
- Optimistic versions prevent reviewed state from being overwritten silently.
- Successful writes are audited; uncertain outcomes use reconciliation.
- Rollback is a new proposal and never automatic.

## Deliberate incomplete real-system areas

This schema does not define individual organization login records, actual usage
analytics, security policies, API keys, invoices or payments. Those are not
invented in this slice.

Company, Drug, Indication and Market access tables have no supplied lifecycle
column or delete rule, so they are accessible through chat as reads but not
mutated.
