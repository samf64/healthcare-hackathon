import smtplib
from email.message import EmailMessage

from app.config import settings


class EmailNotifier:
    """Email sender with console fallback for local development."""

    def send_email(self, to_email: str, subject: str, body: str) -> tuple[bool, str]:
        if not settings.smtp_host:
            print(f"[EMAIL-DRY-RUN] to={to_email} subject={subject}\n{body}\n")
            return True, "dry_run"

        msg = EmailMessage()
        msg["From"] = settings.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            return True, "sent"
        except Exception as exc:  # pragma: no cover - environment dependent
            return False, str(exc)

