"""Error and issue types for the offline device library."""

from __future__ import annotations

from dataclasses import dataclass


class LoadError(Exception):
    """A fatal problem that prevents the registry from being read at all."""


@dataclass(frozen=True)
class Issue:
    """One validation problem attached to a profile or registry entry."""

    code: str
    message: str
    path: str = ""

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "path": self.path}

    def render(self) -> str:
        where = f"{self.path}: " if self.path else ""
        return f"{where}{self.message} [{self.code}]"
