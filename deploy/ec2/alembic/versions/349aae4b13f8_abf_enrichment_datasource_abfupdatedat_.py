"""abf enrichment dataSource + abfUpdatedAt + BusinessModel cols + nullable

Revision ID: 349aae4b13f8
Revises: 9e73d144e686
Create Date: 2026-04-29 13:23:16.782800

Mudancas (Fatia ABF enrichment):
- Franchise:
  - ADD COLUMN abfUpdatedAt DATE (rastreabilidade de update na ABF)
  - ADD COLUMN dataSource VARCHAR(50) + CHECK constraint (5 valores)
  - Data migration: UPDATE WHERE dataSource IS NULL SET 'imported-legacy'
    (popula as 1404 franquias existentes pre-migration)
- BusinessModel:
  - ALTER description SET NULL (era NOT NULL — bloqueava insert via scraper)
  - ALTER photoUrl SET NULL (mesma justificativa)
  - ADD COLUMN headquarter VARCHAR(191) (HQ por modelo, ABF traz)
  - ADD COLUMN totalUnits INTEGER (unidades por modelo)
  - ADD COLUMN advertisingFeeObservation TEXT (texto livre que ABF traz)
  - ADD COLUMN royaltiesObservation TEXT (mesma justificativa)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '349aae4b13f8'
down_revision: Union[str, None] = '9e73d144e686'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Franchise — rastreabilidade ABF
    # ------------------------------------------------------------------
    op.add_column(
        'Franchise',
        sa.Column('abfUpdatedAt', sa.Date(), nullable=True),
    )

    op.add_column(
        'Franchise',
        sa.Column('dataSource', sa.String(length=50), nullable=True),
    )

    op.create_check_constraint(
        'Franchise_dataSource_check',
        'Franchise',
        "\"dataSource\" IS NULL OR \"dataSource\" IN ("
        "'manual', 'claimed', 'abf-portaldofranchising', "
        "'encontresua-franquia', 'imported-legacy')",
    )

    # Data migration: popular legacies (1404 rows pre-existentes) com
    # 'imported-legacy'. Pos-migration, NULL fica reservado pra inserts
    # novos via admin que nao setarem.
    op.execute(
        "UPDATE \"Franchise\" SET \"dataSource\" = 'imported-legacy' "
        "WHERE \"dataSource\" IS NULL"
    )

    # ------------------------------------------------------------------
    # 2. BusinessModel — relax NOT NULL (description + photoUrl)
    # ------------------------------------------------------------------
    op.alter_column(
        'BusinessModel',
        'description',
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        'BusinessModel',
        'photoUrl',
        existing_type=sa.String(length=191),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # 3. BusinessModel — colunas novas pra ABF
    # ------------------------------------------------------------------
    op.add_column(
        'BusinessModel',
        sa.Column('headquarter', sa.String(length=191), nullable=True),
    )
    op.add_column(
        'BusinessModel',
        sa.Column('totalUnits', sa.Integer(), nullable=True),
    )
    op.add_column(
        'BusinessModel',
        sa.Column('advertisingFeeObservation', sa.Text(), nullable=True),
    )
    op.add_column(
        'BusinessModel',
        sa.Column('royaltiesObservation', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # 3. Drop BusinessModel colunas novas
    op.drop_column('BusinessModel', 'royaltiesObservation')
    op.drop_column('BusinessModel', 'advertisingFeeObservation')
    op.drop_column('BusinessModel', 'totalUnits')
    op.drop_column('BusinessModel', 'headquarter')

    # 2. Restaurar NOT NULL em description + photoUrl
    # Atencao: rows com description=NULL ou photoUrl=NULL bloqueiam o
    # downgrade. Se houver rows criadas via scraper sem esses campos,
    # precisara backfill manual antes (ex: SET '' nas que estao NULL).
    op.alter_column(
        'BusinessModel',
        'photoUrl',
        existing_type=sa.String(length=191),
        nullable=False,
    )
    op.alter_column(
        'BusinessModel',
        'description',
        existing_type=sa.Text(),
        nullable=False,
    )

    # 1. Drop Franchise rastreabilidade ABF
    op.drop_constraint('Franchise_dataSource_check', 'Franchise', type_='check')
    op.drop_column('Franchise', 'dataSource')
    op.drop_column('Franchise', 'abfUpdatedAt')
