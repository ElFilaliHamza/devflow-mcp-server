from devflow_mcp.standards import RegexRuleChecker, Violation


RULES = """\
# Style guide for Acme
- No console.log in shipped code: forbid `console\\.log`
- Use === not ==: forbid `([^!=])==([^=])`
"""


def test_check_snippet_finds_console_log():
    checker = RegexRuleChecker.from_markdown(RULES)
    violations = checker.check("const x = 1; console.log(x);")
    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, Violation)
    assert "console" in v.pattern
    assert v.line == 1
    assert v.match == "console.log"


def test_check_snippet_finds_double_equals():
    checker = RegexRuleChecker.from_markdown(RULES)
    violations = checker.check("if (a == b) { return; }")
    assert len(violations) == 1
    assert "==" in violations[0].match
    assert violations[0].line == 1


def test_check_snippet_clean_code_returns_empty():
    checker = RegexRuleChecker.from_markdown(RULES)
    assert checker.check("const x = a === b;") == []


def test_check_snippet_reports_line_numbers():
    checker = RegexRuleChecker.from_markdown(RULES)
    code = "const a = 1;\nconst b = 2;\nconsole.log(a);\n"
    violations = checker.check(code)
    assert len(violations) == 1
    assert violations[0].line == 3


def test_empty_ruleset_returns_no_violations():
    checker = RegexRuleChecker(rules=[])
    assert checker.check("anything goes here") == []


def test_from_markdown_ignores_comments_and_blank_lines():
    checker = RegexRuleChecker.from_markdown("# header\n\n# another\n")
    assert checker.rules == []


def test_from_markdown_handles_invalid_regex_gracefully():
    md = "- Bad regex: forbid `(`"
    checker = RegexRuleChecker.from_markdown(md)
    # Should not raise; bad rules are skipped, not stored.
    assert checker.rules == []
