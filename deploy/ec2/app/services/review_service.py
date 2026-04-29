"""Review service — business logic compartilhada entre routers.

Centraliza o calculo de agregados de Franchise (reviewCount, ratingSum,
averageRating) que historicamente era feito inline em multiplos lugares
do routers/reviews.py com logicas diferentes (incremental no POST,
delta-based no toggle-status).

Agregado calculado SEMPRE como full-recalc via SELECT COUNT/SUM/AVG
WHERE isActive=true. Mais lento que incremental por O(n) por franquia,
mas evita o bug das 15 franquias orfas (reviewCount divergente da
contagem real) que vimos em prod 2026-04-28.

Performance: SELECT em "Review" com filtro isActive=true e indexado
por franchiseId e' barato. Pra franquias com >1000 reviews, considerar
otimizacao (cache, hook SQLAlchemy event listener) — fora de escopo aqui.
"""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Franchise, Review


def recalculate_franchise_aggregates(db: Session, franchise_id: str) -> None:
    """Recalcula reviewCount/ratingSum/averageRating de uma Franchise.

    Le todas as Reviews ATIVAS (isActive=true) da franquia, agrega via SQL,
    e atualiza os 3 campos denormalizados em Franchise.

    Idempotente: chamar 2x seguidas produz o mesmo resultado.
    Seguro: se nao ha reviews ativas, zera count/sum e seta avg=NULL.

    Args:
        db: Session SQLAlchemy ativa.
        franchise_id: ID (string) da Franchise alvo.

    Raises:
        Nenhuma. Se franchise_id nao existe, UPDATE vira no-op.

    Side effects:
        - UPDATE em Franchise.reviewCount, .ratingSum, .averageRating.
        - NAO faz commit. Caller decide quando commitar (transacao).
    """
    result = db.execute(
        select(
            func.count(Review.id).label("count"),
            func.sum(Review.rating).label("sum"),
            func.avg(Review.rating).label("avg"),
        ).where(
            Review.franchiseId == franchise_id,
            Review.isActive.is_(True),
        )
    ).one()

    new_count = int(result.count or 0)
    new_sum = int(result.sum or 0)
    new_avg = float(result.avg) if result.avg is not None else None

    db.execute(
        update(Franchise)
        .where(Franchise.id == franchise_id)
        .values(
            reviewCount=new_count,
            ratingSum=new_sum,
            averageRating=new_avg,
        )
    )
