"""
Constantes centralizadas do backend Mercado Franquia.

Qualquer valor "mágico" (URL, enum, timeout) deve morar aqui,
não hardcoded nos routers ou services.
"""

# =============================================================================
# HubSpot integration
# =============================================================================

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"
HUBSPOT_API_VERSION_CRM = "2026-03"  # versão date-based nova
HUBSPOT_API_VERSION_LEGACY = "v3"    # pra endpoints ainda não migrados
HUBSPOT_TIMEOUT_SECONDS = 10
HUBSPOT_ENV_VAR_TOKEN = "HUBSPOT_API_TOKEN"

# Nomes internos das propriedades custom no objeto Contact
HUBSPOT_CONTACT_PROP_ROLE = "mercado_franquia_role"
HUBSPOT_CONTACT_PROP_SIGNUP_PATH = "mercado_franquia_signup_path"
HUBSPOT_CONTACT_PROP_STATUS = "mercado_franquia_status"
HUBSPOT_CONTACT_PROP_USER_ID = "mercado_franquia_user_id"

# Nomes internos das propriedades custom no objeto Company
HUBSPOT_COMPANY_PROP_STATUS = "mercado_franquia_status"
HUBSPOT_COMPANY_PROP_SIGNUP_PATH = "mercado_franquia_signup_path"
HUBSPOT_COMPANY_PROP_FRANCHISE_ID = "mercado_franquia_franchise_id"
HUBSPOT_COMPANY_PROP_SEGMENT = "mercado_franquia_segment"
HUBSPOT_COMPANY_PROP_UF = "mercado_franquia_uf"


class HubSpotRole:
    """Valores válidos pro dropdown mercado_franquia_role no HubSpot Contact."""
    INVESTOR = "INVESTOR"
    FRANCHISOR = "FRANCHISOR"
    ADMIN = "ADMIN"


class HubSpotSignupPath:
    """Valores válidos pro dropdown mercado_franquia_signup_path."""
    INVESTOR = "INVESTOR"
    FRANCHISOR_NEW = "FRANCHISOR_NEW"
    FRANCHISOR_EXISTING = "FRANCHISOR_EXISTING"


class HubSpotStatus:
    """Valores válidos pro dropdown mercado_franquia_status (contact e company)."""
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"


# =============================================================================
# Application roles (User.role no banco)
# =============================================================================

class UserRole:
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"
    FRANCHISOR = "FRANCHISOR"
    # legacy: FRANCHISEE, CANDIDATE, ENTHUSIAST (manter por retrocompatibilidade,
    # mas não usar em código novo)


# =============================================================================
# FranchisorRequest status/mode
# =============================================================================

class FranchisorRequestStatus:
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class FranchisorRequestMode:
    NEW = "NEW"
    EXISTING = "EXISTING"


# =============================================================================
# Franchise status
# =============================================================================

class FranchiseStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
