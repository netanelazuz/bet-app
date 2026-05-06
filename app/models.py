"""SQLAlchemy models: User and Bet."""
import enum
from datetime import datetime
from app import db


class Difficulty(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BetStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    nickname = db.Column(db.String(80), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    open_bets = db.Column(db.Integer, default=0)
    aura = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    created_bets = db.relationship("Bet", backref="creator", lazy="dynamic", foreign_keys="Bet.created_by_id")
    participations = db.relationship("Participation", backref="user", lazy="dynamic", foreign_keys="Participation.user_id")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname or self.username,
            "bio": self.bio,
            "wins": self.wins,
            "losses": self.losses,
            "open_bets": self.open_bets,
            "aura": self.aura,
        }


class Bet(db.Model):
    __tablename__ = "bets"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    win_prize = db.Column(db.Integer, nullable=True)  # dynamic, can be computed
    difficulty = db.Column(db.Enum(Difficulty, values_callable=lambda x: [e.value for e in x]), default=Difficulty.MEDIUM)
    end_date = db.Column(db.DateTime, nullable=True)
    end_condition = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Enum(BetStatus, values_callable=lambda x: [e.value for e in x]), default=BetStatus.OPEN)
    report_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    winning_side = db.Column(db.String(20), nullable=True)  # "yes" or "no", set when bet closes
    closed_at = db.Column(db.DateTime, nullable=True)

    participations = db.relationship("Participation", backref="bet", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "description": self.description,
            "win_prize": self.win_prize,
            "difficulty": self.difficulty.value if self.difficulty else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "end_condition": self.end_condition,
            "status": self.status.value if self.status else None,
            "report_count": self.report_count,
            "created_by_id": self.created_by_id,
        }


class Participation(db.Model):
    """User participation in a bet (stake, side, and outcome)."""
    __tablename__ = "participations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    bet_id = db.Column(db.Integer, db.ForeignKey("bets.id"), nullable=False)
    stake = db.Column(db.Integer, nullable=False)  # Aura staked (variable)
    side = db.Column(db.String(20), nullable=True)  # "yes" or "no" (user prediction); legacy rows may be NULL
    is_winner = db.Column(db.Boolean, nullable=True)  # None = not settled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "bet_id", name="uq_user_bet"),)
