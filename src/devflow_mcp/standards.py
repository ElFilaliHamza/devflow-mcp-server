"""Coding-standards enforcer.

The default implementation is `RegexRuleChecker`, which parses a simple
markdown list of forbidden patterns and scans code for matches. Future
linters (ESLint, Flake8, etc.) should expose the same `check(code) -> list[Violation]`
interface so they can be swapped in via configuration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class Violation:
    pattern: str
    line: int
    match: str


class RuleChecker(Protocol):
    def check(self, code: str) -> list[Violation]: ...


@dataclass(frozen=True)
class CompiledRule:
    description: str
    pattern: str
    regex: re.Pattern[str]


_FORBID_RE = re.compile(
    r"^\s*-\s*(?P<desc>[^:`]+?):\s*forbid\s*`(?P<pat>[^`]+)`\s*$",
    re.MULTILINE,
)


class RegexRuleChecker:
    """Checker that flags any line matching a forbidden regex pattern."""

    def __init__(self, rules: list[CompiledRule]):
        self.rules = rules

    @classmethod
    def from_markdown(cls, markdown: str) -> "RegexRuleChecker":
        compiled: list[CompiledRule] = []
        for match in _FORBID_RE.finditer(markdown or ""):
            desc = match.group("desc").strip()
            pat = match.group("pat")
            try:
                regex = re.compile(pat)
            except re.error:
                continue
            compiled.append(CompiledRule(description=desc, pattern=pat, regex=regex))
        return cls(compiled)

    def check(self, code: str) -> list[Violation]:
        if not self.rules or not code:
            return []
        violations: list[Violation] = []
        for lineno, line in enumerate(code.splitlines(), start=1):
            for rule in self.rules:
                m = rule.regex.search(line)
                if m:
                    violations.append(
                        Violation(pattern=rule.pattern, line=lineno, match=m.group(0))
                    )
        return violations
