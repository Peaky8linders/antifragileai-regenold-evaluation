"""Article 50 Transparency Obligations risk rules."""

from __future__ import annotations


def is_transparency_inquiry(question: str) -> bool:
    """Detect if question relates to Article 50 transparency obligations (chatbots, deepfakes, etc.)."""
    q_low = question.lower()
    keywords = (
        "transparency", "article 50", "chatbot", "deepfake",
        "deep fake", "synthetic content", "ai-generated content", "watermark"
    )
    return any(kw in q_low for kw in keywords)

