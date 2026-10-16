"""SQLite storage for deals."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from constants import DISCLAIMER, OUTPUTS_DIR

CONTRACT_TYPES = ("MSA", "NDA", "DPA", "Reseller", "SOW", "Vendor terms")
STEPS = ("extracting", "checking_playbook", "drafting_redline", "routing")
STEP_LABELS = {
    "extracting": "Extracting",
    "checking_playbook": "Checking playbook",
    "drafting_redline": "Drafting redline",
    "routing": "Routing",
}
STATUS_LABELS = {
    "in_review": "In review",
    "waiting_on_counsel": "Waiting on counsel",
    "changes_requested": "Changes requested",
    "approved": "Approved",
    "rejected": "Rejected",
    "blocked": "Blocked",
    "needs_human": "Parse failed",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _extraction_detail(plan: dict) -> str:
    items = plan.get("extraction") or []
    if not items:
        return "Nothing extracted."
    failed = [item["field"] for item in items if item.get("error")]
    read = [item["field"] for item in items if not item.get("error")]
    if failed and not read:
        return f"Could not read {', '.join(failed)}."
    if failed:
        return f"Read {', '.join(read)}. Could not read {', '.join(failed)}."
    return f"Read {', '.join(read)}."


def _position_heading(text: str) -> str:
    """The section title only. The clause body stays in the playbook files."""
    for line in str(text or "").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.strip("-") == "" or cleaned == "***":
            continue
        cleaned = cleaned.lstrip("#").strip()
        if cleaned.startswith("**") and cleaned.endswith("**") and len(cleaned) > 4:
            cleaned = cleaned[2:-2].strip()
        return cleaned.replace("**", "").strip()
    return ""


def _playbook_for_storage(items: list) -> list:
    trimmed = []
    for item in items:
        if not isinstance(item, dict):
            trimmed.append(item)
            continue
        row = dict(item)
        for key in ("preferred", "fallback", "walk_away"):
            if key in row:
                row[key] = _position_heading(row.get(key) or "")
        trimmed.append(row)
    return trimmed


def _playbook_detail(plan: dict) -> str:
    families = ", ".join(item["family"] for item in plan["playbook"]) or "no family"
    return f"Matched {families}. Score {plan['score']}, {plan['band']}, tier {plan['tier']}."


def _end_detail(status: str) -> str:
    if status == "approved":
        return "END. This round was auto-approved."
    if status == "waiting_on_counsel":
        return "END. This round is waiting on counsel."
    if status == "blocked":
        return "END. This round stopped before a decision."
    if status == "rejected":
        return "END. This round was rejected."
    if status == "needs_human":
        return "END. Parse failed."
    return "END."


def counterparty_id(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name.strip())
    slug = "-".join(part for part in cleaned.split("-") if part) or "unknown"
    return f"CP-{slug[:48]}"


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class Store:
    def __init__(self, path: Path, step_seconds: float = 1.2, memo_dir: Path | None = None) -> None:
        self.path = path
        self.memo_dir = OUTPUTS_DIR if memo_dir is None else memo_dir
        self.step_seconds = step_seconds
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            self._ensure_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY,
                customer TEXT NOT NULL,
                counterparty_id TEXT NOT NULL,
                contract_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY,
                deal_id INTEGER NOT NULL REFERENCES deals(id),
                round_number INTEGER NOT NULL,
                contract_text TEXT NOT NULL,
                status TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                step_started_at TEXT NOT NULL,
                score INTEGER,
                band TEXT,
                tier INTEGER,
                turnaround_days INTEGER,
                path TEXT,
                route_reason TEXT,
                parse_ok INTEGER NOT NULL DEFAULT 1,
                injection INTEGER NOT NULL DEFAULT 0,
                liability_cap_redline INTEGER NOT NULL DEFAULT 0,
                needs_ceo INTEGER NOT NULL DEFAULT 0,
                ceo_signed INTEGER NOT NULL DEFAULT 0,
                redline_text TEXT,
                memo_name TEXT,
                envelope_sent_at TEXT,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY,
                round_id INTEGER NOT NULL REFERENCES rounds(id),
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY,
                counterparty_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY,
                round_id INTEGER NOT NULL REFERENCES rounds(id),
                step TEXT NOT NULL,
                detail TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info',
                at TEXT NOT NULL
            );
            """
        )
        deal_columns = {row[1] for row in conn.execute("PRAGMA table_info(deals)")}
        if "annual_value" in deal_columns:
            conn.execute("ALTER TABLE deals DROP COLUMN annual_value")
        round_columns = {row[1] for row in conn.execute("PRAGMA table_info(rounds)")}
        if "deadline_pressure" in round_columns:
            conn.execute("ALTER TABLE rounds DROP COLUMN deadline_pressure")
        trace_columns = {row[1] for row in conn.execute("PRAGMA table_info(traces)")}
        if "level" not in trace_columns:
            conn.execute("ALTER TABLE traces ADD COLUMN level TEXT NOT NULL DEFAULT 'info'")

    def create_deal(
        self,
        *,
        customer: str,
        contract_type: str,
        contract_text: str,
    ) -> dict:
        self._validate_new(customer, contract_type, contract_text)
        with self._lock, self._connect() as conn:
            now = _now()
            cp = counterparty_id(customer)
            cur = conn.execute(
                """
                INSERT INTO deals (customer, counterparty_id, contract_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (customer.strip(), cp, contract_type, _iso(now), _iso(now)),
            )
            deal_id = int(cur.lastrowid)
            self._insert_round(
                conn,
                deal_id=deal_id,
                round_number=1,
                customer=customer.strip(),
                contract_text=contract_text.strip(),
                now=now,
            )
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def add_round(self, deal_id: int, *, contract_text: str) -> dict:
        text = (contract_text or "").strip()
        if not text:
            raise ApiError("Paste the contract text.")
        with self._lock, self._connect() as conn:
            deal = self._deal_row(conn, deal_id)
            latest = self._latest_round(conn, deal_id)
            if latest["status"] not in {"changes_requested", "rejected"}:
                raise ApiError(
                    "Submit update is available after changes are requested or the round is rejected.",
                    409,
                )
            now = _now()
            self._insert_round(
                conn,
                deal_id=deal_id,
                round_number=int(latest["round_number"]) + 1,
                customer=deal["customer"],
                contract_text=text,
                now=now,
            )
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def list_deals(self, status: str | None = None) -> dict:
        with self._lock, self._connect() as conn:
            counts = self._counts(conn)
            rows = conn.execute(
                """
                SELECT d.*, r.round_number, r.status, r.tier, r.score, r.updated_at AS round_updated
                FROM deals d
                JOIN rounds r ON r.deal_id = d.id
                JOIN (
                    SELECT deal_id, MAX(round_number) AS round_number
                    FROM rounds GROUP BY deal_id
                ) latest ON latest.deal_id = r.deal_id AND latest.round_number = r.round_number
                ORDER BY r.updated_at DESC, d.id DESC
                """
            ).fetchall()
            deals = []
            for row in rows:
                if status == "waiting_on_counsel" and row["status"] not in {"waiting_on_counsel", "blocked"}:
                    continue
                if status and status != "waiting_on_counsel" and row["status"] != status:
                    continue
                deals.append(
                    {
                        "id": row["id"],
                        "customer": row["customer"],
                        "contract_type": row["contract_type"],
                        "round_number": row["round_number"],
                        "status": row["status"],
                        "status_label": STATUS_LABELS[row["status"]],
                        "tier": row["tier"],
                        "score": row["score"],
                        "updated_at": row["round_updated"],
                    }
                )
            return {"counts": counts, "deals": deals}

    def get_deal(self, deal_id: int) -> dict:
        with self._lock, self._connect() as conn:
            self._deal_row(conn, deal_id)
            return self._deal_payload(conn, deal_id)

    def record_extraction(self, deal_id: int, panel: dict, *, ok: bool) -> dict:
        """Store the extract the service already validated. This method does not call a model."""
        with self._lock, self._connect() as conn:
            rnd = self._latest_round(conn, deal_id)
            plan = json.loads(rnd["plan_json"] or "{}")
            plan.update(panel)
            status = "in_review" if ok else "needs_human"
            now = _now()
            conn.execute(
                """
                UPDATE rounds
                SET status = ?, parse_ok = ?, plan_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, int(ok), json.dumps(plan), _iso(now), rnd["id"]),
            )
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            self._activity(
                conn,
                rnd["id"],
                "Extraction",
                "Read five clause families." if ok else "Could not validate the extract.",
                now,
            )
            summary = _extraction_detail(plan)
            if ok:
                detail, level = f"Stored the extract. {summary}", "info"
            else:
                detail, level = f"Stored the extract with errors. {summary}", "error"
            self._traces(conn, rnd["id"], "extracting", detail, now, level=level)
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def record_playbook(self, deal_id: int, *, playbook: list, playbook_status: str) -> dict:
        """Store the playbook match the supervisor already requested. This method does not call a model."""
        with self._lock, self._connect() as conn:
            rnd = self._latest_round(conn, deal_id)
            plan = json.loads(rnd["plan_json"] or "{}")
            playbook = _playbook_for_storage(playbook)
            plan["playbook"] = playbook
            plan["playbook_status"] = playbook_status
            now = _now()
            conn.execute(
                "UPDATE rounds SET plan_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(plan), _iso(now), rnd["id"]),
            )
            families = ", ".join(item.get("family", "") for item in playbook) or "no family"
            self._activity(conn, rnd["id"], "Playbook", "Matched the extract to the playbook.", now)
            self._traces(
                conn,
                rnd["id"],
                "checking_playbook",
                f"Supervisor sent the extract to Playbook. Matched {families}.",
                now,
                level="info",
            )
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def record_review(
        self,
        deal_id: int,
        *,
        redline: str,
        score: int,
        band: str,
        tier: int,
        turnaround_days: int,
        status: str,
        path: str,
        route_reason: str,
        injection: bool,
        liability_cap_redline: bool,
        needs_ceo: bool,
    ) -> dict:
        """Store the redline, memo, score, and route. Does not call a model."""
        if status not in {"approved", "waiting_on_counsel", "blocked", "rejected"}:
            raise ApiError("Review status is not a finished route.")
        text = (redline or "").strip()
        if not text:
            raise ApiError("Redline text is required.")
        with self._lock, self._connect() as conn:
            rnd = self._latest_round(conn, deal_id)
            if rnd["status"] != "in_review":
                return self._deal_payload(conn, deal_id)
            plan = json.loads(rnd["plan_json"] or "{}")
            plan.update(
                {
                    "redline": text,
                    "score": score,
                    "band": band,
                    "tier": tier,
                    "turnaround_days": turnaround_days,
                    "path": path,
                    "route_reason": route_reason,
                    "injection": int(injection),
                    "liability_cap_redline": int(liability_cap_redline),
                    "needs_ceo": int(needs_ceo),
                    "final_status": status,
                }
            )
            deal = self._deal_row(conn, deal_id)
            memo_name = f"memo-deal-{deal_id}-round-{rnd['round_number']}.md"
            self.memo_dir.mkdir(parents=True, exist_ok=True)
            (self.memo_dir / memo_name).write_text(_memo_body(deal, rnd, plan), encoding="utf-8")
            now = _now()
            conn.execute(
                """
                UPDATE rounds SET
                    status = ?, step_index = 4, plan_json = ?, score = ?, band = ?, tier = ?,
                    turnaround_days = ?, path = ?, route_reason = ?, injection = ?,
                    liability_cap_redline = ?, needs_ceo = ?, redline_text = ?, memo_name = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(plan),
                    score,
                    band,
                    tier,
                    turnaround_days,
                    path,
                    route_reason,
                    int(injection),
                    int(liability_cap_redline),
                    int(needs_ceo),
                    text,
                    memo_name,
                    _iso(now),
                    rnd["id"],
                ),
            )
            self._activity(conn, rnd["id"], "Redline", "Drafted a redline and a memo.", now)
            self._traces(conn, rnd["id"], "drafting_redline", text, now, level="info")
            if status == "approved":
                routed = "Routed this round to approval."
            elif status == "blocked":
                routed = "Stopped this round before a decision."
            elif status == "rejected":
                routed = "Rejected this round."
            else:
                routed = "Left this round for a person to review."
            self._activity(conn, rnd["id"], "Reviewer", routed, now)
            self._traces(conn, rnd["id"], "routing", route_reason, now, level="info")
            self._traces(conn, rnd["id"], "end", _end_detail(status), now, level="info")
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def add_trace(self, deal_id: int, step: str, detail: str, *, level: str = "info") -> None:
        """Append one info or error line for the latest round. Does not call a model."""
        if level not in {"info", "error"}:
            raise ApiError("Trace level must be info or error.")
        text = (detail or "").strip()
        if not text:
            raise ApiError("Trace detail is required.")
        with self._lock, self._connect() as conn:
            rnd = self._latest_round(conn, deal_id)
            self._traces(conn, int(rnd["id"]), step, text, _now(), level=level)
            conn.commit()

    def edit_redline(self, deal_id: int, *, redline_text: str, liability_cap_redline: bool) -> dict:
        text = (redline_text or "").strip()
        if not text:
            raise ApiError("Redline text is required.")
        with self._lock, self._connect() as conn:
            self._advance_open(conn, deal_id)
            rnd = self._latest_round(conn, deal_id)
            if rnd["status"] != "waiting_on_counsel":
                raise ApiError("Edit redline is available while the deal is waiting on counsel.", 409)
            tier = int(rnd["tier"] or 1)
            turnaround = int(rnd["turnaround_days"] or 2)
            liability = bool(rnd["liability_cap_redline"]) or liability_cap_redline
            note = "Person edited the redline."
            if liability_cap_redline and tier < 2:
                tier = 2
                turnaround = 3
                note = "Person edited the redline. The liability cap changed, so the tier is now 2."
            now = _now()
            conn.execute(
                """
                UPDATE rounds
                SET redline_text = ?, liability_cap_redline = ?, tier = ?, turnaround_days = ?, updated_at = ?
                WHERE id = ?
                """,
                (text, int(liability), tier, turnaround, _iso(now), rnd["id"]),
            )
            self._activity(conn, rnd["id"], "Person", note, now)
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def approve(self, deal_id: int) -> dict:
        with self._lock, self._connect() as conn:
            self._advance_open(conn, deal_id)
            rnd = self._latest_round(conn, deal_id)
            if not _actions(rnd)["approve"]:
                raise ApiError("Approve is not available on this deal.", 409)
            if rnd["envelope_sent_at"]:
                raise ApiError("The envelope was already sent.", 409)
            now = _now()
            conn.execute(
                """
                UPDATE rounds
                SET status = 'approved', path = 'counsel', envelope_sent_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (_iso(now), _iso(now), rnd["id"]),
            )
            self._activity(conn, rnd["id"], "Person", "Approved this round for internal routing.", now)
            self._episodic(conn, self._deal_row(conn, deal_id), int(rnd["round_number"]), "was approved for internal routing", now)
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def request_changes(self, deal_id: int) -> dict:
        return self._close(deal_id, "changes_requested", "Requested clause changes.", "had clause changes requested")

    def reject(self, deal_id: int) -> dict:
        return self._close(deal_id, "rejected", "Rejected this round.", "was rejected")

    def ceo_signoff(self, deal_id: int) -> dict:
        with self._lock, self._connect() as conn:
            self._advance_open(conn, deal_id)
            rnd = self._latest_round(conn, deal_id)
            if not _actions(rnd)["ceo_signoff"]:
                raise ApiError("CEO sign-off is not available on this deal.", 409)
            now = _now()
            conn.execute(
                """
                UPDATE rounds
                SET ceo_signed = 1, status = 'waiting_on_counsel', updated_at = ?
                WHERE id = ?
                """,
                (_iso(now), rnd["id"]),
            )
            self._activity(conn, rnd["id"], "Person", "Recorded CEO sign-off. The round is waiting on counsel.", now)
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def memo_file(self, deal_id: int, round_id: int) -> Path:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT memo_name, step_index, status FROM rounds WHERE id = ? AND deal_id = ?",
                (round_id, deal_id),
            ).fetchone()
            if row is None or not row["memo_name"]:
                raise ApiError("No memo for this round.", 404)
            if row["status"] == "in_review" and int(row["step_index"]) < 3:
                raise ApiError("No memo for this round.", 404)
            path = self.memo_dir / row["memo_name"]
            if not path.is_file():
                raise ApiError("No memo for this round.", 404)
            return path

    def _close(self, deal_id: int, status: str, activity: str, episodic: str) -> dict:
        with self._lock, self._connect() as conn:
            self._advance_open(conn, deal_id)
            rnd = self._latest_round(conn, deal_id)
            if rnd["status"] != "waiting_on_counsel":
                raise ApiError("That decision is available while the deal is waiting on counsel.", 409)
            now = _now()
            conn.execute(
                "UPDATE rounds SET status = ?, updated_at = ? WHERE id = ?",
                (status, _iso(now), rnd["id"]),
            )
            self._activity(conn, rnd["id"], "Person", activity, now)
            self._episodic(conn, self._deal_row(conn, deal_id), int(rnd["round_number"]), episodic, now)
            conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(now), deal_id))
            conn.commit()
            return self._deal_payload(conn, deal_id)

    def _validate_new(self, customer: str, contract_type: str, contract_text: str) -> None:
        if not (customer or "").strip():
            raise ApiError("Customer is required.")
        if contract_type not in CONTRACT_TYPES:
            raise ApiError("Choose a contract type.")
        if not (contract_text or "").strip():
            raise ApiError("Paste the contract text.")

    def _insert_round(
        self,
        conn: sqlite3.Connection,
        *,
        deal_id: int,
        round_number: int,
        customer: str,
        contract_text: str,
        now: datetime,
    ) -> None:
        cur = conn.execute(
            """
            INSERT INTO rounds (
                deal_id, round_number, contract_text, status, step_index,
                step_started_at, plan_json, created_at, updated_at
            ) VALUES (?, ?, ?, 'in_review', 0, ?, ?, ?, ?)
            """,
            (
                deal_id,
                round_number,
                contract_text,
                _iso(now),
                "{}",
                _iso(now),
                _iso(now),
            ),
        )
        round_id = int(cur.lastrowid)
        self._activity(conn, round_id, "Person", "Submitted this round.", now)
        deal = self._deal_row(conn, deal_id)
        self._memory(
            conn,
            deal["counterparty_id"],
            "episodic",
            f"Round {round_number} for {customer} was submitted.",
            now,
        )

    def _advance_open(self, conn: sqlite3.Connection, deal_id: int | None = None) -> None:
        query = "SELECT * FROM rounds WHERE status = 'in_review'"
        args: tuple = ()
        if deal_id is not None:
            query += " AND deal_id = ?"
            args = (deal_id,)
        for row in conn.execute(query, args).fetchall():
            self._advance_round(conn, row)

    def _advance_round(self, conn: sqlite3.Connection, row: sqlite3.Row) -> None:
        if row["status"] != "in_review":
            return
        index = int(row["step_index"])
        if index >= 4:
            return
        started = datetime.fromisoformat(row["step_started_at"])
        elapsed = (_now() - started).total_seconds()
        hops = 4 - index if self.step_seconds <= 0 else int(elapsed // self.step_seconds)
        if hops <= 0:
            return
        plan = json.loads(row["plan_json"] or "{}")
        if "score" not in plan:
            return
        deal = self._deal_row(conn, row["deal_id"])
        for _ in range(min(hops, 4 - index)):
            index += 1
            at = _now() if self.step_seconds <= 0 else started + timedelta(seconds=self.step_seconds * index)
            if index == 1:
                self._activity(conn, row["id"], "Extraction", "Read the submitted text into fields.", at)
                self._traces(conn, row["id"], "extracting", _extraction_detail(plan), at, level="info")
            elif index == 2:
                self._activity(conn, row["id"], "Playbook", "Matched playbook positions and stored the score.", at)
                self._traces(conn, row["id"], "checking_playbook", _playbook_detail(plan), at, level="info")
            elif index == 3:
                memo_name = f"memo-deal-{row['deal_id']}-round-{row['round_number']}.md"
                self.memo_dir.mkdir(parents=True, exist_ok=True)
                (self.memo_dir / memo_name).write_text(_memo_body(deal, row, plan), encoding="utf-8")
                conn.execute(
                    "UPDATE rounds SET memo_name = ?, redline_text = ? WHERE id = ?",
                    (memo_name, plan["redline"], row["id"]),
                )
                self._activity(conn, row["id"], "Redline", "Drafted a redline and a memo.", at)
                self._traces(conn, row["id"], "drafting_redline", plan["redline"], at, level="info")
            elif index == 4:
                self._apply_final(conn, row, plan, at)
                self._traces(conn, row["id"], "routing", plan["route_reason"], at, level="info")
                self._traces(conn, row["id"], "end", _end_detail(plan["final_status"]), at, level="info")
        conn.execute(
            "UPDATE rounds SET step_index = ?, step_started_at = ?, updated_at = ? WHERE id = ?",
            (index, _iso(_now()), _iso(_now()), row["id"]),
        )
        conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (_iso(_now()), row["deal_id"]))

    def _apply_final(self, conn: sqlite3.Connection, row: sqlite3.Row, plan: dict, at: datetime) -> None:
        status = plan["final_status"]
        envelope = _iso(at) if status == "approved" else None
        conn.execute(
            """
            UPDATE rounds SET
                status = ?, score = ?, band = ?, tier = ?, turnaround_days = ?, path = ?,
                route_reason = ?, parse_ok = ?, injection = ?, liability_cap_redline = ?,
                needs_ceo = ?, envelope_sent_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                plan["score"],
                plan["band"],
                plan["tier"],
                plan["turnaround_days"],
                plan["path"],
                plan["route_reason"],
                int(plan["parse_ok"]),
                int(plan["injection"]),
                int(plan["liability_cap_redline"]),
                int(plan["needs_ceo"]),
                envelope,
                _iso(at),
                row["id"],
            ),
        )
        if status == "approved":
            action = "Routed this round to approval."
        elif status == "blocked":
            action = "Stopped this round before a decision."
        else:
            action = "Left this round for a person to review."
        self._activity(conn, row["id"], "Reviewer", action, at)

    def _deal_payload(self, conn: sqlite3.Connection, deal_id: int) -> dict:
        deal = self._deal_row(conn, deal_id)
        rounds = conn.execute(
            "SELECT * FROM rounds WHERE deal_id = ? ORDER BY round_number DESC",
            (deal_id,),
        ).fetchall()
        current = self._round_payload(conn, rounds[0], include_actions=True)
        earlier = [self._round_payload(conn, item, include_actions=False) for item in rounds[1:]]
        facts = conn.execute(
            """
            SELECT kind, text, created_at FROM memory
            WHERE counterparty_id = ?
            ORDER BY id DESC LIMIT 8
            """,
            (deal["counterparty_id"],),
        ).fetchall()
        posture = next((row["text"] for row in facts if row["kind"] == "semantic"), "")
        return {
            "id": deal["id"],
            "customer": deal["customer"],
            "counterparty_id": deal["counterparty_id"],
            "contract_type": deal["contract_type"],
            "round": current,
            "earlier_rounds": earlier,
            "memory": {
                "posture": posture,
                "facts": [{"kind": row["kind"], "text": row["text"], "at": row["created_at"]} for row in facts],
            },
        }

    def _round_payload(self, conn: sqlite3.Connection, row: sqlite3.Row, *, include_actions: bool) -> dict:
        plan = json.loads(row["plan_json"] or "{}")
        stored_playbook = plan.get("playbook") or []
        if stored_playbook:
            trimmed_playbook = _playbook_for_storage(stored_playbook)
            if trimmed_playbook != stored_playbook:
                plan["playbook"] = trimmed_playbook
                conn.execute(
                    "UPDATE rounds SET plan_json = ? WHERE id = ?",
                    (json.dumps(plan), row["id"]),
                )
        index = int(row["step_index"])
        extracted = bool(plan.get("extracted"))
        playbook_ready = bool(plan.get("playbook_status"))
        pipeline_done = row["status"] not in {"in_review", "needs_human"}
        show_extraction = extracted or pipeline_done or index >= 1
        show_playbook = playbook_ready or ((pipeline_done or index >= 2) and "score" in plan)
        show_redline = (pipeline_done or index >= 3) and ("redline" in plan or row["redline_text"])
        actions = _actions(row) if include_actions else _no_actions()
        show_reasons = include_actions and (
            row["status"] == "blocked" or (row["status"] == "waiting_on_counsel" and not actions["approve"])
        )
        activity = conn.execute(
            "SELECT actor, action, at FROM activity WHERE round_id = ? ORDER BY id ASC",
            (row["id"],),
        ).fetchall()
        traces = conn.execute(
            "SELECT step, detail, level, at FROM traces WHERE round_id = ? ORDER BY id ASC",
            (row["id"],),
        ).fetchall()
        step = STEPS[min(index, 3)] if row["status"] == "in_review" else None
        if pipeline_done:
            score, band, tier, turnaround = row["score"], row["band"], row["tier"], row["turnaround_days"]
            liability = bool(row["liability_cap_redline"])
        elif show_playbook and "score" in plan:
            score, band, tier, turnaround = plan["score"], plan["band"], plan["tier"], plan["turnaround_days"]
            liability = bool(plan["liability_cap_redline"])
        else:
            score = band = tier = turnaround = None
            liability = False
        return {
            "id": row["id"],
            "round_number": row["round_number"],
            "contract_text": row["contract_text"],
            "status": row["status"],
            "status_label": STATUS_LABELS[row["status"]],
            "step": step,
            "step_label": STEP_LABELS.get(step or "", ""),
            "steps": [
                {
                    "id": name,
                    "label": STEP_LABELS[name],
                    "state": _step_state(
                        index,
                        pos,
                        extracted=extracted,
                        needs_human=row["status"] == "needs_human",
                        playbook_done=playbook_ready,
                    ),
                }
                for pos, name in enumerate(STEPS)
            ],
            "score": score,
            "band": band,
            "tier": tier,
            "turnaround_days": turnaround,
            "path": row["path"],
            "path_label": "Auto" if row["path"] == "auto" else "Counsel" if row["path"] == "counsel" else "",
            "route_reason": row["route_reason"] if pipeline_done else "",
            "extraction": (plan.get("extraction") or []) if show_extraction else [],
            "clauses": (plan.get("clauses") or []) if show_extraction else [],
            "raw_json": (plan.get("raw_json") or "") if show_extraction else "",
            "extracted": extracted,
            "playbook": (plan.get("playbook") or []) if show_playbook else [],
            "playbook_status": (plan.get("playbook_status") or "") if show_playbook else "",
            "redline": (row["redline_text"] or plan.get("redline") or "") if show_redline else "",
            "memo_name": row["memo_name"] if show_redline else "",
            "envelope_sent_at": row["envelope_sent_at"],
            "liability_cap_redline": liability,
            "actions": actions,
            "block_reasons": _block_reasons(row) if show_reasons else [],
            "activity": [{"actor": item["actor"], "action": item["action"], "at": item["at"]} for item in activity],
            "traces": [
                {
                    "step": item["step"],
                    "detail": item["detail"],
                    "level": item["level"] or "info",
                    "at": item["at"],
                }
                for item in traces
            ],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _counts(self, conn: sqlite3.Connection) -> dict:
        rows = conn.execute(
            """
            SELECT r.status, COUNT(*) AS n
            FROM rounds r
            JOIN (
                SELECT deal_id, MAX(round_number) AS round_number
                FROM rounds GROUP BY deal_id
            ) latest ON latest.deal_id = r.deal_id AND latest.round_number = r.round_number
            GROUP BY r.status
            """
        ).fetchall()
        raw = {row["status"]: row["n"] for row in rows}
        blocked = raw.get("blocked", 0)
        return {
            "in_review": raw.get("in_review", 0),
            "waiting_on_counsel": raw.get("waiting_on_counsel", 0) + blocked,
            "changes_requested": raw.get("changes_requested", 0),
            "approved": raw.get("approved", 0),
            "rejected": raw.get("rejected", 0),
            "blocked": blocked,
            "needs_human": raw.get("needs_human", 0),
        }

    def _deal_row(self, conn: sqlite3.Connection, deal_id: int) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if row is None:
            raise ApiError("Deal not found.", 404)
        return row

    def _latest_round(self, conn: sqlite3.Connection, deal_id: int) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM rounds WHERE deal_id = ? ORDER BY round_number DESC LIMIT 1",
            (deal_id,),
        ).fetchone()
        if row is None:
            raise ApiError("Deal not found.", 404)
        return row

    def _traces(
        self,
        conn: sqlite3.Connection,
        round_id: int,
        step: str,
        detail: str,
        at: datetime,
        *,
        level: str = "info",
    ) -> None:
        conn.execute(
            "INSERT INTO traces (round_id, step, detail, level, at) VALUES (?, ?, ?, ?, ?)",
            (round_id, step, detail, level, _iso(at)),
        )

    def _activity(self, conn: sqlite3.Connection, round_id: int, actor: str, action: str, at: datetime) -> None:
        conn.execute(
            "INSERT INTO activity (round_id, actor, action, at) VALUES (?, ?, ?, ?)",
            (round_id, actor, action, _iso(at)),
        )

    def _memory(self, conn: sqlite3.Connection, cp: str, kind: str, text: str, at: datetime) -> None:
        conn.execute(
            "INSERT INTO memory (counterparty_id, kind, text, created_at) VALUES (?, ?, ?, ?)",
            (cp, kind, text, _iso(at)),
        )

    def _episodic(self, conn: sqlite3.Connection, deal: sqlite3.Row, round_number: int, verb: str, at: datetime) -> None:
        self._memory(
            conn,
            deal["counterparty_id"],
            "episodic",
            f"Round {round_number} for {deal['customer']} {verb}.",
            at,
        )


def _step_state(
    index: int,
    pos: int,
    *,
    extracted: bool = False,
    needs_human: bool = False,
    playbook_done: bool = False,
) -> str:
    if extracted and pos == 0:
        return "failed" if needs_human else "done"
    if playbook_done and pos == 1:
        return "done"
    if index > pos:
        return "done"
    if index == pos:
        return "current"
    return "upcoming"


def _no_actions() -> dict:
    return {
        "edit_redline": False,
        "approve": False,
        "changes": False,
        "reject": False,
        "submit_update": False,
        "ceo_signoff": False,
    }


def _actions(row: sqlite3.Row) -> dict:
    actions = _no_actions()
    status = row["status"]
    if status == "waiting_on_counsel":
        actions["edit_redline"] = True
        actions["changes"] = True
        actions["reject"] = True
        actions["approve"] = bool(row["parse_ok"]) and not (bool(row["needs_ceo"]) and not bool(row["ceo_signed"]))
    elif status == "blocked":
        actions["ceo_signoff"] = bool(row["needs_ceo"]) and not bool(row["injection"]) and not bool(row["ceo_signed"])
    elif status in {"changes_requested", "rejected"}:
        actions["submit_update"] = True
    return actions


def _block_reasons(row: sqlite3.Row) -> list[str]:
    reasons = []
    if not row["parse_ok"]:
        reasons.append("A field could not be read from the submitted text.")
    if row["injection"]:
        reasons.append("Prompt injection was detected in the submitted text.")
    if row["needs_ceo"] and not row["ceo_signed"]:
        reasons.append("The score is below 50. CEO sign-off is required before a decision.")
    return reasons


def _memo_body(deal: sqlite3.Row, row: sqlite3.Row, plan: dict) -> str:
    return "\n".join(
        [
            f"# Internal memo — {deal['customer']} round {row['round_number']}",
            "",
            plan["route_reason"],
            "",
            "## Redline",
            "",
            plan["redline"],
            "",
            "---",
            "",
            DISCLAIMER,
            "",
        ]
    )
