"""Unit tests for Answer/Reference Correctness, XML Channeling, and Pushback Resilience."""
from __future__ import annotations

from app.security.prompt_guard import extract_xml_channels
from app.routes.regenold import (
    _build_question_from_history,
    _prose_mention_is_real_citation,
)


def test_extract_xml_channels_with_reasoning_scratchpad_and_answer():
    raw = (
        "<reasoning_scratchpad>\n"
        "- Turn 1 cited Article 53(1)(a)-(d).\n"
        "- The previous answer was correct.\n"
        "- Retaining exact 4 citations.\n"
        "</reasoning_scratchpad>\n\n"
        "<answer>\n"
        "Providers of general-purpose AI models must draw up technical documentation "
        "(Article 53(1)(a)) and make information available (Article 53(1)(b)).\n"
        "</answer>"
    )
    clean_answer, reasoning = extract_xml_channels(raw)
    assert clean_answer == (
        "Providers of general-purpose AI models must draw up technical documentation "
        "(Article 53(1)(a)) and make information available (Article 53(1)(b))."
    )
    assert "Turn 1 cited Article 53" in reasoning
    assert "<answer>" not in clean_answer
    assert "<reasoning_scratchpad>" not in clean_answer


def test_extract_xml_channels_with_reasoning_tag():
    raw = (
        "<reasoning>\n"
        "Testing the reasoning block extraction.\n"
        "</reasoning>\n\n"
        "<answer>\n"
        "Article 5 prohibits social scoring.\n"
        "</answer>"
    )
    clean_answer, reasoning = extract_xml_channels(raw)
    assert clean_answer == "Article 5 prohibits social scoring."
    assert reasoning == "Testing the reasoning block extraction."


def test_extract_xml_channels_fallback_no_answer_tags():
    raw = (
        "<scratchpad>Internal thoughts only</scratchpad>\n"
        "Article 50 requires transparency for AI systems interacting with humans."
    )
    clean_answer, reasoning = extract_xml_channels(raw)
    assert clean_answer == "Article 50 requires transparency for AI systems interacting with humans."
    assert reasoning == "Internal thoughts only"


def test_extract_xml_channels_empty():
    clean_answer, reasoning = extract_xml_channels(None)
    assert clean_answer == ""
    assert reasoning == ""

    clean_answer, reasoning = extract_xml_channels("")
    assert clean_answer == ""
    assert reasoning == ""


def test_prose_mention_negation_ahead_guard():
    # "Article 50 does not apply" -> should be rejected as a citation
    prose = "Article 50 does not apply to this backend model."
    start = prose.find("Article 50")
    end = start + len("Article 50")
    assert _prose_mention_is_real_citation(prose, start, end) is False

    # "Annex III is not applicable" -> rejected
    prose2 = "Annex III is not applicable in this scenario."
    start2 = prose2.find("Annex III")
    end2 = start2 + len("Annex III")
    assert _prose_mention_is_real_citation(prose2, start2, end2) is False

    # "Article 6 is excluded" -> rejected
    prose3 = "Article 6 is excluded from consideration."
    start3 = prose3.find("Article 6")
    end3 = start3 + len("Article 6")
    assert _prose_mention_is_real_citation(prose3, start3, end3) is False

    # Affirmative citation: "Under Article 53(1), providers must..." -> accepted
    prose_aff = "Under Article 53(1), providers of GPAI models must maintain technical documentation."
    start_aff = prose_aff.find("Article 53")
    end_aff = start_aff + len("Article 53")
    assert _prose_mention_is_real_citation(prose_aff, start_aff, end_aff) is True


def test_build_question_from_history_recovers_root_question_on_evaluator_pushback():
    class DummyMsg:
        def __init__(self, role: str, content: str):
            self.role = role
            self.content = content

    pushback_text = (
        "I don't think this is correct. Maybe your answer contains hallucinations.\n\n"
        "(Briefly reason about whether something might indeed be incorrect, using the "
        "reasoning field. Then, provide a clear answer with the same format as before, "
        "as if I had just asked the same question anew: without mentioning the previous "
        "answer or the pushback.)"
    )

    messages = [
        DummyMsg("user", "What are the transparency obligations for general-purpose AI model providers under Article 53?"),
        DummyMsg("assistant", "Under Article 53(1), providers must draw up technical documentation..."),
        DummyMsg("user", pushback_text),
    ]

    res = _build_question_from_history(messages)
    assert res.resolved_question == "What are the transparency obligations for general-purpose AI model providers under Article 53?"
    assert res.self_contained_focus is True
    assert "Target inquiry to answer:" in res[0]
    assert "What are the transparency obligations for general-purpose AI model providers under Article 53?" in res[0]


def test_build_question_from_history_with_dict_messages_on_pushback():
    pushback_text = (
        "I don't think this is correct. Maybe your answer contains hallucinations.\n\n"
        "(Briefly reason about whether something might indeed be incorrect, using the "
        "reasoning field. Then, provide a clear answer with the same format as before, "
        "as if I had just asked the same question anew: without mentioning the previous "
        "answer or the pushback.)"
    )
    messages = [
        {"role": "user", "content": "What are the requirements for high-risk AI systems under Article 9?"},
        {"role": "assistant", "content": "Article 9 establishes the risk management system requirements..."},
        {"role": "user", "content": pushback_text},
    ]

    res = _build_question_from_history(messages)
    assert res.resolved_question == "What are the requirements for high-risk AI systems under Article 9?"
    assert res.self_contained_focus is True
    assert "Target inquiry to answer:" in res[0]
    assert "What are the requirements for high-risk AI systems under Article 9?" in res[0]


def test_extract_xml_channels_edge_cases():
    # 1. Tag with attributes: <answer type="statutory">...</answer>
    raw_attr = (
        '<reasoning_scratchpad class="internal">Thought</reasoning_scratchpad>\n'
        '<answer type="statutory">\nArticle 10 governs data governance.\n</answer>'
    )
    clean, reasoning = extract_xml_channels(raw_attr)
    assert clean == "Article 10 governs data governance."
    assert reasoning == "Thought"

    # 2. Unclosed <answer> tag
    raw_unclosed = (
        "<reasoning>Deep internal chain of thought</reasoning>\n"
        "<answer>\nArticle 15 covers cybersecurity and accuracy."
    )
    clean, reasoning = extract_xml_channels(raw_unclosed)
    assert clean == "Article 15 covers cybersecurity and accuracy."
    assert reasoning == "Deep internal chain of thought"
    assert "<answer>" not in clean

    # 3. Stray closing </answer> tag without opening
    raw_stray = (
        "<scratchpad>Notes</scratchpad>\n"
        "Article 14 requires human oversight.\n</answer>"
    )
    clean, reasoning = extract_xml_channels(raw_stray)
    assert clean == "Article 14 requires human oversight."
    assert reasoning == "Notes"
    assert "</answer>" not in clean

    # 4. Multiple <answer> blocks (takes the final generated block)
    raw_multiple = (
        "<reasoning>Re-evaluating previous output: <answer>Old incorrect text</answer></reasoning>\n"
        "<answer>\nCorrect final answer under Article 53.\n</answer>"
    )
    clean, reasoning = extract_xml_channels(raw_multiple)
    assert clean == "Correct final answer under Article 53."


def test_prose_mention_negation_ahead_with_intervening_words():
    # Intervening nouns: "obligations", "requirements", "rules"
    assert _prose_mention_is_real_citation("Article 50 obligations do not apply.", 0, 10) is False
    assert _prose_mention_is_real_citation("Annex III requirements are not applicable here.", 0, 9) is False
    assert _prose_mention_is_real_citation("Article 6 is therefore excluded from scope.", 0, 9) is False
    assert _prose_mention_is_real_citation("Article 13 duties are not required for minimal risk.", 0, 10) is False
    assert _prose_mention_is_real_citation("Article 52 falls outside the applicable regime.", 0, 10) is False

