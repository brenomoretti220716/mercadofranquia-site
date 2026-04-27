#!/usr/bin/env python3
"""
Seed idempotente de pizza-do-joao — APENAS DEV.

Uso:
    DATABASE_URL=postgresql://mf_user:dev_password_local@localhost:5432/mercadofranquia \
        ~/Developer/mercadofranquia/.venv/bin/python \
        deploy/ec2/scripts/dev/seed_reviews_pizza_joao.py

O que faz (tudo idempotente):
    1. Procura a Franchise pizza-do-joao. Aborta se nao existir.
    2. Aprova (PENDING -> APPROVED) — necessario pro endpoint publico
       servir o payload (PENDING/REJECTED retorna 404 pra nao-admins).
    3. Atualiza campos da Franchise alinhados com o mockup v10:
       tagline, description, segment, franchiseStartYear, headquarter,
       headquarterState, totalUnits, min/maxInvestment, min/maxROI,
       processSteps (JSONB), differentials (JSONB),
       idealFranchiseeProfile, galleryUrls (TEXT JSON-encoded).
    4. Cria/atualiza 3 BusinessModels (Loja / Container / Quiosque)
       via lookup (franchiseId, name) — sem duplicar.
    5. Conta reviews ativos. Se 0, cria 4 reviews + 1 ReviewResponse
       espelhando o mockup. Se >0, skip (idempotente).
    6. Refresh dos counters denormalizados (reviewCount, averageRating,
       ratingSum).

Unidades do DB:
    - Franchise.minimumInvestment / maximumInvestment: Numeric(15,2)
      em REAIS (nao centavos). Frontend formatBRL espera valor em
      reais — formatBRL(139000) -> "R$ 139k".
    - minimumReturnOnInvestment / maximumReturnOnInvestment: int em
      meses.

Limitacoes de schema:
    - BusinessModel so tem id/name/description/photoUrl/franchiseId no
      model. Os campos por modelo do mockup v10 (investimento, payback,
      area, category) nao tem coluna ainda. Por enquanto a description
      carrega esses dados em texto livre.
    - O ModelosLanding na Fase 3.3 usa os valores agregados da
      Franchise (min/max) repetidos em cada card ate o backend ter
      colunas per-model.

NUNCA rode em prod — hashes de senha sao invalidos por design.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    import psycopg
except ImportError:
    sys.exit("Missing dependency: pip install 'psycopg[binary]>=3.1'")


SLUG = "pizza-do-joao"


# ---------------------------------------------------------------------------
# Franchise — campos canonicos pra alinhar com o mockup v10
# ---------------------------------------------------------------------------

FRANCHISE_FIELDS = {
    "tagline": (
        "Rede de pizzarias artesanais com foco em bairros nobres. Modelo "
        "enxuto, operação 5 funcionários, ticket médio alto."
    ),
    "description": (
        "Gelato artesanal premium, feito sem gordura hidrogenada, com sabores "
        "autorais e versões veganas e sem açúcar. Modelo testado e validado, "
        "com 6 unidades próprias e 56 franqueadas em atividade."
    ),
    "segment": "Alimentação",
    "headquarter": "São Paulo",
    "headquarterState": "SP",
    "idealFranchiseeProfile": (
        "Empreendedor com perfil de gestão e dedicação ao negócio. Não é "
        "necessário experiência prévia em alimentação. Capital disponível a "
        "partir de R$ 139 mil. Disponibilidade para acompanhar a operação "
        "nos primeiros 6 meses."
    ),
    "franchiseStartYear": 2014,
    "totalUnits": 62,
    "minimumReturnOnInvestment": 22,  # meses
    "maximumReturnOnInvestment": 22,
    # Numeric(15,2) em REAIS — formatBRL no frontend faz n / 1000.
    "minimumInvestment": 139000,
    "maximumInvestment": 342000,
}


PROCESS_STEPS = [
    {
        "title": "Pré-qualificação",
        "description": (
            "Análise do seu perfil de investidor e do capital disponível. "
            "Resposta em até 5 dias úteis."
        ),
    },
    {
        "title": "Análise da COF",
        "description": (
            "Recebimento e análise da Circular de Oferta de Franquia. "
            "Período mínimo legal de 10 dias antes da assinatura."
        ),
    },
    {
        "title": "Contrato e ponto comercial",
        "description": (
            "Assinatura do contrato e auxílio na escolha do ponto. "
            "Inauguração estimada em 120 dias."
        ),
    },
]


DIFFERENTIALS = [
    "Produto premium difícil de substituir, ticket médio R$ 94 por pessoa",
    "Cardápio inclusivo (vegano, sem lactose, sem açúcar) atende público-alvo crescente",
    "Sabores sazonais que fidelizam e aumentam frequência de visita",
    "Marketing pronto e operação validada em 62 unidades",
]


GALLERY_URLS = [
    "https://placehold.co/600x600/E3DED1/6B6B75?text=Foto+1",
    "https://placehold.co/600x600/E3DED1/6B6B75?text=Foto+2",
    "https://placehold.co/600x600/E3DED1/6B6B75?text=Foto+3",
    "https://placehold.co/600x600/E3DED1/6B6B75?text=Foto+4",
]


# ---------------------------------------------------------------------------
# BusinessModels — pizza-do-joao tem 3 formatos
# ---------------------------------------------------------------------------

BUSINESS_MODELS = [
    {
        "name": "Loja",
        "description": (
            "Loja completa com 80m². Investimento R$ 342k, payback estimado "
            "de 22 meses. Modelo flagship em vias de alto fluxo."
        ),
        "photoUrl": "https://placehold.co/600x400/0B0B0D/E3DED1?text=Loja",
    },
    {
        "name": "Container",
        "description": (
            "Container modular com 35m². Investimento R$ 205k, payback "
            "estimado de 22 meses. Setup rápido e portátil."
        ),
        "photoUrl": "https://placehold.co/600x400/0B0B0D/E3DED1?text=Container",
    },
    {
        "name": "Quiosque",
        "description": (
            "Quiosque compacto com 12m². Investimento R$ 139k, payback "
            "estimado de 22 meses. Ideal pra shoppings."
        ),
        "photoUrl": "https://placehold.co/600x400/0B0B0D/E3DED1?text=Quiosque",
    },
]


# ---------------------------------------------------------------------------
# Reviews + Response — alinhados com o mockup v10
# ---------------------------------------------------------------------------

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
            "O suporte da rede pra escolher ponto comercial fez muita "
            "diferenca - me pouparam de erros caros que eu provavelmente "
            "cometeria sozinho."
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
            "Negocio solido e marca bem posicionada. Capital de giro "
            "recomendado parece subestimado pra cidades menores. Tive que "
            "ajustar nos primeiros 4 meses."
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
            "Pesquisei muito antes de escolher franqueador. Pizza do Joao "
            "respondeu todas as duvidas em ate 24h, mandou COF detalhada e "
            "indicou outros franqueados pra eu conversar."
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
            "A operacao funciona bem mas o tempo de resposta do suporte "
            "caiu nos ultimos meses. Espero que melhore — o resto da rede "
            "compensa."
        ),
    },
]


RESPONSE = {
    "review_index": 0,  # responde o review rating 5 mais recente
    "author_email": "marca.seed@example.com",
    "author_name": "Pizza do Joao - Atendimento",
    "author_phone": "+55 11 90000-9999",
    "author_role": "FRANCHISOR",
    "days_ago": 11,
    "content": (
        "Itamar, valeu demais pelo depoimento. Voce eh referencia no nosso "
        "programa de mentoria. Continue assim!"
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _update_franchise_fields(cur, franchise_id: str) -> None:
    """UPDATE canonico — sobrescreve com os valores do FRANCHISE_FIELDS."""
    params = dict(FRANCHISE_FIELDS)
    params["id"] = franchise_id
    params["processSteps"] = json.dumps(PROCESS_STEPS)
    params["differentials"] = json.dumps(DIFFERENTIALS)
    params["galleryUrls"] = json.dumps(GALLERY_URLS)
    cur.execute(
        """
        UPDATE "Franchise"
        SET tagline = %(tagline)s,
            description = %(description)s,
            segment = %(segment)s,
            headquarter = %(headquarter)s,
            "headquarterState" = %(headquarterState)s,
            "idealFranchiseeProfile" = %(idealFranchiseeProfile)s,
            "franchiseStartYear" = %(franchiseStartYear)s,
            "totalUnits" = %(totalUnits)s,
            "minimumReturnOnInvestment" = %(minimumReturnOnInvestment)s,
            "maximumReturnOnInvestment" = %(maximumReturnOnInvestment)s,
            "minimumInvestment" = %(minimumInvestment)s,
            "maximumInvestment" = %(maximumInvestment)s,
            "processSteps" = %(processSteps)s::jsonb,
            differentials = %(differentials)s::jsonb,
            "galleryUrls" = %(galleryUrls)s,
            "updatedAt" = NOW()
        WHERE id = %(id)s
        """,
        params,
    )


def _ensure_business_models(cur, franchise_id: str) -> None:
    """Idempotente — lookup por (franchiseId, name); insere ou atualiza."""
    for bm in BUSINESS_MODELS:
        cur.execute(
            'SELECT id FROM "BusinessModel" WHERE "franchiseId" = %s AND name = %s',
            (franchise_id, bm["name"]),
        )
        row = cur.fetchone()
        if row is None:
            bm_id = _deterministic_id(f"{franchise_id}-bm-{bm['name']}")
            cur.execute(
                """
                INSERT INTO "BusinessModel" (
                    id, name, description, "photoUrl", "franchiseId",
                    "createdAt", "updatedAt"
                )
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (
                    bm_id,
                    bm["name"],
                    bm["description"],
                    bm["photoUrl"],
                    franchise_id,
                ),
            )
            print(f"  + business model '{bm['name']}' id={bm_id}")
        else:
            cur.execute(
                """
                UPDATE "BusinessModel"
                SET description = %s, "photoUrl" = %s, "updatedAt" = NOW()
                WHERE id = %s
                """,
                (bm["description"], bm["photoUrl"], row[0]),
            )
            print(f"  ~ business model '{bm['name']}' updated id={row[0]}")


def _create_reviews_with_response(cur, franchise_id: str) -> None:
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
            f"  + review id={rid} rating={spec['rating']} anon={spec['anonymous']}"
        )

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
        f"  + response id={resp_id} on review {review_ids[RESPONSE['review_index']]}"
    )


def _refresh_counters(cur, franchise_id: str) -> None:
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
    print(f"Counters: reviewCount={rc} averageRating={ar} ratingSum={rs}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL environment variable is required.")
    if db_url.startswith("postgresql+psycopg://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg://") :]

    with psycopg.connect(db_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            # 1. Lookup franchise.
            cur.execute(
                'SELECT id, status FROM "Franchise" WHERE slug = %s', (SLUG,)
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

            # 3. Atualiza campos canonicos da Franchise.
            print("Atualizando campos da Franchise...")
            _update_franchise_fields(cur, franchise_id)
            print("  + Franchise fields aplicados")

            # 4. Cria/atualiza BusinessModels.
            print("Atualizando BusinessModels...")
            _ensure_business_models(cur, franchise_id)

            # 5. Reviews + response (so se 0).
            cur.execute(
                'SELECT COUNT(*) FROM "Review" WHERE "franchiseId" = %s AND "isActive" = true',
                (franchise_id,),
            )
            review_count = cur.fetchone()[0]
            print(f"Reviews ativos existentes: {review_count}")

            if review_count == 0:
                _create_reviews_with_response(cur, franchise_id)
            else:
                print("Skip de criacao de reviews (idempotente).")

            # 6. Refresh counters.
            _refresh_counters(cur, franchise_id)

        conn.commit()
        print("Done.")


if __name__ == "__main__":
    main()
