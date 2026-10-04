"""Persistence failure categories; callers supply metadata-only messages."""


class PersistenceError(Exception):
    """A controlled persistence boundary failed."""


class ConflictError(PersistenceError):
    """Stored identity or revision conflicts with the attempted operation."""


class NotFoundError(PersistenceError):
    """An owner-scoped record is absent."""


class CorruptStorageError(PersistenceError):
    """Stored data fails the accepted domain or integrity contract."""


class DeletedWorkspaceError(PersistenceError):
    """The workspace has been deleted and cannot be restored by an ordinary write."""


class UnsupportedEventError(PersistenceError):
    """The event cannot accompany the requested state operation."""


class SchemaMismatchError(PersistenceError):
    """The database migration state is absent, unknown or unavailable."""
