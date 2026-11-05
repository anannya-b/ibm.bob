"""
interest_explainer.py – Loan Interest Rate Explainer
=====================================================
Calculates simple and compound interest for various loan types, flags
above-safe-range rates, and provides RBI-informed contextual guidance.
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RBI-informed safe rate ranges per loan type (min%, max%) as of 2024
# ---------------------------------------------------------------------------
SAFE_RATES: dict[str, tuple[float, float]] = {
    "home":       (8.5,  12.0),
    "personal":   (10.0, 24.0),
    "education":  (7.0,  15.0),
    "car":        (7.0,  12.0),
    "gold":       (7.5,  15.0),
}

# Descriptive info for each loan type
LOAN_TYPE_INFO: dict[str, dict] = {
    "home": {
        "name": "Home Loan",
        "typical_tenure": "15–30 years",
        "typical_rate_2024": "8.5% – 9.5% p.a. (leading banks)",
        "notes": [
            "Most home loans are floating rate, linked to the repo rate.",
            "Processing fee: 0.25% – 1% of loan amount.",
            "Tax benefit: Deduct up to ₹2 lakh interest under Section 24(b).",
            "Principal repayment qualifies for 80C deduction (up to ₹1.5 lakh).",
            "RBI mandates banks to switch you to a lower rate free of charge if you request it.",
        ],
    },
    "personal": {
        "name": "Personal Loan",
        "typical_tenure": "1–5 years",
        "typical_rate_2024": "10.5% – 24% p.a. (banks); up to 36% (NBFCs)",
        "notes": [
            "Unsecured loan — no collateral required.",
            "Higher CIBIL score (750+) gives significantly lower rates.",
            "Avoid personal loans with rates above 24% — explore gold loan or top-up home loan instead.",
            "Foreclosure charges: 0–4% of outstanding principal.",
            "Processing fee: 1% – 3% of loan amount.",
        ],
    },
    "education": {
        "name": "Education Loan",
        "typical_tenure": "5–15 years",
        "typical_rate_2024": "8.15% – 10.75% (PSU banks); government subsidy schemes available",
        "notes": [
            "Moratorium period: Course duration + 1 year (no EMI during study).",
            "Government CSIS scheme: Subsidizes interest for EWS students during moratorium.",
            "Interest paid is fully deductible under Section 80E (no upper limit).",
            "No collateral needed for loans up to ₹7.5 lakh (varies by bank).",
        ],
    },
    "car": {
        "name": "Car Loan",
        "typical_tenure": "1–7 years",
        "typical_rate_2024": "8.65% – 12% p.a.",
        "notes": [
            "Usually fixed rate for the entire tenure.",
            "Down payment typically 10–20% of vehicle cost.",
            "Prepayment penalty: 0–4% (check before signing).",
            "Electric vehicle loans often have lower rates (green incentives).",
        ],
    },
    "gold": {
        "name": "Gold Loan",
        "typical_tenure": "3 months – 3 years",
        "typical_rate_2024": "8.75% – 17% p.a.",
        "notes": [
            "Fastest disbursal — often within 30 minutes.",
            "LTV (Loan-to-Value) capped at 75% of gold value by RBI.",
            "No credit score check required in most cases.",
            "Default leads to gold auction by the lender.",
            "NBFCs like Muthoot and Manappuram charge higher rates than banks.",
        ],
    },
}


def explain_interest(
    loan_type: str,
    amount: float,
    rate: float,
    tenure_years: int,
) -> dict:
    """
    Explain interest calculations for a given loan scenario.
    Computes both simple interest and compound interest (annual compounding),
    provides a comparison, and flags above-safe-range rates.

    Args:
        loan_type:    Type of loan: "home" | "personal" | "education" | "car" | "gold"
        amount:       Principal loan amount in ₹.
        rate:         Annual interest rate in % (e.g., 9.5 for 9.5%).
        tenure_years: Loan tenure in full years.

    Returns:
        dict with keys:
            loan_type (str):                Normalised loan type
            loan_name (str):                Human-readable loan name
            principal (float):              Input principal
            annual_rate (float):            Input rate
            tenure_years (int):             Input tenure
            simple_interest (dict):         SI breakdown
            compound_interest (dict):       CI breakdown (annual compounding)
            rate_assessment (dict):         Safe/warning/danger + context
            loan_info (dict):               Typical rates, tenure, notes
            comparison_insight (str):       SI vs CI difference explanation
            recommendation (str):           Actionable advice

    Raises:
        ValueError: If loan_type is unrecognised or numeric inputs are invalid.
    """
    loan_type = loan_type.lower().strip()
    if loan_type not in SAFE_RATES:
        valid = ", ".join(SAFE_RATES.keys())
        raise ValueError(
            f"Unknown loan type '{loan_type}'. Valid types: {valid}"
        )
    if amount <= 0:
        raise ValueError("Loan amount must be a positive number.")
    if rate < 0:
        raise ValueError("Interest rate cannot be negative.")
    if tenure_years <= 0:
        raise ValueError("Tenure must be at least 1 year.")

    # --- Simple Interest ---
    si = round((amount * rate * tenure_years) / 100, 2)
    si_total = round(amount + si, 2)

    # --- Compound Interest (annual compounding) ---
    ci_total = round(amount * ((1 + rate / 100) ** tenure_years), 2)
    ci = round(ci_total - amount, 2)

    # --- Rate Assessment ---
    rate_assessment = _assess_rate(loan_type, rate)

    # --- Comparison insight ---
    difference = round(ci - si, 2)
    comparison_insight = (
        f"For ₹{amount:,.0f} at {rate}% for {tenure_years} years:\n"
        f"• Simple Interest: ₹{si:,.2f} (total repayment: ₹{si_total:,.2f})\n"
        f"• Compound Interest: ₹{ci:,.2f} (total repayment: ₹{ci_total:,.2f})\n"
        f"• Compound interest costs ₹{difference:,.2f} MORE than simple interest over {tenure_years} years.\n"
        f"Note: Most bank loans use monthly-reducing balance (closer to compound interest)."
    )

    # --- Recommendation ---
    recommendation = _build_recommendation(loan_type, rate, amount, rate_assessment["status"])

    loan_info = LOAN_TYPE_INFO[loan_type].copy()

    return {
        "loan_type": loan_type,
        "loan_name": loan_info["name"],
        "principal": amount,
        "annual_rate": rate,
        "tenure_years": tenure_years,
        "simple_interest": {
            "interest_amount": si,
            "total_repayment": si_total,
            "method": "SI = P × R × T / 100",
        },
        "compound_interest": {
            "interest_amount": ci,
            "total_repayment": ci_total,
            "method": "CI = P × (1 + R/100)^T − P (annual compounding)",
        },
        "rate_assessment": rate_assessment,
        "loan_info": loan_info,
        "comparison_insight": comparison_insight,
        "recommendation": recommendation,
    }


def _assess_rate(loan_type: str, rate: float) -> dict:
    """
    Assess whether the given rate is safe, borderline, or predatory
    based on RBI guidelines and market norms.

    Args:
        loan_type: Normalised loan type string.
        rate:      Annual interest rate in %.

    Returns:
        dict with keys: status ("safe"|"warning"|"danger"), message, safe_range.
    """
    min_rate, max_rate = SAFE_RATES[loan_type]
    loan_name = LOAN_TYPE_INFO[loan_type]["name"]

    if rate < min_rate:
        status = "warning"
        message = (
            f"⚠️ {rate}% is unusually LOW for a {loan_name}. "
            f"The typical safe range is {min_rate}%–{max_rate}% p.a. "
            f"Verify the offer carefully — check for hidden fees or balloon payments."
        )
    elif rate <= max_rate:
        status = "safe"
        message = (
            f"✅ {rate}% is within the safe range ({min_rate}%–{max_rate}%) "
            f"for a {loan_name} as per RBI guidelines and market norms."
        )
    elif rate <= max_rate * 1.25:
        status = "warning"
        message = (
            f"⚠️ {rate}% is above the typical range ({min_rate}%–{max_rate}%) "
            f"for a {loan_name}. Consider negotiating or comparing other lenders."
        )
    else:
        status = "danger"
        message = (
            f"🚨 {rate}% is SIGNIFICANTLY above the safe range ({min_rate}%–{max_rate}%) "
            f"for a {loan_name}. This may be a predatory rate. "
            f"Check if the lender is RBI-registered at rbi.org.in."
        )

    return {
        "status": status,
        "message": message,
        "safe_range": {"min": min_rate, "max": max_rate},
        "provided_rate": rate,
    }


def _build_recommendation(
    loan_type: str,
    rate: float,
    amount: float,
    status: str,
) -> str:
    """
    Build an actionable recommendation based on the loan scenario.

    Args:
        loan_type: Normalised loan type.
        rate:      Annual interest rate in %.
        amount:    Principal amount.
        status:    Rate assessment status.

    Returns:
        str: Recommendation text.
    """
    recs = []

    if status in ("warning", "danger"):
        recs.append(
            "🔍 Compare rates from at least 3 lenders before committing. "
            "Use BankBazaar or Paisabazaar for side-by-side comparisons."
        )

    if loan_type == "home":
        recs.append(
            "📉 A 1% lower rate on a ₹50L home loan over 20 years saves ~₹7–8 lakh in interest. "
            "Always negotiate with your bank using competing offers."
        )
        recs.append("📋 Ensure the lender follows RBI's fair practices code — charges must be disclosed upfront.")

    elif loan_type == "personal":
        if amount > 500000:
            recs.append(
                "💡 For loans above ₹5 lakh, consider a secured loan (gold/property-backed) "
                "which typically offers 3–5% lower rates than unsecured personal loans."
            )
        recs.append("📊 Pay your credit card bills in full and maintain CIBIL > 750 to get the best rates.")

    elif loan_type == "education":
        recs.append(
            "🎓 Check eligibility for PM Vidyalakshmi scheme and Central Sector Interest Subsidy "
            "if your family income is under ₹4.5 lakh/year."
        )

    elif loan_type == "car":
        recs.append(
            "🚗 Check manufacturer-backed low-rate offers (festive season deals often offer 0% or sub-8% loans)."
        )

    elif loan_type == "gold":
        recs.append(
            "🏦 Prefer bank gold loans over NBFCs — banks typically charge 3–8% less. "
            "SBI and HDFC offer some of the lowest gold loan rates."
        )

    recs.append(
        "📱 Use our EMI Calculator (/emi endpoint) to compute your exact monthly payment."
    )

    return " ".join(recs)


def get_current_rates_summary() -> dict:
    """
    Return a summary of typical current loan rates across all loan types.
    Useful for displaying a quick rates overview.

    Returns:
        dict: Mapping of loan type to rate info.
    """
    return {
        loan_type: {
            "name": info["name"],
            "typical_rate_2024": info["typical_rate_2024"],
            "safe_range": f"{SAFE_RATES[loan_type][0]}% – {SAFE_RATES[loan_type][1]}%",
        }
        for loan_type, info in LOAN_TYPE_INFO.items()
    }
