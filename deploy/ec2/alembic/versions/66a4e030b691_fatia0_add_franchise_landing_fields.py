"""fatia 0: add 14 nullable Franchise fields for landing redesign

Revision ID: 66a4e030b691
Revises: 951cd4ff243a
Create Date: 2026-04-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '66a4e030b691'
down_revision: Union[str, Sequence[str], None] = '951cd4ff243a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Fatia 0 do redesign editor + landing publica (docs/specs/REDESIGN_EDITOR_FRANQUIA.md
    secao 3.2): adiciona 14 colunas nullable a tabela Franchise para alimentar a
    nova landing. Agrupado em 1 migration unica para evitar 4 deploys de DB ao
    longo das fatias 1-4. Frontend e backend ainda nao consomem esses campos;
    serao habilitados nas fatias seguintes. Todos nullable, sem default — risco
    zero para franquias ja cadastradas.

    Nomenclatura: camelCase para alinhar com a convencao Prisma legada ja em uso
    na tabela (headquarterState, videoUrl, galleryUrls, lastScrapedAt etc.). A
    spec usa snake_case (forma idiomatica Python), mas o nome da coluna SQL real
    segue o resto da Franchise.

    Tipos JSON: postgresql.JSONB, alinhado com sponsorPlacements ja em producao.
    """
    # Tab Informacoes (5 campos)
    op.add_column(
        "Franchise",
        sa.Column("tagline", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column(
            "differentials",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "Franchise",
        sa.Column("idealFranchiseeProfile", sa.Text(), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column(
            "processSteps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "Franchise",
        sa.Column(
            "testimonials",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Tab Midia & contato (7 campos)
    op.add_column(
        "Franchise",
        sa.Column("bannerUrl", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column("phone", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column("whatsapp", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column("publicEmail", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column("instagramUrl", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column("facebookUrl", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "Franchise",
        sa.Column("linkedinUrl", sa.String(length=200), nullable=True),
    )

    # Frescor de unidades (2 campos)
    op.add_column(
        "Franchise",
        sa.Column(
            "totalUnitsUpdatedAt",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
    )
    op.add_column(
        "Franchise",
        sa.Column(
            "totalUnitsLastConfirmedAt",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Frescor de unidades
    op.drop_column("Franchise", "totalUnitsLastConfirmedAt")
    op.drop_column("Franchise", "totalUnitsUpdatedAt")

    # Tab Midia & contato
    op.drop_column("Franchise", "linkedinUrl")
    op.drop_column("Franchise", "facebookUrl")
    op.drop_column("Franchise", "instagramUrl")
    op.drop_column("Franchise", "publicEmail")
    op.drop_column("Franchise", "whatsapp")
    op.drop_column("Franchise", "phone")
    op.drop_column("Franchise", "bannerUrl")

    # Tab Informacoes
    op.drop_column("Franchise", "testimonials")
    op.drop_column("Franchise", "processSteps")
    op.drop_column("Franchise", "idealFranchiseeProfile")
    op.drop_column("Franchise", "differentials")
    op.drop_column("Franchise", "tagline")
