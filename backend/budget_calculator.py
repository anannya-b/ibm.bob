"""
budget_calculator.py – Personal Budget and EMI Calculator
==========================================================
Implements the 50/30/20 budgeting rule and the standard EMI formula
for loan calculations. India-focused with ₹ denominations.
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Budget Categories (50/30/20 Rule)
# ---------------------------------------------------------------------------

NEEDS_EXAMPLES = [
    "Rent / Home Loan EMI",
    "Groceries & household essentials",
    "Electricity, water & gas bills",
    "Mobile & internet bills",
    "Transport / commute (fuel, metro, bus)",
    "Health insurance premium",
    "School / tuition fees",
    "Minimum credit card / loan payments",
]

WANTS_EXAMPLES = [
    "Dining out & food delivery (Swiggy/Zomato)",
    "Entertainment (movies, OTT, events)",
    "Shopping (non-essential clothes & gadgets)",
    "Vacations & weekend trips",
    "Gym & fitness memberships",
    "Hobbies & leisure activities",
    "Gifts & celebrations",
]

SAVINGS_EXAMPLES = [
    "Emergency fund (3–6 months of expenses)",
    "EPF / PPF contributions",
    "SIP in mutual funds",
    "Fixed / Recurring Deposits",
    "Down payment savings (home / car)",
    "ELSS for tax saving under 80C",
    "NPS for retirement planning",
]


def calculate_budget(monthly_income: float) -> dict:
    """
    Apply the 50/30/20 budgeting rule to a given monthly income.

    Rule breakdown:
        50% – Needs: essential fixed and variable expenses
        30% – Wants: discretionary/lifestyle spending
        20% – Savings & Investments: emergency fund, SIP, EPF top-up

    Args:
        monthly_income: Gross monthly take-home income in ₹.

    Returns:
        dict with keys:
            monthly_income (float):   Input income
            needs (dict):             amount, percentage, examples
            wants (dict):             amount, percentage, examples
            savings (dict):           amount, percentage, examples
            summary (str):            Human-readable summary
            tips (list[str]):         Personalized budgeting tips

    Raises:
        ValueError: If monthly_income is not a positive number.
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be a positive number.")

    needs_pct = 0.50
    wants_pct = 0.30
    savings_pct = 0.20

    needs_amount = round(monthly_income * needs_pct, 2)
    wants_amount = round(monthly_income * wants_pct, 2)
    savings_amount = round(monthly_income * savings_pct, 2)

    # Generate tips based on income bracket
    tips = _generate_budget_tips(monthly_income, savings_amount)

    summary = (
        f"On a monthly income of ₹{monthly_income:,.0f}, the 50/30/20 rule recommends: "
        f"₹{needs_amount:,.0f} for needs, ₹{wants_amount:,.0f} for wants, "
        f"and ₹{savings_amount:,.0f} for savings & investments."
    )

    return {
        "monthly_income": monthly_income,
        "needs": {
            "amount": needs_amount,
            "percentage": 50,
            "label": "Needs (Essential Expenses)",
            "examples": NEEDS_EXAMPLES,
        },
        "wants": {
            "amount": wants_amount,
            "percentage": 30,
            "label": "Wants (Lifestyle & Discretionary)",
            "examples": WANTS_EXAMPLES,
        },
        "savings": {
            "amount": savings_amount,
            "percentage": 20,
            "label": "Savings & Investments",
            "examples": SAVINGS_EXAMPLES,
        },
        "summary": summary,
        "tips": tips,
    }


def _generate_budget_tips(income: float, savings_amount: float) -> list[str]:
    """
    Generate contextual budgeting tips based on income and savings amount.

    Args:
        income:         Monthly income in ₹.
        savings_amount: Calculated savings amount (20% of income).

    Returns:
        list[str]: 3–5 personalized tips.
    """
    tips = []

    # Emergency fund tip
    emergency_fund_target = income * 3  # 3 months of income as proxy
    months_to_emergency = math.ceil(emergency_fund_target / savings_amount) if savings_amount > 0 else 0
    tips.append(
        f"💰 Emergency Fund Goal: ₹{emergency_fund_target:,.0f} (3 months of income). "
        f"At ₹{savings_amount:,.0f}/month, you'll reach it in ~{months_to_emergency} months."
    )

    # SIP recommendation
    sip_amount = round(savings_amount * 0.5)  # 50% of savings into SIP
    tips.append(
        f"📈 Consider a SIP of ₹{sip_amount:,.0f}/month in an equity mutual fund. "
        f"At 12% CAGR, this grows to ₹{_future_value_sip(sip_amount, 12, 10):,.0f} in 10 years!"
    )

    # Tax saving tip
    annual_savings = savings_amount * 12
    if annual_savings >= 150000:
        tips.append(
            "🎯 You can max out your ₹1.5 lakh Section 80C limit. "
            "Use EPF + PPF/ELSS to save up to ₹46,800 in taxes annually."
        )
    else:
        remaining_80c = 150000 - annual_savings
        tips.append(
            f"📊 Invest ₹{min(annual_savings, 150000):,.0f}/year in ELSS or PPF "
            f"to claim Section 80C deductions and reduce your tax burden."
        )

    # Income-based additional tip
    if income < 30000:
        tips.append(
            "🏦 Open a PPF account at SBI/Post Office — minimum ₹500/year, "
            "earns 7.1% tax-free, and qualifies for 80C deductions."
        )
    elif income < 75000:
        tips.append(
            "🔄 Set up an auto-debit SIP on the 1st of every month "
            "(the day after salary credit) so savings happen before spending."
        )
    else:
        tips.append(
            "💼 At this income level, consider consulting a SEBI-registered investment advisor "
            "for a personalized financial plan including NPS, direct equity, and real estate."
        )

    return tips


def _future_value_sip(monthly_amount: float, annual_rate: float, years: int) -> float:
    """
    Calculate the future value of a Systematic Investment Plan (SIP).
    Formula: FV = P × [((1 + r)^n - 1) / r] × (1 + r)

    Args:
        monthly_amount: Monthly SIP amount in ₹.
        annual_rate:    Expected annual return rate (%).
        years:          Investment tenure in years.

    Returns:
        float: Future value in ₹.
    """
    r = (annual_rate / 100) / 12  # Monthly rate
    n = years * 12               # Total months
    if r == 0:
        return monthly_amount * n
    fv = monthly_amount * (((1 + r) ** n - 1) / r) * (1 + r)
    return round(fv, 2)


def calculate_emi(
    principal: float,
    rate: float,
    tenure_months: int,
) -> dict:
    """
    Calculate the Equated Monthly Instalment (EMI) for a loan.

    Formula: EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
        where P = principal, r = monthly interest rate, n = tenure in months

    Args:
        principal:      Loan principal amount in ₹.
        rate:           Annual interest rate in % (e.g., 8.5 for 8.5%).
        tenure_months:  Loan tenure in months.

    Returns:
        dict with keys:
            principal (float):       Input principal
            annual_rate (float):     Input annual rate
            tenure_months (int):     Input tenure
            tenure_years (float):    Tenure in years
            emi (float):             Monthly EMI amount
            total_payment (float):   Total amount paid over loan life
            total_interest (float):  Total interest paid
            interest_percentage (float): Interest as % of principal
            amortization_summary (str): Human-readable summary

    Raises:
        ValueError: If any input is invalid.
    """
    if principal <= 0:
        raise ValueError("Principal must be a positive number.")
    if rate < 0:
        raise ValueError("Interest rate cannot be negative.")
    if tenure_months <= 0:
        raise ValueError("Tenure must be a positive number of months.")

    # Handle zero interest (interest-free loans)
    if rate == 0:
        emi = round(principal / tenure_months, 2)
        return {
            "principal": principal,
            "annual_rate": rate,
            "tenure_months": tenure_months,
            "tenure_years": round(tenure_months / 12, 2),
            "emi": emi,
            "total_payment": round(emi * tenure_months, 2),
            "total_interest": 0.0,
            "interest_percentage": 0.0,
            "amortization_summary": (
                f"Zero-interest loan: EMI of ₹{emi:,.2f} for {tenure_months} months."
            ),
        }

    monthly_rate = rate / (12 * 100)  # Convert annual % to monthly decimal
    n = tenure_months

    # Standard EMI formula
    emi = principal * monthly_rate * ((1 + monthly_rate) ** n) / (((1 + monthly_rate) ** n) - 1)
    emi = round(emi, 2)

    total_payment = round(emi * n, 2)
    total_interest = round(total_payment - principal, 2)
    interest_pct = round((total_interest / principal) * 100, 2)

    summary = (
        f"For a loan of ₹{principal:,.0f} at {rate}% p.a. for "
        f"{tenure_months} months ({tenure_months // 12} years {tenure_months % 12} months): "
        f"EMI = ₹{emi:,.2f}, Total Interest = ₹{total_interest:,.2f}, "
        f"Total Payment = ₹{total_payment:,.2f}."
    )

    return {
        "principal": principal,
        "annual_rate": rate,
        "tenure_months": tenure_months,
        "tenure_years": round(tenure_months / 12, 2),
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "interest_percentage": interest_pct,
        "amortization_summary": summary,
    }
