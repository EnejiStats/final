# ============================================================
# EMAIL TEMPLATE HELPER  — CID-branded version
# Drop-in replacement for the _email_html / send_email section
# of backend/app/main.py
#
# How it works:
#   • The branding PNG is read from backend/static/images/eneji-stats-branding.png
#     at import time and base64-encoded once.
#   • _email_html() references the image via <img src="cid:eneji-branding">.
#   • send_email() attaches the base64 blob as an inline (CID) attachment so
#     every email client that supports MIME multipart/related renders it
#     correctly — no external URL needed, no broken image.
#
# Place this file alongside main.py, or copy the relevant sections into it.
# ============================================================

import base64
import html as _html
import logging
import os
import traceback
from pathlib import Path

import httpx
from fastapi import HTTPException


logger = logging.getLogger("enejistats.email")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip() or "enejistats@gmail.com"
FROM_NAME = os.getenv("FROM_NAME", "").strip() or "EnejiStats"

# ---------------------------------------------------------------------------
# Resolve the branding image once at startup
# ---------------------------------------------------------------------------
# Adjust this path if your layout differs.
_HERE = Path(__file__).resolve().parent
_BRANDING_CANDIDATES = (
    Path(os.getenv("ENEJISTATS_BRANDING_PATH", "")).expanduser()
    if os.getenv("ENEJISTATS_BRANDING_PATH")
    else None,
    _HERE / "static" / "images" / "eneji-stats-branding.png",
    _HERE.parent / "static" / "images" / "eneji-stats-branding.png",
    Path.cwd() / "static" / "images" / "eneji-stats-branding.png",
)
_BRANDING_PNG = next(
    (candidate for candidate in _BRANDING_CANDIDATES if candidate and candidate.is_file()),
    _HERE.parent / "static" / "images" / "eneji-stats-branding.png",
)

_BRANDING_B64: str | None = None

def _load_branding_image() -> str | None:
    """
    Load the branding PNG and return its base64-encoded content.
    Called once at module import so every email call is fast.
    Returns None if the file is missing (a text-fallback is used instead).
    """
    try:
        with open(_BRANDING_PNG, "rb") as fh:
            return base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        logger.warning(
            "Branding PNG not found at %s — email will use text fallback logo.", _BRANDING_PNG
        )
        return None

_BRANDING_B64 = _load_branding_image()


def _escape(value: object) -> str:
    """Escape dynamic values before inserting them into an HTML email."""
    return _html.escape("" if value is None else str(value), quote=True)


# ============================================================
# EMAIL TEMPLATE HELPER
# ============================================================

def _email_html(subject: str, inner_html: str) -> str:
    """
    Wrap inner_html in the EnejiStats branded dark-theme email template.

    The header logo is an <img src="cid:eneji-branding"> tag.
    The actual PNG bytes are attached by send_email() as an inline
    MIME part so the image is self-contained inside the email and
    never fetched over HTTP.

    A text fallback is included for clients that block all images.
    """

    # ------------------------------------------------------------------
    # Header: CID image if branding loaded; graceful text fallback if not
    # ------------------------------------------------------------------
    if _BRANDING_B64:
        # max-width/width both set so Outlook (which ignores max-width on <img>)
        # and web clients both respect the 240 px cap.
        logo_block = """
<tr>
  <td align="center" bgcolor="#162060"
      style="background-color:#162060;padding:26px 32px 22px;font-size:0;line-height:0;">
    <!--[if mso]>
    <table border="0" cellpadding="0" cellspacing="0"><tr><td width="240">
    <![endif]-->
    <img src="cid:eneji-branding"
         alt="EnejiStats — Tracking talent with precision, integrity and reliability"
         width="240"
         style="display:block;max-width:240px;width:240px;height:auto;
                border:0;outline:0;text-decoration:none;
                -ms-interpolation-mode:bicubic;" />
    <!--[if mso]></td></tr></table><![endif]-->
  </td>
</tr>"""
    else:
        # Text fallback — preserves brand colours if the PNG is unavailable
        logo_block = """
<tr>
  <td align="center" bgcolor="#162060"
      style="background-color:#162060;padding:26px 32px 18px;">
    <table width="0" border="0" cellpadding="0" cellspacing="0"
           style="margin:0 auto;">
      <tr>
        <td align="center" style="padding-bottom:6px;font-size:0;line-height:0;">
          <span style="display:inline-block;width:22px;height:22px;
                       border-radius:50%;
                       background:radial-gradient(circle at 50% 50%,#1a4fa0 3.8px,transparent 4.5px),#f5b800;
                       box-shadow:inset 0 0 0 0.8px rgba(0,0,0,0.28);">&nbsp;</span>
        </td>
      </tr>
      <tr>
        <td align="center" style="padding:0;">
          <span style="font-weight:900;font-size:34px;color:#ffffff;
                       letter-spacing:3px;font-family:'Segoe UI',Arial,sans-serif;">
            Ene&#x0237;&#x0131;
          </span>
          <span style="font-weight:900;font-size:34px;color:#f5b800;
                       letter-spacing:3px;font-family:'Segoe UI',Arial,sans-serif;">
            Stats
          </span>
        </td>
      </tr>
      <tr>
        <td align="center" style="padding:6px 0 4px;">
          <span style="font-size:9px;font-style:italic;
                       color:rgba(255,255,255,.74);
                       font-family:'Segoe UI',Arial,sans-serif;">
            Tracking talent with precision, integrity and reliability
          </span>
        </td>
      </tr>
    </table>
  </td>
</tr>"""

    html_template = (
        r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="color-scheme" content="dark light"/>
  <meta name="supported-color-schemes" content="dark light"/>
  <title>{{SUBJECT}}</title>
  <!--[if mso]>
  <noscript><xml><o:OfficeDocumentSettings>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings></xml></noscript>
  <![endif]-->
  <style>
    /* ---- Responsive ---- */
    @media only screen and (max-width:600px){
      table[class="card"]  { width:100%!important; max-width:560px!important; }
      table[class="inner"] { width:100%!important; }
      img[class="branding-img"] { width:180px!important; max-width:180px!important; }
    }
    /* ---- Body typography ---- */
    body p, body td, body span, body li {
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }
  </style>
</head>
<body style="margin:0;padding:0;background-color:#0f172a;
             font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
             -webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:#0f172a;padding:32px 0;">
  <tr>
    <td align="center" valign="top">

      <!-- ===== CARD ===== -->
      <table class="card" width="560" cellpadding="0" cellspacing="0" border="0"
             style="background-color:#1e1e2f;
                    border:1px solid rgba(255,255,255,0.08);
                    border-collapse:collapse;">

        <!-- LOGO / HEADER -->
"""
        + logo_block
        + r"""
        <!-- GOLD STRIPE -->
        <tr>
          <td height="7" bgcolor="#f5b800"
              style="background:#f5b800;font-size:1px;line-height:1px;">&nbsp;</td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="padding:32px 36px;background-color:#1e1e2f;">
            <!-- Body typography defaults — every builder overrides individual styles;
                 these are sensible fallbacks for any raw text injected directly. -->
            <div style="color:#cbd5e1;font-size:15px;line-height:1.75;
                        text-align:justify;word-break:break-word;">
              {{INNER_HTML}}
            </div>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="padding:18px 32px 20px;
                     background-color:rgba(0,0,0,0.25);
                     text-align:center;
                     font-size:12px;
                     color:#475569;
                     border-top:1px solid rgba(255,255,255,0.06);
                     font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
            &#169; 2026 EnejiStats. All rights reserved.<br/>
            <a href="https://enejistats.com"
               style="color:#60a5fa;text-decoration:none;">enejistats.com</a>
          </td>
        </tr>

      </table>
      <!-- ===== / CARD ===== -->

    </td>
  </tr>
</table>

</body>
</html>"""
    )

    return (
        html_template
        .replace("{{SUBJECT}}", _escape(subject))
        .replace("{{INNER_HTML}}", inner_html)
    )


# ============================================================
# EMAIL CONTENT BUILDERS
# ============================================================
# Body-copy style used consistently across all builders.
# Justified text, comfortable line-height, readable size.
_BODY_STYLE = (
    "margin:0 0 14px;"
    "color:#94a3b8;"
    "font-size:14px;"
    "line-height:1.75;"
    "text-align:justify;"
)
_NAME_STYLE = "color:#f5b800;font-weight:700;"
_H2_STYLE = (
    "margin:0 0 10px;"
    "font-size:18px;"
    "font-weight:700;"
    "color:#ffffff;"
    "letter-spacing:.3px;"
)


def _build_otp_email(display_name: str, otp: str) -> tuple:
    """Return (plain_text, html_body) for OTP verification email."""
    plain_display_name = display_name
    plain_otp = otp
    display_name = _escape(display_name)
    otp = _escape(otp)
    plain = (
        f"Hi {plain_display_name},\n\n"
        "Your EnejiStats email verification code is:\n\n"
        f"  {plain_otp}\n\n"
        "This code expires in 30 minutes.\n"
        "If you did not create an account, please ignore this email.\n\n"
        "— The EnejiStats Team"
    )
    html_inner = (
        f"<h2 style='{_H2_STYLE}'>Verify Your Email Address</h2>"
        f"<p style='{_BODY_STYLE}'>"
        f"Hi <strong style='{_NAME_STYLE}'>{display_name}</strong>,<br/>"
        "Please enter the code below on the EnejiStats verification screen "
        "to confirm your email address and activate your account.</p>"
        "<div style='text-align:center;margin:28px 0;'>"
        f"<div style='display:inline-block;background:#f5b800;color:#1e1e2f;"
        "padding:18px 48px;border-radius:12px;font-size:32px;font-weight:900;"
        "letter-spacing:10px;font-family:monospace;'>"
        f"{otp}</div></div>"
        f"<p style='margin:16px 0 0;font-size:12px;color:#64748b;text-align:center;'>"
        "This code expires in <strong>30 minutes</strong>. "
        "If you did not create an EnejiStats account, you may safely ignore this email.</p>"
    )
    return plain, _email_html("EnejiStats — Verify Your Email", html_inner)


def _build_trial_email(display_name: str, days_left: int) -> tuple:
    """Return (plain_text, html_body) for trial expiry warning."""
    plain_display_name = display_name
    display_name = _escape(display_name)
    if days_left == 0:
        subject_suffix = "Trial Expired"
        headline = "Your Free Trial Has Ended"
        body_text = (
            "Your 14-day free trial has expired. "
            "Subscribe now to regain full access to all EnejiStats features, "
            "including player tracking, advanced statistics, and reporting tools."
        )
        cta = "Subscribe Now"
        cta_color = "#ef4444"
    else:
        subject_suffix = f"Trial Expires in {days_left} Day{'s' if days_left != 1 else ''}"
        headline = f"{days_left} Day{'s' if days_left != 1 else ''} Left on Your Free Trial"
        body_text = (
            f"Your EnejiStats free trial expires in "
            f"{days_left} day{'s' if days_left != 1 else ''}. "
            "Subscribe before it ends to ensure uninterrupted access to "
            "all platform features."
        )
        cta = "View Subscription Plans"
        cta_color = "#f59e0b"

    plain = (
        f"Hi {plain_display_name},\n\n{body_text}\n\n"
        "Log in to your dashboard to subscribe:\n"
        "  https://enejistats.com\n\n"
        "— The EnejiStats Team"
    )
    html_inner = (
        f"<h2 style='{_H2_STYLE}'>{headline}</h2>"
        f"<p style='{_BODY_STYLE}'>"
        f"Hi <strong style='{_NAME_STYLE}'>{display_name}</strong>,<br/>"
        f"{body_text}</p>"
        f"<div style='text-align:center;margin:28px 0;'>"
        f"<a href='https://enejistats.com' "
        f"style='background:{cta_color};color:#fff;"
        "padding:14px 40px;border-radius:8px;font-weight:700;font-size:15px;"
        f"text-decoration:none;display:inline-block;letter-spacing:.3px;'>{cta}</a></div>"
    )
    return plain, _email_html(f"EnejiStats — {subject_suffix}", html_inner)


def _build_sub_confirm_email(
    display_name: str, plan: str, amount: float, expiry_date: str, method: str
) -> tuple:
    """Return (plain_text, html_body) for subscription confirmation."""
    plain_display_name = display_name
    plain_plan = plan
    plain_expiry_date = expiry_date
    plain_method = method
    display_name = _escape(display_name)
    plan = _escape(plan)
    expiry_date = _escape(expiry_date)
    method = _escape(method)
    plain = (
        f"Hi {plain_display_name},\n\n"
        "Your EnejiStats subscription is now active.\n\n"
        f"  Plan:    {plain_plan.replace('_', ' ').title()}\n"
        f"  Amount:  N{amount:,.0f}\n"
        f"  Method:  {plain_method}\n"
        f"  Expires: {plain_expiry_date}\n\n"
        "Thank you for subscribing. We are glad to have you on board!\n\n"
        "— The EnejiStats Team"
    )
    # Table row helper for consistent styling
    _row = lambda label, value, value_style="color:#ffffff;", bg="transparent": (
        f"<tr style='background:{bg};'>"
        f"<td style='padding:10px 12px;color:#94a3b8;font-size:13px;"
        "border-bottom:1px solid rgba(255,255,255,.05);'>"
        f"{label}</td>"
        f"<td style='padding:10px 12px;{value_style}font-weight:600;font-size:13px;"
        "border-bottom:1px solid rgba(255,255,255,.05);'>"
        f"{value}</td></tr>"
    )
    html_inner = (
        f"<h2 style='{_H2_STYLE}'>Subscription Activated ✓</h2>"
        f"<p style='{_BODY_STYLE}'>"
        f"Hi <strong style='{_NAME_STYLE}'>{display_name}</strong>,<br/>"
        "Your EnejiStats subscription is now active. Below is a summary "
        "of your subscription details for your records.</p>"
        "<table style='width:100%;border-collapse:collapse;margin:16px 0 20px;"
        "border:1px solid rgba(255,255,255,.07);border-radius:6px;overflow:hidden;'>"
        + _row("Plan", plan.replace("_", " ").title())
        + _row("Amount", f"&#8358;{amount:,.0f}", "color:#f5b800;", "rgba(255,255,255,.03)")
        + _row("Payment Method", method)
        + _row("Valid Until", expiry_date, "color:#22c55e;", "rgba(255,255,255,.03)")
        + "</table>"
        f"<p style='{_BODY_STYLE}'>"
        "Thank you for subscribing to EnejiStats. Should you have any questions "
        "about your subscription, please contact us at "
        "<a href='mailto:enejistats@gmail.com' style='color:#f5b800;"
        "text-decoration:none;'>enejistats@gmail.com</a>.</p>"
    )
    return plain, _email_html("EnejiStats — Subscription Activated", html_inner)


def _build_verification_email(display_name: str, verify_url: str, role: str) -> tuple:
    """Return (plain_text, html_body) for email address verification link."""
    plain_display_name = display_name
    plain_verify_url = verify_url
    plain_role_label = role.capitalize()
    display_name = _escape(display_name)
    verify_url = _escape(verify_url)
    role_label = _escape(plain_role_label)
    plain = (
        f"Hi {plain_display_name},\n\n"
        f"Thank you for registering on EnejiStats as a {plain_role_label}.\n\n"
        "To activate your account, please verify your email address by "
        "clicking the link below:\n\n"
        f"  {plain_verify_url}\n\n"
        "This link expires in 24 hours. "
        "If you did not create an EnejiStats account, please ignore this email.\n\n"
        "— The EnejiStats Team"
    )
    html_inner = (
        f"<h2 style='{_H2_STYLE}'>Verify Your Email Address</h2>"
        f"<p style='{_BODY_STYLE}'>"
        f"Hi <strong style='color:#ffd700;font-weight:700;'>{display_name}</strong>,<br/>"
        f"Thank you for registering on EnejiStats as a "
        f"<strong style='color:#e2e8f0;'>{role_label}</strong>. "
        "Please click the button below to verify your email address and "
        "activate your account.</p>"
        "<div style='text-align:center;margin:28px 0;'>"
        f"<a href='{verify_url}' "
        "style='background:#22c55e;color:#fff;padding:16px 44px;"
        "border-radius:10px;font-weight:700;font-size:15px;"
        "text-decoration:none;display:inline-block;letter-spacing:.3px;'>"
        "&#10003;&nbsp; Verify My Email</a></div>"
        f"<p style='margin:16px 0 0;font-size:12px;color:#64748b;text-align:center;'>"
        "This link expires in <strong>24 hours</strong>. "
        "If you did not register for EnejiStats, ignore this email or contact "
        "<a href='mailto:enejistats@gmail.com' style='color:#ffd700;'>"
        "enejistats@gmail.com</a>.</p>"
        "<hr style='border:none;border-top:1px solid rgba(255,255,255,.08);"
        "margin:22px 0;'/>"
        "<p style='font-size:12px;color:#475569;text-align:left;line-height:1.6;'>"
        "If the button above does not work, copy and paste the link below into "
        "your browser:<br/>"
        f"<a href='{verify_url}' "
        "style='color:#60a5fa;word-break:break-all;text-decoration:none;'>"
        f"{verify_url}</a></p>"
    )
    return plain, _email_html("EnejiStats — Verify Your Email Address", html_inner)


def build_welcome_email(
    role: str,
    display_name: str,
    user_unique_id: str,
    email: str,
    password_plain: str | None = None,
) -> tuple:
    """Return (plain_text, html_body) welcome email for a newly registered user."""
    plain_role_label = role.capitalize()
    plain_display_name = display_name
    plain_user_unique_id = user_unique_id
    plain_email = email
    plain_password = password_plain
    display_name = _escape(display_name)
    user_unique_id = _escape(user_unique_id)
    email = _escape(email)
    password_plain = _escape(password_plain) if password_plain else None
    role_label = _escape(plain_role_label)

    _row = lambda label, value, value_style="color:#e2e8f0;", bg="transparent": (
        f"<tr style='background:{bg};'>"
        f"<td style='padding:8px 12px;color:#64748b;font-size:13px;"
        "border-bottom:1px solid rgba(255,255,255,.05);white-space:nowrap;'>"
        f"{label}</td>"
        f"<td style='padding:8px 12px;{value_style}font-size:13px;"
        "border-bottom:1px solid rgba(255,255,255,.05);word-break:break-all;'>"
        f"{value}</td></tr>"
    )

    inner = (
        f"<h2 style='{_H2_STYLE}color:#ffd700;'>"
        f"Welcome to EnejiStats, {display_name}!</h2>"
        f"<p style='{_BODY_STYLE}'>"
        f"Your <strong style='color:#e2e8f0;'>{role_label}</strong> account has been "
        "created successfully. Below are your account details — please keep this "
        "email safe for future reference.</p>"
        "<table style='width:100%;border-collapse:collapse;margin:16px 0 20px;"
        "border:1px solid rgba(255,255,255,.07);'>"
        + _row("Role", role_label)
        + _row("Account ID", user_unique_id, "color:#e2e8f0;font-family:monospace;",
               "rgba(255,255,255,.03)")
        + _row("Email", email)
        + (
            _row("Temporary Password", password_plain,
                 "color:#f5b800;font-family:monospace;",
                 "rgba(255,255,255,.03)")
            if password_plain else ""
        )
        + "</table>"
        f"<p style='{_BODY_STYLE}'>"
        "If you did not register on EnejiStats or believe this email was sent in "
        "error, please contact us immediately at "
        "<a href='mailto:enejistats@gmail.com' style='color:#ffd700;"
        "text-decoration:none;'>enejistats@gmail.com</a>.</p>"
    )

    plain = (
        f"Welcome to EnejiStats, {plain_display_name}!\n\n"
        f"Your {plain_role_label} account has been created.\n"
        f"Account ID : {plain_user_unique_id}\n"
        f"Email      : {plain_email}\n"
        + (f"Password   : {plain_password}\n" if plain_password else "")
        + "\n— The EnejiStats Team\n"
    )
    return plain, _email_html(f"Welcome to EnejiStats — {role_label} Account", inner)


# ============================================================
# EMAIL SENDER (Brevo API)  — with CID inline attachment
# ============================================================

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    raise_on_error: bool = False,
) -> bool:
    """
    Send a branded email via the Brevo transactional API.

    The branding PNG is attached as an inline (Content-ID) MIME part so that
    <img src="cid:eneji-branding"> in the HTML always resolves — even in
    clients that block remote images.
    """
    try:
        logger.info(
            "Sending email to %s | subject=%s | brevo_set=%s",
            to_email, subject, bool(BREVO_API_KEY),
        )
        if not BREVO_API_KEY:
            logger.error("BREVO_API_KEY is not configured")
            return False

        # ---- Build final HTML -----------------------------------------------
        content_html = html_body
        if not content_html:
            _plain_inner = (
                f"<p style='color:#cbd5e1;font-size:15px;line-height:1.75;"
                f"text-align:justify;white-space:pre-wrap;'>"
                f"{_escape(body)}</p>"
            )
            content_html = _email_html(subject, _plain_inner)
        elif not content_html.strip().lower().startswith("<!doctype"):
            content_html = _email_html(subject, content_html)

        # ---- Brevo payload --------------------------------------------------
        payload: dict = {
            "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": content_html,
        }

        # ---- Attach branding PNG as inline (CID) attachment ----------------
        # Brevo supports inline images via the "attachment" array when each
        # entry carries a "contentId" field.  The HTML references them as
        # cid:<contentId>.  This keeps the image self-contained in the email.
        if _BRANDING_B64:
            payload["attachment"] = [
                {
                    "content": _BRANDING_B64,          # base64-encoded PNG
                    "name": "eneji-stats-branding.png", # MIME filename
                    "contentId": "eneji-branding",      # matches cid: in HTML
                }
            ]

        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as _http_client:
            response = await _http_client.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers=headers,
            )

        logger.info("Brevo response: %s — %s", response.status_code, response.text)

        if response.status_code in (200, 201, 202):
            logger.info("Email sent successfully via Brevo to %s", to_email)
            return True

        logger.error(
            "Brevo API rejected email: %s — %s", response.status_code, response.text
        )
        if raise_on_error:
            raise HTTPException(
                status_code=500, detail=f"Brevo error: {response.text}"
            )
        return False

    except HTTPException:
        raise
    except Exception as e:
        logger.error("BREVO EMAIL ERROR: %s\n%s", e, traceback.format_exc())
        if raise_on_error:
            raise HTTPException(status_code=500, detail=f"Email error: {str(e)}")
        return False
