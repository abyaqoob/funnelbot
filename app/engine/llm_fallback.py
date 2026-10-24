"""Pluggable LLM fallback provider interface.

Supports Groq and Gemini free-tiers. Default = 'none'.
If keys are missing, rates exceeded, or calls fail, smoothly falls back to rule-based logic. Never crashes.
"""
import logging
import os

logger = logging.getLogger("funnelbot.llm")


class LLMProvider:
    """Base interface for optional LLM fallback providers."""

    def generate_reply(self, prompt: str, context: str | None = None) -> str | None:
        """
        Generate conversational fallback response.
        Returns response string if successful, or None on failure/disabled.
        """
        raise NotImplementedError


class NoneLLMProvider(LLMProvider):
    """Default provider: disabled, zero API calls, 100% local rule-based."""

    def generate_reply(self, prompt: str, context: str | None = None) -> str | None:
        return None


class GroqLLMProvider(LLMProvider):
    """Groq API provider (free tier)."""

    def __init__(self, api_key: str | None = None, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", model)

    def generate_reply(self, prompt: str, context: str | None = None) -> str | None:
        if not self.api_key:
            return None

        try:
            import httpx

            system_content = (
                "You are an assistant for a social media creator. Answer concisely in under 2 sentences. "
                "If you cannot answer with high certainty, suggest asking for a human."
            )
            if context:
                system_content += f"\nContext:\n{context}"

            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150,
                },
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.warning("Groq API error (%s): %s", response.status_code, response.text)
                return None
        except Exception as exc:
            logger.warning("Groq fallback failed safely: %s", exc)
            return None


class GeminiLLMProvider(LLMProvider):
    """Google Gemini API provider (free tier)."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", model)

    def generate_reply(self, prompt: str, context: str | None = None) -> str | None:
        if not self.api_key:
            return None

        try:
            import httpx

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            system_instruction = (
                "You are an assistant for a social media creator. Answer concisely in under 2 sentences. "
                "If you cannot answer with high certainty, suggest asking for a human."
            )
            if context:
                system_instruction += f"\nContext:\n{context}"

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_instruction}\n\nUser Question: {prompt}"}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 150},
            }

            response = httpx.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                logger.warning("Gemini API error (%s): %s", response.status_code, response.text)
                return None
        except Exception as exc:
            logger.warning("Gemini fallback failed safely: %s", exc)
            return None


def get_llm_provider(provider_type: str | None = None) -> LLMProvider:
    """Factory to retrieve configured LLM provider with fallback to none."""
    prov = (provider_type or os.getenv("LLM_PROVIDER", "none")).lower().strip()
    if prov == "groq":
        return GroqLLMProvider()
    elif prov == "gemini":
        return GeminiLLMProvider()
    return NoneLLMProvider()
