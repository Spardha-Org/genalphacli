"""Repository layer — all DB access behind clean interfaces.

Repos never commit. The service layer commits once per operation (Unit of Work).
"""
