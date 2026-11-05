"""
main.py – FinLit AI FastAPI Backend
=====================================
Main entry point for the Digital Financial Literacy AI Agent backend.
Provides REST API endpoints for chat, budget calculation, EMI, and
interest rate explanation.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import uuid
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Local module imports
# ---------------------------------------------------------------------------
from rag_pipeline import retrieve_context
from granite_llm import build_prompt, generate_response
from translator import detect_language, translate_to_english, translate_from_english
from fraud_detector import analyze_message
from budget_calculator import calculate_budget, calculate_emi
from interest_explainer import explain_interest

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FinLit AI – Digital Financial Literacy Agent",
    description=(
        "An AI-powered RAG agent that helps Indian users understand digital "
        "financial tools, detect scams, calculate budgets, and learn about "
        "interest rates. Powered by IBM Granite via watsonx.ai."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS – allow all origins for development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory conversation history store
# Key: session_id (str)
# Value: list of {"role": "user"|"assistant", "content": str}
# ---------------------------------------------------------------------------
_conversation_store: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY_TURNS = 5  # Keep last 5 turns (10 messages) per session


# ===========================================================================
# Pydantic request/response models
# ===========================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    language: str = Field(default="en", description="Language code: en, hi, bn, ta, te, mr, gu, or 'auto'")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation history")


class ChatResponse(BaseModel):
    response: str
    fraud_warning: Optional[dict]
    sources_used: int
    language: str
    session_id: str


class BudgetRequest(BaseModel):
    monthly_income: float = Field(..., gt=0, description="Monthly take-home income in ₹")


class EMIRequest(BaseModel):
    principal: float = Field(..., gt=0, description="Loan principal amount in ₹")
    rate: float = Field(..., ge=0, description="Annual interest rate in %")
    tenure_months: int = Field(..., gt=0, description="Loan tenure in months")


class InterestRequest(BaseModel):
    loan_type: str = Field(..., description="Loan type: home, personal, education, car, gold")
    amount: float = Field(..., gt=0, description="Principal loan amount in ₹")
    rate: float = Field(..., ge=0, description="Annual interest rate in %")
    tenure_years: int = Field(..., gt=0, description="Loan tenure in full years")


# ===========================================================================
# Helper functions
# ===========================================================================

def _resolve_session_id(session_id: Optional[str]) -> str:
    """Return existing session_id or generate a new UUID."""
    return session_id if session_id else str(uuid.uuid4())


def _get_history(session_id: str) -> list[dict]:
    """Get last MAX_HISTORY_TURNS turns from conversation history."""
    history = _conversation_store[session_id]
    # Each turn = 1 user message + 1 assistant message = 2 entries
    return history[-(MAX_HISTORY_TURNS * 2):]


def _store_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """Append a conversation turn to the session history."""
    _conversation_store[session_id].extend([
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": assistant_msg},
    ])
    # Prevent unbounded growth: keep at most 20 messages per session
    if len(_conversation_store[session_id]) > 20:
        _conversation_store[session_id] = _conversation_store[session_id][-20:]


# ===========================================================================
# Endpoints
# ===========================================================================

@app.get("/health", summary="Health check")
def health_check() -> dict:
    """
    Health check endpoint. Returns service status and model name.
    """
    return {
        "status": "ok",
        "model": "ibm/granite-13b-chat-v2",
        "service": "FinLit AI",
        "version": "1.0.0",
    }


@app.post("/chat", response_model=ChatResponse, summary="Main chat endpoint")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main conversational chat endpoint.

    Flow:
    1. Resolve / generate session ID
    2. Detect language if set to 'auto'
    3. Translate message to English if needed
    4. Run fraud signal detection on the original message
    5. Retrieve relevant context from the RAG knowledge base
    6. Build structured prompt with context + conversation history
    7. Generate response via IBM Granite LLM (with rule-based fallback)
    8. Translate response back to the user's language
    9. Store the turn in session history
    10. Return response with fraud warning and metadata
    """
    session_id = _resolve_session_id(request.session_id)
    original_message = request.message.strip()

    logger.info("Chat request | session=%s | lang=%s | msg='%s…'",
                session_id, request.language, original_message[:60])

    # ------------------------------------------------------------------
    # Step 1 & 2: Language detection
    # ------------------------------------------------------------------
    if request.language == "auto":
        user_lang = detect_language(original_message)
        logger.info("Auto-detected language: %s", user_lang)
    else:
        user_lang = request.language

    # ------------------------------------------------------------------
    # Step 3: Translate to English for processing
    # ------------------------------------------------------------------
    english_message = translate_to_english(original_message, user_lang)

    # ------------------------------------------------------------------
    # Step 4: Fraud detection (on original message — catches transliterated scam text too)
    # ------------------------------------------------------------------
    fraud_result = analyze_message(original_message)
    fraud_warning = fraud_result if fraud_result["is_suspicious"] else None

    if fraud_warning:
        logger.warning(
            "Fraud signals detected | session=%s | severity=%s | keywords=%s",
            session_id,
            fraud_result.get("severity"),
            fraud_result.get("matched_keywords", [])[:5],
        )

    # ------------------------------------------------------------------
    # Step 5: RAG context retrieval
    # ------------------------------------------------------------------
    context = retrieve_context(english_message, k=4)
    sources_used = context.count("[Source:") if context else 0

    # ------------------------------------------------------------------
    # Step 6: Build prompt
    # ------------------------------------------------------------------
    history = _get_history(session_id)
    prompt = build_prompt(english_message, context, history)

    # ------------------------------------------------------------------
    # Step 7: Generate LLM response (with fallback)
    # ------------------------------------------------------------------
    english_response = generate_response(prompt, fallback_context=context)

    # ------------------------------------------------------------------
    # Step 8: Translate response back to user's language
    # ------------------------------------------------------------------
    final_response = translate_from_english(english_response, user_lang)

    # ------------------------------------------------------------------
    # Step 9: Store conversation turn (store English versions for history coherence)
    # ------------------------------------------------------------------
    _store_turn(session_id, english_message, english_response)

    logger.info(
        "Chat response | session=%s | lang=%s | sources=%d | fraud=%s",
        session_id,
        user_lang,
        sources_used,
        fraud_warning is not None,
    )

    return ChatResponse(
        response=final_response,
        fraud_warning=fraud_warning,
        sources_used=sources_used,
        language=user_lang,
        session_id=session_id,
    )


@app.post("/budget", summary="50/30/20 Budget Calculator")
async def budget(request: BudgetRequest) -> dict:
    """
    Calculate a 50/30/20 budget breakdown for the given monthly income.
    Returns needs, wants, and savings amounts with examples and tips.
    """
    try:
        result = calculate_budget(request.monthly_income)
        logger.info("Budget calculated for income ₹%s", request.monthly_income)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Budget calculation error: %s", exc)
        raise HTTPException(status_code=500, detail="Budget calculation failed.")


@app.post("/emi", summary="EMI Calculator")
async def emi(request: EMIRequest) -> dict:
    """
    Calculate the Equated Monthly Instalment (EMI) for a loan.
    Uses the standard reducing-balance EMI formula.
    """
    try:
        result = calculate_emi(request.principal, request.rate, request.tenure_months)
        logger.info(
            "EMI calculated | principal=₹%s | rate=%s%% | tenure=%sm",
            request.principal, request.rate, request.tenure_months,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("EMI calculation error: %s", exc)
        raise HTTPException(status_code=500, detail="EMI calculation failed.")


@app.post("/interest", summary="Interest Rate Explainer")
async def interest(request: InterestRequest) -> dict:
    """
    Explain interest calculations for a given loan scenario.
    Returns simple interest, compound interest, rate assessment,
    and RBI-informed guidance.
    """
    try:
        result = explain_interest(
            request.loan_type,
            request.amount,
            request.rate,
            request.tenure_years,
        )
        logger.info(
            "Interest explained | type=%s | amount=₹%s | rate=%s%%",
            request.loan_type, request.amount, request.rate,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Interest explanation error: %s", exc)
        raise HTTPException(status_code=500, detail="Interest calculation failed.")


@app.delete("/session/{session_id}", summary="Clear conversation history")
async def clear_session(session_id: str) -> dict:
    """
    Clear the conversation history for a given session ID.
    Useful when a user wants to start a fresh conversation.
    """
    if session_id in _conversation_store:
        del _conversation_store[session_id]
        logger.info("Cleared session history: %s", session_id)
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}


@app.get("/rebuild-index", summary="Rebuild RAG vector index")
async def rebuild_index() -> dict:
    """
    Force-rebuild the ChromaDB vector index from the knowledge base files.
    Use this after adding new documents to the knowledge_base/ directory.
    """
    from rag_pipeline import rebuild_index as _rebuild
    success = _rebuild()
    if success:
        return {"status": "rebuilt", "message": "Vector index rebuilt successfully."}
    raise HTTPException(status_code=500, detail="Index rebuild failed.")


# ---------------------------------------------------------------------------
# Startup event – pre-load the vector store
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Pre-load the RAG vector store on application startup so the first
    request does not incur the index-loading latency.
    """
    logger.info("FinLit AI starting up — pre-loading RAG vector store…")
    try:
        from rag_pipeline import get_vector_store
        get_vector_store()
        logger.info("RAG vector store loaded successfully.")
    except Exception as exc:
        logger.error("Failed to pre-load vector store: %s", exc)
        logger.warning("The /chat endpoint will attempt to load it on first request.")
