"""
granite_llm.py – IBM Granite LLM Integration via IBM watsonx.ai
================================================================
Provides a clean interface to call IBM Granite models through the
ibm-watsonx-ai SDK. Reads credentials from environment variables.
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------------------------
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL_ID = "ibm/granite-13b-chat-v2"
DEFAULT_WATSONX_URL = "https://us-south.ml.cloud.ibm.com"

# Generation parameters tuned for conversational financial Q&A
GENERATION_PARAMS = {
    "max_new_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50,
    "repetition_penalty": 1.1,
    "stop_sequences": ["Human:", "User:", "\n\n\n"],
}

# Module-level cached model instance
_model_instance = None


def _get_credentials() -> dict:
    """
    Retrieve IBM watsonx.ai credentials from environment variables.

    Required env vars:
        WATSONX_API_KEY    – IBM Cloud API key
        WATSONX_PROJECT_ID – watsonx.ai project ID

    Optional env vars:
        WATSONX_URL        – Service URL (default: https://us-south.ml.cloud.ibm.com)

    Returns:
        dict: Credentials dictionary for the watsonx.ai SDK.

    Raises:
        ValueError: If required credentials are not set.
    """
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    url = os.getenv("WATSONX_URL", DEFAULT_WATSONX_URL)

    if not api_key:
        raise ValueError(
            "WATSONX_API_KEY environment variable is not set. "
            "Please add it to your .env file."
        )
    if not project_id:
        raise ValueError(
            "WATSONX_PROJECT_ID environment variable is not set. "
            "Please add it to your .env file."
        )

    return {"url": url, "apikey": api_key}


def get_model():
    """
    Get the cached IBM Granite ModelInference instance.
    Initializes the model on first call and reuses it subsequently.

    Returns:
        ModelInference: Configured IBM Granite model instance.
    """
    global _model_instance

    if _model_instance is not None:
        return _model_instance

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        creds_dict = _get_credentials()
        project_id = os.getenv("WATSONX_PROJECT_ID")
        model_id = os.getenv("WATSONX_MODEL_ID", DEFAULT_MODEL_ID)

        credentials = Credentials(
            url=creds_dict["url"],
            api_key=creds_dict["apikey"],
        )

        params = {
            GenParams.MAX_NEW_TOKENS: GENERATION_PARAMS["max_new_tokens"],
            GenParams.TEMPERATURE: GENERATION_PARAMS["temperature"],
            GenParams.TOP_P: GENERATION_PARAMS["top_p"],
            GenParams.TOP_K: GENERATION_PARAMS["top_k"],
            GenParams.REPETITION_PENALTY: GENERATION_PARAMS["repetition_penalty"],
            GenParams.STOP_SEQUENCES: GENERATION_PARAMS["stop_sequences"],
        }

        _model_instance = ModelInference(
            model_id=model_id,
            credentials=credentials,
            project_id=project_id,
            params=params,
        )

        logger.info("IBM Granite model initialized: %s", model_id)
        return _model_instance

    except ImportError:
        raise ImportError(
            "ibm-watsonx-ai package is not installed. "
            "Run: pip install ibm-watsonx-ai"
        )
    except Exception as exc:
        logger.error("Failed to initialize IBM Granite model: %s", exc)
        raise


def build_prompt(user_message: str, context: str, conversation_history: list) -> str:
    """
    Build a structured prompt for IBM Granite that includes:
    - System instructions for a financial literacy assistant
    - Retrieved RAG context
    - Conversation history (last N turns)
    - Current user message

    Args:
        user_message:          The current user question (already in English).
        context:               Relevant context retrieved from the knowledge base.
        conversation_history:  List of {"role": "user"|"assistant", "content": str} dicts.

    Returns:
        str: The fully formatted prompt string.
    """
    system_prompt = (
        "You are FinLit AI, a helpful and trustworthy digital financial literacy assistant "
        "for Indian users. You provide clear, accurate, and practical guidance on topics like "
        "UPI payments, online scam prevention, budgeting, interest rates, credit scores, "
        "insurance, mutual funds, and tax saving in India.\n\n"
        "Guidelines:\n"
        "- Always give concise, actionable answers\n"
        "- Use Indian context (₹, RBI, NPCI, SEBI, CIBIL, EPF, PPF, etc.)\n"
        "- If the answer is in the provided context, use it; otherwise use your general knowledge\n"
        "- Never make up specific interest rates or regulatory figures without context\n"
        "- If a question involves financial fraud, always advise caution and report to cybercrime.gov.in\n"
        "- Be empathetic and never condescending\n"
    )

    # Format conversation history
    history_text = ""
    if conversation_history:
        history_lines = []
        for turn in conversation_history:
            role = "Human" if turn["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {turn['content']}")
        history_text = "\n".join(history_lines) + "\n"

    # Format context
    context_section = ""
    if context.strip():
        context_section = f"\n[Relevant Knowledge Base Information]\n{context}\n"

    prompt = (
        f"[SYSTEM]\n{system_prompt}\n"
        f"{context_section}"
        f"\n[CONVERSATION]\n{history_text}"
        f"Human: {user_message}\nAssistant:"
    )

    return prompt


def generate_response(
    prompt: str,
    fallback_context: Optional[str] = None,
) -> str:
    """
    Generate a response from IBM Granite for the given prompt.
    Falls back to a rule-based response if the LLM call fails.

    Args:
        prompt:           The fully formatted prompt string (from build_prompt).
        fallback_context: RAG context to use for rule-based fallback.

    Returns:
        str: The generated response text.
    """
    try:
        model = get_model()
        result = model.generate_text(prompt=prompt)

        if isinstance(result, dict):
            # Some SDK versions return a dict
            response_text = (
                result.get("results", [{}])[0].get("generated_text", "")
                or result.get("generated_text", "")
            )
        else:
            response_text = str(result)

        response_text = response_text.strip()

        if not response_text:
            logger.warning("Granite returned an empty response; using fallback")
            return _rule_based_fallback(fallback_context)

        logger.info("Granite response generated (%d chars)", len(response_text))
        return response_text

    except Exception as exc:
        logger.error("Granite LLM call failed: %s", exc)
        return _rule_based_fallback(fallback_context)


def _rule_based_fallback(context: Optional[str]) -> str:
    """
    Provide a helpful rule-based response when the LLM is unavailable.
    Uses the retrieved RAG context if available.

    Args:
        context: RAG-retrieved text to include in the fallback response.

    Returns:
        str: A structured fallback response.
    """
    if context and context.strip():
        # Extract and present the most relevant portion of context
        lines = [line.strip() for line in context.split("\n") if line.strip() and not line.startswith("[Source:")]
        relevant = "\n".join(lines[:15])  # First 15 non-empty lines
        return (
            "I found some relevant information from our knowledge base:\n\n"
            f"{relevant}\n\n"
            "⚠️ Note: The AI model is temporarily unavailable. "
            "The above is from our curated knowledge base. "
            "For personalized advice, please consult a certified financial advisor."
        )

    return (
        "I'm sorry, I'm having trouble connecting to the AI service right now. "
        "Please try again in a moment.\n\n"
        "For immediate help:\n"
        "• UPI fraud: Call 1930 (Cyber Crime Helpline)\n"
        "• Banking issues: Contact your bank's 24x7 helpline\n"
        "• File complaints: cybercrime.gov.in\n"
        "• RBI complaints: cms.rbi.org.in"
    )
