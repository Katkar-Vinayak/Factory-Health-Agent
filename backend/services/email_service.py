"""
Email Service for Factory Health & Response Agent
==================================================
Handles vendor replacement request notifications.

Supports two operational modes:
1. REAL MODE:
   Triggered when SMTP environment variables are fully configured:
   - SMTP_HOST
   - SMTP_PORT (default 587)
   - SMTP_USERNAME
   - SMTP_PASSWORD
   - SENDER_EMAIL
   Transmits actual email via smtplib with STARTTLS.

2. MOCK / SIMULATED MODE:
   Active when any required SMTP configuration is missing.
   - Generates the complete, deterministic vendor email text.
   - Never crashes or exposes internal credentials.
   - Safely logs/stores the simulated message.
   - Explicitly flags email_status as 'SIMULATED' and is_simulated as True.
   - Transparently communicates that no real email was dispatched.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional


def is_smtp_configured() -> bool:
    """
    Checks if all required SMTP environment variables are present and non-empty.
    """
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SENDER_EMAIL", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    return bool(host and sender and username and password)


def generate_vendor_email_content(
    machine_id: str,
    component: str,
    part_number: str,
    quantity: int = 1,
    priority: str = "High",
    reason: Optional[str] = None
) -> Dict[str, str]:
    """
    Deterministically formats standard vendor replacement email content.
    No LLM hallucination or synthetic companies used.
    """
    clean_mid = str(machine_id).strip()
    clean_comp = str(component).strip()
    clean_part = str(part_number).strip()
    clean_priority = str(priority).strip().capitalize()
    clean_reason = str(reason).strip() if reason else "Predictive maintenance analysis identified a critical degradation condition."

    subject = f"Urgent Replacement Request — {clean_mid} — {clean_comp}"

    body = (
        f"Dear Vendor,\n\n"
        f"We would like to request a replacement component for the following machine.\n\n"
        f"Machine ID: {clean_mid}\n"
        f"Component: {clean_comp}\n"
        f"Part Number: {clean_part}\n"
        f"Quantity: {quantity}\n"
        f"Priority: {clean_priority}\n\n"
        f"Reason:\n"
        f"{clean_reason}\n\n"
        f"Please confirm availability and expected lead time.\n\n"
        f"Regards,\n"
        f"Factory Health & Response Agent"
    )

    return {
        "subject": subject,
        "body": body
    }


def send_vendor_replacement_email(
    machine_id: str,
    component: str,
    part_number: str,
    vendor_email: str,
    vendor_name: Optional[str] = None,
    quantity: int = 1,
    priority: str = "High",
    reason: Optional[str] = None,
    notification_id: Optional[str] = None,
    log_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends or simulates sending a vendor replacement request email.

    Returns structured status dictionary.
    """
    clean_recipient = str(vendor_email).strip()
    if not clean_recipient:
        return {
            "success": False,
            "email_status": "FAILED",
            "is_simulated": False,
            "error": "Vendor email address is required.",
            "message": "Cannot send email without a recipient address."
        }

    email_content = generate_vendor_email_content(
        machine_id=machine_id,
        component=component,
        part_number=part_number,
        quantity=quantity,
        priority=priority,
        reason=reason
    )
    subject = email_content["subject"]
    body = email_content["body"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check whether real SMTP credentials are present
    if not is_smtp_configured():
        # MOCK MODE: Safe deterministic simulation
        simulated_sender = os.getenv("SENDER_EMAIL", "agent-system@example.com").strip()
        
        # Optional logging of mock emails
        if log_file_path:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(log_file_path)), exist_ok=True)
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"\n--- [SIMULATED EMAIL {timestamp}] ---\n")
                    f.write(f"To: {clean_recipient}\n")
                    f.write(f"From: {simulated_sender}\n")
                    f.write(f"Subject: {subject}\n\n")
                    f.write(f"{body}\n")
                    f.write("-------------------------------------\n")
            except Exception:
                pass

        return {
            "success": True,
            "email_status": "SIMULATED",
            "is_simulated": True,
            "recipient": clean_recipient,
            "sender": simulated_sender,
            "subject": subject,
            "body": body,
            "timestamp": timestamp,
            "notification_id": notification_id,
            "vendor_name": vendor_name or "Demo Vendor",
            "part_number": part_number,
            "quantity": quantity,
            "message": "Email simulated successfully in mock mode. No real SMTP credentials configured."
        }

    # REAL MODE: SMTP Transmission
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    sender_email = os.getenv("SENDER_EMAIL", "").strip()

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = clean_recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, [clean_recipient], msg.as_string())

        return {
            "success": True,
            "email_status": "SENT",
            "is_simulated": False,
            "recipient": clean_recipient,
            "sender": sender_email,
            "subject": subject,
            "body": body,
            "timestamp": timestamp,
            "notification_id": notification_id,
            "vendor_name": vendor_name,
            "part_number": part_number,
            "quantity": quantity,
            "message": "Replacement email successfully dispatched via SMTP."
        }
    except Exception as e:
        return {
            "success": False,
            "email_status": "FAILED",
            "is_simulated": False,
            "recipient": clean_recipient,
            "sender": sender_email,
            "subject": subject,
            "body": body,
            "timestamp": timestamp,
            "notification_id": notification_id,
            "error": str(e),
            "message": f"SMTP transmission failed: {str(e)}"
        }
