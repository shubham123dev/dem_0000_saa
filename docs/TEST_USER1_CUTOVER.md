# Test_user1 cutover

`dbmr_Database_Nucleus.dbo.Test_user1` is the only production user
identity/profile table. The Workplace database retains organization
memberships, roles, seats, actions, runs, and audits, whose user ID fields
contain the string representation of `Test_user1.UserID`.

## Required environment

```bash
export WORKPLACE_NUCLEUS_USER_DATABASE_URL='mssql+aioodbc://...'
export WORKPLACE_NUCLEUS_USER_DATABASE_NAME='dbmr_Database_Nucleus'
export WORKPLACE_NUCLEUS_USER_SCHEMA_NAME='dbo'
export WORKPLACE_NUCLEUS_USER_TABLE_NAME='Test_user1'
```

The ODBC connection string must use an installed Microsoft SQL Server ODBC
driver. Production startup fails closed when this URL is absent.

## Existing populated deployment

Before Alembic 0018, map every legacy local user by email:

```bash
python -m scripts.map_legacy_users_to_test_user1
python -m scripts.map_legacy_users_to_test_user1 --apply
alembic upgrade head
```

The first command is a mandatory dry run. Duplicate or missing EmailID
matches stop the migration. After 0018, the local `users` table no longer
exists and Alembic never manages `Test_user1`.

## User creation

Reads are available as soon as the Nucleus connection is configured.
Writes remain disabled by default:

```bash
export WORKPLACE_NUCLEUS_USER_WRITES_ENABLED=false
```

The repository introspects the live Test_user1 metadata before INSERT. Set
trusted defaults using JSON only for columns verified by DB metadata:

```bash
export WORKPLACE_NUCLEUS_USER_DEFAULT_TYPE_ID='...'
export WORKPLACE_NUCLEUS_USER_CREATE_DEFAULTS='{"company":"..."}'
export WORKPLACE_NUCLEUS_USER_WRITES_ENABLED=true
```

`Password` is always rejected. If it is a required column without a DB
default, user creation must be routed through the official authentication
stored procedure/API rather than direct SQL.
