from __future__ import annotations


class DomainError(Exception):
    """Base exception for business-rule failures."""


class NotFoundError(DomainError):
    pass


class InvalidStateTransitionError(DomainError):
    pass


class ValidationError(DomainError):
    pass

