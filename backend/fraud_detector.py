"""
fraud_detector.py – Online Fraud and Scam Signal Detection
===========================================================
Keyword-based and pattern-based detection of potential financial fraud signals
in user messages or content being evaluated. Runs on every chat message.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fraud keyword / phrase patterns
# ---------------------------------------------------------------------------
FRAUD_KEYWORDS: list[str] = [
    # OTP / PIN sharing
    "otp",
    "share your otp",
    "enter your otp",
    "send otp",
    "give otp",
    "otp share karo",
    "otp batao",
    # KYC fraud
    "kyc update",
    "kyc expire",
    "kyc blocked",
    "complete your kyc",
    "kyc verification",
    "update kyc",
    # Phishing / suspicious links
    "click this link",
    "click here to verify",
    "verify your account",
    "account will be blocked",
    "account suspended",
    "login immediately",
    # Prize / lottery scams
    "you won",
    "you have won",
    "congratulations you",
    "prize money",
    "lottery winner",
    "lucky draw",
    "claim your prize",
    "claim reward",
    "kbc winner",
    "free iphone",
    "free gift",
    # Fake UPI collect / money request scams
    "upi collect request",
    "approve this request",
    "accept payment request",
    "send money to claim",
    "pay to receive",
    "deposit to unlock",
    "advance fee",
    # Urgency pressure tactics
    "urgent",
    "act now",
    "limited time",
    "immediately transfer",
    "transfer now",
    "do it now",
    "last chance",
    "account will be closed",
    "legal action",
    "arrest warrant",
    "cbi notice",
    # Remote access / impersonation
    "install anydesk",
    "install teamviewer",
    "screen share",
    "remote access",
    "allow access",
    # Investment scams
    "guaranteed returns",
    "guaranteed profit",
    "risk free returns",
    "double your money",
    "triple your investment",
    "100% returns",
    "fixed return",
    "daily profit",
    # Job scams
    "pay registration fee",
    "deposit to activate",
    "work from home earn",
]

# High-severity patterns (regex) — these alone trigger a strong warning
HIGH_SEVERITY_PATTERNS: list[str] = [
    r"\botp\b.{0,30}(share|send|give|enter|batao|dena)",
    r"(share|send|give).{0,20}\botp\b",
    r"(kyc).{0,30}(expire|block|suspend|update)",
    r"(click|tap).{0,20}(link|here).{0,30}(verify|confirm|login)",
    r"(you|you've|youve).{0,10}(won|win|winner)",
    r"(guaranteed|fixed|assured).{0,15}(return|profit|income)",
    r"(collect request|payment request).{0,30}(approve|accept|enter pin)",
    r"(arrest|cbi|police|court).{0,20}(notice|warrant|action|case)",
    r"(anydesk|teamviewer|screen.?share|remote.?access)",
    r"(advance fee|registration fee|deposit).{0,20}(job|work|earn|income)",
]

# ---------------------------------------------------------------------------
# Safety tips to return when fraud is detected
# ---------------------------------------------------------------------------
GENERAL_FRAUD_TIPS: list[str] = [
    "🔒 NEVER share your OTP, UPI PIN, ATM PIN, or CVV with anyone — not even bank officials.",
    "🚫 You only enter your UPI PIN to SEND money. You never need a PIN to RECEIVE money.",
    "📵 Hang up immediately on suspicious calls and call back on the bank's official number.",
    "🌐 Report cyber fraud: cybercrime.gov.in | Helpline: 1930",
    "🏦 Contact your bank immediately to block your account if you suspect fraud.",
    "❌ Legitimate lotteries, government schemes, and companies NEVER ask for upfront fees.",
    "📱 Never install apps suggested by unknown callers (AnyDesk, TeamViewer, etc.).",
    "✅ Always verify UPI collect requests — approve ONLY from known, trusted sources.",
]

OTP_TIPS: list[str] = [
    "🔴 CRITICAL: You are NEVER required to share your OTP with anyone.",
    "🔴 Anyone asking for your OTP is attempting FRAUD — end the call immediately.",
    "📞 Call your bank at their official number (on the back of your card) to report the incident.",
    "🌐 File a cyber complaint at cybercrime.gov.in or call 1930 right away.",
]

COLLECT_REQUEST_TIPS: list[str] = [
    "⚠️ UPI COLLECT REQUEST SCAM: Entering your PIN approves a PAYMENT FROM your account.",
    "🚫 You do NOT enter any PIN to receive money — this is always a fraud attempt.",
    "📵 Do not approve collect requests from unknown UPI IDs.",
    "🌐 Report to cybercrime.gov.in or call 1930.",
]

LOTTERY_TIPS: list[str] = [
    "🎰 Lottery / prize scams are extremely common in India.",
    "💸 Real prize claims NEVER require any upfront payment, processing fee, or GST payment.",
    "🗑️ Ignore and block the sender/caller.",
    "🌐 Report at cybercrime.gov.in or call 1930.",
]

KYC_TIPS: list[str] = [
    "🏦 Banks/telecom companies NEVER ask for OTP or PIN to update KYC over phone.",
    "🏢 Visit your bank branch or official website directly for any KYC updates.",
    "📵 Hang up and report the call to your bank's fraud helpline.",
    "🌐 File a complaint at cybercrime.gov.in.",
]


def _check_high_severity(text_lower: str) -> tuple[bool, str]:
    """
    Check text against high-severity regex patterns.

    Args:
        text_lower: Lowercase input text.

    Returns:
        Tuple of (is_high_severity: bool, matched_pattern: str).
    """
    for pattern in HIGH_SEVERITY_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, pattern
    return False, ""


def _select_tips(text_lower: str) -> list[str]:
    """
    Select the most contextually relevant set of tips based on what was detected.

    Args:
        text_lower: Lowercase input text.

    Returns:
        list[str]: A list of 3–4 targeted safety tips.
    """
    if re.search(r"\botp\b", text_lower):
        return OTP_TIPS[:4]
    if re.search(r"(collect request|payment request|upi.{0,20}request)", text_lower):
        return COLLECT_REQUEST_TIPS[:4]
    if re.search(r"(lottery|prize|won|winner|kbc|lucky draw)", text_lower):
        return LOTTERY_TIPS[:4]
    if re.search(r"(kyc)", text_lower):
        return KYC_TIPS[:4]
    # Default general tips
    return GENERAL_FRAUD_TIPS[:4]


def analyze_message(text: str) -> dict:
    """
    Analyze a message for potential fraud signals using keyword matching
    and regex pattern detection.

    Args:
        text: The message text to analyze (any language — detection is
              primarily keyword-based and works on transliterated text too).

    Returns:
        dict with keys:
            is_suspicious (bool):  True if fraud signals detected.
            warning (str):         Human-readable warning message.
            tips (list[str]):      List of 3–4 actionable safety tips.
            severity (str):        "high" | "medium" | "none"
            matched_keywords (list[str]): Keywords that triggered the alert.
    """
    if not text or not text.strip():
        return {
            "is_suspicious": False,
            "warning": "",
            "tips": [],
            "severity": "none",
            "matched_keywords": [],
        }

    text_lower = text.lower().strip()

    # Phase 1: Check high-severity regex patterns
    is_high_severity, matched_pattern = _check_high_severity(text_lower)

    # Phase 2: Keyword matching
    matched_keywords = [kw for kw in FRAUD_KEYWORDS if kw in text_lower]

    # Determine suspicion
    is_suspicious = is_high_severity or len(matched_keywords) >= 1

    if not is_suspicious:
        return {
            "is_suspicious": False,
            "warning": "",
            "tips": [],
            "severity": "none",
            "matched_keywords": [],
        }

    # Determine severity level
    if is_high_severity or len(matched_keywords) >= 3:
        severity = "high"
        warning = (
            "🚨 HIGH ALERT: This message contains strong indicators of a financial scam. "
            "Do NOT follow any instructions, share any personal details, or make any payments. "
            "This appears to be a fraud attempt."
        )
    else:
        severity = "medium"
        warning = (
            "⚠️ CAUTION: This message contains language commonly used in online scams. "
            "Please be careful and verify through official channels before taking any action."
        )

    tips = _select_tips(text_lower)

    logger.info(
        "Fraud analysis: severity=%s, keywords=%s",
        severity,
        matched_keywords[:5],
    )

    return {
        "is_suspicious": True,
        "warning": warning,
        "tips": tips,
        "severity": severity,
        "matched_keywords": matched_keywords[:10],  # Cap at 10 for response size
    }


def get_fraud_awareness_tip() -> str:
    """
    Return a random daily fraud awareness tip for display in the UI.

    Returns:
        str: A single fraud awareness tip.
    """
    import random
    return random.choice(GENERAL_FRAUD_TIPS)
