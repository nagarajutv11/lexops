"""Risk, renewal, and the memo. Failures come back as observations.

Wrap order matches Day 1 Session 2: circuit check, then retry, then the tool.
The memo writes the calculator score and the calendar dates, not model guesses.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from ai.reliability import CircuitBreaker, CircuitOpenError, ToolFailure, call_with_retry
from ai.scoring import renewal_calendar, score_clause
from constants import OUTPUTS_DIR, SHORT_DISCLAIMER


def clause_risk_calculator(clause_text: str) -> dict:
    risk = score_clause(clause_text)
    return risk.as_dict()


def renewal_date_calendar(
    *,
    as_of: str,
    term_text: str = "",
    term_months: int | None = None,
    effective: str | None = None,
    notice_days: int = 30,
    auto_renew: bool = True,
) -> dict:
    return renewal_calendar(
        as_of=as_of,
        term_text=term_text,
        term_months=term_months,
        effective=effective,
        notice_days=notice_days,
        auto_renew=auto_renew,
    )


def summary_memo_writer(
    *,
    review_id: str,
    counterparty: str,
    clause_text: str,
    as_of: str,
    term_text: str = "",
    term_months: int | None = None,
    effective: str | None = None,
    notice_days: int = 30,
    directory: Path | None = None,
) -> dict:
    risk = score_clause(clause_text)
    renewal = renewal_date_calendar(
        as_of=as_of,
        term_text=term_text or clause_text,
        term_months=term_months,
        effective=effective,
        notice_days=notice_days,
    )
    folder = directory or OUTPUTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{review_id}.md"
    path.write_text(
        "\n".join(
            [
                f"# LexOps review memo — {counterparty}",
                "",
                SHORT_DISCLAIMER,
                "",
                "## Risk",
                f"Score: {risk.score:.0f}",
                f"Band: {risk.band}",
                "",
                "## Renewal",
                f"Next renewal: {renewal['next_renewal']}",
                f"Notice window opens: {renewal['notice_window_opens']}",
                "",
                "## Clause",
                clause_text.strip(),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "path": str(path),
        "score": risk.score,
        "band": risk.band,
        "next_renewal": renewal["next_renewal"],
        "notice_window_opens": renewal["notice_window_opens"],
        "disclaimer": SHORT_DISCLAIMER,
    }


class ToolKit:
    """The three review tools, each behind the breaker and the retry loop."""

    def __init__(
        self,
        *,
        breaker: CircuitBreaker | None = None,
        attempts: int = 3,
        sleeper: Callable[[float], None] = lambda _seconds: None,
        directory: Path | None = None,
    ) -> None:
        self.breaker = breaker or CircuitBreaker()
        self.attempts = attempts
        self.sleeper = sleeper
        self.directory = directory
        self.log: list[dict] = []
        self._force: set[str] = set()
        self.tools = {
            "clause_risk_calculator": self._risk,
            "renewal_date_calendar": self._renewal,
            "summary_memo_writer": self._memo,
        }

    def force(self, name: str) -> None:
        self._force.add(name)

    def invoke(self, name: str, arguments: dict | None = None) -> str:
        """Run one tool. A failure is an observation string, not an exception."""
        arguments = dict(arguments or {})
        if name == "summary_memo_writer" and self.directory is not None:
            arguments.setdefault("directory", self.directory)
        self.log.append({"tool": name, "arguments": {key: value for key, value in arguments.items() if key != "directory"}})
        try:
            self.breaker.before_call()
        except CircuitOpenError as exc:
            self.breaker.record_failure()
            return f"ERROR: {exc}"
        if name not in self.tools:
            self.breaker.record_failure()
            return f"ERROR: unknown tool {name}"

        def attempt() -> dict:
            if name in self._force:
                self._force.remove(name)
                raise ToolFailure(f"forced failure in {name}")
            return self.tools[name](arguments)

        try:
            result = call_with_retry(attempt, attempts=self.attempts, sleeper=self.sleeper)
        except Exception as exc:
            self.breaker.record_failure()
            return f"ERROR: {exc}"
        self.breaker.record_success()
        return json.dumps(result)

    def _risk(self, arguments: dict) -> dict:
        return clause_risk_calculator(arguments["clause_text"])

    def _renewal(self, arguments: dict) -> dict:
        return renewal_date_calendar(
            as_of=arguments["as_of"],
            term_text=arguments.get("term_text", ""),
            term_months=arguments.get("term_months"),
            effective=arguments.get("effective"),
            notice_days=int(arguments.get("notice_days", 30)),
            auto_renew=bool(arguments.get("auto_renew", True)),
        )

    def _memo(self, arguments: dict) -> dict:
        return summary_memo_writer(
            review_id=arguments["review_id"],
            counterparty=arguments["counterparty"],
            clause_text=arguments["clause_text"],
            as_of=arguments["as_of"],
            term_text=arguments.get("term_text", ""),
            term_months=arguments.get("term_months"),
            effective=arguments.get("effective"),
            notice_days=int(arguments.get("notice_days", 30)),
            directory=arguments.get("directory"),
        )
