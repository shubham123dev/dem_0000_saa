# Agent-native workplace resources

## Scope

This milestone connects the governed workplace-resource runtime to the existing
LLM planner without exposing SQL, ORM classes, physical table names, credentials,
organization scope, actor identity, approval state or execution controls.

## Planner contract

The backend supplies a secret-free catalog containing resource types, business
field names, safe field capabilities and canonical tool/action routes. The model
may select only listed tools and actions. Missing required business arguments
produce `clarification_required`; identifiers are never guessed.

## Canonical routes

Synchronized resources stay on their dedicated handlers. In particular,
organization display-name changes route through the Nucleus organization-name
handler and contact-email changes route through the contact-email bridge. The
generic organization resource may update only fields that do not require a
projection bridge.

## Read tools

- `list_workplace_resource_types`
- `describe_workplace_resource`
- `search_workplace_resources`
- `get_workplace_resource`
- `count_workplace_resources`

The generic search path remains equality-filtered and organization-scoped in
this milestone. Relationship traversal and advanced query operators remain in
the subsequent workflow milestone.

## Restore integrity

A restore proposal is generated from the active tombstone snapshot. Execution
revalidates both the resource version and tombstone version, reapplies the exact
reviewed business snapshot, increments the resource version, and marks the
tombstone restored. A resource changed after deletion cannot be restored from a
stale proposal.
