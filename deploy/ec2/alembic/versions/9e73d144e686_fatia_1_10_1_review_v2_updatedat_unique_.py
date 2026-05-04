"""fatia 1.10.1 review v2 updatedAt + unique partial + ReviewRemovalRequest

Revision ID: 9e73d144e686
Revises: b5a2c91e7f4d
Create Date: 2026-04-28 23:01:25.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9e73d144e686'
down_revision: Union[str, None] = 'b5a2c91e7f4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Adicionar updatedAt como nullable primeiro (pra rodar backfill)
    op.add_column(
        'Review',
        sa.Column(
            'updatedAt',
            postgresql.TIMESTAMP(precision=3, timezone=False),
            nullable=True,
        ),
    )

    # 2. Backfill: reviews existentes recebem updatedAt = createdAt
    op.execute('UPDATE "Review" SET "updatedAt" = "createdAt" WHERE "updatedAt" IS NULL')

    # 3. Aplicar NOT NULL + server_default
    op.alter_column(
        'Review',
        'updatedAt',
        existing_type=postgresql.TIMESTAMP(precision=3, timezone=False),
        nullable=False,
        server_default=sa.text('CURRENT_TIMESTAMP'),
    )

    # 4. Drop UNIQUE constraint hard existente em (authorId, franchiseId)
    # Nome historico do Prisma: "Review_authorId_franchiseId_key" — verificar antes
    op.execute('ALTER TABLE "Review" DROP CONSTRAINT IF EXISTS "Review_authorId_franchiseId_key"')

    # 5. Criar UNIQUE INDEX parcial: 1 review ATIVA por user/franquia
    # Soft-deleted (isActive=false) nao bloqueia nova review do mesmo user
    op.execute("""
        CREATE UNIQUE INDEX "Review_author_franchise_active_idx"
        ON "Review" ("authorId", "franchiseId")
        WHERE "isActive" = true
    """)

    # 6. Criar tabela ReviewRemovalRequest (preparacao pra fatia 1.10.5)
    # Sem codigo consumindo ainda - migration idempotente
    op.create_table(
        'ReviewRemovalRequest',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('reviewId', sa.Integer(), nullable=False),
        sa.Column('requestedBy', sa.String(length=191), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('adminNote', sa.Text(), nullable=True),
        sa.Column('reviewedBy', sa.String(length=191), nullable=True),
        sa.Column('reviewedAt', postgresql.TIMESTAMP(precision=3, timezone=False), nullable=True),
        sa.Column(
            'createdAt',
            postgresql.TIMESTAMP(precision=3, timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.ForeignKeyConstraint(
            ['reviewId'],
            ['Review.id'],
            name='ReviewRemovalRequest_reviewId_fkey',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['requestedBy'],
            ['User.id'],
            name='ReviewRemovalRequest_requestedBy_fkey',
        ),
        sa.ForeignKeyConstraint(
            ['reviewedBy'],
            ['User.id'],
            name='ReviewRemovalRequest_reviewedBy_fkey',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name='ReviewRemovalRequest_status_check',
        ),
    )

    op.create_index(
        'ReviewRemovalRequest_status_idx',
        'ReviewRemovalRequest',
        ['status'],
    )
    op.create_index(
        'ReviewRemovalRequest_review_idx',
        'ReviewRemovalRequest',
        ['reviewId'],
    )


def downgrade() -> None:
    # Drop tabela ReviewRemovalRequest
    op.drop_index('ReviewRemovalRequest_review_idx', table_name='ReviewRemovalRequest')
    op.drop_index('ReviewRemovalRequest_status_idx', table_name='ReviewRemovalRequest')
    op.drop_table('ReviewRemovalRequest')

    # Drop UNIQUE parcial criado no upgrade
    op.execute('DROP INDEX IF EXISTS "Review_author_franchise_active_idx"')

    # NOTA: NAO recriar UNIQUE hard porque ela nao existia no DB pre-upgrade
    # (verificado em prod: pg_constraint mostra zero UNIQUE em Review).
    # Controle de "1 review por user/franquia" e app-level no router.

    # Drop coluna updatedAt
    op.drop_column('Review', 'updatedAt')
