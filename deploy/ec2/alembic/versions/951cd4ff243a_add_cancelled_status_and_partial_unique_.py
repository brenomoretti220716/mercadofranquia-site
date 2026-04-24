"""add cancelled status and partial unique to franchisor_request

Revision ID: 951cd4ff243a
Revises: f71b856158d0
Create Date: 2026-04-24 17:54:25.426236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '951cd4ff243a'
down_revision: Union[str, Sequence[str], None] = 'f71b856158d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Two changes to FranchisorRequest needed for the "cancel my request" flow:

    1. Replace the legacy Prisma-era CHECK constraint "FranchisorRequest_status_check"
       so CANCELLED is accepted. The old CHECK only allowed
       ('PENDING', 'APPROVED', 'REJECTED', 'UNDER_REVIEW'), so setting
       status='CANCELLED' was raising IntegrityError even though models.py
       declares status as a plain String(20). The constraint is not declared
       in SQLAlchemy models — it lives in the DB from the old Prisma schema —
       so we have to DROP + CREATE by exact name via raw SQL.

    2. Add a partial unique index preventing two active (PENDING/UNDER_REVIEW)
       FranchisorRequest rows for the same franchiseId simultaneously.
    """
    # 1. Replace legacy CHECK constraint to accept CANCELLED.
    op.execute(
        'ALTER TABLE "FranchisorRequest" '
        'DROP CONSTRAINT "FranchisorRequest_status_check"'
    )
    op.execute(
        'ALTER TABLE "FranchisorRequest" '
        'ADD CONSTRAINT "FranchisorRequest_status_check" '
        "CHECK (status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'CANCELLED'))"
    )

    # 2. Partial unique: at most one active claim per franchise.
    op.create_index(
        "idx_franchisor_request_unique_active_claim",
        "FranchisorRequest",
        ["franchiseId"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'UNDER_REVIEW')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Inverse of step 2.
    op.drop_index(
        "idx_franchisor_request_unique_active_claim",
        table_name="FranchisorRequest",
    )
    # Inverse of step 1: restore the pre-CANCELLED CHECK.
    op.execute(
        'ALTER TABLE "FranchisorRequest" '
        'DROP CONSTRAINT "FranchisorRequest_status_check"'
    )
    op.execute(
        'ALTER TABLE "FranchisorRequest" '
        'ADD CONSTRAINT "FranchisorRequest_status_check" '
        "CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'UNDER_REVIEW'))"
    )
