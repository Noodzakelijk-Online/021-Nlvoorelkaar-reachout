"""
Database Manager for NLvoorelkaar Tool
Handles SQLite database operations and schema management
"""

import sqlite3
import os
import logging
import json
import re
from contextlib import closing
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    SCHEMA_VERSION = 4

    def __init__(self, db_path="data/nlvoorelkaar.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self.init_database()
        
    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o700)
            
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn
        
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with closing(self.get_connection()) as conn:
                # Create volunteers table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS volunteers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT UNIQUE NOT NULL,
                        name TEXT,
                        description TEXT,
                        location TEXT,
                        skills TEXT,
                        categories TEXT,
                        availability TEXT,
                        contact_info TEXT,
                        profile_url TEXT,
                        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create campaigns table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        target_categories TEXT,
                        target_location TEXT,
                        target_distance INTEGER,
                        message_template TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create contacts table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER,
                        message_sent TEXT,
                        contact_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        response_received BOOLEAN DEFAULT FALSE,
                        response_date TIMESTAMP,
                        response_content TEXT,
                        status TEXT DEFAULT 'sent',
                        notes TEXT,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')
                
                # Create blacklist table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS blacklist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT UNIQUE NOT NULL,
                        reason TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create settings table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Outreach operating ledger: review-gated message lifecycle
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS message_drafts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id INTEGER NOT NULL,
                        volunteer_id TEXT NOT NULL,
                        subject TEXT,
                        body TEXT NOT NULL,
                        template_id TEXT,
                        personalization_json TEXT,
                        status TEXT DEFAULT 'draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id),
                        UNIQUE (campaign_id, volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS message_approvals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_draft_id INTEGER NOT NULL,
                        decision TEXT NOT NULL,
                        decision_reason TEXT,
                        approved_subject_snapshot TEXT,
                        approved_body_snapshot TEXT,
                        decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (message_draft_id) REFERENCES message_drafts (id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS message_send_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_draft_id INTEGER NOT NULL,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        finished_at TIMESTAMP,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0,
                        delivery_evidence TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (message_draft_id) REFERENCES message_drafts (id),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS volunteer_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER,
                        contact_id INTEGER,
                        raw_content TEXT NOT NULL,
                        classification TEXT DEFAULT 'unknown',
                        confidence REAL DEFAULT 0.0,
                        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source TEXT DEFAULT 'manual',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (contact_id) REFERENCES contacts (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS follow_up_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER,
                        previous_message_id INTEGER,
                        due_at TIMESTAMP NOT NULL,
                        status TEXT DEFAULT 'due',
                        suggested_message TEXT,
                        approved_message_snapshot TEXT,
                        approved_at TIMESTAMP,
                        sent_at TIMESTAMP,
                        delivery_evidence TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (previous_message_id) REFERENCES message_drafts (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS follow_up_send_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        follow_up_id INTEGER NOT NULL,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER,
                        status TEXT NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        finished_at TIMESTAMP,
                        error_message TEXT,
                        delivery_evidence TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (follow_up_id) REFERENCES follow_up_plans (id),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS outreach_outcomes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT NOT NULL,
                        campaign_id INTEGER,
                        response_id INTEGER,
                        follow_up_id INTEGER,
                        outcome_type TEXT NOT NULL,
                        status TEXT DEFAULT 'recorded',
                        notes TEXT,
                        actor TEXT DEFAULT 'user',
                        decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id),
                        FOREIGN KEY (response_id) REFERENCES volunteer_responses (id),
                        FOREIGN KEY (follow_up_id) REFERENCES follow_up_plans (id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        actor TEXT DEFAULT 'system',
                        before_state TEXT,
                        after_state TEXT,
                        risk_level TEXT DEFAULT 'low',
                        approval_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (approval_id) REFERENCES message_approvals (id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS runtime_controls (
                        control_key TEXT PRIMARY KEY,
                        value_json TEXT NOT NULL,
                        actor TEXT NOT NULL DEFAULT 'system',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute(
                    """
                    INSERT OR IGNORE INTO runtime_controls(control_key, value_json, actor)
                    VALUES ('safety_stop', 'false', 'system')
                    """
                )

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        criteria_json TEXT,
                        status TEXT DEFAULT 'started',
                        result_count INTEGER DEFAULT 0,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        finished_at TIMESTAMP,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_session_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        search_session_id INTEGER NOT NULL,
                        task_id TEXT,
                        volunteer_id TEXT NOT NULL,
                        result_rank INTEGER DEFAULT 0,
                        source_url TEXT,
                        snapshot_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (search_session_id) REFERENCES search_sessions (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id),
                        UNIQUE (search_session_id, volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS match_assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id INTEGER NOT NULL,
                        volunteer_id TEXT NOT NULL,
                        score REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'possible',
                        reasons_json TEXT,
                        assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id),
                        UNIQUE (campaign_id, volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS campaign_exclusions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id INTEGER NOT NULL,
                        volunteer_id TEXT NOT NULL,
                        reason_code TEXT NOT NULL,
                        reason_message TEXT,
                        evidence_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id),
                        UNIQUE (campaign_id, volunteer_id, reason_code)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS task_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        status TEXT NOT NULL,
                        progress_json TEXT,
                        result_json TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS privacy_retention_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        volunteer_id TEXT,
                        action TEXT NOT NULL,
                        status TEXT DEFAULT 'proposed',
                        reason TEXT,
                        evidence_json TEXT,
                        actor TEXT DEFAULT 'system',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS volunteer_identities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        canonical_volunteer_id TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (canonical_volunteer_id) REFERENCES volunteers (volunteer_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS volunteer_identity_members (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        identity_id INTEGER NOT NULL,
                        volunteer_id TEXT NOT NULL,
                        merge_status TEXT DEFAULT 'proposed',
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (identity_id) REFERENCES volunteer_identities (id),
                        FOREIGN KEY (volunteer_id) REFERENCES volunteers (volunteer_id),
                        UNIQUE (identity_id, volunteer_id)
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_volunteers_categories ON volunteers(categories)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_volunteers_location ON volunteers(location)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_volunteers_updated ON volunteers(updated_at DESC, id DESC)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_volunteer_id ON contacts(volunteer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_campaign_id ON contacts(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_date ON contacts(contact_date)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_message_drafts_status ON message_drafts(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_message_drafts_campaign ON message_drafts(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_send_attempts_draft ON message_send_attempts(message_draft_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_responses_campaign ON volunteer_responses(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_follow_up_due ON follow_up_plans(status, due_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_follow_up_send_attempts_plan ON follow_up_send_attempts(follow_up_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_outcomes_campaign ON outreach_outcomes(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_outcomes_volunteer ON outreach_outcomes(volunteer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_search_sessions_task ON search_sessions(task_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_search_results_session ON search_session_results(search_session_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_search_results_volunteer ON search_session_results(volunteer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_match_assessments_campaign ON match_assessments(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_campaign_exclusions_campaign ON campaign_exclusions(campaign_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_campaign_exclusions_volunteer ON campaign_exclusions(volunteer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_task_runs_status ON task_runs(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_privacy_retention_volunteer ON privacy_retention_records(volunteer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_identity_members_volunteer ON volunteer_identity_members(volunteer_id)')

                self._ensure_column(conn, 'follow_up_plans', 'approved_message_snapshot', 'TEXT')
                self._ensure_column(conn, 'follow_up_plans', 'approved_at', 'TIMESTAMP')
                self._ensure_column(conn, 'follow_up_plans', 'sent_at', 'TIMESTAMP')
                self._ensure_column(conn, 'follow_up_plans', 'delivery_evidence', 'TEXT')
                self._ensure_column(conn, 'volunteers', 'retention_status', "TEXT DEFAULT 'active'")
                self._ensure_column(conn, 'volunteers', 'archived_at', 'TIMESTAMP')
                self._ensure_column(conn, 'volunteers', 'redacted_at', 'TIMESTAMP')
                self._ensure_column(conn, 'volunteers', 'retention_notes', 'TEXT')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_volunteers_retention ON volunteers(retention_status, updated_at DESC)')

                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
                    (self.SCHEMA_VERSION, "durable_cross_process_runtime_controls")
                )
                conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except (OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to initialize database: %s", type(e).__name__)
            raise
            
    def add_volunteer(self, volunteer_data: Dict[str, Any]) -> bool:
        """Add or update volunteer information"""
        try:
            with closing(self.get_connection()) as conn:
                conn.execute('''
                    INSERT INTO volunteers
                    (volunteer_id, name, description, location, skills, categories, 
                     availability, contact_info, profile_url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(volunteer_id) DO UPDATE SET
                        name = excluded.name,
                        description = excluded.description,
                        location = excluded.location,
                        skills = excluded.skills,
                        categories = excluded.categories,
                        availability = excluded.availability,
                        contact_info = excluded.contact_info,
                        profile_url = excluded.profile_url,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE COALESCE(volunteers.retention_status, 'active') != 'redacted'
                ''', (
                    volunteer_data.get('volunteer_id'),
                    volunteer_data.get('name'),
                    volunteer_data.get('description'),
                    volunteer_data.get('location'),
                    volunteer_data.get('skills'),
                    volunteer_data.get('categories'),
                    volunteer_data.get('availability'),
                    volunteer_data.get('contact_info'),
                    volunteer_data.get('profile_url')
                ))
                conn.commit()
                return True
                
        except (TypeError, ValueError, sqlite3.DatabaseError, AttributeError) as e:
            logger.error("Failed to add volunteer: %s", type(e).__name__)
            return False

    def _json(self, value: Any) -> str:
        """Serialize local ledger metadata without leaking Python reprs."""
        return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)

    def _text_metadata(self, value: Any) -> Dict[str, Any]:
        """Summarize operator text for audit events without duplicating content."""
        text = "" if value is None else str(value)
        return {
            "present": bool(text.strip()),
            "length": len(text)
        }

    def _error_label(self, error: Any) -> Optional[str]:
        """Reduce error details to a non-sensitive class-style label."""
        if error is None:
            return None
        if isinstance(error, BaseException):
            return type(error).__name__
        text = str(error).strip()
        if not text:
            return None
        prefix = text.split(":", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", prefix) and len(prefix) <= 120:
            return prefix
        return "Error"

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str):
        """Add a column to an existing SQLite table if it is missing."""
        existing_columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def record_audit_event(
        self,
        entity_type: str,
        entity_id: Any,
        action: str,
        actor: str = "system",
        before_state: Any = None,
        after_state: Any = None,
        risk_level: str = "low",
        approval_id: Optional[int] = None
    ) -> int:
        """Record an audit event for a consequential ledger action."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO audit_events
                (entity_type, entity_id, action, actor, before_state, after_state, risk_level, approval_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entity_type,
                str(entity_id),
                action,
                actor,
                self._json(before_state) if before_state is not None else None,
                self._json(after_state) if after_state is not None else None,
                risk_level,
                approval_id
            ))
            conn.commit()
            return cursor.lastrowid

    def get_runtime_control(self, control_key: str, default: Any = None) -> Any:
        """Read one cross-process runtime control from SQLite."""
        if not isinstance(control_key, str) or not control_key.strip():
            raise ValueError("control_key is required")
        with closing(self.get_connection()) as conn:
            row = conn.execute(
                "SELECT value_json FROM runtime_controls WHERE control_key = ?",
                (control_key.strip(),),
            ).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value_json"])
        except (TypeError, json.JSONDecodeError):
            return default

    def set_runtime_control(self, control_key: str, value: Any, actor: str = "system") -> None:
        """Atomically update one cross-process control and record its audit event."""
        if not isinstance(control_key, str) or not control_key.strip():
            raise ValueError("control_key is required")
        serialized = json.dumps(value, sort_keys=True)
        with closing(self.get_connection()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT value_json FROM runtime_controls WHERE control_key = ?",
                (control_key.strip(),),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO runtime_controls(control_key, value_json, actor, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(control_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    actor = excluded.actor,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (control_key.strip(), serialized, actor),
            )
            conn.execute(
                """
                INSERT INTO audit_events(
                    entity_type, entity_id, action, actor, before_state, after_state, risk_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "runtime_control",
                    control_key.strip(),
                    "runtime_control_updated",
                    actor,
                    previous["value_json"] if previous else None,
                    serialized,
                    "high" if control_key.strip() == "safety_stop" else "medium",
                ),
            )
            conn.commit()

    def create_message_draft(self, draft_data: Dict[str, Any]) -> int:
        """Create or update a personalized message draft for review."""
        with closing(self.get_connection()) as conn:
            existing = conn.execute('''
                SELECT id FROM message_drafts
                WHERE campaign_id = ? AND volunteer_id = ?
            ''', (draft_data.get('campaign_id'), draft_data.get('volunteer_id'))).fetchone()

            if existing:
                conn.execute('''
                    UPDATE message_drafts
                    SET subject = ?, body = ?, template_id = ?, personalization_json = ?,
                        status = 'draft', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status IN ('draft', 'rejected', 'failed')
                ''', (
                    draft_data.get('subject', ''),
                    draft_data.get('body', ''),
                    draft_data.get('template_id'),
                    self._json(draft_data.get('personalization')),
                    existing['id']
                ))
                draft_id = existing['id']
            else:
                cursor = conn.execute('''
                    INSERT INTO message_drafts
                    (campaign_id, volunteer_id, subject, body, template_id, personalization_json, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'draft')
                ''', (
                    draft_data.get('campaign_id'),
                    draft_data.get('volunteer_id'),
                    draft_data.get('subject', ''),
                    draft_data.get('body', ''),
                    draft_data.get('template_id'),
                    self._json(draft_data.get('personalization'))
                ))
                draft_id = cursor.lastrowid

            conn.commit()

        self.record_audit_event(
            "message_draft",
            draft_id,
            "draft_created",
            after_state={"campaign_id": draft_data.get('campaign_id'), "volunteer_id": draft_data.get('volunteer_id')}
        )
        return draft_id

    def get_message_draft(self, draft_id: int) -> Optional[Dict[str, Any]]:
        """Get one message draft with campaign and volunteer context."""
        with closing(self.get_connection()) as conn:
            row = conn.execute('''
                SELECT md.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       c.name AS campaign_name
                FROM message_drafts md
                LEFT JOIN volunteers v ON md.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON md.campaign_id = c.id
                WHERE md.id = ?
            ''', (draft_id,)).fetchone()
            return dict(row) if row else None

    def get_message_drafts(
        self,
        status: Optional[str] = None,
        campaign_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List message drafts for review and operations views."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT md.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       c.name AS campaign_name,
                       (
                           SELECT decision FROM message_approvals ma
                           WHERE ma.message_draft_id = md.id
                           ORDER BY ma.created_at DESC LIMIT 1
                       ) AS latest_decision
                FROM message_drafts md
                LEFT JOIN volunteers v ON md.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON md.campaign_id = c.id
                WHERE 1=1
            '''
            params = []
            if status:
                query += ' AND md.status = ?'
                params.append(status)
            if campaign_id:
                query += ' AND md.campaign_id = ?'
                params.append(campaign_id)
            query += ' ORDER BY md.updated_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def update_message_draft(self, draft_id: int, subject: Optional[str] = None, body: Optional[str] = None) -> bool:
        """Edit a draft before approval."""
        draft = self.get_message_draft(draft_id)
        if not draft or draft.get('status') in {'sent', 'sending'}:
            return False

        with closing(self.get_connection()) as conn:
            conn.execute('''
                UPDATE message_drafts
                SET subject = COALESCE(?, subject), body = COALESCE(?, body),
                    status = 'draft', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (subject, body, draft_id))
            conn.commit()

        self.record_audit_event(
            "message_draft",
            draft_id,
            "draft_edited",
            before_state={
                "subject": self._text_metadata(draft.get('subject')),
                "body": self._text_metadata(draft.get('body'))
            },
            after_state={
                "subject_changed": subject is not None,
                "body_changed": body is not None,
                "subject": self._text_metadata(subject or draft.get('subject')),
                "body": self._text_metadata(body or draft.get('body'))
            },
            risk_level="medium"
        )
        return True

    def approve_message_draft(self, draft_id: int, decision_reason: str = "", actor: str = "user") -> int:
        """Persist explicit approval and approved content snapshots."""
        draft = self.get_message_draft(draft_id)
        if not draft:
            raise ValueError(f"Message draft {draft_id} not found")
        if draft.get('status') not in {'draft', 'rejected', 'failed'}:
            raise ValueError("Only draft, rejected, or failed messages can be approved")

        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO message_approvals
                (message_draft_id, decision, decision_reason, approved_subject_snapshot, approved_body_snapshot)
                VALUES (?, 'approved', ?, ?, ?)
            ''', (draft_id, decision_reason, draft.get('subject'), draft.get('body')))
            approval_id = cursor.lastrowid
            conn.execute('''
                UPDATE message_drafts
                SET status = 'approved', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (draft_id,))
            conn.commit()

        self.record_audit_event(
            "message_draft",
            draft_id,
            "message_approved",
            actor=actor,
            after_state={"approval_id": approval_id},
            risk_level="high",
            approval_id=approval_id
        )
        return approval_id

    def reject_message_draft(self, draft_id: int, decision_reason: str = "", actor: str = "user") -> int:
        """Persist explicit rejection of a message draft."""
        draft = self.get_message_draft(draft_id)
        if not draft:
            raise ValueError(f"Message draft {draft_id} not found")
        if draft.get('status') in {'sending', 'sent'}:
            raise ValueError("A sending or sent message cannot be rejected")

        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO message_approvals
                (message_draft_id, decision, decision_reason, approved_subject_snapshot, approved_body_snapshot)
                VALUES (?, 'rejected', ?, NULL, NULL)
            ''', (draft_id, decision_reason))
            approval_id = cursor.lastrowid
            conn.execute('''
                UPDATE message_drafts
                SET status = 'rejected', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (draft_id,))
            conn.commit()

        self.record_audit_event(
            "message_draft",
            draft_id,
            "message_rejected",
            actor=actor,
            after_state={"approval_id": approval_id, "reason": self._text_metadata(decision_reason)},
            risk_level="medium",
            approval_id=approval_id
        )
        return approval_id

    def record_send_attempt(
        self,
        draft_id: int,
        status: str = "started",
        error_message: Optional[str] = None,
        delivery_evidence: Optional[str] = None,
        retry_count: int = 0
    ) -> int:
        """Create a send-attempt record for an approved draft."""
        finished_at = datetime.now().isoformat() if status in {'sent', 'failed'} else None
        with closing(self.get_connection()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            draft_row = conn.execute(
                "SELECT * FROM message_drafts WHERE id = ?",
                (draft_id,)
            ).fetchone()
            if not draft_row:
                raise ValueError(f"Message draft {draft_id} not found")
            draft = dict(draft_row)

            if status == 'started':
                claimed = conn.execute('''
                    UPDATE message_drafts
                    SET status = 'sending', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'approved'
                ''', (draft_id,))
                if claimed.rowcount != 1:
                    raise ValueError("Draft is not approved or is already being sent")
            elif draft.get('status') not in {'approved', 'sending', 'failed'}:
                raise ValueError("Cannot record a send result without approval")

            cursor = conn.execute('''
                INSERT INTO message_send_attempts
                (message_draft_id, volunteer_id, campaign_id, status, finished_at,
                 error_message, retry_count, delivery_evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                draft_id,
                draft.get('volunteer_id'),
                draft.get('campaign_id'),
                status,
                finished_at,
                error_message,
                retry_count,
                delivery_evidence
            ))
            attempt_id = cursor.lastrowid
            if status != 'started':
                conn.execute('''
                    UPDATE message_drafts
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, draft_id))
            conn.commit()

        self.record_audit_event(
            "message_send_attempt",
            attempt_id,
            f"send_attempt_{status}",
            after_state={
                "draft_id": draft_id,
                "status": status,
                "error": self._text_metadata(error_message)
            },
            risk_level="high"
        )
        return attempt_id

    def finish_send_attempt(
        self,
        attempt_id: int,
        status: str,
        error_message: Optional[str] = None,
        delivery_evidence: Optional[str] = None
    ) -> bool:
        """Finish a send attempt and update the draft status."""
        if status not in {'sent', 'failed'}:
            raise ValueError("status must be 'sent' or 'failed'")

        with closing(self.get_connection()) as conn:
            attempt = conn.execute(
                'SELECT * FROM message_send_attempts WHERE id = ?',
                (attempt_id,)
            ).fetchone()
            if not attempt:
                return False

            conn.execute('''
                UPDATE message_send_attempts
                SET status = ?, finished_at = CURRENT_TIMESTAMP, error_message = ?,
                    delivery_evidence = ?
                WHERE id = ?
            ''', (status, error_message, delivery_evidence, attempt_id))
            conn.execute('''
                UPDATE message_drafts
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, attempt['message_draft_id']))
            conn.commit()

        self.record_audit_event(
            "message_send_attempt",
            attempt_id,
            f"send_attempt_{status}",
            after_state={
                "status": status,
                "error": self._text_metadata(error_message),
                "delivery_evidence": self._text_metadata(delivery_evidence)
            },
            risk_level="high"
        )
        return True

    def get_send_attempts(self, draft_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List send attempts with volunteer/campaign context."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT msa.*, v.name AS volunteer_name, c.name AS campaign_name
                FROM message_send_attempts msa
                LEFT JOIN volunteers v ON msa.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON msa.campaign_id = c.id
                WHERE 1=1
            '''
            params = []
            if draft_id:
                query += ' AND msa.message_draft_id = ?'
                params.append(draft_id)
            query += ' ORDER BY msa.created_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_daily_sent_count(self) -> int:
        """Return confirmed message sends recorded since local midnight."""
        with closing(self.get_connection()) as conn:
            row = conn.execute('''
                SELECT COUNT(*)
                FROM message_send_attempts
                WHERE status = 'sent'
                  AND datetime(created_at, 'localtime') >= datetime('now', 'localtime', 'start of day')
            ''').fetchone()
            return int(row[0])

    def reconcile_ambiguous_send_attempts(
        self,
        stale_minutes: int = 15,
        actor: str = "operator",
    ) -> int:
        """Fail stale in-flight sends without guessing whether the provider accepted them."""
        stale_minutes = int(stale_minutes)
        if not 1 <= stale_minutes <= 1440:
            raise ValueError("stale_minutes must be between 1 and 1440")
        threshold = f"-{stale_minutes} minutes"
        with closing(self.get_connection()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute('''
                SELECT id, message_draft_id
                FROM message_send_attempts
                WHERE status = 'started'
                  AND datetime(started_at) <= datetime('now', ?)
            ''', (threshold,)).fetchall()
            for row in rows:
                conn.execute('''
                    UPDATE message_send_attempts
                    SET status = 'failed', finished_at = CURRENT_TIMESTAMP,
                        error_message = 'external_outcome_unknown'
                    WHERE id = ?
                ''', (row['id'],))
                conn.execute('''
                    UPDATE message_drafts
                    SET status = 'failed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'sending'
                ''', (row['message_draft_id'],))
            conn.commit()

        for row in rows:
            self.record_audit_event(
                "message_send_attempt",
                row['id'],
                "ambiguous_send_reconciled",
                actor=actor,
                after_state={
                    "draft_id": row['message_draft_id'],
                    "status": "failed",
                    "reason": "external_outcome_unknown",
                },
                risk_level="high",
            )
        return len(rows)

    def get_database_health(self) -> Dict[str, Any]:
        """Return non-sensitive integrity and migration diagnostics."""
        with closing(self.get_connection()) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_issues = [dict(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
            version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            table_count = int(conn.execute('''
                SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'
            ''').fetchone()[0])
        return {
            "integrity": integrity,
            "foreign_key_issue_count": len(foreign_key_issues),
            "schema_version": version,
            "expected_schema_version": self.SCHEMA_VERSION,
            "table_count": table_count,
            "ready": (
                integrity == "ok"
                and not foreign_key_issues
                and version == self.SCHEMA_VERSION
            ),
        }

    def confirm_manual_send(
        self,
        draft_id: int,
        delivery_evidence: str,
        actor: str = "user"
    ) -> int:
        """Record explicit manual confirmation that an approved draft was sent."""
        evidence = (delivery_evidence or "").strip()
        if not evidence:
            raise ValueError("Manual send confirmation requires delivery evidence")

        draft = self.get_message_draft(draft_id)
        if not draft:
            raise ValueError(f"Message draft {draft_id} not found")
        if draft.get("status") not in {"approved", "sending", "failed"}:
            raise ValueError("Manual send confirmation requires an approved or attempted draft")

        attempt_id = self.record_send_attempt(
            draft_id,
            status="sent",
            delivery_evidence=f"manual_confirmation: {evidence}"
        )
        self.add_contact({
            "volunteer_id": draft["volunteer_id"],
            "campaign_id": draft["campaign_id"],
            "message_sent": draft["body"],
            "status": "sent",
            "notes": f"Manual send confirmation for draft {draft_id}; evidence={evidence}"
        })
        self.record_audit_event(
            "message_send_attempt",
            attempt_id,
            "manual_send_confirmed",
            actor=actor,
            after_state={"draft_id": draft_id, "delivery_evidence": self._text_metadata(evidence)},
            risk_level="high"
        )
        return attempt_id

    def record_volunteer_response(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        raw_content: str,
        classification: str = "unknown",
        confidence: float = 0.0,
        contact_id: Optional[int] = None,
        source: str = "manual"
    ) -> int:
        """Record a volunteer response or manually entered reply."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO volunteer_responses
                (volunteer_id, campaign_id, contact_id, raw_content, classification, confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (volunteer_id, campaign_id, contact_id, raw_content, classification, confidence, source))
            response_id = cursor.lastrowid
            if contact_id:
                conn.execute('''
                    UPDATE contacts
                    SET response_received = TRUE, response_date = CURRENT_TIMESTAMP,
                        response_content = ?, status = 'responded'
                    WHERE id = ?
                ''', (raw_content, contact_id))
            conn.commit()

        self.record_audit_event(
            "volunteer_response",
            response_id,
            "response_recorded",
            after_state={"volunteer_id": volunteer_id, "campaign_id": campaign_id, "classification": classification}
        )
        return response_id

    def create_follow_up(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        due_at: str,
        suggested_message: str,
        previous_message_id: Optional[int] = None,
        status: str = "due"
    ) -> int:
        """Create a follow-up plan that still requires approval before sending."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO follow_up_plans
                (volunteer_id, campaign_id, previous_message_id, due_at, status, suggested_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (volunteer_id, campaign_id, previous_message_id, due_at, status, suggested_message))
            follow_up_id = cursor.lastrowid
            conn.commit()

        self.record_audit_event(
            "follow_up_plan",
            follow_up_id,
            "follow_up_created",
            after_state={"volunteer_id": volunteer_id, "campaign_id": campaign_id, "due_at": due_at}
        )
        return follow_up_id

    def get_follow_ups_due(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get due or overdue follow-ups."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                SELECT fp.*, v.name AS volunteer_name, c.name AS campaign_name
                FROM follow_up_plans fp
                LEFT JOIN volunteers v ON fp.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON fp.campaign_id = c.id
                WHERE fp.status = 'due' AND fp.due_at <= CURRENT_TIMESTAMP
                ORDER BY fp.due_at ASC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_follow_ups(
        self,
        status: Optional[str] = None,
        include_future: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get follow-up plans for queue review."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT fp.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       c.name AS campaign_name
                FROM follow_up_plans fp
                LEFT JOIN volunteers v ON fp.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON fp.campaign_id = c.id
                WHERE 1=1
            '''
            params: List[Any] = []
            if status:
                query += ' AND fp.status = ?'
                params.append(status)
            if not include_future:
                query += ' AND fp.due_at <= CURRENT_TIMESTAMP'
            query += ' ORDER BY fp.due_at ASC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def update_follow_up_status(
        self,
        follow_up_id: int,
        status: str,
        actor: str = "user"
    ) -> bool:
        """Update a follow-up status and record an audit event."""
        allowed_statuses = {"due", "approved", "sent", "completed", "cancelled"}
        if status not in allowed_statuses:
            raise ValueError(f"Unsupported follow-up status: {status}")

        with closing(self.get_connection()) as conn:
            before = conn.execute(
                'SELECT * FROM follow_up_plans WHERE id = ?',
                (follow_up_id,)
            ).fetchone()
            if not before:
                return False

            conn.execute('''
                UPDATE follow_up_plans
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, follow_up_id))
            conn.commit()

        self.record_audit_event(
            "follow_up_plan",
            follow_up_id,
            "follow_up_status_updated",
            actor=actor,
            before_state={"status": before["status"]},
            after_state={"status": status}
        )
        return True

    def approve_follow_up(
        self,
        follow_up_id: int,
        message_snapshot: Optional[str] = None,
        actor: str = "user"
    ) -> bool:
        """Approve a follow-up message snapshot before any send confirmation."""
        with closing(self.get_connection()) as conn:
            follow_up = conn.execute(
                'SELECT * FROM follow_up_plans WHERE id = ?',
                (follow_up_id,)
            ).fetchone()
            if not follow_up:
                return False
            if follow_up["status"] in {"sent", "completed", "cancelled"}:
                raise ValueError("Cannot approve a closed follow-up")

            approved_message = (message_snapshot or follow_up["suggested_message"] or "").strip()
            if not approved_message:
                raise ValueError("Follow-up approval requires a message snapshot")

            conn.execute('''
                UPDATE follow_up_plans
                SET status = 'approved',
                    approved_message_snapshot = ?,
                    approved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (approved_message, follow_up_id))
            conn.commit()

        self.record_audit_event(
            "follow_up_plan",
            follow_up_id,
            "follow_up_approved",
            actor=actor,
            before_state={
                "status": follow_up["status"],
                "suggested_message": self._text_metadata(follow_up["suggested_message"])
            },
            after_state={
                "status": "approved",
                "approved_message_snapshot": self._text_metadata(approved_message)
            },
            risk_level="high"
        )
        return True

    def confirm_follow_up_sent(
        self,
        follow_up_id: int,
        delivery_evidence: str,
        actor: str = "user"
    ) -> int:
        """Record explicit manual evidence that an approved follow-up was sent."""
        evidence = (delivery_evidence or "").strip()
        if not evidence:
            raise ValueError("Follow-up send confirmation requires delivery evidence")

        with closing(self.get_connection()) as conn:
            follow_up = conn.execute(
                'SELECT * FROM follow_up_plans WHERE id = ?',
                (follow_up_id,)
            ).fetchone()
            if not follow_up:
                raise ValueError(f"Follow-up {follow_up_id} not found")
            if follow_up["status"] != "approved":
                raise ValueError("Follow-up must be approved before send confirmation")

            volunteer = conn.execute(
                'SELECT retention_status FROM volunteers WHERE volunteer_id = ?',
                (follow_up["volunteer_id"],)
            ).fetchone()
            retention_status = (
                volunteer["retention_status"]
                if volunteer and "retention_status" in volunteer.keys()
                else "active"
            ) or "active"
            if retention_status.lower() in {"archived", "redacted"}:
                raise ValueError("Follow-up cannot be sent to an archived or redacted volunteer")

            blacklisted = conn.execute(
                'SELECT 1 FROM blacklist WHERE volunteer_id = ? LIMIT 1',
                (follow_up["volunteer_id"],)
            ).fetchone()
            if blacklisted:
                raise ValueError("Follow-up cannot be sent to a blacklisted volunteer")

            duplicate = conn.execute('''
                SELECT 1
                FROM volunteer_identities vi
                JOIN volunteer_identity_members vim ON vim.identity_id = vi.id
                WHERE vi.status = 'confirmed'
                  AND vim.merge_status = 'confirmed'
                  AND vim.volunteer_id = ?
                  AND vim.volunteer_id != vi.canonical_volunteer_id
                LIMIT 1
            ''', (follow_up["volunteer_id"],)).fetchone()
            if duplicate:
                raise ValueError("Follow-up cannot be sent to a confirmed duplicate profile")

            closed_outcome = conn.execute('''
                SELECT 1
                FROM outreach_outcomes
                WHERE volunteer_id = ?
                  AND (campaign_id = ? OR ? IS NULL)
                  AND outcome_type IN ('declined', 'unavailable', 'not_suitable', 'do_not_contact')
                LIMIT 1
            ''', (
                follow_up["volunteer_id"],
                follow_up["campaign_id"],
                follow_up["campaign_id"]
            )).fetchone()
            if closed_outcome:
                raise ValueError("Follow-up cannot be sent after a closed outreach outcome")

            cursor = conn.execute('''
                INSERT INTO follow_up_send_attempts
                (follow_up_id, volunteer_id, campaign_id, status, finished_at, delivery_evidence)
                VALUES (?, ?, ?, 'sent', CURRENT_TIMESTAMP, ?)
            ''', (
                follow_up_id,
                follow_up["volunteer_id"],
                follow_up["campaign_id"],
                f"manual_confirmation: {evidence}"
            ))
            attempt_id = cursor.lastrowid
            conn.execute('''
                UPDATE follow_up_plans
                SET status = 'sent',
                    sent_at = CURRENT_TIMESTAMP,
                    delivery_evidence = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (evidence, follow_up_id))
            conn.commit()

        self.add_contact({
            "volunteer_id": follow_up["volunteer_id"],
            "campaign_id": follow_up["campaign_id"],
            "message_sent": follow_up["approved_message_snapshot"],
            "status": "sent",
            "notes": f"Manual follow-up send confirmation for follow-up {follow_up_id}; evidence={evidence}"
        })
        self.record_audit_event(
            "follow_up_send_attempt",
            attempt_id,
            "follow_up_sent_confirmed",
            actor=actor,
            after_state={"follow_up_id": follow_up_id, "delivery_evidence": self._text_metadata(evidence)},
            risk_level="high"
        )
        return attempt_id

    def get_follow_up_send_attempts(
        self,
        follow_up_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List follow-up send attempts with context."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT fusa.*, v.name AS volunteer_name, c.name AS campaign_name
                FROM follow_up_send_attempts fusa
                LEFT JOIN volunteers v ON fusa.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON fusa.campaign_id = c.id
                WHERE 1=1
            '''
            params: List[Any] = []
            if follow_up_id:
                query += ' AND fusa.follow_up_id = ?'
                params.append(follow_up_id)
            query += ' ORDER BY fusa.created_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def record_outreach_outcome(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        outcome_type: str,
        notes: str = "",
        response_id: Optional[int] = None,
        follow_up_id: Optional[int] = None,
        status: str = "recorded",
        actor: str = "user"
    ) -> int:
        """Record a final or current outreach outcome for a volunteer/campaign."""
        outcome = (outcome_type or "").strip().lower()
        if not volunteer_id:
            raise ValueError("volunteer_id is required")
        if not outcome:
            raise ValueError("outcome_type is required")

        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO outreach_outcomes
                (volunteer_id, campaign_id, response_id, follow_up_id, outcome_type, status, notes, actor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                volunteer_id, campaign_id, response_id, follow_up_id,
                outcome, status, notes, actor
            ))
            outcome_id = cursor.lastrowid
            conn.commit()

        self.record_audit_event(
            "outreach_outcome",
            outcome_id,
            "outcome_recorded",
            actor=actor,
            after_state={
                "volunteer_id": volunteer_id,
                "campaign_id": campaign_id,
                "outcome_type": outcome,
                "status": status
            },
            risk_level="medium"
        )
        return outcome_id

    def get_outreach_outcomes(
        self,
        campaign_id: Optional[int] = None,
        volunteer_id: Optional[str] = None,
        outcome_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List outreach outcomes with campaign and volunteer context."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT oo.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       c.name AS campaign_name
                FROM outreach_outcomes oo
                LEFT JOIN volunteers v ON oo.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON oo.campaign_id = c.id
                WHERE 1=1
            '''
            params: List[Any] = []
            if campaign_id is not None:
                query += ' AND oo.campaign_id = ?'
                params.append(campaign_id)
            if volunteer_id:
                query += ' AND oo.volunteer_id = ?'
                params.append(volunteer_id)
            if outcome_type:
                query += ' AND oo.outcome_type = ?'
                params.append(outcome_type)
            query += ' ORDER BY oo.decided_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_volunteer_responses(
        self,
        campaign_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recorded volunteer responses for inbox triage."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT vr.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       c.name AS campaign_name
                FROM volunteer_responses vr
                LEFT JOIN volunteers v ON vr.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON vr.campaign_id = c.id
                WHERE 1=1
            '''
            params: List[Any] = []
            if campaign_id is not None:
                query += ' AND vr.campaign_id = ?'
                params.append(campaign_id)
            query += ' ORDER BY vr.received_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_privacy_retention_candidates(
        self,
        days: int = 365,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find stale volunteer records that may need retention review."""
        cutoff_modifier = f"-{int(days)} days"
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                SELECT v.volunteer_id, v.name, v.location, v.categories, v.updated_at,
                       COALESCE(v.retention_status, 'active') AS retention_status,
                       COUNT(DISTINCT c.id) AS contact_count,
                       COUNT(DISTINCT vr.id) AS response_count,
                       MAX(c.contact_date) AS last_contact_at,
                       MAX(vr.received_at) AS last_response_at
                FROM volunteers v
                LEFT JOIN contacts c ON c.volunteer_id = v.volunteer_id
                LEFT JOIN volunteer_responses vr ON vr.volunteer_id = v.volunteer_id
                WHERE datetime(COALESCE(v.updated_at, '1970-01-01 00:00:00')) <= datetime('now', ?)
                  AND COALESCE(v.retention_status, 'active') = 'active'
                  AND NOT EXISTS (
                      SELECT 1 FROM contacts recent_c
                      WHERE recent_c.volunteer_id = v.volunteer_id
                        AND datetime(recent_c.contact_date) > datetime('now', ?)
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM volunteer_responses recent_r
                      WHERE recent_r.volunteer_id = v.volunteer_id
                        AND datetime(recent_r.received_at) > datetime('now', ?)
                  )
                GROUP BY v.volunteer_id
                ORDER BY v.updated_at ASC
                LIMIT ?
            ''', (cutoff_modifier, cutoff_modifier, cutoff_modifier, limit))
            return [dict(row) for row in cursor.fetchall()]

    def record_search_session(
        self,
        criteria: Dict[str, Any],
        task_id: Optional[str] = None,
        status: str = "started",
        result_count: int = 0,
        error_message: Optional[str] = None
    ) -> int:
        """Record a volunteer search session and its criteria."""
        finished_at = datetime.now().isoformat() if status in {"completed", "failed", "cancelled"} else None
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO search_sessions
                (task_id, criteria_json, status, result_count, finished_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                self._json(criteria),
                status,
                result_count,
                finished_at,
                self._error_label(error_message)
            ))
            search_session_id = cursor.lastrowid
            conn.commit()

        self.record_audit_event(
            "search_session",
            search_session_id,
            "search_session_recorded",
            after_state={"status": status, "result_count": result_count}
        )
        return search_session_id

    def finish_search_session(
        self,
        task_id: str,
        status: str,
        result_count: int = 0,
        error_message: Optional[str] = None
    ) -> bool:
        """Finish a previously recorded search session."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                UPDATE search_sessions
                SET status = ?, result_count = ?, finished_at = CURRENT_TIMESTAMP,
                    error_message = ?
                WHERE task_id = ?
            ''', (status, result_count, self._error_label(error_message), task_id))
            conn.commit()

        if cursor.rowcount:
            self.record_audit_event(
                "search_session",
                task_id,
                "search_session_finished",
                after_state={
                    "status": status,
                    "result_count": result_count,
                    "error_type": self._error_label(error_message)
                }
            )
            return True
        return False

    def record_search_session_results(
        self,
        task_id: str,
        volunteers: List[Dict[str, Any]],
        actor: str = "system"
    ) -> int:
        """Persist the volunteer membership returned by a search task."""
        if not task_id:
            raise ValueError("task_id is required")

        prepared = []
        for index, volunteer in enumerate(volunteers or [], start=1):
            volunteer_id = volunteer.get('volunteer_id') or volunteer.get('id') or volunteer.get('profile_id')
            if not volunteer_id:
                continue
            snapshot = {
                'name': volunteer.get('name'),
                'location': volunteer.get('location'),
                'categories': volunteer.get('categories'),
                'skills': volunteer.get('skills'),
                'availability': volunteer.get('availability'),
                'profile_url': volunteer.get('profile_url')
            }
            prepared.append((str(volunteer_id), index, volunteer.get('profile_url'), self._json(snapshot)))

        with closing(self.get_connection()) as conn:
            session = conn.execute('''
                SELECT id FROM search_sessions
                WHERE task_id = ?
                ORDER BY id DESC
                LIMIT 1
            ''', (task_id,)).fetchone()
            if not session:
                cursor = conn.execute('''
                    INSERT INTO search_sessions
                    (task_id, criteria_json, status, result_count, finished_at)
                    VALUES (?, ?, 'completed', ?, CURRENT_TIMESTAMP)
                ''', (task_id, self._json({}), len(prepared)))
                search_session_id = cursor.lastrowid
            else:
                search_session_id = session['id']

            conn.execute('DELETE FROM search_session_results WHERE search_session_id = ?', (search_session_id,))
            for volunteer_id, result_rank, source_url, snapshot_json in prepared:
                conn.execute('''
                    INSERT INTO search_session_results
                    (search_session_id, task_id, volunteer_id, result_rank, source_url, snapshot_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (search_session_id, task_id, volunteer_id, result_rank, source_url, snapshot_json))

            distinct_count = len({volunteer_id for volunteer_id, _, _, _ in prepared})
            conn.execute('''
                UPDATE search_sessions
                SET result_count = ?, status = CASE
                        WHEN status = 'started' THEN 'completed'
                        ELSE status
                    END,
                    finished_at = COALESCE(finished_at, CURRENT_TIMESTAMP)
                WHERE id = ?
            ''', (distinct_count, search_session_id))
            conn.commit()

        self.record_audit_event(
            "search_session",
            search_session_id,
            "search_session_results_recorded",
            actor=actor,
            after_state={"task_id": task_id, "result_count": distinct_count},
            risk_level="low"
        )
        return distinct_count

    def get_search_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent search sessions with compact result membership."""
        with closing(self.get_connection()) as conn:
            rows = conn.execute('''
                SELECT ss.*,
                       COUNT(ssr.id) AS linked_result_count,
                       GROUP_CONCAT(ssr.volunteer_id) AS volunteer_ids
                FROM search_sessions ss
                LEFT JOIN search_session_results ssr ON ssr.search_session_id = ss.id
                GROUP BY ss.id
                ORDER BY ss.created_at DESC, ss.id DESC
                LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_search_session_results(
        self,
        search_session_id: Optional[int] = None,
        task_id: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Return volunteer rows captured for one search session or task."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT ssr.*, ss.criteria_json, ss.status AS search_status,
                       v.name AS volunteer_name, v.location AS volunteer_location,
                       v.categories AS volunteer_categories, v.skills AS volunteer_skills
                FROM search_session_results ssr
                JOIN search_sessions ss ON ss.id = ssr.search_session_id
                LEFT JOIN volunteers v ON v.volunteer_id = ssr.volunteer_id
                WHERE 1=1
            '''
            params: List[Any] = []
            if search_session_id is not None:
                query += ' AND ssr.search_session_id = ?'
                params.append(search_session_id)
            if task_id is not None:
                query += ' AND ssr.task_id = ?'
                params.append(task_id)
            query += ' ORDER BY ssr.result_rank ASC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def record_match_assessment(
        self,
        campaign_id: int,
        volunteer_id: str,
        score: float,
        reasons: List[str],
        status: str
    ) -> int:
        """Create or update a campaign-volunteer match assessment."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO match_assessments
                (campaign_id, volunteer_id, score, status, reasons_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, volunteer_id) DO UPDATE SET
                    score = excluded.score,
                    status = excluded.status,
                    reasons_json = excluded.reasons_json,
                    assessed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                campaign_id,
                volunteer_id,
                score,
                status,
                self._json(reasons)
            ))
            conn.commit()

            row = conn.execute('''
                SELECT id FROM match_assessments
                WHERE campaign_id = ? AND volunteer_id = ?
            ''', (campaign_id, volunteer_id)).fetchone()
            assessment_id = row["id"] if row else cursor.lastrowid

        self.record_audit_event(
            "match_assessment",
            assessment_id,
            "match_assessed",
            after_state={
                "campaign_id": campaign_id,
                "volunteer_id": volunteer_id,
                "score": score,
                "status": status
            }
        )
        return assessment_id

    def get_match_assessments(
        self,
        campaign_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List match assessments with volunteer and campaign context."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT ma.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       v.categories AS volunteer_categories, v.skills AS volunteer_skills,
                       c.name AS campaign_name
                FROM match_assessments ma
                LEFT JOIN volunteers v ON ma.volunteer_id = v.volunteer_id
                LEFT JOIN campaigns c ON ma.campaign_id = c.id
                WHERE 1=1
            '''
            params: List[Any] = []
            if campaign_id is not None:
                query += ' AND ma.campaign_id = ?'
                params.append(campaign_id)
            if status:
                query += ' AND ma.status = ?'
                params.append(status)
            query += ' ORDER BY ma.score DESC, ma.assessed_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def record_task_run(self, task_data: Dict[str, Any]) -> None:
        """Create or update durable task-run state."""
        task_id = task_data.get("task_id") or task_data.get("id")
        if not task_id:
            raise ValueError("task_id is required")

        with closing(self.get_connection()) as conn:
            conn.execute('''
                INSERT INTO task_runs
                (task_id, name, description, status, progress_json, result_json,
                 error_message, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    progress_json = excluded.progress_json,
                    result_json = excluded.result_json,
                    error_message = excluded.error_message,
                    started_at = COALESCE(excluded.started_at, task_runs.started_at),
                    completed_at = excluded.completed_at,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                task_id,
                task_data.get("name", ""),
                task_data.get("description", ""),
                task_data.get("status", "unknown"),
                self._json(task_data.get("progress")),
                self._json(task_data.get("result")),
                self._error_label(task_data.get("error_message")),
                task_data.get("started_at"),
                task_data.get("completed_at")
            ))
            conn.commit()

    def get_task_runs(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List durable task-run history."""
        with closing(self.get_connection()) as conn:
            query = 'SELECT * FROM task_runs WHERE 1=1'
            params: List[Any] = []
            if status:
                query += ' AND status = ?'
                params.append(status)
            query += ' ORDER BY updated_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def record_privacy_retention_action(
        self,
        action: str,
        volunteer_id: Optional[str] = None,
        status: str = "proposed",
        reason: str = "",
        evidence: Any = None,
        actor: str = "system"
    ) -> int:
        """Record proposed or completed retention/privacy actions."""
        completed_at = datetime.now().isoformat() if status == "completed" else None
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                INSERT INTO privacy_retention_records
                (volunteer_id, action, status, reason, evidence_json, actor, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                volunteer_id,
                action,
                status,
                reason,
                self._json(evidence),
                actor,
                completed_at
            ))
            record_id = cursor.lastrowid
            conn.commit()

        self.record_audit_event(
            "privacy_retention_record",
            record_id,
            "privacy_retention_recorded",
            actor=actor,
            after_state={
                "volunteer_id": volunteer_id,
                "action": action,
                "status": status,
                "reason": reason
            },
            risk_level="high" if status == "completed" else "medium"
        )
        return record_id

    def get_privacy_retention_records(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List proposed and completed retention/privacy actions."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT prr.*, v.name AS volunteer_name, v.location AS volunteer_location
                FROM privacy_retention_records prr
                LEFT JOIN volunteers v ON prr.volunteer_id = v.volunteer_id
                WHERE 1=1
            '''
            params: List[Any] = []
            if status:
                query += ' AND prr.status = ?'
                params.append(status)
            query += ' ORDER BY prr.created_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def archive_volunteer_for_retention(
        self,
        volunteer_id: str,
        reason: str,
        actor: str = "user"
    ) -> bool:
        """Mark a stale volunteer record as archived without deleting ledger history."""
        with closing(self.get_connection()) as conn:
            volunteer = conn.execute(
                "SELECT volunteer_id, retention_status FROM volunteers WHERE volunteer_id = ?",
                (volunteer_id,)
            ).fetchone()
            if not volunteer:
                return False

            conn.execute('''
                UPDATE volunteers
                SET retention_status = 'archived',
                    archived_at = CURRENT_TIMESTAMP,
                    retention_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE volunteer_id = ?
            ''', (reason, volunteer_id))
            conn.commit()

        self.record_privacy_retention_action(
            action="archive_volunteer",
            volunteer_id=volunteer_id,
            status="completed",
            reason=reason,
            evidence={"volunteer_id": volunteer_id},
            actor=actor
        )
        self.record_audit_event(
            "volunteer",
            volunteer_id,
            "volunteer_archived_for_retention",
            actor=actor,
            before_state={"retention_status": volunteer["retention_status"]},
            after_state={"retention_status": "archived"},
            risk_level="medium"
        )
        return True

    def redact_volunteer_personal_data(
        self,
        volunteer_id: str,
        reason: str,
        actor: str = "user"
    ) -> bool:
        """Minimize personal volunteer fields while preserving ledger references."""
        with closing(self.get_connection()) as conn:
            volunteer = conn.execute(
                "SELECT volunteer_id, retention_status FROM volunteers WHERE volunteer_id = ?",
                (volunteer_id,)
            ).fetchone()
            if not volunteer:
                return False

            conn.execute('''
                UPDATE volunteers
                SET name = 'Redacted volunteer',
                    description = NULL,
                    location = NULL,
                    skills = NULL,
                    categories = NULL,
                    availability = NULL,
                    contact_info = NULL,
                    profile_url = NULL,
                    retention_status = 'redacted',
                    redacted_at = CURRENT_TIMESTAMP,
                    retention_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE volunteer_id = ?
            ''', (reason, volunteer_id))
            conn.commit()

        self.record_privacy_retention_action(
            action="redact_volunteer_personal_data",
            volunteer_id=volunteer_id,
            status="completed",
            reason=reason,
            evidence={"volunteer_id": volunteer_id, "fields": "personal_profile_fields"},
            actor=actor
        )
        self.record_audit_event(
            "volunteer",
            volunteer_id,
            "volunteer_personal_data_redacted",
            actor=actor,
            before_state={"retention_status": volunteer["retention_status"]},
            after_state={"retention_status": "redacted"},
            risk_level="high"
        )
        return True

    def find_duplicate_volunteers(self) -> List[Dict[str, Any]]:
        """Find likely duplicate volunteer records by normalized name and location."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute('''
                SELECT lower(trim(name)) AS normalized_name,
                       lower(trim(location)) AS normalized_location,
                       COUNT(*) AS duplicate_count,
                       GROUP_CONCAT(volunteer_id) AS volunteer_ids
                FROM volunteers
                WHERE COALESCE(trim(name), '') != ''
                GROUP BY normalized_name, normalized_location
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def propose_duplicate_identities(self) -> List[int]:
        """Persist duplicate volunteer groups as identity merge proposals."""
        duplicate_groups = self.find_duplicate_volunteers()
        identity_ids: List[int] = []

        for group in duplicate_groups:
            volunteer_ids = [
                volunteer_id.strip()
                for volunteer_id in (group.get("volunteer_ids") or "").split(",")
                if volunteer_id.strip()
            ]
            if len(volunteer_ids) < 2:
                continue

            canonical_id = volunteer_ids[0]
            reason = (
                f"Same normalized name/location: "
                f"{group.get('normalized_name')} / {group.get('normalized_location')}"
            )

            with closing(self.get_connection()) as conn:
                existing = conn.execute('''
                    SELECT vim.identity_id
                    FROM volunteer_identity_members vim
                    WHERE vim.volunteer_id IN ({})
                    GROUP BY vim.identity_id
                    HAVING COUNT(DISTINCT vim.volunteer_id) = ?
                    LIMIT 1
                '''.format(",".join("?" for _ in volunteer_ids)), (*volunteer_ids, len(volunteer_ids))).fetchone()
                if existing:
                    identity_ids.append(existing["identity_id"])
                    continue

                cursor = conn.execute('''
                    INSERT INTO volunteer_identities
                    (canonical_volunteer_id, status, notes)
                    VALUES (?, 'proposed', ?)
                ''', (canonical_id, reason))
                identity_id = cursor.lastrowid

                for volunteer_id in volunteer_ids:
                    conn.execute('''
                        INSERT INTO volunteer_identity_members
                        (identity_id, volunteer_id, merge_status, reason)
                        VALUES (?, ?, 'proposed', ?)
                    ''', (identity_id, volunteer_id, reason))

                conn.commit()
                identity_ids.append(identity_id)

            self.record_audit_event(
                "volunteer_identity",
                identity_id,
                "duplicate_identity_proposed",
                after_state={"canonical_volunteer_id": canonical_id, "volunteer_ids": volunteer_ids},
                risk_level="medium"
            )

        return identity_ids

    def get_volunteer_identities(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List duplicate identity proposals and confirmed groups."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT vi.id, vi.canonical_volunteer_id, vi.status, vi.notes,
                       vi.created_at, vi.updated_at,
                       cv.name AS canonical_name,
                       GROUP_CONCAT(vim.volunteer_id) AS volunteer_ids,
                       GROUP_CONCAT(v.name) AS volunteer_names
                FROM volunteer_identities vi
                LEFT JOIN volunteer_identity_members vim ON vim.identity_id = vi.id
                LEFT JOIN volunteers v ON vim.volunteer_id = v.volunteer_id
                LEFT JOIN volunteers cv ON vi.canonical_volunteer_id = cv.volunteer_id
                WHERE 1=1
            '''
            params: List[Any] = []
            if status:
                query += ' AND vi.status = ?'
                params.append(status)
            query += '''
                GROUP BY vi.id
                ORDER BY vi.updated_at DESC
                LIMIT ?
            '''
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_confirmed_duplicate_member_map(self) -> Dict[str, Dict[str, Any]]:
        """Map confirmed non-canonical duplicate members to their canonical volunteer."""
        with closing(self.get_connection()) as conn:
            rows = conn.execute('''
                SELECT vi.id AS identity_id,
                       vi.canonical_volunteer_id,
                       vi.notes,
                       vim.volunteer_id
                FROM volunteer_identities vi
                JOIN volunteer_identity_members vim ON vim.identity_id = vi.id
                WHERE vi.status = 'confirmed'
                  AND vim.merge_status = 'confirmed'
                  AND vim.volunteer_id != vi.canonical_volunteer_id
            ''').fetchall()
            return {
                row["volunteer_id"]: {
                    "identity_id": row["identity_id"],
                    "canonical_volunteer_id": row["canonical_volunteer_id"],
                    "notes": row["notes"]
                }
                for row in rows
            }

    def confirm_volunteer_identity(
        self,
        identity_id: int,
        canonical_volunteer_id: str,
        actor: str = "user"
    ) -> bool:
        """Confirm a duplicate identity group without deleting source profiles."""
        with closing(self.get_connection()) as conn:
            identity = conn.execute(
                'SELECT * FROM volunteer_identities WHERE id = ?',
                (identity_id,)
            ).fetchone()
            if not identity:
                return False

            member = conn.execute('''
                SELECT 1 FROM volunteer_identity_members
                WHERE identity_id = ? AND volunteer_id = ?
            ''', (identity_id, canonical_volunteer_id)).fetchone()
            if not member:
                raise ValueError("Canonical volunteer must be a member of the identity group")

            conn.execute('''
                UPDATE volunteer_identities
                SET canonical_volunteer_id = ?, status = 'confirmed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (canonical_volunteer_id, identity_id))
            conn.execute('''
                UPDATE volunteer_identity_members
                SET merge_status = 'confirmed', updated_at = CURRENT_TIMESTAMP
                WHERE identity_id = ?
            ''', (identity_id,))
            conn.commit()

        self.record_audit_event(
            "volunteer_identity",
            identity_id,
            "duplicate_identity_confirmed",
            actor=actor,
            before_state={"canonical_volunteer_id": identity["canonical_volunteer_id"], "status": identity["status"]},
            after_state={"canonical_volunteer_id": canonical_volunteer_id, "status": "confirmed"},
            risk_level="medium"
        )
        return True

    def get_audit_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List audit events for operational review."""
        with closing(self.get_connection()) as conn:
            query = 'SELECT * FROM audit_events WHERE 1=1'
            params = []
            if entity_type:
                query += ' AND entity_type = ?'
                params.append(entity_type)
            if entity_id is not None:
                query += ' AND entity_id = ?'
                params.append(str(entity_id))
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def record_campaign_exclusions(
        self,
        campaign_id: int,
        exclusions: List[Dict[str, Any]],
        actor: str = "system"
    ) -> int:
        """Replace the current explainable exclusion snapshot for a campaign."""
        prepared = [
            (
                exclusion.get('volunteer_id'),
                exclusion.get('reason_code'),
                exclusion.get('reason_message'),
                self._json(exclusion.get('evidence'))
            )
            for exclusion in exclusions
        ]

        with closing(self.get_connection()) as conn:
            existing = conn.execute('''
                SELECT volunteer_id, reason_code, reason_message, evidence_json
                FROM campaign_exclusions
                WHERE campaign_id = ?
            ''', (campaign_id,)).fetchall()
            existing_snapshot = sorted(tuple(row) for row in existing)
            new_snapshot = sorted(prepared)
            if existing_snapshot == new_snapshot:
                return len({volunteer_id for volunteer_id, _, _, _ in prepared if volunteer_id})

            conn.execute('DELETE FROM campaign_exclusions WHERE campaign_id = ?', (campaign_id,))
            for volunteer_id, reason_code, reason_message, evidence_json in prepared:
                conn.execute('''
                    INSERT INTO campaign_exclusions
                    (campaign_id, volunteer_id, reason_code, reason_message, evidence_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    campaign_id,
                    volunteer_id,
                    reason_code,
                    reason_message,
                    evidence_json
                ))
            conn.commit()

        reason_counts: Dict[str, int] = {}
        excluded_volunteers = set()
        for exclusion in exclusions:
            reason_code = exclusion.get('reason_code') or 'unknown'
            reason_counts[reason_code] = reason_counts.get(reason_code, 0) + 1
            if exclusion.get('volunteer_id'):
                excluded_volunteers.add(exclusion['volunteer_id'])

        self.record_audit_event(
            "campaign",
            campaign_id,
            "campaign_exclusions_refreshed",
            actor=actor,
            after_state={
                "excluded_volunteers": len(excluded_volunteers),
                "exclusion_reasons": reason_counts
            },
            risk_level="low"
        )
        return len(excluded_volunteers)

    def get_campaign_exclusions(
        self,
        campaign_id: int,
        reason_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return explainable campaign volunteer exclusions."""
        with closing(self.get_connection()) as conn:
            query = '''
                SELECT ce.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       v.categories AS volunteer_categories, v.retention_status
                FROM campaign_exclusions ce
                LEFT JOIN volunteers v ON ce.volunteer_id = v.volunteer_id
                WHERE ce.campaign_id = ?
            '''
            params: List[Any] = [campaign_id]
            if reason_code:
                query += ' AND ce.reason_code = ?'
                params.append(reason_code)
            query += ' ORDER BY ce.created_at DESC, ce.reason_code ASC LIMIT ?'
            params.append(limit)
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_campaign_operating_summary(
        self,
        campaign_id: int,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Return campaign-level operating ledger state for the desktop UI."""
        with closing(self.get_connection()) as conn:
            campaign = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,)
            ).fetchone()
            if not campaign:
                return None

            def count_rows(query: str, params: tuple = ()) -> int:
                return conn.execute(query, params).fetchone()[0]

            def counts_by_status(table: str, status_column: str = "status") -> Dict[str, int]:
                rows = conn.execute(
                    f'''
                        SELECT {status_column} AS status, COUNT(*) AS count
                        FROM {table}
                        WHERE campaign_id = ?
                        GROUP BY {status_column}
                    ''',
                    (campaign_id,)
                ).fetchall()
                return {row["status"] or "unknown": row["count"] for row in rows}

            message_drafts = conn.execute('''
                SELECT md.*, v.name AS volunteer_name, v.location AS volunteer_location
                FROM message_drafts md
                LEFT JOIN volunteers v ON md.volunteer_id = v.volunteer_id
                WHERE md.campaign_id = ?
                ORDER BY md.updated_at DESC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            send_attempts = conn.execute('''
                SELECT msa.*, v.name AS volunteer_name
                FROM message_send_attempts msa
                LEFT JOIN volunteers v ON msa.volunteer_id = v.volunteer_id
                WHERE msa.campaign_id = ?
                ORDER BY msa.created_at DESC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            responses = conn.execute('''
                SELECT vr.*, v.name AS volunteer_name
                FROM volunteer_responses vr
                LEFT JOIN volunteers v ON vr.volunteer_id = v.volunteer_id
                WHERE vr.campaign_id = ?
                ORDER BY vr.received_at DESC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            follow_ups = conn.execute('''
                SELECT fp.*, v.name AS volunteer_name
                FROM follow_up_plans fp
                LEFT JOIN volunteers v ON fp.volunteer_id = v.volunteer_id
                WHERE fp.campaign_id = ?
                ORDER BY fp.due_at ASC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            contacts = conn.execute('''
                SELECT c.*, v.name AS volunteer_name, v.location AS volunteer_location
                FROM contacts c
                LEFT JOIN volunteers v ON c.volunteer_id = v.volunteer_id
                WHERE c.campaign_id = ?
                ORDER BY c.contact_date DESC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            matches = conn.execute('''
                SELECT ma.*, v.name AS volunteer_name, v.location AS volunteer_location
                FROM match_assessments ma
                LEFT JOIN volunteers v ON ma.volunteer_id = v.volunteer_id
                WHERE ma.campaign_id = ?
                ORDER BY ma.score DESC, ma.assessed_at DESC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            outcomes = conn.execute('''
                SELECT oo.*, v.name AS volunteer_name, v.location AS volunteer_location
                FROM outreach_outcomes oo
                LEFT JOIN volunteers v ON oo.volunteer_id = v.volunteer_id
                WHERE oo.campaign_id = ?
                ORDER BY oo.decided_at DESC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            exclusions = conn.execute('''
                SELECT ce.*, v.name AS volunteer_name, v.location AS volunteer_location,
                       v.categories AS volunteer_categories
                FROM campaign_exclusions ce
                LEFT JOIN volunteers v ON ce.volunteer_id = v.volunteer_id
                WHERE ce.campaign_id = ?
                ORDER BY ce.created_at DESC, ce.reason_code ASC
                LIMIT ?
            ''', (campaign_id, limit)).fetchall()

            audit_events = conn.execute('''
                SELECT *
                FROM audit_events
                WHERE (entity_type = 'campaign' AND entity_id = ?)
                   OR (entity_type = 'message_draft' AND entity_id IN (
                       SELECT CAST(id AS TEXT) FROM message_drafts WHERE campaign_id = ?
                   ))
                   OR (entity_type = 'message_send_attempt' AND entity_id IN (
                       SELECT CAST(id AS TEXT) FROM message_send_attempts WHERE campaign_id = ?
                   ))
                   OR (entity_type = 'volunteer_response' AND entity_id IN (
                       SELECT CAST(id AS TEXT) FROM volunteer_responses WHERE campaign_id = ?
                   ))
                   OR (entity_type = 'follow_up_plan' AND entity_id IN (
                       SELECT CAST(id AS TEXT) FROM follow_up_plans WHERE campaign_id = ?
                   ))
                   OR (entity_type = 'follow_up_send_attempt' AND entity_id IN (
                       SELECT CAST(id AS TEXT) FROM follow_up_send_attempts WHERE campaign_id = ?
                   ))
                   OR (entity_type = 'outreach_outcome' AND entity_id IN (
                       SELECT CAST(id AS TEXT) FROM outreach_outcomes WHERE campaign_id = ?
                   ))
                ORDER BY created_at DESC
                LIMIT ?
            ''', (
                str(campaign_id),
                campaign_id,
                campaign_id,
                campaign_id,
                campaign_id,
                campaign_id,
                campaign_id,
                limit
            )).fetchall()

            return {
                "campaign": dict(campaign),
                "counts": {
                    "volunteers_found": count_rows("SELECT COUNT(*) FROM volunteers"),
                    "contacts": count_rows("SELECT COUNT(*) FROM contacts WHERE campaign_id = ?", (campaign_id,)),
                    "message_drafts": counts_by_status("message_drafts"),
                    "send_attempts": counts_by_status("message_send_attempts"),
                    "responses": counts_by_status("volunteer_responses", "classification"),
                    "follow_ups": counts_by_status("follow_up_plans"),
                    "matches": counts_by_status("match_assessments"),
                    "exclusions": counts_by_status("campaign_exclusions", "reason_code"),
                    "outcomes": counts_by_status("outreach_outcomes", "outcome_type"),
                    "excluded_volunteers": count_rows(
                        "SELECT COUNT(DISTINCT volunteer_id) FROM campaign_exclusions WHERE campaign_id = ?",
                        (campaign_id,)
                    )
                },
                "message_drafts": [dict(row) for row in message_drafts],
                "send_attempts": [dict(row) for row in send_attempts],
                "responses": [dict(row) for row in responses],
                "follow_ups": [dict(row) for row in follow_ups],
                "contacts": [dict(row) for row in contacts],
                "matches": [dict(row) for row in matches],
                "exclusions": [dict(row) for row in exclusions],
                "outcomes": [dict(row) for row in outcomes],
                "audit_events": [dict(row) for row in audit_events]
            }

    def get_operating_statistics(self) -> Dict[str, Any]:
        """Get volunteer outreach operating-ledger statistics for dashboard visibility."""
        stats: Dict[str, Any] = {}
        with closing(self.get_connection()) as conn:
            for status in ["draft", "approved", "rejected", "sending", "sent", "failed"]:
                stats[f"message_drafts_{status}"] = conn.execute(
                    "SELECT COUNT(*) FROM message_drafts WHERE status = ?",
                    (status,)
                ).fetchone()[0]

            stats["responses_received"] = conn.execute(
                "SELECT COUNT(*) FROM volunteer_responses"
            ).fetchone()[0]
            stats["outcomes_recorded"] = conn.execute(
                "SELECT COUNT(*) FROM outreach_outcomes"
            ).fetchone()[0]
            stats["follow_ups_due"] = conn.execute('''
                SELECT COUNT(*) FROM follow_up_plans
                WHERE status = 'due' AND due_at <= CURRENT_TIMESTAMP
            ''').fetchone()[0]
            stats["failed_sends"] = conn.execute(
                "SELECT COUNT(*) FROM message_send_attempts WHERE status = 'failed'"
            ).fetchone()[0]
            stats["duplicate_groups"] = conn.execute('''
                SELECT COUNT(*) FROM (
                    SELECT lower(trim(name)), lower(trim(location))
                    FROM volunteers
                    WHERE COALESCE(trim(name), '') != ''
                    GROUP BY lower(trim(name)), lower(trim(location))
                    HAVING COUNT(*) > 1
                )
            ''').fetchone()[0]
            stats["strong_matches"] = conn.execute(
                "SELECT COUNT(*) FROM match_assessments WHERE status = 'strong'"
            ).fetchone()[0]
            stats["search_sessions_completed"] = conn.execute(
                "SELECT COUNT(*) FROM search_sessions WHERE status = 'completed'"
            ).fetchone()[0]
            stats["search_results_linked"] = conn.execute(
                "SELECT COUNT(*) FROM search_session_results"
            ).fetchone()[0]
            stats["excluded_campaign_volunteers"] = conn.execute(
                "SELECT COUNT(DISTINCT campaign_id || ':' || volunteer_id) FROM campaign_exclusions"
            ).fetchone()[0]
            stats["task_runs_failed"] = conn.execute(
                "SELECT COUNT(*) FROM task_runs WHERE status = 'failed'"
            ).fetchone()[0]
            stats["retention_actions_proposed"] = conn.execute(
                "SELECT COUNT(*) FROM privacy_retention_records WHERE status = 'proposed'"
            ).fetchone()[0]

        return stats
            
    def get_volunteers(
        self,
        filters: Dict[str, Any] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get volunteers with optional filters and bounded database pagination."""
        try:
            if limit is not None and not 1 <= int(limit) <= 5000:
                raise ValueError("limit must be between 1 and 5000")
            if int(offset) < 0:
                raise ValueError("offset cannot be negative")
            with closing(self.get_connection()) as conn:
                query = "SELECT * FROM volunteers WHERE 1=1"
                params = []
                
                if filters:
                    if 'categories' in filters:
                        query += " AND categories LIKE ?"
                        params.append(f"%{filters['categories']}%")
                        
                    if 'location' in filters:
                        query += " AND location LIKE ?"
                        params.append(f"%{filters['location']}%")
                        
                    if 'not_contacted' in filters and filters['not_contacted']:
                        query += " AND volunteer_id NOT IN (SELECT volunteer_id FROM contacts)"
                        
                    if 'not_blacklisted' in filters and filters['not_blacklisted']:
                        query += " AND volunteer_id NOT IN (SELECT volunteer_id FROM blacklist)"
                        
                query += " ORDER BY updated_at DESC, id DESC"
                if limit is not None:
                    query += " LIMIT ? OFFSET ?"
                    params.extend((int(limit), int(offset)))
                elif offset:
                    query += " LIMIT -1 OFFSET ?"
                    params.append(int(offset))
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except (AttributeError, TypeError, sqlite3.DatabaseError) as e:
            logger.error("Failed to get volunteers: %s", type(e).__name__)
            return []

    def get_volunteer_operating_profile(self, volunteer_id: str) -> Optional[Dict[str, Any]]:
        """Get one volunteer with outreach ledger context."""
        try:
            with closing(self.get_connection()) as conn:
                volunteer = conn.execute(
                    'SELECT * FROM volunteers WHERE volunteer_id = ?',
                    (volunteer_id,)
                ).fetchone()
                if not volunteer:
                    return None

                contacts = conn.execute('''
                    SELECT c.*, camp.name AS campaign_name
                    FROM contacts c
                    LEFT JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.volunteer_id = ?
                    ORDER BY c.contact_date DESC
                ''', (volunteer_id,)).fetchall()

                responses = conn.execute('''
                    SELECT vr.*, camp.name AS campaign_name
                    FROM volunteer_responses vr
                    LEFT JOIN campaigns camp ON vr.campaign_id = camp.id
                    WHERE vr.volunteer_id = ?
                    ORDER BY vr.received_at DESC
                ''', (volunteer_id,)).fetchall()

                follow_ups = conn.execute('''
                    SELECT fp.*, camp.name AS campaign_name
                    FROM follow_up_plans fp
                    LEFT JOIN campaigns camp ON fp.campaign_id = camp.id
                    WHERE fp.volunteer_id = ?
                    ORDER BY fp.due_at DESC
                ''', (volunteer_id,)).fetchall()

                match_assessments = conn.execute('''
                    SELECT ma.*, camp.name AS campaign_name
                    FROM match_assessments ma
                    LEFT JOIN campaigns camp ON ma.campaign_id = camp.id
                    WHERE ma.volunteer_id = ?
                    ORDER BY ma.score DESC, ma.assessed_at DESC
                ''', (volunteer_id,)).fetchall()

                duplicate_identities = conn.execute('''
                    SELECT vi.id, vi.canonical_volunteer_id, vi.status, vi.notes,
                           GROUP_CONCAT(vim.volunteer_id) AS volunteer_ids,
                           GROUP_CONCAT(v.name) AS volunteer_names
                    FROM volunteer_identity_members vim
                    LEFT JOIN volunteer_identities vi ON vim.identity_id = vi.id
                    LEFT JOIN volunteers v ON vim.volunteer_id = v.volunteer_id
                    WHERE vim.identity_id IN (
                        SELECT identity_id
                        FROM volunteer_identity_members
                        WHERE volunteer_id = ?
                    )
                    GROUP BY vi.id
                    ORDER BY vi.updated_at DESC
                ''', (volunteer_id,)).fetchall()

                outcomes = conn.execute('''
                    SELECT oo.*, camp.name AS campaign_name
                    FROM outreach_outcomes oo
                    LEFT JOIN campaigns camp ON oo.campaign_id = camp.id
                    WHERE oo.volunteer_id = ?
                    ORDER BY oo.decided_at DESC
                ''', (volunteer_id,)).fetchall()

                return {
                    "volunteer": dict(volunteer),
                    "contacts": [dict(row) for row in contacts],
                    "responses": [dict(row) for row in responses],
                    "follow_ups": [dict(row) for row in follow_ups],
                    "match_assessments": [dict(row) for row in match_assessments],
                    "outcomes": [dict(row) for row in outcomes],
                    "duplicate_identities": [dict(row) for row in duplicate_identities]
                }

        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to get volunteer operating profile: %s", type(e).__name__)
            return None
            
    def add_campaign(self, campaign_data: Dict[str, Any]) -> int:
        """Add new campaign and return campaign ID"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.execute('''
                    INSERT INTO campaigns 
                    (name, description, target_categories, target_location, 
                     target_distance, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    campaign_data.get('name'),
                    campaign_data.get('description'),
                    campaign_data.get('target_categories'),
                    campaign_data.get('target_location'),
                    campaign_data.get('target_distance'),
                    campaign_data.get('message_template')
                ))
                conn.commit()
                return cursor.lastrowid
                
        except (TypeError, ValueError, sqlite3.DatabaseError, AttributeError) as e:
            logger.error("Failed to add campaign: %s", type(e).__name__)
            return None
            
    def get_campaigns(self) -> List[Dict[str, Any]]:
        """Get all campaigns"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to get campaigns: %s", type(e).__name__)
            return []
            
    def add_contact(self, contact_data: Dict[str, Any]) -> bool:
        """Record a contact attempt"""
        try:
            with closing(self.get_connection()) as conn:
                conn.execute('''
                    INSERT INTO contacts 
                    (volunteer_id, campaign_id, message_sent, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    contact_data.get('volunteer_id'),
                    contact_data.get('campaign_id'),
                    contact_data.get('message_sent'),
                    contact_data.get('status', 'sent'),
                    contact_data.get('notes')
                ))
                conn.commit()
                return True
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to add contact: %s", type(e).__name__)
            return False
            
    def get_contacts(self, campaign_id: int = None) -> List[Dict[str, Any]]:
        """Get contact history"""
        try:
            with closing(self.get_connection()) as conn:
                if campaign_id:
                    cursor = conn.execute('''
                        SELECT c.*, v.name as volunteer_name, v.location as volunteer_location
                        FROM contacts c
                        LEFT JOIN volunteers v ON c.volunteer_id = v.volunteer_id
                        WHERE c.campaign_id = ?
                        ORDER BY c.contact_date DESC
                    ''', (campaign_id,))
                else:
                    cursor = conn.execute('''
                        SELECT c.*, v.name as volunteer_name, v.location as volunteer_location,
                               camp.name as campaign_name
                        FROM contacts c
                        LEFT JOIN volunteers v ON c.volunteer_id = v.volunteer_id
                        LEFT JOIN campaigns camp ON c.campaign_id = camp.id
                        ORDER BY c.contact_date DESC
                    ''')
                    
                return [dict(row) for row in cursor.fetchall()]
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to get contacts: %s", type(e).__name__)
            return []
            
    def add_to_blacklist(self, volunteer_id: str, reason: str = "") -> bool:
        """Add volunteer to blacklist"""
        try:
            with closing(self.get_connection()) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO blacklist (volunteer_id, reason)
                    VALUES (?, ?)
                ''', (volunteer_id, reason))
                conn.commit()
                return True
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to add to blacklist: %s", type(e).__name__)
            return False
            
    def remove_from_blacklist(self, volunteer_id: str) -> bool:
        """Remove volunteer from blacklist"""
        try:
            with closing(self.get_connection()) as conn:
                conn.execute('DELETE FROM blacklist WHERE volunteer_id = ?', (volunteer_id,))
                conn.commit()
                return True
                
        except (TypeError, ValueError, sqlite3.DatabaseError, AttributeError) as e:
            logger.error("Failed to remove from blacklist: %s", type(e).__name__)
            return False
            
    def get_blacklist(self) -> List[Dict[str, Any]]:
        """Get blacklisted volunteers"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.execute('''
                    SELECT b.*, v.name as volunteer_name
                    FROM blacklist b
                    LEFT JOIN volunteers v ON b.volunteer_id = v.volunteer_id
                    ORDER BY b.added_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to get blacklist: %s", type(e).__name__)
            return []
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with closing(self.get_connection()) as conn:
                stats = {}
                
                # Total volunteers
                cursor = conn.execute("SELECT COUNT(*) FROM volunteers")
                stats['total_volunteers'] = cursor.fetchone()[0]
                
                # Total campaigns
                cursor = conn.execute("SELECT COUNT(*) FROM campaigns")
                stats['total_campaigns'] = cursor.fetchone()[0]
                
                # Total contacts
                cursor = conn.execute("SELECT COUNT(*) FROM contacts")
                stats['total_contacts'] = cursor.fetchone()[0]
                
                # Blacklisted volunteers
                cursor = conn.execute("SELECT COUNT(*) FROM blacklist")
                stats['blacklisted_volunteers'] = cursor.fetchone()[0]
                
                # Response rate
                cursor = conn.execute("SELECT COUNT(*) FROM contacts WHERE response_received = TRUE")
                responses = cursor.fetchone()[0]
                stats['response_rate'] = (responses / stats['total_contacts'] * 100) if stats['total_contacts'] > 0 else 0
                
                # Recent activity (last 7 days)
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM contacts 
                    WHERE contact_date >= datetime('now', '-7 days')
                ''')
                stats['recent_contacts'] = cursor.fetchone()[0]
                
                return stats
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError, ZeroDivisionError) as e:
            logger.error("Failed to get statistics: %s", type(e).__name__)
            return {}
            
    def search_volunteers(self, search_term: str) -> List[Dict[str, Any]]:
        """Full-text search across volunteer data"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.execute('''
                    SELECT * FROM volunteers 
                    WHERE name LIKE ? OR description LIKE ? OR skills LIKE ? OR location LIKE ?
                    ORDER BY updated_at DESC
                ''', (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Failed to search volunteers: %s", type(e).__name__)
            return []
            
    def cleanup_old_data(self, days: int = 365, confirm: bool = False, actor: str = "user") -> bool:
        """Review or clean up old data beyond the retention period.

        Deletion is high-risk. By default this only records proposed retention
        actions; callers must pass confirm=True for actual deletion.
        """
        try:
            days = int(days)
            if days < 1:
                raise ValueError("days must be positive")
            retention = f"-{days} days"
            candidates = self.get_privacy_retention_candidates(days=days, limit=10000)

            if not confirm:
                for candidate in candidates:
                    self.record_privacy_retention_action(
                        action="delete_volunteer_candidate",
                        volunteer_id=candidate.get("volunteer_id"),
                        status="proposed",
                        reason=f"No recent contact or response within {days} days",
                        evidence=candidate,
                        actor=actor
                    )
                logger.info(f"Recorded {len(candidates)} retention candidate(s); no data deleted")
                return False

            with closing(self.get_connection()) as conn:
                # Remove old contacts
                conn.execute('''
                    DELETE FROM contacts 
                    WHERE contact_date < datetime('now', ?)
                ''', (retention,))
                
                # Remove volunteers not contacted in the retention period
                conn.execute('''
                    DELETE FROM volunteers 
                    WHERE volunteer_id NOT IN (
                        SELECT DISTINCT volunteer_id FROM contacts 
                        WHERE contact_date >= datetime('now', ?)
                    )
                    AND updated_at < datetime('now', ?)
                ''', (retention, retention))
                
                conn.commit()

            for candidate in candidates:
                self.record_privacy_retention_action(
                    action="delete_volunteer",
                    volunteer_id=candidate.get("volunteer_id"),
                    status="completed",
                    reason=f"Confirmed retention cleanup for data older than {days} days",
                    evidence=candidate,
                    actor=actor
                )

            self.record_audit_event(
                "privacy_retention_cleanup",
                days,
                "retention_cleanup_completed",
                actor=actor,
                after_state={"days": days, "volunteer_count": len(candidates)},
                risk_level="high"
            )
            logger.info(f"Cleaned up data older than {days} days after explicit confirmation")
            return True
                
        except (AttributeError, ValueError, RuntimeError, TypeError, sqlite3.DatabaseError, OSError) as e:
            logger.error("Failed to cleanup old data: %s", type(e).__name__)
            return False
