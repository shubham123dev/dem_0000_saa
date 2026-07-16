"""Organization adapter package.

Step 0 ships ``MockOrganizationApiAdapter``, which delegates to the in-process
``MockOrganizationApi`` backed by the mock SQLite database. The future
production implementation will be ``NucleusOrganizationApiAdapter`` (NOT
implemented in Step 0). Both satisfy the ``OrganizationApiGateway`` contract.
"""
