"""fatia 1.8.1: BusinessModel profitability per modelo

Revision ID: b5a2c91e7f4d
Revises: e7a3f1d8b9c2
Create Date: 2026-04-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5a2c91e7f4d'
down_revision: Union[str, Sequence[str], None] = 'e7a3f1d8b9c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Fatia 1.8.1 (terceira migration apos c4d8e9a1b3f2 e e7a3f1d8b9c2):
    BusinessModel ganha profitability — rentabilidade media em
    percentual sobre faturamento. Usado nos cards simplificados de
    modelos (Investimento, Payback, Faturamento, Rentabilidade,
    Area).

    Tipo: Numeric(5, 2) — mesmo padrao de royalties/advertisingFee.
    Nullable, sem default — risco zero.
    """
    op.add_column(
        "BusinessModel",
        sa.Column("profitability", sa.Numeric(precision=5, scale=2), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("BusinessModel", "profitability")
