"""Email delivery of EPUB files to a Kindle "Send to Kindle" address via Gmail SMTP."""

import smtplib
from email.message import EmailMessage
from pathlib import Path

def send_to_kindle(
    epub_path: Path,
    kindle_email: str,
    gmail_address: str,
    gmail_app_password: str,
) -> None:
    """Send an EPUB file as an email attachment to a Kindle email address.

    Requires a Gmail App Password (not your normal Gmail password) — see
    project README for setup steps.
    """
    msg = EmailMessage()
    msg["Subject"] = epub_path.stem
    msg["From"] = gmail_address
    msg["To"] = kindle_email
    msg.set_content("Sent automatically by kindle-clipper.")

    msg.add_attachment(
        epub_path.read_bytes(),
        maintype="application",
        subtype="epub+zip",
        filename=epub_path.name,
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, gmail_app_password)
        smtp.send_message(msg)