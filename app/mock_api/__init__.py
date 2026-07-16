"""Mock external organization API (`/mock-api/v1`).

This package simulates the future real Nucleus organization API as HTTP
endpoints backed by the sandbox SQLite database. It is intentionally separate
from the Workplace-Agent tool endpoints: this surface returns raw resource data
and is later replaced by the real API, while the agent keeps enforcing backend-
owned permissions through the adapter contract.
"""
