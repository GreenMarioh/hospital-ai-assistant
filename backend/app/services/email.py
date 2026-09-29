import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("app.email")


def send_email(to: str, subject: str, body: str) -> None:
    """Pluggable backend: 'console' logs (dev), 'smtp' sends (prod)."""
    s = get_settings()
    if s.email_backend == "smtp" and s.smtp_host:
        msg = EmailMessage()
        msg["To"], msg["From"], msg["Subject"] = to, s.smtp_user or "noreply@hospital", subject
        msg.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
    else:
        log.info("email (console backend)", extra={"to": to, "subject": subject, "body": body})
