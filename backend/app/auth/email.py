"""Magic-link email delivery via Resend. No-op when RESEND_API_KEY is unset."""

import resend

from app.config import settings


def send_magic_link(email: str, token: str) -> None:
    if not settings.resend_api_key:
        return

    resend.api_key = settings.resend_api_key
    link = f"{settings.frontend_url}/auth/verify?token={token}"

    resend.Emails.send(
        {
            "from": "Whats-What <noreply@whats-what.app>",
            "to": [email],
            "subject": "Your Whats-What sign-in link",
            "html": (
                "<p>Click below to sign in to Whats-What."
                " This link expires in 15 minutes.</p>"
                f'<p><a href="{link}">Sign in to Whats-What</a></p>'
                "<p>If you didn't request this, you can ignore this email.</p>"
            ),
        }
    )
