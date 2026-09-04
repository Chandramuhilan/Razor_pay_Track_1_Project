"""
SQLite Database Persistent Ledger Service.
Maintains durable audit trails, transaction session records, bounding engine evaluations,
and hexadecimal audit record IDs (e.g. 0x8F4A1C9).
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_FILE = "merchant_ledger.db"

class DatabaseLedger:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_record_id TEXT UNIQUE NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    state TEXT NOT NULL,
                    title TEXT NOT NULL,
                    intent TEXT,
                    vector_matches_count INTEGER DEFAULT 0,
                    budget_max_inr REAL DEFAULT 0.0,
                    offered_amount_inr REAL DEFAULT 0.0,
                    bounding_rule_status TEXT DEFAULT 'PASSED',
                    razorpay_order_id TEXT,
                    razorpay_payment_id TEXT,
                    ap2_signature_status TEXT DEFAULT 'VALID',
                    details_json TEXT,
                    prev_hash TEXT,
                    current_hash TEXT
                )
            """)
            conn.commit()

    def generate_audit_record_id(self, session_id: str, seq: int) -> str:
        raw = f"{session_id}:{seq}:{datetime.now(timezone.utc).timestamp()}"
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:7].upper()
        return f"0x{digest}"

    def insert_record(
        self,
        session_id: str,
        seq: int,
        actor: str,
        state: str,
        title: str,
        details: Dict[str, Any],
        prev_hash: str = "",
        current_hash: str = "",
        audit_record_id: Optional[str] = None
    ) -> str:
        audit_rec_id = audit_record_id or self.generate_audit_record_id(session_id, seq)
        intent = details.get("intent", details.get("user_query", "Hardware Procurement"))
        vector_count = details.get("matched_count", details.get("vector_matches_count", 0))
        budget_max = details.get("max_budget_inr", details.get("authorized_max_inr", 0.0))
        offered_amt = details.get("total_amount_inr", details.get("price_inr", 0.0))
        bounding_status = "FAILED" if state == "FAILED" or details.get("valid") is False else "PASSED"
        rzp_order = details.get("razorpay_order_id", details.get("order_id", ""))
        rzp_pay = details.get("razorpay_payment_id", details.get("payment_id", ""))
        ap2_status = "INVALID" if details.get("valid") is False else "VALID"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_records (
                    audit_record_id, session_id, timestamp, actor, state, title,
                    intent, vector_matches_count, budget_max_inr, offered_amount_inr,
                    bounding_rule_status, razorpay_order_id, razorpay_payment_id,
                    ap2_signature_status, details_json, prev_hash, current_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit_rec_id,
                session_id,
                datetime.now(timezone.utc).isoformat(),
                actor,
                state,
                title,
                str(intent),
                int(vector_count),
                float(budget_max),
                float(offered_amt),
                bounding_status,
                str(rzp_order),
                str(rzp_pay),
                ap2_status,
                json.dumps(details, sort_keys=True),
                prev_hash,
                current_hash
            ))
            conn.commit()

        return audit_rec_id

    def get_records_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_records WHERE session_id = ? ORDER BY id ASC
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_records ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
