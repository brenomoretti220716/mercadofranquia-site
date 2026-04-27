"""fatia 1.8.1: BusinessModel investment + payback per modelo

Revision ID: e7a3f1d8b9c2
Revises: c4d8e9a1b3f2
Create Date: 2026-04-27 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a3f1d8b9c2'
down_revision: Union[str, Sequence[str], None] = 'c4d8e9a1b3f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Fatia 1.8.1 (continuacao c4d8e9a1b3f2): cada BusinessModel ganha
    investment (valor unico do investimento total) e payback (meses).
    Sao os dois numeros que o investidor mais compara entre modelos
    (Loja vs Container vs Quiosque). Range agregado da Franchise
    (min/maxInvestment, min/maxReturnOnInvestment) pode ser
    auto-derivado dos modelos numa fatia futura.

    Tipos espelham equivalentes em Franchise:
      - investment: Numeric(15, 2) (REAIS, mesmo padrao dos outros
        monetarios em BusinessModel ja adicionados na c4d8e9a1b3f2)
      - payback: Integer (meses, igual a Franchise.minimumReturnOnInvestment)

    Ambos nullable, sem default — risco zero pras franquias ja
    cadastradas.
    """
    op.add_column(
        "BusinessModel",
        sa.Column("investment", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "BusinessModel",
        sa.Column("payback", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("BusinessModel", "payback")
    op.drop_column("BusinessModel", "investment")
