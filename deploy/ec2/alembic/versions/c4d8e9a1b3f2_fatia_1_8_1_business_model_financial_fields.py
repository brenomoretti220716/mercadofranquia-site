"""fatia 1.8.1: BusinessModel financial fields per modelo

Revision ID: c4d8e9a1b3f2
Revises: 66a4e030b691
Create Date: 2026-04-27 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e9a1b3f2'
down_revision: Union[str, Sequence[str], None] = '66a4e030b691'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Fatia 1.8.1: cada BusinessModel passa a ter dataset financeiro proprio,
    espelhando o set de campos ja existente em Franchise. Permite cards de
    modelo (Loja / Container / Quiosque) com Investimento, Royalties, Taxa
    de propaganda, Capital de giro etc. PER modelo, em vez do agregado da
    Franchise repetido.

    Tipos espelham Franchise pra consistency:
      - Valores monetarios: Numeric(15, 2) (REAIS)
      - Percentuais: Numeric(5, 2) (max 999.99)
      - Area: Integer (m²)
      - Strings descritivas: String(191)

    Todos nullable, sem default — risco zero pras franquias ja cadastradas.
    Editor de franquia em backlog (Fatia 1.8.2) — neste momento os valores
    sao populados via seed dev.
    """
    op.add_column(
        "BusinessModel",
        sa.Column("franchiseFee", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("royalties", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("advertisingFee", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("workingCapital", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("setupCapital", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column(
            "averageMonthlyRevenue",
            sa.Numeric(precision=15, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("storeArea", sa.Integer(), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column(
            "calculationBaseRoyaltie", sa.String(length=191), nullable=True
        ),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("calculationBaseAdFee", sa.String(length=191), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("BusinessModel", "calculationBaseAdFee")
    op.drop_column("BusinessModel", "calculationBaseRoyaltie")
    op.drop_column("BusinessModel", "storeArea")
    op.drop_column("BusinessModel", "averageMonthlyRevenue")
    op.drop_column("BusinessModel", "setupCapital")
    op.drop_column("BusinessModel", "workingCapital")
    op.drop_column("BusinessModel", "advertisingFee")
    op.drop_column("BusinessModel", "royalties")
    op.drop_column("BusinessModel", "franchiseFee")
