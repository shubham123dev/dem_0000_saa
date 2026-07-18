# Artifact validation report

Validation performed in the artifact environment:

- Python compilation for all included Python files: passed.
- Python AST parse for all included Python files: passed.
- SQLAlchemy metadata creation for all eight exact tables and the internal
  version sidecar: passed.
- Repository smoke checks for account update, legacy profile synchronization,
  stale-version rejection, category grant/revoke/reactivate, report grant, and
  exact permission-row create/update/stale rejection: passed.
- Password outward-model absence check: passed through repository/domain smoke.
- Archive manifest and bytecode exclusion: checked during packaging.

The complete repository test suite cannot be truthfully claimed in the isolated
artifact environment because a full checkout was not available there. Run the
commands in `APPLY_AND_VALIDATE.md` in the user's validated local checkout and
do not commit unless all tests pass.
