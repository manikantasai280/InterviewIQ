import smtplib
from email.message import EmailMessage

from backend.app.core.config import settings


def send_invitation_email(
    to_email: str,
    interview_title: str,
    interview_id: int,
    access_code: str,
    scheduled_at_text: str,
) -> None:
    """Send (or, in dry-run mode, print) one interview invitation."""
    subject = f"Interview invitation: {interview_title}"
    body = (
        f"Hello,\n\n"
        f"You are invited to an AI interview: {interview_title}\n"
        f"Date and time: {scheduled_at_text}\n\n"
        f"Interview ID: {interview_id}\n"
        f"Access code: {access_code}\n\n"
        f"Open {settings.frontend_url} on the interview day, enter the "
        f"interview ID and your access code, and wait for the start time.\n\n"
        f"Good luck!\nInterviewIQ"
    )

    if settings.email_dry_run:
        print(f"\n--- DRY RUN EMAIL to {to_email} ---\n{subject}\n\n{body}\n---\n")
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_username
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)

def send_email(to_email: str, subject: str, body: str) -> None:
    """Send (or, in dry-run mode, print) one email."""
    if settings.email_dry_run:
        print(f"\n--- DRY RUN EMAIL to {to_email} ---\n{subject}\n\n{body}\n---\n")
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_username
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)