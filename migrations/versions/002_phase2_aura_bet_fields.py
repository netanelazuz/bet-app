"""Phase 2: winning_side, closed_at on bets; side on participations; last_login_at on users.

Revision ID: 002_phase2
Revises: 001_initial
Create Date: 2025-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_phase2"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bets", sa.Column("winning_side", sa.String(20), nullable=True))
    op.add_column("bets", sa.Column("closed_at", sa.DateTime(), nullable=True))

    op.add_column("participations", sa.Column("side", sa.String(20), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE participations SET side = 'yes' WHERE side IS NULL"))

    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("participations", "side")
    op.drop_column("bets", "closed_at")
    op.drop_column("bets", "winning_side")
