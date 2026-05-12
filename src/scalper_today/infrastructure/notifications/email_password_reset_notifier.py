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
                    "Has solicitado restablecer tu contraseña de Scalpers Today.",
                    "",
                    "Abre este enlace para crear una nueva contraseña:",
                    reset_url,
                    "",
                    "Si no has solicitado este cambio, puedes ignorar este correo.",
                    "Este enlace caduca por seguridad.",
                ]
            )
        )
        message.add_alternative(
            f"""
            <html>
              <body>
                <p>Has solicitado restablecer tu contraseña de <strong>Scalpers Today</strong>.</p>
                <p>
                  <a href="{reset_url}">Restablecer contraseña</a>
                </p>
                <p>Si no has solicitado este cambio, puedes ignorar este correo.</p>
                <p>Este enlace caduca por seguridad.</p>
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
