"""
models.py - database tables for FoundIt.

All three tables are defined now so the database file is created with its
final shape. Step 1 only uses `User`; `Report` is used from Step 2 and
`Match` from Step 4.

Times are stored as naive UTC. When sending them to the browser, use
`to_iso()` so they end in "Z" and JavaScript converts them to local time.
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_iso(dt):
    """Naive-UTC datetime -> '2026-09-20T10:15:00Z' (or None)."""
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_public_dict(self):
        # Never include password_hash here - this goes to the browser.
        return {"id": self.id, "name": self.name, "email": self.email}


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(10), nullable=False)  # "lost" or "found"
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.String(200), nullable=False)
    event_time = db.Column(db.DateTime, nullable=False, default=utcnow)  # when lost / found
    photo_filename = db.Column(db.String(255), nullable=True)  # file inside backend/uploads
    # searching | potential_match | claimed | returned
    status = db.Column(db.String(20), nullable=False, default="searching")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    owner = db.relationship("User", backref="reports")

    def to_dict(self):
        """The shape the frontend already expects (camelCase)."""
        match_id = None
        if self.kind == "lost":
            pending = Match.query.filter_by(lost_report_id=self.id, status="pending").first()
            match_id = pending.id if pending else None
        return {
            "id": self.id,
            "kind": self.kind,
            "itemName": self.item_name,
            "description": self.description,
            "location": self.location,
            "dateTime": to_iso(self.event_time),
            "photo": f"/api/photos/{self.photo_filename}" if self.photo_filename else None,
            "status": self.status,
            "createdAt": to_iso(self.created_at),
            "matchId": match_id,  # set once the AI finds a potential match
        }


class Match(db.Model):
    __tablename__ = "matches"
    __table_args__ = (
        db.UniqueConstraint("lost_report_id", "found_report_id", name="uq_match_pair"),
    )

    id = db.Column(db.Integer, primary_key=True)
    lost_report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True)
    found_report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True)
    # pending | confirmed | rejected
    status = db.Column(db.String(20), nullable=False, default="pending")
    confidence = db.Column(db.Float, nullable=True)  # 0.0 - 1.0 from Gemini
    reason = db.Column(db.Text, nullable=True)  # Gemini's short explanation
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    lost_report = db.relationship("Report", foreign_keys=[lost_report_id])
    found_report = db.relationship("Report", foreign_keys=[found_report_id])
