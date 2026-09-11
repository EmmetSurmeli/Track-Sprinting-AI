"""Durable local training log, independent of temporary browser sessions."""
from datetime import date, datetime, timezone
from contextlib import contextmanager
from pathlib import Path
import json
import re
import shutil
import sqlite3
import uuid

from .artifacts import read_json


class HistoryStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, session_date TEXT NOT NULL, label TEXT NOT NULL,
                event TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL,
                summary_json TEXT NOT NULL, manifest_json TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / "history.sqlite3", timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def directory(self, analysis_id):
        if not re.fullmatch(r"[a-f0-9]{64}", analysis_id):
            raise ValueError("Invalid analysis identifier.")
        return self.root / "analyses" / analysis_id

    def save(self, source: Path, session_date: date, label: str, event: str, notes=""):
        """Save once per computed analysis; repeated saves edit its log metadata."""
        summary = read_json(source / "summary.json")
        manifest = read_json(source / "manifest.json")
        identity = summary["analysis_id"]
        if manifest["analysis_id"] != identity:
            raise ValueError("Analysis and completion marker do not match.")
        destination = self.directory(identity)
        if not destination.exists():
            destination.parent.mkdir(exist_ok=True)
            staging = destination.parent / ("pending-" + uuid.uuid4().hex)
            staging.mkdir()
            try:
                for name in ("summary.json", "series.json", "manifest.json", "landmarks.npz", "original.mp4", "annotated.mp4"):
                    shutil.copyfile(source / name, staging / name)
                shutil.copytree(source / "frames", staging / "frames")
                if (source / "reports").is_dir():
                    shutil.copytree(source / "reports", staging / "reports")
                for name in ("contacts.json", "contact_results.json"):
                    if (source / name).exists():
                        shutil.copyfile(source / name, staging / name)
                try:
                    staging.rename(destination)
                except OSError:
                    if not destination.exists():
                        raise
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        with self.connect() as db:
            db.execute("""INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET session_date=excluded.session_date,
                label=excluded.label, event=excluded.event, notes=excluded.notes""",
                (identity, date.fromisoformat(str(session_date)).isoformat(), label[:120], event[:40],
                 notes[:1000], datetime.now(timezone.utc).isoformat(),
                 json.dumps(summary, allow_nan=False), json.dumps(manifest, allow_nan=False)))
        return identity

    def list(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM sessions ORDER BY session_date, created_at, id").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json"))
            item["manifest"] = json.loads(item.pop("manifest_json"))
            contact_path = self.directory(item["id"]) / "contact_results.json"
            item["contact_results"] = read_json(contact_path) if contact_path.exists() else None
            result.append(item)
        return result

    def update(self, identity, session_date, label, event, notes):
        self.directory(identity)  # Validate even though identifiers are bound SQL parameters.
        with self.connect() as db:
            db.execute("UPDATE sessions SET session_date=?, label=?, event=?, notes=? WHERE id=?",
                (date.fromisoformat(str(session_date)).isoformat(), label[:120], event[:40], notes[:1000], identity))

    def remove(self, identity):
        """Remove from active calendar; retain files/metadata in a recoverable local archive."""
        self.directory(identity)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS removed_sessions AS SELECT * FROM sessions WHERE 0")
            db.execute("INSERT INTO removed_sessions SELECT * FROM sessions WHERE id=?", (identity,))
            db.execute("DELETE FROM sessions WHERE id=?", (identity,))


def compare_sessions(current, previous):
    """Observed differences only. There is no evidence-based 'ideal angle' score."""
    a, b = current["summary"], previous["summary"]
    warnings = []
    if current["event"] != previous["event"]:
        warnings.append("The events differ.")
    if a["review_side"] != b["review_side"]:
        warnings.append("The model review sides differ.")
    if any(s["config"]["near_side"] == "unknown" for s in (a, b)):
        warnings.append("The camera-facing anatomical side is unconfirmed in at least one session.")
    if any(s["config"]["camera_moving"] for s in (a, b)):
        warnings.append("Camera movement affects comparability; orientation metrics are excluded.")
    ma, mb = current["manifest"], previous["manifest"]
    version_keys = ("pipeline_version", "model_sha256", "dependencies")
    changed_method = any(ma.get(k) != mb.get(k) for k in version_keys)
    if changed_method or a["config"].get("score_threshold") != b["config"].get("score_threshold"):
        warnings.append("The model, processing version, dependencies or visibility threshold changed.")
        changed_method = True
    if current["id"] == previous["id"]:
        warnings.append("These are the same analysis.")
    if a["video"]["sha256"] == b["video"]["sha256"]:
        warnings.append("Both analyses come from the same source video; they are not independent training sessions.")
    compatible = (current["event"] == previous["event"] and a["review_side"] == b["review_side"]
                  and not changed_method and current["id"] != previous["id"])
    rows = []
    if compatible:
        for ref, metric in a["metrics"].items():
            old = b["metrics"].get(ref)
            if metric["side"] != a["review_side"] or not old:
                continue
            if min(metric["coverage"], old["coverage"]) < .85:
                continue
            if metric["metric"] in ("trunk", "thigh") and any(s["config"]["camera_moving"] for s in (a, b)):
                continue
            for stat, label in (("min", "minimum"), ("max", "maximum")):
                rows.append({"Measurement": f"{metric['label']} · {label}", "Previous (°)": old[stat],
                             "Current (°)": metric[stat], "Change (°)": round(metric[stat] - old[stat], 1)})
    return rows, warnings


def compare_contact_sessions(current, previous):
    a, b = current.get("contact_results"), previous.get("contact_results")
    if (not a or not b or not a.get("comparison") or not b.get("comparison") or
            a.get("method") != b.get("method") or current["event"] != previous["event"]):
        return []
    rows = []
    for side in ("left", "right"):
        new, old = a["sides"][side], b["sides"][side]
        rows.append({"Side": side, "Previous mean (ms)": old["mean_ms"], "Current mean (ms)": new["mean_ms"],
            "Change (ms)": round(new["mean_ms"] - old["mean_ms"], 2),
            "Change lower bound (ms)": round(new["lower_ms"] - old["upper_ms"], 2),
            "Change upper bound (ms)": round(new["upper_ms"] - old["lower_ms"], 2)})
    return rows
