"""Replaceable organization system-of-record adapter package.

``MockOrganizationApiAdapter`` provides the current SQLite-backed sandbox.
A future ``NucleusOrganizationApiAdapter`` must satisfy the same
``OrganizationApiGateway`` and map real provider fields into stable domain
models without changing agent or frontend contracts.
"""
