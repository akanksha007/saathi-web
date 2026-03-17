"""
Saathi — Authentication Module.
Handles Phone OTP (via Twilio/MSG91), Google Sign-In, and JWT token management.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from jose import jwt, JWTError

from config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_DAYS,
    OTP_PROVIDER,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_VERIFY_SERVICE_ID,
    MSG91_AUTH_KEY, MSG91_TEMPLATE_ID,
    GOOGLE_CLIENT_ID,
)


# ─── JWT Token Management ───

def create_token(user_id: str) -> str:
    """Create a JWT token for an authenticated user."""
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """
    Verify a JWT token and return the user_id.
    Returns None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ─── OTP — Send ───

async def send_otp(phone: str) -> dict:
    """
    Send an OTP to the given phone number.
    Uses Twilio Verify or MSG91 depending on config.

    Args:
        phone: Phone number with country code (e.g., "+919876543210")

    Returns:
        {"success": True/False, "message": "..."}
    """
    if OTP_PROVIDER == "twilio":
        return await _send_otp_twilio(phone)
    elif OTP_PROVIDER == "msg91":
        return await _send_otp_msg91(phone)
    else:
        return {"success": False, "message": f"Unknown OTP provider: {OTP_PROVIDER}"}


async def _send_otp_twilio(phone: str) -> dict:
    """Send OTP via Twilio Verify."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_ID:
        return {"success": False, "message": "Twilio credentials not configured."}

    url = f"https://verify.twilio.com/v2/Services/{TWILIO_VERIFY_SERVICE_ID}/Verifications"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                data={"To": phone, "Channel": "sms"},
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                timeout=10.0,
            )
            if response.status_code in (200, 201):
                return {"success": True, "message": "OTP sent successfully."}
            else:
                error_msg = response.json().get("message", "Unknown error")
                return {"success": False, "message": f"Twilio error: {error_msg}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to send OTP: {str(e)}"}


async def _send_otp_msg91(phone: str) -> dict:
    """Send OTP via MSG91."""
    if not MSG91_AUTH_KEY or not MSG91_TEMPLATE_ID:
        return {"success": False, "message": "MSG91 credentials not configured."}

    # Strip '+' prefix for MSG91
    mobile = phone.lstrip("+")

    url = "https://control.msg91.com/api/v5/otp"
    headers = {"authkey": MSG91_AUTH_KEY}
    params = {
        "template_id": MSG91_TEMPLATE_ID,
        "mobile": mobile,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=params, timeout=10.0)
            data = response.json()
            if data.get("type") == "success":
                return {"success": True, "message": "OTP sent successfully."}
            else:
                return {"success": False, "message": data.get("message", "MSG91 error")}
        except Exception as e:
            return {"success": False, "message": f"Failed to send OTP: {str(e)}"}


# ─── OTP — Verify ───

async def verify_otp(phone: str, code: str) -> dict:
    """
    Verify an OTP code for the given phone number.

    Args:
        phone: Phone number with country code
        code: The OTP code entered by the user

    Returns:
        {"success": True/False, "message": "..."}
    """
    if OTP_PROVIDER == "twilio":
        return await _verify_otp_twilio(phone, code)
    elif OTP_PROVIDER == "msg91":
        return await _verify_otp_msg91(phone, code)
    else:
        return {"success": False, "message": f"Unknown OTP provider: {OTP_PROVIDER}"}


async def _verify_otp_twilio(phone: str, code: str) -> dict:
    """Verify OTP via Twilio Verify."""
    url = f"https://verify.twilio.com/v2/Services/{TWILIO_VERIFY_SERVICE_ID}/VerificationCheck"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                data={"To": phone, "Code": code},
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                timeout=10.0,
            )
            data = response.json()
            if data.get("status") == "approved":
                return {"success": True, "message": "OTP verified."}
            else:
                return {"success": False, "message": "Invalid OTP. Please try again."}
        except Exception as e:
            return {"success": False, "message": f"Verification failed: {str(e)}"}


async def _verify_otp_msg91(phone: str, code: str) -> dict:
    """Verify OTP via MSG91."""
    mobile = phone.lstrip("+")
    url = f"https://control.msg91.com/api/v5/otp/verify?mobile={mobile}&otp={code}"
    headers = {"authkey": MSG91_AUTH_KEY}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            data = response.json()
            if data.get("type") == "success":
                return {"success": True, "message": "OTP verified."}
            else:
                return {"success": False, "message": data.get("message", "Invalid OTP.")}
        except Exception as e:
            return {"success": False, "message": f"Verification failed: {str(e)}"}


# ─── Google Sign-In ───

async def verify_google_token(id_token: str) -> Optional[dict]:
    """
    Verify a Google ID token and return user info.

    Returns:
        {"google_id": "...", "email": "...", "name": "..."} or None if invalid.
    """
    if not GOOGLE_CLIENT_ID:
        return None

    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                return None

            data = response.json()

            # Verify the token is for our app
            if data.get("aud") != GOOGLE_CLIENT_ID:
                return None

            return {
                "google_id": data.get("sub"),
                "email": data.get("email"),
                "name": data.get("name", data.get("given_name", "")),
            }
        except Exception:
            return None
