# Apply the Test_user1 replacement patch

Target repository: `shubham123dev/dem_0000_saa`

Pinned base commit:

```text
2e8f9c5afb677d84044d01e39cb4e57acb86cdc6
```

## Apply, validate, and commit

Copy `apply_test_user1_replacement.py` into or alongside the repository, then run:

```bash
git switch main
git pull --ff-only
git rev-parse HEAD

python /path/to/apply_test_user1_replacement.py \
  --repo . \
  --run-tests \
  --commit
```

The script creates/switches to:

```text
agent/replace-users-with-test-user1
```

and commits:

```text
replace local users with Test_user1 directory
```

It never pushes. After reviewing:

```bash
git status --short
git show --stat --oneline HEAD
git push -u origin agent/replace-users-with-test-user1
```

Without automatic commit:

```bash
python /path/to/apply_test_user1_replacement.py --repo . --run-tests
```

## What the patch changes

- Removes the runtime `UserORM` and local `users` table.
- Uses `[dbmr_Database_Nucleus].[dbo].[Test_user1]` as the production user directory.
- Keeps public IDs as strings, containing `str(Test_user1.UserID)`, so frontend and action contracts are not broken.
- Removes local physical FKs to `users.id`; memberships, seats, actions, approvals, runs, and audits retain canonical user-ID values.
- Adds an isolated `mssql+aioodbc` SQL Server engine.
- Uses explicit user projections that never select `Password`.
- Rewires authentication, user lists, invitations, onboarding, offboarding reads, action labels, and relationship traversal.
- Replaces sandbox user persistence with an in-memory test adapter.
- Adds Alembic revision `0018_replace_local_users`.
- Adds a one-time legacy ID mapper for populated deployments.
- Adds readiness checks and tests.

## Existing populated database cutover

Run this while the legacy `users` table still exists and before Alembic 0018:

```bash
export WORKPLACE_NUCLEUS_USER_DATABASE_URL='mssql+aioodbc://...'

python -m scripts.map_legacy_users_to_test_user1
python -m scripts.map_legacy_users_to_test_user1 --apply
alembic upgrade head
```

The first command is a dry run. Missing or duplicate `EmailID` matches stop the operation.

## Production reads and writes

Required for production reads:

```bash
export WORKPLACE_NUCLEUS_USER_DATABASE_URL='mssql+aioodbc://...'
export WORKPLACE_NUCLEUS_USER_DATABASE_NAME='dbmr_Database_Nucleus'
export WORKPLACE_NUCLEUS_USER_SCHEMA_NAME='dbo'
export WORKPLACE_NUCLEUS_USER_TABLE_NAME='Test_user1'
```

Writes are disabled by default. The implementation introspects live SQL Server metadata and fails closed when required fields are not configured.

```bash
export WORKPLACE_NUCLEUS_USER_DEFAULT_TYPE_ID='...'
export WORKPLACE_NUCLEUS_USER_CREATE_DEFAULTS='{"company":"..."}'
export WORKPLACE_NUCLEUS_USER_WRITES_ENABLED=true
```

`Password` can never be selected or written by this adapter. If it is required without a database default, user creation must use the official Nucleus authentication stored procedure/API instead of direct SQL.
