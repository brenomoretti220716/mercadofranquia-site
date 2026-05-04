"""business_model_royalty_v2 — royalty/adFee type + fixed amount

Revision ID: 3c59cb1b21a4
Revises: 349aae4b13f8
Create Date: 2026-05-04 00:00:00.000000

Mudancas (Fatia ABF refresh / EncontreSuaFranquia):
- BusinessModel:
  - ADD COLUMN royaltyType VARCHAR(20) + CHECK
    (PERCENTAGE / FIXED / VARIABLE / NONE)
  - ADD COLUMN royaltyFixedAmount INTEGER (centavos, populado quando type=FIXED)
  - ADD COLUMN adFeeType VARCHAR(20) + CHECK (mesmo enum)
  - ADD COLUMN adFeeFixedAmount INTEGER (centavos)

Backfill esperado em prod (validado via queries pre-migration):
  - PERCENTAGE: 148 BMs com royalties IS NOT NULL
  - FIXED: 29 BMs com calculationBaseRoyaltie ILIKE '%fixo%' (todos parseaveis)
  - NULL: 59 BMs sem dados estruturados
  - Mesma distribuicao para adFee (com adicional para 'Valor fixo' patterns)

Pre-requisito de:
  - apply_enrichment.py do ABF refresh (BMs novos populam royalty_type)
  - apply_encontresua_v1.py (idem)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3c59cb1b21a4'
down_revision: Union[str, None] = '349aae4b13f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROYALTY_TYPE_VALUES = "'PERCENTAGE','FIXED','VARIABLE','NONE'"


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. BusinessModel — colunas novas
    # ------------------------------------------------------------------
    op.add_column(
        'BusinessModel',
        sa.Column('royaltyType', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'BusinessModel',
        sa.Column('royaltyFixedAmount', sa.Integer(), nullable=True),
    )
    op.add_column(
        'BusinessModel',
        sa.Column('adFeeType', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'BusinessModel',
        sa.Column('adFeeFixedAmount', sa.Integer(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. CHECK constraints
    # ------------------------------------------------------------------
    op.create_check_constraint(
        'BusinessModel_royaltyType_check',
        'BusinessModel',
        f"\"royaltyType\" IS NULL OR \"royaltyType\" IN ({ROYALTY_TYPE_VALUES})",
    )
    op.create_check_constraint(
        'BusinessModel_adFeeType_check',
        'BusinessModel',
        f"\"adFeeType\" IS NULL OR \"adFeeType\" IN ({ROYALTY_TYPE_VALUES})",
    )

    # ------------------------------------------------------------------
    # 3. Backfill royaltyType
    # ------------------------------------------------------------------
    # Royalty IS NOT NULL → certamente PERCENTAGE
    # (Query 1 confirmou zero_count=0, então toda valor existente é %)
    op.execute(
        "UPDATE \"BusinessModel\" SET \"royaltyType\" = 'PERCENTAGE' "
        "WHERE \"royalties\" IS NOT NULL"
    )
    # Royalty IS NULL + base contendo 'Fixo' → FIXED legado
    # (29 rows na prod com calculationBaseRoyaltie='Fixo Mensal')
    op.execute(
        "UPDATE \"BusinessModel\" SET \"royaltyType\" = 'FIXED' "
        "WHERE \"royalties\" IS NULL "
        "AND \"calculationBaseRoyaltie\" ILIKE '%fixo%'"
    )

    # ------------------------------------------------------------------
    # 4. Backfill royaltyFixedAmount via regex em royaltiesObservation
    # ------------------------------------------------------------------
    # Validado em Query 3: 29/29 rows tem 'R$ <valor>' parseavel
    # Conversao: 'R$ 1.500,50' -> 150050 centavos
    #   step 1: substring extrai '1.500,50'
    #   step 2: REPLACE('.','') -> '1500,50' (remove milhar BR)
    #   step 3: REPLACE(',','.') -> '1500.50' (decimal US)
    #   step 4: ::numeric * 100 -> 150050
    op.execute(r"""
        UPDATE "BusinessModel" SET "royaltyFixedAmount" = (
            ROUND(
                CAST(
                    REPLACE(REPLACE(
                        substring("royaltiesObservation" FROM 'R\$\s*([\d.,]+)'),
                        '.', ''), ',', '.'
                    ) AS NUMERIC
                ) * 100
            )::integer
        )
        WHERE "royaltyType" = 'FIXED'
          AND "royaltiesObservation" ~ 'R\$\s*[\d.,]+'
    """)

    # ------------------------------------------------------------------
    # 5. Backfill adFeeType (mesmo padrao + 'valor' como sinonimo de fixo)
    # ------------------------------------------------------------------
    op.execute(
        "UPDATE \"BusinessModel\" SET \"adFeeType\" = 'PERCENTAGE' "
        "WHERE \"advertisingFee\" IS NOT NULL"
    )
    # Query 2b mostrou 'Fixo Mensal' (32) + 'Valor Fixo para modelo loja' (2)
    # + 'Valor fixo' (1) — todos sao tipos FIXED disfarcados de base
    op.execute(
        "UPDATE \"BusinessModel\" SET \"adFeeType\" = 'FIXED' "
        "WHERE \"advertisingFee\" IS NULL "
        "AND (\"calculationBaseAdFee\" ILIKE '%fixo%' "
        "OR \"calculationBaseAdFee\" ILIKE '%valor%')"
    )

    # ------------------------------------------------------------------
    # 6. Backfill adFeeFixedAmount
    # ------------------------------------------------------------------
    op.execute(r"""
        UPDATE "BusinessModel" SET "adFeeFixedAmount" = (
            ROUND(
                CAST(
                    REPLACE(REPLACE(
                        substring("advertisingFeeObservation" FROM 'R\$\s*([\d.,]+)'),
                        '.', ''), ',', '.'
                    ) AS NUMERIC
                ) * 100
            )::integer
        )
        WHERE "adFeeType" = 'FIXED'
          AND "advertisingFeeObservation" ~ 'R\$\s*[\d.,]+'
    """)


def downgrade() -> None:
    op.drop_constraint(
        'BusinessModel_adFeeType_check', 'BusinessModel', type_='check'
    )
    op.drop_constraint(
        'BusinessModel_royaltyType_check', 'BusinessModel', type_='check'
    )
    op.drop_column('BusinessModel', 'adFeeFixedAmount')
    op.drop_column('BusinessModel', 'adFeeType')
    op.drop_column('BusinessModel', 'royaltyFixedAmount')
    op.drop_column('BusinessModel', 'royaltyType')
