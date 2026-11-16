import os
import resend
from datetime import datetime, timezone

resend.api_key = os.environ["RESEND_API_KEY"]
EMAIL_FROM = os.environ.get("EMAIL_FROM", "AYAKA API <noreply@ayaka.dev>")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")

BRAND_YELLOW = "#FFD600"
BRAND_BLACK = "#151515"

def _layout(title: str, body_html: str, footer_note: str = "") -> str:
    return f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    </head>
    <body style="margin:0;padding:0;background:#F7F7F2;font-family:Inter,Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F7F2;padding:32px 0;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#fff;border:4px solid {BRAND_BLACK};
                        box-shadow:8px 8px 0 {BRAND_BLACK};border-radius:16px;">
            <tr>
              <td style="background:{BRAND_YELLOW};padding:24px 32px;
                         border-bottom:4px solid {BRAND_BLACK};border-radius:12px 12px 0 0;">
                <div style="font-size:26px;font-weight:900;letter-spacing:-0.5px;color:{BRAND_BLACK};">
                  AYAKA API
                </div>
                <div style="font-size:11px;font-weight:700;color:{BRAND_BLACK};opacity:.7;">
                  POWERED BY AYAKA SYNC
                </div>
              </td>
            </tr>
            <tr><td style="padding:32px;">
              <h1 style="font-size:22px;font-weight:900;color:{BRAND_BLACK};margin:0 0 16px;">
                {title}
              </h1>
              {body_html}
            </td></tr>
            <tr>
              <td style="padding:20px 32px;background:#F7F7F2;
                         border-top:4px solid {BRAND_BLACK};font-size:11px;color:#555;">
                {footer_note}
                <div style="margin-top:8px;">
                  AYAKA API · Powered by AYAKA Sync · Owner: OLPI STORE
                </div>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """

def send_magic_link_email(to_email: str, token: str, plan: str, expires_minutes: int = 15) -> dict:
    verify_url = f"{BASE_URL}/api/am/verif?token={token}"
    body = f"""
    <p style="font-size:15px;line-height:1.6;color:{BRAND_BLACK};">
      Seseorang meminta Magic Link untuk mengaktifkan <strong>{plan}</strong>
      pada akun <strong>{to_email}</strong>.
    </p>
    <p style="font-size:14px;color:#444;line-height:1.6;">
      Klik tombol di bawah untuk memverifikasi. Tautan ini berlaku selama
      <strong>{expires_minutes} menit</strong> dan hanya dapat digunakan sekali.
    </p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{verify_url}"
         style="display:inline-block;background:{BRAND_YELLOW};color:{BRAND_BLACK};
                font-weight:900;font-size:16px;text-decoration:none;
                padding:16px 36px;border:4px solid {BRAND_BLACK};
                box-shadow:6px 6px 0 {BRAND_BLACK};border-radius:12px;">
        VERIFY MAGIC LINK
      </a>
    </div>
    <p style="font-size:12px;color:#777;line-height:1.6;">
      Jika Anda tidak meminta tautan ini, abaikan email ini.
      Jangan pernah membagikan tautan ini kepada siapa pun.
    </p>
    """
    html = _layout("Magic Link Premium", body,
                   "Email ini dikirim secara otomatis oleh sistem keamanan AYAKA API.")
    params = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": f"AYAKA API — Magic Link untuk {plan}",
        "html": html,
    }
    result = resend.Emails.send(params)
    return {"id": result.get("id")}

def send_premium_notification(to_email: str, title: str, message: str) -> dict:
    body = f"""
    <p style="font-size:15px;line-height:1.6;color:{BRAND_BLACK};">{message}</p>
    <p style="font-size:12px;color:#777;margin-top:24px;">
      Waktu: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}
    </p>
    """
    html = _layout(title, body, "Pemberitahuan keamanan akun AYAKA API.")
    params = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": f"AYAKA API — {title}",
        "html": html,
    }
    result = resend.Emails.send(params)
    return {"id": result.get("id")}

def send_password_reset_email(to_email: str, token: str) -> dict:
    reset_url = f"{BASE_URL}/login?reset_token={token}"
    body = f"""
    <p style="font-size:15px;line-height:1.6;color:{BRAND_BLACK};">
      Kami menerima permintaan reset password untuk akun Anda.
    </p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{reset_url}"
         style="display:inline-block;background:{BRAND_YELLOW};color:{BRAND_BLACK};
                font-weight:900;font-size:16px;text-decoration:none;
                padding:16px 36px;border:4px solid {BRAND_BLACK};
                box-shadow:6px 6px 0 {BRAND_BLACK};border-radius:12px;">
        RESET PASSWORD
      </a>
    </div>
    <p style="font-size:12px;color:#777;">
      Tautan berlaku 30 menit. Jika bukan Anda, abaikan email ini.
    </p>
    """
    html = _layout("Reset Password", body,
                   "Email keamanan AYAKA API. Jangan bagikan tautan ini.")
    params = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": "AYAKA API — Reset Password",
        "html": html,
    }
    result = resend.Emails.send(params)
    return {"id": result.get("id")}