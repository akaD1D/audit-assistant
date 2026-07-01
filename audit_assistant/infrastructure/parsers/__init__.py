"""Document parsers: raw bytes -> unified :class:`ParsedDocument`.

Each parser handles one family of file types and satisfies the
:class:`audit_assistant.domain.interfaces.Parser` port. The
:class:`ParserRegistry` selects the right parser for a given file type.
"""

from audit_assistant.infrastructure.parsers.base import (
    ParserRegistry,
    build_default_registry,
    detect_file_type,
)

__all__ = ["ParserRegistry", "build_default_registry", "detect_file_type"]
