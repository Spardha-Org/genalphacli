"""Parser modules for extracting API routes from source code."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from genalphacli.models import ParsedRoute


class FrameworkParser(Protocol):
    """Contract all framework parsers must implement."""

    @property
    def framework_name(self) -> str: ...

    def supported_extensions(self) -> list[str]: ...

    def parse(self, files: list[Path], repo_root: Path) -> list[ParsedRoute]: ...


# Registry — new frameworks register here
PARSER_REGISTRY: dict[str, FrameworkParser] = {}


def register_parser(parser: FrameworkParser) -> None:
    PARSER_REGISTRY[parser.framework_name] = parser
