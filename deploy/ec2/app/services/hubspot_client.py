"""
HubSpot CRM integration client.

Todas as funções são async e projetadas pra rodar como BackgroundTask do FastAPI.
Erros nunca propagam pro caller — são logados. Se HubSpot estiver fora, o
usuário não percebe nada: o cadastro no Mercado Franquia funciona normalmente,
e a sync com HubSpot só não acontece.

Escopo:
- Contact: upsert (investor e franchisor), update de role/status
- Company: create (pra franchisor), update de status
- Association: vincular Contact com Company

Autenticação: Bearer token via env var HUBSPOT_API_TOKEN.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

from app.constantes import (
    HUBSPOT_API_BASE_URL,
    HUBSPOT_API_VERSION_CRM,
    HUBSPOT_COMPANY_PROP_FRANCHISE_ID,
    HUBSPOT_COMPANY_PROP_SIGNUP_PATH,
    HUBSPOT_COMPANY_PROP_STATUS,
    HUBSPOT_CONTACT_PROP_ROLE,
    HUBSPOT_CONTACT_PROP_SIGNUP_PATH,
    HUBSPOT_CONTACT_PROP_STATUS,
    HUBSPOT_CONTACT_PROP_USER_ID,
    HUBSPOT_ENV_VAR_TOKEN,
    HUBSPOT_TIMEOUT_SECONDS,
    HubSpotRole,
    HubSpotSignupPath,
    HubSpotStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers internos
# =============================================================================


def _get_token() -> Optional[str]:
    token = os.environ.get(HUBSPOT_ENV_VAR_TOKEN)
    if not token:
        logger.warning(
            "HUBSPOT_API_TOKEN não está configurado — integração desabilitada"
        )
        return None
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def _post(
    url: str, payload: dict[str, Any], operation: str
) -> Optional[dict[str, Any]]:
    """POST request com tratamento de erro. Retorna response JSON ou None."""
    token = _get_token()
    if not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=HUBSPOT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=_headers(token), json=payload)
            if response.status_code in (200, 201):
                return response.json()
            logger.error(
                "HubSpot %s falhou: HTTP %s — %s",
                operation,
                response.status_code,
                response.text[:500],
            )
            return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("HubSpot %s exceção: %s", operation, exc)
        return None


async def _patch(
    url: str, payload: dict[str, Any], operation: str
) -> Optional[dict[str, Any]]:
    """PATCH request com tratamento de erro."""
    token = _get_token()
    if not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=HUBSPOT_TIMEOUT_SECONDS) as client:
            response = await client.patch(url, headers=_headers(token), json=payload)
            if response.status_code in (200, 201):
                return response.json()
            logger.error(
                "HubSpot %s falhou: HTTP %s — %s",
                operation,
                response.status_code,
                response.text[:500],
            )
            return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("HubSpot %s exceção: %s", operation, exc)
        return None


def _contacts_url() -> str:
    return f"{HUBSPOT_API_BASE_URL}/crm/objects/{HUBSPOT_API_VERSION_CRM}/contacts"


def _companies_url() -> str:
    return f"{HUBSPOT_API_BASE_URL}/crm/objects/{HUBSPOT_API_VERSION_CRM}/companies"


# =============================================================================
# Contact operations
# =============================================================================


async def create_investor_contact(
    *,
    email: str,
    name: str,
    phone: str,
    user_id: str,
) -> Optional[str]:
    """
    Cria contact no HubSpot quando user se cadastra como INVESTOR.
    Retorna o hubspotContactId ou None em caso de falha.
    """
    payload = {
        "properties": {
            "email": email,
            "firstname": name,
            "phone": phone,
            HUBSPOT_CONTACT_PROP_ROLE: HubSpotRole.INVESTOR,
            HUBSPOT_CONTACT_PROP_SIGNUP_PATH: HubSpotSignupPath.INVESTOR,
            HUBSPOT_CONTACT_PROP_STATUS: HubSpotStatus.ACTIVE,
            HUBSPOT_CONTACT_PROP_USER_ID: str(user_id),
        }
    }
    data = await _post(_contacts_url(), payload, "create_investor_contact")
    if not data:
        return None
    contact_id = data.get("id")
    logger.info("HubSpot contact criado (investor): %s", contact_id)
    return contact_id


async def update_contact_for_franchisor_request(
    *,
    hubspot_contact_id: str,
    mode: str,
) -> bool:
    """
    Atualiza contact existente quando user envia FranchisorRequest.
    Muda status pra PENDING e signup_path pra FRANCHISOR_NEW/EXISTING.
    Role continua INVESTOR — só vira FRANCHISOR após aprovação.
    """
    signup_path = (
        HubSpotSignupPath.FRANCHISOR_NEW
        if mode == "NEW"
        else HubSpotSignupPath.FRANCHISOR_EXISTING
    )
    payload = {
        "properties": {
            HUBSPOT_CONTACT_PROP_SIGNUP_PATH: signup_path,
            HUBSPOT_CONTACT_PROP_STATUS: HubSpotStatus.PENDING,
        }
    }
    url = f"{_contacts_url()}/{hubspot_contact_id}"
    data = await _patch(url, payload, "update_contact_franchisor_request")
    return data is not None


async def mark_contact_approved(hubspot_contact_id: str) -> bool:
    """Admin aprovou o FranchisorRequest: role vira FRANCHISOR, status APPROVED."""
    payload = {
        "properties": {
            HUBSPOT_CONTACT_PROP_ROLE: HubSpotRole.FRANCHISOR,
            HUBSPOT_CONTACT_PROP_STATUS: HubSpotStatus.APPROVED,
        }
    }
    url = f"{_contacts_url()}/{hubspot_contact_id}"
    data = await _patch(url, payload, "mark_contact_approved")
    return data is not None


async def mark_contact_rejected(hubspot_contact_id: str) -> bool:
    """Admin rejeitou o FranchisorRequest: status REJECTED, role fica INVESTOR."""
    payload = {
        "properties": {
            HUBSPOT_CONTACT_PROP_STATUS: HubSpotStatus.REJECTED,
        }
    }
    url = f"{_contacts_url()}/{hubspot_contact_id}"
    data = await _patch(url, payload, "mark_contact_rejected")
    return data is not None


# =============================================================================
# Company operations
# =============================================================================


async def get_company_by_franchise_id(
    franchise_id: str,
) -> Optional[str]:
    """
    Busca Company no HubSpot que tem mercado_franquia_franchise_id == franchise_id.
    Retorna hubspotCompanyId se encontrou, ou None.

    Usa a HubSpot CRM Search API. Falhas retornam None (fallback: cria Company nova).
    """
    token = _get_token()
    if not token:
        return None

    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/companies/search"
    payload = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": HUBSPOT_COMPANY_PROP_FRANCHISE_ID,
                        "operator": "EQ",
                        "value": str(franchise_id),
                    }
                ]
            }
        ],
        "properties": ["name"],
        "limit": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=HUBSPOT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=_headers(token), json=payload)
            if response.status_code != 200:
                logger.warning(
                    "HubSpot search company falhou: HTTP %s — %s",
                    response.status_code,
                    response.text[:300],
                )
                return None
            data = response.json()
            results = data.get("results", [])
            if not results:
                return None
            company_id = results[0].get("id")
            logger.info(
                "HubSpot company encontrada pra franchise_id=%s: %s",
                franchise_id,
                company_id,
            )
            return company_id
    except Exception as exc:  # noqa: BLE001
        logger.exception("HubSpot search company exceção: %s", exc)
        return None


async def create_franchisor_company(
    *,
    stream_name: str,
    mode: str,
    franchise_id: Optional[str] = None,
) -> Optional[str]:
    """
    Cria company no HubSpot quando user cadastra FranchisorRequest.

    Dedup: se franchise_id foi passado e já existe uma Company no HubSpot
    com esse mercado_franquia_franchise_id, reutiliza essa Company
    em vez de criar nova. 1 Franchise no banco = 1 Company no HubSpot.

    mode: 'NEW' ou 'EXISTING'.
    Retorna o hubspotCompanyId ou None em caso de falha total.
    """
    if franchise_id:
        existing_id = await get_company_by_franchise_id(franchise_id)
        if existing_id:
            logger.info(
                "Reutilizando HubSpot company %s pra franchise_id=%s (evitando duplicata)",
                existing_id,
                franchise_id,
            )
            return existing_id

    signup_path = (
        HubSpotSignupPath.FRANCHISOR_NEW
        if mode == "NEW"
        else HubSpotSignupPath.FRANCHISOR_EXISTING
    )
    properties: dict[str, Any] = {
        "name": stream_name,
        HUBSPOT_COMPANY_PROP_STATUS: HubSpotStatus.PENDING,
        HUBSPOT_COMPANY_PROP_SIGNUP_PATH: signup_path,
    }
    if franchise_id:
        properties[HUBSPOT_COMPANY_PROP_FRANCHISE_ID] = str(franchise_id)

    data = await _post(_companies_url(), {"properties": properties}, "create_company")
    if not data:
        return None
    company_id = data.get("id")
    logger.info("HubSpot company criada: %s (%s)", company_id, stream_name)
    return company_id


async def mark_company_approved(hubspot_company_id: str) -> bool:
    payload = {
        "properties": {HUBSPOT_COMPANY_PROP_STATUS: HubSpotStatus.APPROVED}
    }
    url = f"{_companies_url()}/{hubspot_company_id}"
    data = await _patch(url, payload, "mark_company_approved")
    return data is not None


async def mark_company_rejected(hubspot_company_id: str) -> bool:
    payload = {
        "properties": {HUBSPOT_COMPANY_PROP_STATUS: HubSpotStatus.REJECTED}
    }
    url = f"{_companies_url()}/{hubspot_company_id}"
    data = await _patch(url, payload, "mark_company_rejected")
    return data is not None


# =============================================================================
# Associations
# =============================================================================


async def associate_contact_with_company(
    *,
    hubspot_contact_id: str,
    hubspot_company_id: str,
) -> bool:
    """
    Vincula um Contact com uma Company no HubSpot.
    Usa a API v4 de associações.
    """
    url = (
        f"{HUBSPOT_API_BASE_URL}/crm/v4/objects/contacts/"
        f"{hubspot_contact_id}/associations/default/companies/{hubspot_company_id}"
    )
    token = _get_token()
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=HUBSPOT_TIMEOUT_SECONDS) as client:
            response = await client.put(url, headers=_headers(token))
            if response.status_code in (200, 201):
                logger.info(
                    "HubSpot association: contact %s <-> company %s",
                    hubspot_contact_id,
                    hubspot_company_id,
                )
                return True
            logger.error(
                "HubSpot association falhou: HTTP %s — %s",
                response.status_code,
                response.text[:500],
            )
            return False
    except Exception as exc:  # noqa: BLE001
        logger.exception("HubSpot association exceção: %s", exc)
        return False
