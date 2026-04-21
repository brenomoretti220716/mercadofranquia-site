"""
AWS SES mailer for transactional emails.

Credentials are resolved by boto3 from the standard AWS environment
(AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION); the sender
address is read from SES_FROM_EMAIL.
"""
from __future__ import annotations

import html
import logging
import os
from typing import Optional
from urllib.parse import quote as urlquote

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

logger = logging.getLogger(__name__)

# Brand
BRAND_URL = "https://mercadofranquia.com.br"
BRAND_COLOR = "#E25E3E"
TEXT_COLOR = "#111111"
TEXT_SECONDARY = "#555555"
FROM_NAME = "Mercado Franquia"
LOGO_URL = f"{BRAND_URL}/assets/MercadoFranquia.png"

# Subjects
SUBJECT = "Código de recuperação de senha — Mercado Franquia"
SUBJECT_WELCOME = "Bem-vindo ao Mercado Franquia"
SUBJECT_EMAIL_VERIFICATION = "Confirme seu email no Mercado Franquia"
SUBJECT_REQUEST_RECEIVED = "Recebemos sua solicitação de franqueador"
SUBJECT_DOCUMENTS_REQUEST = "Precisamos de alguns documentos — Mercado Franquia"
SUBJECT_APPROVED = "Seu cadastro de franqueador foi aprovado"
SUBJECT_REJECTED = "Atualização sobre seu cadastro de franqueador"

# URLs used in templates
URL_MERCADO = f"{BRAND_URL}/mercado"
URL_FRANCHISOR_PANEL = f"{BRAND_URL}/franqueador"
URL_ADMIN_REQUESTS = f"{BRAND_URL}/admin/franqueadores"
URL_DOC_VALIDATION_BASE = f"{BRAND_URL}/franqueador/validacao"
URL_ADMIN_FRANCHISES = f"{BRAND_URL}/admin/franchises"
URL_FRANCHISOR_MY_FRANCHISES = f"{URL_FRANCHISOR_PANEL}/minhas-franquias"


def _render_html(*, user_name: str, code: str, expires_at_minutes: int) -> str:
    # Inline styles only — most email clients strip <style> and external CSS.
    safe_user_name = html.escape(user_name, quote=True)
    safe_code = html.escape(code, quote=True)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:Arial,Helvetica,sans-serif;color:#111111;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;padding:32px 24px;">
    <tr><td>
      <p style="font-size:16px;line-height:1.5;color:#111111;margin:0 0 16px 0;">Olá, {safe_user_name},</p>
      <p style="font-size:16px;line-height:1.5;color:#111111;margin:0 0 24px 0;">
        Recebemos um pedido para redefinir a senha da sua conta.
        Use o código abaixo para concluir a recuperação:
      </p>
      <div style="font-size:32px;letter-spacing:4px;font-weight:bold;color:#E25E3E;text-align:center;padding:20px 0;background:#f7f7f7;border-radius:6px;margin:0 0 24px 0;">
        {safe_code}
      </div>
      <p style="font-size:14px;line-height:1.5;color:#111111;margin:0 0 16px 0;">
        Este código expira em {expires_at_minutes} minutos.
      </p>
      <p style="font-size:14px;line-height:1.5;color:#111111;margin:0 0 24px 0;">
        Se você não solicitou esta redefinição, ignore este email.
        Sua senha permanece inalterada.
      </p>
      <p style="font-size:14px;line-height:1.5;color:#111111;margin:0 0 24px 0;">Equipe Mercado Franquia</p>
      <hr style="border:none;border-top:1px solid #eeeeee;margin:24px 0;">
      <p style="font-size:12px;line-height:1.5;color:#888888;margin:0;">
        <a href="{BRAND_URL}" style="color:#888888;text-decoration:underline;">{BRAND_URL}</a>
      </p>
    </td></tr>
  </table>
</body>
</html>"""


def _render_text(*, user_name: str, code: str, expires_at_minutes: int) -> str:
    return (
        f"Olá, {user_name},\n\n"
        f"Recebemos um pedido para redefinir a senha da sua conta.\n"
        f"Use o código abaixo para concluir a recuperação:\n\n"
        f"    {code}\n\n"
        f"Este código expira em {expires_at_minutes} minutos.\n\n"
        f"Se você não solicitou esta redefinição, ignore este email. "
        f"Sua senha permanece inalterada.\n\n"
        f"Equipe Mercado Franquia\n"
        f"{BRAND_URL}\n"
    )


def _render_html_with_button(
    *,
    user_name: str,
    intro: str,
    body_paragraphs: Optional[list[str]] = None,
    button_text: Optional[str] = None,
    button_url: Optional[str] = None,
    code: Optional[str] = None,
    code_expires_minutes: Optional[int] = None,
) -> str:
    """
    Standard HTML layout for transactional emails.

    `user_name`, `button_text`, `button_url` and `code` are escaped internally.
    `intro` and entries in `body_paragraphs` are treated as HTML-ready strings —
    callers MUST pre-escape any user-supplied data before passing them here, so
    they can still include safe markup (e.g. <strong>).
    """
    safe_user_name = html.escape(user_name, quote=True)

    code_block = ""
    if code is not None:
        safe_code = html.escape(code, quote=True)
        code_block = (
            f'<div style="font-size:32px;letter-spacing:4px;font-weight:bold;'
            f'color:{BRAND_COLOR};text-align:center;padding:20px 0;'
            f'background:#f7f7f7;border-radius:6px;margin:0 0 24px 0;">'
            f"{safe_code}"
            f"</div>"
        )
        if code_expires_minutes is not None:
            code_block += (
                f'<p style="font-size:14px;line-height:1.5;color:{TEXT_COLOR};margin:0 0 24px 0;">'
                f"Este código expira em {int(code_expires_minutes)} minutos."
                f"</p>"
            )

    body_html = ""
    if body_paragraphs:
        for paragraph in body_paragraphs:
            body_html += (
                f'<p style="font-size:16px;line-height:1.5;color:{TEXT_COLOR};margin:0 0 16px 0;">'
                f"{paragraph}"
                f"</p>"
            )

    button_block = ""
    if button_text and button_url:
        safe_button_text = html.escape(button_text, quote=True)
        safe_button_url = html.escape(button_url, quote=True)
        button_block = (
            f'<div style="text-align:center;margin:24px 0;">'
            f'<a href="{safe_button_url}" '
            f'style="display:inline-block;background:{BRAND_COLOR};color:#ffffff;'
            f'padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">'
            f"{safe_button_text}"
            f"</a>"
            f"</div>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:Arial,Helvetica,sans-serif;color:{TEXT_COLOR};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">
    <tr>
      <td style="background:#111111;padding:20px 24px;text-align:center;">
        <img src="{LOGO_URL}" alt="Mercado Franquia" style="height:32px;vertical-align:middle;border:0;display:inline-block;">
      </td>
    </tr>
    <tr>
      <td style="padding:32px 24px;">
        <p style="font-size:16px;line-height:1.5;color:{TEXT_COLOR};margin:0 0 16px 0;">Olá, {safe_user_name},</p>
        <p style="font-size:16px;line-height:1.5;color:{TEXT_COLOR};margin:0 0 24px 0;">{intro}</p>
        {code_block}
        {body_html}
        {button_block}
        <p style="font-size:14px;line-height:1.5;color:{TEXT_COLOR};margin:0 0 24px 0;">Equipe Mercado Franquia</p>
        <hr style="border:none;border-top:1px solid #eeeeee;margin:24px 0;">
        <p style="font-size:12px;line-height:1.5;color:#888888;margin:0;">
          <a href="{BRAND_URL}" style="color:#888888;text-decoration:underline;">{BRAND_URL}</a>
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _render_text_with_button(
    *,
    user_name: str,
    intro: str,
    body_paragraphs: Optional[list[str]] = None,
    button_text: Optional[str] = None,
    button_url: Optional[str] = None,
    code: Optional[str] = None,
    code_expires_minutes: Optional[int] = None,
) -> str:
    """
    Plain-text counterpart. `body_paragraphs` should be plain text (no HTML).
    """
    lines: list[str] = [f"Olá, {user_name},", "", intro, ""]

    if code is not None:
        lines.append(f"    {code}")
        lines.append("")
        if code_expires_minutes is not None:
            lines.append(f"Este código expira em {int(code_expires_minutes)} minutos.")
            lines.append("")

    if body_paragraphs:
        for paragraph in body_paragraphs:
            lines.append(paragraph)
            lines.append("")

    if button_text and button_url:
        lines.append(f"{button_text}: {button_url}")
        lines.append("")

    lines.append("Equipe Mercado Franquia")
    lines.append(BRAND_URL)
    lines.append("")

    return "\n".join(lines)


def _send_email(
    *,
    to_addresses: list[str],
    subject: str,
    html_body: str,
    text_body: str,
) -> str:
    """
    Low-level SES dispatch. Returns the SES MessageId.

    Raises:
        RuntimeError: if SES_FROM_EMAIL is not configured.
        ValueError: if `to_addresses` is empty.
        ClientError / EndpointConnectionError: propagated from boto3.
    """
    from_email = os.environ.get("SES_FROM_EMAIL")
    if not from_email:
        raise RuntimeError(
            "SES_FROM_EMAIL environment variable is not set — cannot send email."
        )
    if not to_addresses:
        raise ValueError("to_addresses is empty")

    source = f"{FROM_NAME} <{from_email}>"
    recipients = list(to_addresses)
    client = boto3.client("ses")

    try:
        response = client.send_email(
            Source=source,
            Destination={"ToAddresses": recipients},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
    except ClientError as err:
        logger.error(
            "SES ClientError sending subject=%r to=%s: %s",
            subject,
            ",".join(recipients),
            err.response.get("Error", {}).get("Message", str(err)),
        )
        raise
    except EndpointConnectionError as err:
        logger.error(
            "SES EndpointConnectionError sending subject=%r to=%s: %s",
            subject,
            ",".join(recipients),
            err,
        )
        raise

    message_id = response.get("MessageId", "")
    logger.info(
        "SES send OK subject=%r to=%s message_id=%s",
        subject,
        ",".join(recipients),
        message_id,
    )
    return message_id


def send_password_reset_email(
    *,
    to: str,
    code: str,
    expires_at_minutes: int,
    user_name: str,
) -> str:
    """
    Send the password-reset code via AWS SES and return the SES MessageId.

    Raises:
        RuntimeError: if SES_FROM_EMAIL is not configured.
        ClientError / EndpointConnectionError: propagated from boto3 so the
            caller can decide the retry/alerting policy.
    """
    from_email = os.environ.get("SES_FROM_EMAIL")
    if not from_email:
        raise RuntimeError(
            "SES_FROM_EMAIL environment variable is not set — "
            "cannot send password reset email."
        )

    client = boto3.client("ses")

    html_body = _render_html(
        user_name=user_name, code=code, expires_at_minutes=expires_at_minutes
    )
    text_body = _render_text(
        user_name=user_name, code=code, expires_at_minutes=expires_at_minutes
    )

    try:
        response = client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": SUBJECT, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
    except ClientError as err:
        logger.error(
            "SES ClientError sending password reset to %s: %s",
            to,
            err.response.get("Error", {}).get("Message", str(err)),
        )
        raise
    except EndpointConnectionError as err:
        logger.error(
            "SES EndpointConnectionError sending password reset to %s: %s", to, err
        )
        raise

    message_id: str = response.get("MessageId", "")
    return message_id


# ---------------------------------------------------------------------------
# Registration / onboarding emails
# ---------------------------------------------------------------------------


def send_welcome_email(*, to: str, user_name: str) -> str:
    """Post-registration welcome. Returns SES MessageId."""
    intro = (
        "Seu cadastro foi concluído com sucesso! "
        "Agora você pode explorar as melhores oportunidades de franquia do mercado."
    )
    body_html = [
        (
            "Navegue por franquias de diversos segmentos, acompanhe rankings, "
            "favorite suas opções preferidas e compare modelos de negócio."
        ),
        (
            "Se quiser, você também pode confirmar seu email para reforçar a "
            "segurança da sua conta — vamos te enviar um código em breve."
        ),
    ]
    body_text = [
        (
            "Navegue por franquias de diversos segmentos, acompanhe rankings, "
            "favorite suas opções preferidas e compare modelos de negócio."
        ),
        (
            "Se quiser, você também pode confirmar seu email para reforçar a "
            "segurança da sua conta — vamos te enviar um código em breve."
        ),
    ]

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro,
        body_paragraphs=body_html,
        button_text="Explorar franquias",
        button_url=URL_MERCADO,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro,
        body_paragraphs=body_text,
        button_text="Explorar franquias",
        button_url=URL_MERCADO,
    )

    return _send_email(
        to_addresses=[to],
        subject=SUBJECT_WELCOME,
        html_body=html_body,
        text_body=text_body,
    )


def send_email_verification(
    *,
    to: str,
    code: str,
    expires_at_minutes: int,
    user_name: str,
) -> str:
    """Opt-in email verification with 6-digit code. Returns SES MessageId."""
    intro = "Use o código abaixo para confirmar seu email."
    body_paragraphs = [
        (
            "Confirmar seu email ajuda a manter sua conta segura e permite "
            "recuperar seu acesso caso você esqueça a senha."
        ),
        "Se você não solicitou esta verificação, ignore este email.",
    ]

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro,
        body_paragraphs=body_paragraphs,
        code=code,
        code_expires_minutes=expires_at_minutes,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro,
        body_paragraphs=body_paragraphs,
        code=code,
        code_expires_minutes=expires_at_minutes,
    )

    return _send_email(
        to_addresses=[to],
        subject=SUBJECT_EMAIL_VERIFICATION,
        html_body=html_body,
        text_body=text_body,
    )


# ---------------------------------------------------------------------------
# Franchisor request lifecycle
# ---------------------------------------------------------------------------

_MODE_NEW = "NEW"
_MODE_EXISTING = "EXISTING"
_MODE_LABEL_PT = {
    _MODE_NEW: "Nova franquia",
    _MODE_EXISTING: "Franquia existente",
}


def _validate_mode(mode: str) -> None:
    if mode not in (_MODE_NEW, _MODE_EXISTING):
        raise ValueError(
            f"mode must be {_MODE_NEW!r} or {_MODE_EXISTING!r}, got {mode!r}"
        )


def send_franchisor_request_received(
    *,
    to: str,
    user_name: str,
    stream_name: str,
    mode: str,
) -> str:
    """Acknowledges the franchisor request to the applicant. Returns SES MessageId."""
    _validate_mode(mode)
    safe_stream = html.escape(stream_name, quote=True)

    if mode == _MODE_NEW:
        intro_html = (
            f"Recebemos seu pedido para cadastrar a franquia "
            f"<strong>{safe_stream}</strong>."
        )
        intro_text = (
            f"Recebemos seu pedido para cadastrar a franquia {stream_name}."
        )
    else:
        intro_html = (
            f"Recebemos seu pedido para se vincular à franquia "
            f"<strong>{safe_stream}</strong>."
        )
        intro_text = (
            f"Recebemos seu pedido para se vincular à franquia {stream_name}."
        )

    body_paragraphs = [
        (
            "Nossa equipe vai analisar seu pedido e entrar em contato em até "
            "48h úteis solicitando os documentos necessários para validação."
        ),
        "Enquanto isso, você pode continuar navegando normalmente pelo site.",
    ]

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro_html,
        body_paragraphs=body_paragraphs,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro_text,
        body_paragraphs=body_paragraphs,
    )

    return _send_email(
        to_addresses=[to],
        subject=SUBJECT_REQUEST_RECEIVED,
        html_body=html_body,
        text_body=text_body,
    )


def send_admin_new_franchisor_request(
    *,
    to_admins_list: list[str],
    user_name: str,
    user_email: str,
    stream_name: str,
    mode: str,
    request_id: str,
) -> str:
    """
    Notify the admin team of a new franchisor request. Single SES call with
    multiple recipients (not a loop). Returns SES MessageId.
    """
    _validate_mode(mode)
    if not to_admins_list:
        raise ValueError("to_admins_list is empty")

    safe_applicant_name = html.escape(user_name, quote=True)
    safe_applicant_email = html.escape(user_email, quote=True)
    safe_stream = html.escape(stream_name, quote=True)
    mode_label = _MODE_LABEL_PT[mode]
    safe_mode_label = html.escape(mode_label, quote=True)

    # request_id may contain cuid/uuid-safe chars but url-encode to be defensive.
    encoded_id = urlquote(str(request_id), safe="")
    panel_url = f"{URL_ADMIN_REQUESTS}?highlight={encoded_id}"

    # Strip CR/LF from stream_name before using in Subject (header-injection safety).
    subject_stream = stream_name.replace("\r", " ").replace("\n", " ")
    subject = f"Novo pedido de franqueador — {subject_stream}"

    intro_html = "Um novo pedido de cadastro de franqueador foi recebido."
    body_html = [
        f"Solicitante: <strong>{safe_applicant_name}</strong> ({safe_applicant_email})",
        f"Marca: <strong>{safe_stream}</strong>",
        f"Tipo: {safe_mode_label}",
    ]

    intro_text = intro_html
    body_text = [
        f"Solicitante: {user_name} ({user_email})",
        f"Marca: {stream_name}",
        f"Tipo: {mode_label}",
    ]

    html_body = _render_html_with_button(
        user_name="equipe",
        intro=intro_html,
        body_paragraphs=body_html,
        button_text="Ver no painel admin",
        button_url=panel_url,
    )
    text_body = _render_text_with_button(
        user_name="equipe",
        intro=intro_text,
        body_paragraphs=body_text,
        button_text="Ver no painel admin",
        button_url=panel_url,
    )

    return _send_email(
        to_addresses=list(to_admins_list),
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def send_documents_request(
    *,
    to: str,
    user_name: str,
    stream_name: str,
    validation_token: str,
) -> str:
    """
    Tell the applicant the admin started the review and needs documents.
    Returns SES MessageId.
    """
    safe_stream = html.escape(stream_name, quote=True)
    encoded_token = urlquote(str(validation_token), safe="")
    link = f"{URL_DOC_VALIDATION_BASE}/{encoded_token}"

    intro_html = (
        f"Nossa equipe iniciou a análise do seu pedido para a franquia "
        f"<strong>{safe_stream}</strong> e precisa de alguns documentos para "
        f"concluir a validação."
    )
    intro_text = (
        f"Nossa equipe iniciou a análise do seu pedido para a franquia "
        f"{stream_name} e precisa de alguns documentos para concluir a validação."
    )

    body_paragraphs_html = [
        "Precisamos dos seguintes documentos da empresa:",
        "• Cartão CNPJ atualizado",
        "• Contrato social vigente",
        "• Comprovante de endereço da sede",
        (
            "Use o botão abaixo para enviar os arquivos com segurança. "
            "Este link é pessoal e intransferível — não compartilhe."
        ),
    ]
    body_paragraphs_text = body_paragraphs_html  # no HTML markup in the strings

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro_html,
        body_paragraphs=body_paragraphs_html,
        button_text="Enviar documentos agora",
        button_url=link,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro_text,
        body_paragraphs=body_paragraphs_text,
        button_text="Enviar documentos agora",
        button_url=link,
    )

    return _send_email(
        to_addresses=[to],
        subject=SUBJECT_DOCUMENTS_REQUEST,
        html_body=html_body,
        text_body=text_body,
    )


def send_franchisor_approved(
    *,
    to: str,
    user_name: str,
    stream_name: str,
) -> str:
    """Notify the applicant their franchisor registration was approved."""
    safe_stream = html.escape(stream_name, quote=True)

    intro_html = (
        f"Boas notícias! Seu cadastro como franqueador da marca "
        f"<strong>{safe_stream}</strong> foi aprovado."
    )
    intro_text = (
        f"Boas notícias! Seu cadastro como franqueador da marca "
        f"{stream_name} foi aprovado."
    )

    body_paragraphs = [
        "Agora você já pode acessar o painel do franqueador e:",
        "• Completar e atualizar os dados da página da sua franquia",
        "• Responder avaliações dos seus franqueados e clientes",
        "• Visualizar leads e candidatos interessados na sua marca",
        "• Acompanhar estatísticas de visualização e interesse",
    ]

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro_html,
        body_paragraphs=body_paragraphs,
        button_text="Acessar painel do franqueador",
        button_url=URL_FRANCHISOR_PANEL,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro_text,
        body_paragraphs=body_paragraphs,
        button_text="Acessar painel do franqueador",
        button_url=URL_FRANCHISOR_PANEL,
    )

    return _send_email(
        to_addresses=[to],
        subject=SUBJECT_APPROVED,
        html_body=html_body,
        text_body=text_body,
    )


def send_franchisor_rejected(
    *,
    to: str,
    user_name: str,
    stream_name: str,
    rejection_reason: str,
) -> str:
    """
    Notify the applicant that their request was not approved. No CTA button —
    intentionally neutral tone.
    """
    safe_stream = html.escape(stream_name, quote=True)
    safe_reason = html.escape(rejection_reason, quote=True)

    intro_html = (
        f"Analisamos com atenção seu pedido de cadastro como franqueador da "
        f"marca <strong>{safe_stream}</strong> e, neste momento, não poderemos "
        f"aprová-lo."
    )
    intro_text = (
        f"Analisamos com atenção seu pedido de cadastro como franqueador da "
        f"marca {stream_name} e, neste momento, não poderemos aprová-lo."
    )

    body_html = [
        f"Motivo da não aprovação: {safe_reason}",
        (
            "Sua conta permanece ativa na plataforma como INVESTIDOR. "
            "Você continua podendo explorar franquias, favoritar opções e "
            "acompanhar rankings normalmente."
        ),
        (
            "Se tiver dúvidas ou acreditar que podemos reavaliar o pedido "
            "após ajustes, entre em contato com nossa equipe pelo email "
            "contato@mercadofranquia.com.br."
        ),
    ]
    body_text = [
        f"Motivo da não aprovação: {rejection_reason}",
        (
            "Sua conta permanece ativa na plataforma como INVESTIDOR. "
            "Você continua podendo explorar franquias, favoritar opções e "
            "acompanhar rankings normalmente."
        ),
        (
            "Se tiver dúvidas ou acreditar que podemos reavaliar o pedido "
            "após ajustes, entre em contato com nossa equipe pelo email "
            "contato@mercadofranquia.com.br."
        ),
    ]

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro_html,
        body_paragraphs=body_html,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro_text,
        body_paragraphs=body_text,
    )

    return _send_email(
        to_addresses=[to],
        subject=SUBJECT_REJECTED,
        html_body=html_body,
        text_body=text_body,
    )


def send_additional_franchise_received(
    *,
    to: str,
    franchisor_name: str,
    franchisor_email: str,
    stream_name: str,
    franchise_id: str,
) -> str:
    """
    Notifica admins que um franqueador aprovado acabou de criar uma marca adicional
    (Franchise com status=PENDING) pra aprovação.
    """
    safe_name = html.escape(franchisor_name, quote=True)
    safe_email = html.escape(franchisor_email, quote=True)
    safe_stream = html.escape(stream_name, quote=True)

    subject_stream = stream_name.replace("\r", " ").replace("\n", " ")
    subject = f"Nova marca adicional pra revisar — {subject_stream}"

    intro = "Um franqueador aprovado acabou de criar uma marca adicional que precisa de revisão."
    body_html = [
        f"Solicitante: <strong>{safe_name}</strong> ({safe_email})",
        f"Marca: <strong>{safe_stream}</strong>",
        "Tipo: Franquia adicional (franqueador já aprovado)",
    ]
    body_text = [
        f"Solicitante: {franchisor_name} ({franchisor_email})",
        f"Marca: {stream_name}",
        "Tipo: Franquia adicional (franqueador já aprovado)",
    ]
    button_text = "Ver no painel admin"
    button_url = f"{URL_ADMIN_FRANCHISES}/{franchise_id}"

    html_body = _render_html_with_button(
        user_name="equipe",
        intro=intro,
        body_paragraphs=body_html,
        button_text=button_text,
        button_url=button_url,
    )
    text_body = _render_text_with_button(
        user_name="equipe",
        intro=intro,
        body_paragraphs=body_text,
        button_text=button_text,
        button_url=button_url,
    )

    return _send_email(
        to_addresses=[to],
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def send_additional_franchise_approved(
    *,
    to: str,
    user_name: str,
    stream_name: str,
    franchise_slug: str,
) -> str:
    """
    Notifica o franqueador que a marca adicional foi aprovada e já está publicada.
    """
    safe_stream = html.escape(stream_name, quote=True)

    subject_stream = stream_name.replace("\r", " ").replace("\n", " ")
    subject = f"Sua marca {subject_stream} foi aprovada"

    intro_html = (
        f"Boas notícias — sua marca <strong>{safe_stream}</strong> foi aprovada "
        f"e já está publicada no Mercado Franquia."
    )
    intro_text = (
        f"Boas notícias — sua marca {stream_name} foi aprovada "
        f"e já está publicada no Mercado Franquia."
    )
    body_html = [
        "Você pode editar os detalhes e gerenciar leads pelo seu painel de franqueador.",
    ]
    body_text = [
        "Você pode editar os detalhes e gerenciar leads pelo seu painel de franqueador.",
    ]
    button_text = "Ir pro painel"
    button_url = URL_FRANCHISOR_MY_FRANCHISES

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro_html,
        body_paragraphs=body_html,
        button_text=button_text,
        button_url=button_url,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro_text,
        body_paragraphs=body_text,
        button_text=button_text,
        button_url=button_url,
    )

    return _send_email(
        to_addresses=[to],
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def send_additional_franchise_rejected(
    *,
    to: str,
    user_name: str,
    stream_name: str,
    rejection_reason: str,
) -> str:
    """
    Notifica o franqueador que a marca adicional foi rejeitada. Tom neutro, sem CTA.
    """
    safe_stream = html.escape(stream_name, quote=True)
    safe_reason = html.escape(rejection_reason, quote=True)

    subject_stream = stream_name.replace("\r", " ").replace("\n", " ")
    subject = f"Atualização sobre sua marca {subject_stream}"

    intro_html = (
        f"Sua solicitação de publicação da marca <strong>{safe_stream}</strong> "
        f"não foi aprovada nesta análise."
    )
    intro_text = (
        f"Sua solicitação de publicação da marca {stream_name} "
        f"não foi aprovada nesta análise."
    )
    body_html = [
        f"Motivo: {safe_reason}",
        "Caso queira reenviar, entre em contato com nossa equipe ou cadastre novamente com os dados complementares.",
    ]
    body_text = [
        f"Motivo: {rejection_reason}",
        "Caso queira reenviar, entre em contato com nossa equipe ou cadastre novamente com os dados complementares.",
    ]

    html_body = _render_html_with_button(
        user_name=user_name,
        intro=intro_html,
        body_paragraphs=body_html,
    )
    text_body = _render_text_with_button(
        user_name=user_name,
        intro=intro_text,
        body_paragraphs=body_text,
    )

    return _send_email(
        to_addresses=[to],
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )
