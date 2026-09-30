"""Email delivery (SMTP) for the notification dispatcher.

Settings are read from the environment on every call so tests and operators can
toggle ``SMTP_ENABLED`` without re-importing. Passwords are never logged.

| Variable | Default |
|---|---|
| ``SMTP_ENABLED`` | ``false`` (simulate: rows are marked ``simulated``) |
| ``SMTP_HOST`` | ``smtp.gmail.com`` |
| ``SMTP_PORT`` | ``587`` (STARTTLS) |
| ``SMTP_USER`` | required when enabled (also the From address) |
| ``SMTP_PASSWORD`` | required when enabled (Gmail: App Password) |
| ``SMTP_FROM_NAME`` | ``B2B Sales Notifications`` |
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sales_common.config import ConfigError, env_bool, env_int, env_str

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmtpSettings:
    enabled: bool
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    from_name: str

    @classmethod
    def from_env(cls) -> "SmtpSettings":
        return cls(
            enabled=env_bool("SMTP_ENABLED", False),
            host=env_str("SMTP_HOST", "smtp.gmail.com"),
            port=env_int("SMTP_PORT", 587),
            user=env_str("SMTP_USER", ""),
            password=env_str("SMTP_PASSWORD", ""),
            from_name=env_str("SMTP_FROM_NAME", "B2B Sales Notifications"),
        )

    def validate(self) -> None:
        """Raise ``ConfigError`` when SMTP is enabled without credentials."""
        if self.enabled and (not self.user or not self.password):
            raise ConfigError("SMTP_ENABLED=true requires SMTP_USER and SMTP_PASSWORD")


def send_email(settings: SmtpSettings, to_address: str, subject: str, body: str) -> dict:
    """Send one plain-text email via SMTP (STARTTLS).

    Returns ``{"sent": bool, "detail": str}``; never raises for SMTP/network errors.
    Only call this when ``settings.enabled`` is true.
    """
    try:
        settings.validate()
    except ConfigError as exc:
        return {"sent": False, "detail": str(exc)}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.from_name} <{settings.user}>"
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.user, settings.password)
            server.sendmail(settings.user, [to_address], msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        # smtp_code only: the server message can echo the username.
        logger.error("SMTP authentication failed (code %s)", exc.smtp_code)
        return {"sent": False, "detail": f"SMTP auth error (code {exc.smtp_code})"}
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Email send failed: %s", type(exc).__name__)
        return {"sent": False, "detail": f"SMTP error: {type(exc).__name__}: {exc}"}
    logger.info("Email delivered: %s", subject)
    return {"sent": True, "detail": "delivered"}
