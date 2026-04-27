#!/usr/bin/env python3
"""
Seed idempotente de pizza-do-joao com 4 reviews + 1 response — APENAS DEV.

Uso:
    DATABASE_URL=postgresql://mf_user:dev_password_local@localhost:5432/mercadofranquia \
        ~/Developer/mercadofranquia/.venv/bin/python \
        deploy/ec2/scripts/dev/seed_reviews_pizza_joao.py

O que faz:
    1. Procura a Franchise pizza-do-joao. Aborta se nao existir.
    2. Aprova (status=APPROVED) se estiver em PENDING — necessario pro
       endpoint publico GET /api/franchises/pizza-do-joao servir o
       payload (PENDING/REJECTED retornam 404 pra nao-admins).
    3. Conta reviews ativos. Se 0, cria 4 reviews + 1 ReviewResponse com
       o shape do mockup v10. Se ha reviews, pula criacao (idempotente —
       nao duplica).
    4. Refresh denormalized counters em Franchise.

Reviews seedados (espelham o mockup pagina_publica_franquia_v10_handoff.html):
    - rating 5, NAO anonima, "payback rapido", 12 dias atras
    - rating 4, NAO anonima, "capital de giro subestimado", 28 dias atras
    - rating 5, ANONIMA, "transparencia da rede", 41 dias atras
    - rating 3, NAO anonima, "critica suporte", 60 dias atras
    - 1 ReviewResponse no review rating 5 mais recente (11 dias atras)

Os usuarios de teste sao criados com IDs deterministicos (sha256 do email)
pra a re-execucao reaproveitar as mesmas linhas.

NUNCA rode em prod — os hashes de senha sao invalidos por design.
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    import psycopg
except ImportError:
    sys.exit("Missing dependency: pip install 'psycopg[binary]>=3.1'")


SLUG = "pizza-do-joao"


REVIEWS = [
    {
        "name": "Itamar Lopes",
        "email": "itamar.seed@example.com",
        "phone": "+55 11 90000-0001",
        "rating": 5,
        "anonymous": False,
        "days_ago": 12,
        "comment": (
            "Investi em uma loja em 2023. Em 18 meses ja tinha o payback. "
            "O suporte da rede pra escolher ponto comercial fez muita diferenca - "
            "me pouparam de erros caros que eu provavelmente cometeria sozinho."
        ),
    },
    {
        "name": "Mariana Souza",
        "email": "mariana.seed@example.com",
        "phone": "+55 11 90000-0002",
        "rating": 4,
        "anonymous": False,
        "days_ago": 28,
        "comment": (
            "Negocio solido e marca bem posicionada. Capital de giro recomendado "
            "parece subestimado pra cidades menores. Tive que ajustar nos primeiros 4 meses."
        ),
    },
    {
        "name": "Investidor Anonimo",
        "email": "anonimo.seed@example.com",
        "phone": "+55 11 90000-0003",
        "rating": 5,
        "anonymous": True,
        "days_ago": 41,
        "comment": (
            "Pesquisei muito antes de escolher franqueador. Pizza do Joao respondeu "
            "todas as duvidas em ate 24h, mandou COF detalhada e indicou outros "
            "franqueados pra eu conversar."
        ),
    },
    {
        "name": "Felipe Ramos",
        "email": "felipe.seed@example.com",
        "phone": "+55 11 90000-0004",
        "rating": 3,
        "anonymous": False,
        "days_ago": 60,
        "comment": (
            "A operacao funciona bem mas o tempo de resposta do suporte caiu nos "
            "ultimos meses. Espero que melhore — o resto da rede compensa."
        ),
    },
]


RESPONSE = {
    "review_index": 0,  # responde o primeiro review da lista (rating 5, mais recente)
    "author_email": "marca.seed@example.com",
    "author_name": "Pizza do Joao - Atendimento",
    "author_phone": "+55 11 90000-9999",
    "author_role": "FRANCHISOR",
    "days_ago": 11,
    "content": (
        "Itamar, valeu demais pelo depoimento. Voce eh referencia no nosso programa "
        "de mentoria. Continue assim!"
    ),
}


def _deterministic_id(seed: str) -> str:
    """32-char hex id derivado do seed string. Estavel entre runs."""
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_user(cur, spec: dict) -> str:
    """Cria usuario se nao existir (lookup por email). Retorna id."""
    cur.execute('SELECT id FROM "User" WHERE email = %s', (spec["email"],))
    row = cur.fetchone()
    if row is not None:
        return row[0]
    user_id = _deterministic_id(spec["email"])
    cur.execute(
        """
        INSERT INTO "User" (
            id, name, email, password, role, "profileType",
            "isActive", phone, "createdAt", "updatedAt"
        )
        VALUES (
            %s, %s, %s, %s, %s, 'INVESTOR',
            true, %s, NOW(), NOW()
        )
        """,
        (
            user_id,
            spec["name"],
            spec["email"],
            "$seed$disabled-not-loginable",
            spec.get("role", "MEMBER"),
            spec["phone"],
        ),
    )
    print(f"  + user '{spec['name']}' ({spec['email']}) id={user_id}")
    return user_id


def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL environment variable is required.")
    # SQLAlchemy-style postgresql+psycopg:// nao eh aceito pelo psycopg
    # bruto — strip o dialect.
    if db_url.startswith("postgresql+psycopg://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg://") :]

    with psycopg.connect(db_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            # 1. Lookup franchise.
            cur.execute(
                'SELECT id, status FROM "Franchise" WHERE slug = %s',
                (SLUG,),
            )
            row = cur.fetchone()
            if row is None:
                sys.exit(f"Franchise '{SLUG}' not found in DB.")
            franchise_id, status = row
            print(f"Found franchise {SLUG}: id={franchise_id} status={status}")

            # 2. Aprova se PENDING.
            if status != "APPROVED":
                cur.execute(
                    'UPDATE "Franchise" SET status = %s, "updatedAt" = NOW() WHERE id = %s',
                    ("APPROVED", franchise_id),
                )
                print(f"Status: {status} -> APPROVED")
            else:
                print("Status ja APPROVED.")

            # 3. Conta reviews ativos. Se 0, cria; se >0, skip (idempotente).
            cur.execute(
                'SELECT COUNT(*) FROM "Review" WHERE "franchiseId" = %s AND "isActive" = true',
                (franchise_id,),
            )
            review_count = cur.fetchone()[0]
            print(f"Reviews ativos existentes: {review_count}")

            if review_count == 0:
                review_ids: list[int] = []
                for spec in REVIEWS:
                    user_id = _ensure_user(cur, spec)
                    created_at = _utcnow() - timedelta(days=spec["days_ago"])
                    cur.execute(
                        """
                        INSERT INTO "Review" (
                            rating, comment, anonymous, "createdAt",
                            "isActive", "isFranchisee", "franchiseId", "authorId"
                        )
                        VALUES (%s, %s, %s, %s, true, false, %s, %s)
                        RETURNING id
                        """,
                        (
                            spec["rating"],
                            spec["comment"],
                            spec["anonymous"],
                            created_at,
                            franchise_id,
                            user_id,
                        ),
                    )
                    rid = cur.fetchone()[0]
                    review_ids.append(rid)
                    print(
                        f"  + review id={rid} rating={spec['rating']} "
                        f"anon={spec['anonymous']}"
                    )

                # Response no primeiro review.
                response_user_id = _ensure_user(
                    cur,
                    {
                        "name": RESPONSE["author_name"],
                        "email": RESPONSE["author_email"],
                        "phone": RESPONSE["author_phone"],
                        "role": RESPONSE["author_role"],
                    },
                )
                response_at = _utcnow() - timedelta(days=RESPONSE["days_ago"])
                cur.execute(
                    """
                    INSERT INTO "ReviewResponse" (
                        content, "createdAt", "updatedAt", "reviewId", "authorId"
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        RESPONSE["content"],
                        response_at,
                        response_at,
                        review_ids[RESPONSE["review_index"]],
                        response_user_id,
                    ),
                )
                resp_id = cur.fetchone()[0]
                print(
                    f"  + response id={resp_id} on review "
                    f"{review_ids[RESPONSE['review_index']]}"
                )
            else:
                print("Skip de criacao (idempotente — reviews ja existem).")

            # 4. Refresh counters.
            cur.execute(
                """
                UPDATE "Franchise"
                SET "reviewCount" = (
                        SELECT COUNT(*) FROM "Review"
                        WHERE "franchiseId" = %s AND "isActive" = true
                    ),
                    "ratingSum" = COALESCE((
                        SELECT SUM(rating) FROM "Review"
                        WHERE "franchiseId" = %s AND "isActive" = true
                    ), 0),
                    "averageRating" = (
                        SELECT AVG(rating)::float FROM "Review"
                        WHERE "franchiseId" = %s AND "isActive" = true
                    ),
                    "updatedAt" = NOW()
                WHERE id = %s
                """,
                (franchise_id, franchise_id, franchise_id, franchise_id),
            )

            cur.execute(
                'SELECT "reviewCount", "averageRating", "ratingSum" '
                'FROM "Franchise" WHERE id = %s',
                (franchise_id,),
            )
            rc, ar, rs = cur.fetchone()
            print(
                f"Counters: reviewCount={rc} averageRating={ar} ratingSum={rs}"
            )

        conn.commit()
        print("Done.")


if __name__ == "__main__":
    main()
