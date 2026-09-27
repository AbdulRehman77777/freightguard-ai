"""Domain-specific exceptions exposed by FreightGuard AI."""


class FreightGuardError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(FreightGuardError):
    """Required application configuration is unavailable or invalid."""


class DocumentReadError(FreightGuardError):
    """A document cannot be opened or converted into usable text."""


class DocumentExtractionError(FreightGuardError):
    """The LLM extraction operation did not produce a trustworthy result."""


class SchemaValidationError(FreightGuardError):
    """Extracted data does not satisfy the strict freight schema."""
