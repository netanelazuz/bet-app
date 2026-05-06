"""Initial schema: users, bets, participations.

Revision ID: 001_initial
Revises:
Create Date: 2025-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("nickname", sa.String(80), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("open_bets", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("aura", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "bets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("win_prize", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.Enum("easy", "medium", "hard", name="difficulty"), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("end_condition", sa.String(200), nullable=True),
        sa.Column("status", sa.Enum("open", "closed", "canceled", name="betstatus"), nullable=True),
        sa.Column("report_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bets_created_by_id", "bets", ["created_by_id"], unique=False)

    op.create_table(
        "participations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bet_id", sa.Integer(), nullable=False),
        sa.Column("stake", sa.Integer(), nullable=False),
        sa.Column("is_winner", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bet_id"], ["bets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "bet_id", name="uq_user_bet"),
    )


def downgrade() -> None:
    op.drop_table("participations")
    op.drop_table("bets")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    sa.Enum(name="betstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="difficulty").drop(op.get_bind(), checkfirst=True)
