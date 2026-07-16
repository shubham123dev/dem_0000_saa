"""Repositories: the only components that touch the ORM directly.

Repositories translate ORM rows into framework-agnostic domain models so that
services and the API layer never depend on SQLAlchemy objects.
"""
