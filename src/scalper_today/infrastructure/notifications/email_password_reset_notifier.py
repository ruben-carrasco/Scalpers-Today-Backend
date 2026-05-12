import asyncio
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import quote

from scalper_today.config import Settings
from scalper_today.domain.interfaces import IPasswordResetNotifier

logger = logging.getLogger(__name__)


class EmailPasswordResetNotifier(IPasswordResetNotifier):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_password_reset(self, email: str, token: str) -> None:
        if not self.settings.is_smtp_configured:
            logger.warning("SMTP is not configured; password reset email skipped")
            return

        message = self._build_message(email, token)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._send_sync, message)
        logger.info("Password reset email sent", extra={"email": email})

    def _build_message(self, email: str, token: str) -> EmailMessage:
        reset_url = self.settings.password_reset_url_template.format(
            token=quote(token, safe=""),
            email=quote(email, safe=""),
        )
        from_email = formataddr((self.settings.smtp_from_name, self.settings.smtp_from_email))

        message = EmailMessage()
        message["Subject"] = "Restablece tu contraseña de Scalpers Today"
        message["From"] = from_email
        message["To"] = email
        message.set_content(
            "\n".join(
                [
                    "Scalpers Today",
                    "Restablecimiento de contraseña",
                    "",
                    "Hemos recibido una solicitud para restablecer tu contraseña.",
                    "Abre este enlace desde tu móvil para crear una nueva contraseña:",
                    reset_url,
                    "",
                    "Si el enlace no se abre automáticamente, copia este código en la app:",
                    token,
                    "",
                    "Si no has solicitado este cambio, puedes ignorar este correo.",
                    f"El enlace caduca en {self.settings.password_reset_token_expire_minutes} minutos.",
                ]
            )
        )
        message.add_alternative(
            f"""
            <html>
              <body style="margin:0;padding:0;background:#f4f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111827;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:32px 16px;">
                  <tr>
                    <td align="center">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:22px;overflow:hidden;border:1px solid #e5e7eb;">
                        <tr>
                          <td style="background:#07111f;padding:28px 32px;">
                            <div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#22c7ee;font-weight:700;">Scalpers Today</div>
                            <h1 style="margin:10px 0 0;color:#ffffff;font-size:26px;line-height:1.2;">Restablece tu contraseña</h1>
                          </td>
                        </tr>
                        <tr>
                          <td style="padding:30px 32px;">
                            <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#374151;">
                              Hemos recibido una solicitud para restablecer tu contraseña. Pulsa el botón desde tu móvil para crear una nueva.
                            </p>
                            <p style="margin:26px 0;text-align:center;">
                              <a href="{reset_url}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:700;padding:15px 24px;border-radius:999px;">
                                Restablecer contraseña
                              </a>
                            </p>
                            <p style="margin:0 0 10px;font-size:14px;line-height:1.5;color:#6b7280;">
                              Si el enlace no se abre automáticamente, copia este código en la app:
                            </p>
                            <div style="background:#f3f4f6;border:1px solid #e5e7eb;border-radius:14px;padding:14px 16px;font-family:'SFMono-Regular',Consolas,monospace;font-size:12px;line-height:1.45;color:#111827;word-break:break-all;">
                              {token}
                            </div>
                            <p style="margin:20px 0 0;font-size:13px;line-height:1.5;color:#6b7280;">
                              Este enlace caduca en {self.settings.password_reset_token_expire_minutes} minutos. Si no has solicitado este cambio, puedes ignorar este correo.
                            </p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </body>
            </html>
            """,
            subtype="html",
        )
        return message

    def _send_sync(self, message: EmailMessage) -> None:
        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port) as smtp:
                self._authenticate_and_send(smtp, message)
            return

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            self._authenticate_and_send(smtp, message)

    def _authenticate_and_send(self, smtp: smtplib.SMTP, message: EmailMessage) -> None:
        if self.settings.smtp_username:
            smtp.login(self.settings.smtp_username, self.settings.smtp_password)
        smtp.send_message(message)
