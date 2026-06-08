import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    """Send email via Brevo's transactional HTTP API (port 443).

    Bypasses Render Free Tier's outbound SMTP port 587 restriction.
    Requires BREVO_API_KEY in environment (Brevo Dashboard → SMTP & API → API Keys).
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        api_key = getattr(settings, "BREVO_API_KEY", "")
        if not api_key:
            raise RuntimeError("BREVO_API_KEY is not configured in environment variables.")

        from email.utils import parseaddr

        from_name, from_email = parseaddr(message.from_email)
        to_list = [{"email": addr} for addr in message.to]

        payload = {
            "sender": {"name": from_name or from_email.split("@")[0], "email": from_email},
            "to": to_list,
            "subject": message.subject,
            "textContent": message.body,
        }

        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = content

        if message.reply_to:
            payload["replyTo"] = {"email": message.reply_to[0]}

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=getattr(settings, "EMAIL_TIMEOUT", 10),
        )

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Brevo API returned {response.status_code}: {response.text}"
            )
