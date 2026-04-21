"""sprint 3 phase 2: add User.jobTitle

Revision ID: f71b856158d0
Revises: 1d52f2c66760
Create Date: 2026-04-21 19:00:26.654525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f71b856158d0'
down_revision: Union[str, Sequence[str], None] = '1d52f2c66760'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Noise do autogenerate removido: alter_column em 'AdminActionLog.id' era só
    # diferença textual entre CAST(...) e ::character varying. Semanticamente igual.
    op.add_column('User', sa.Column('jobTitle', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('User', 'jobTitle')
