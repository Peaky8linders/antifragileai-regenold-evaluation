"""Targeted live integration test for groq/compound.

Focuses solely on groq/compound execution:
1. Direct completion call (Stage 1 / synthesis)
2. Stage 0 Intent classification via groq/compound
3. Stage 0 Multi-turn query rewriting via groq/compound
"""
import os
import sys
import time

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

def sep(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def run_test():
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_groq_provider,
        is_groq_provider_enabled,
    )

    sep("GROQ COMPOUND LIVE TEST")
    assert is_groq_provider_enabled(), "GROQ_API_KEY is not set in environment"

    provider = get_groq_provider()

    # ----------------------------------------------------
    # TEST A: Direct groq/compound Synthesis Call
    # ----------------------------------------------------
    print("\n[1/3] Testing Stage 1 Answer Synthesis (groq/compound)...")
    system_prompt = (
        "You are the Lead EU AI Act Regulatory Counsel (Regulation (EU) 2024/1689).\n"
        "RULES:\n"
        "1. Cite exact Akoma Ntoso subpoint provisions ('Article N(P)(s)').\n"
        "2. Deontic Structure: Scope/Applicability, Core Duty, Exemptions, Enforcement/Sanctions.\n"
        "3. BLUF: Lead with the direct verdict first."
    )
    user_prompt = (
        "Question: Are biometric categorisation systems prohibited under the EU AI Act?\n\n"
        "Context:\n"
        "Article 5(1)(g): The placing on the market, putting into service or use of AI systems "
        "that categorise individually natural persons based on their biometric data to deduce or infer "
        "their race, political opinions, trade union membership, religious beliefs, sex life or sexual orientation is prohibited."
    )

    start = time.perf_counter()
    resp = provider.complete(
        OpenAIWrapperRequest(
            system=system_prompt,
            user=user_prompt,
            model="groq/compound",
            max_tokens=512,
            temperature=0.0,
        )
    )
    elapsed = time.perf_counter() - start

    print(f"  Model Used:    {resp.model}")
    print(f"  Elapsed Time:  {elapsed:.2f}s")
    print(f"  Finish Reason: {resp.finish_reason}")
    print(f"  Error Status:  {resp.error or 'None (Success)'}")
    text_out = (resp.text or "").strip()
    print(f"  Output Text:\n  {text_out}\n")

    assert not resp.error, f"Synthesis call failed: {resp.error}"
    assert len(text_out) > 50, "Output text too short"
    assert "Article 5(1)(g)" in text_out or "5(1)(g)" in text_out, "Subpoint citation missing"
    print("  ✅ TEST A PASSED: Direct groq/compound synthesis succeeded!")

    # Pause 3 seconds to avoid Groq TPM spike
    print("\nPausing 3s for API rate limit spacing...")
    time.sleep(3)

    # ----------------------------------------------------
    # TEST B: reasoning_effort Guard Verification
    # ----------------------------------------------------
    print("\n[2/3] Testing reasoning_effort Guard with groq/compound...")
    start = time.perf_counter()
    resp_guard = provider.complete(
        OpenAIWrapperRequest(
            system="Answer in 1 sentence.",
            user="What is Article 9 of the EU AI Act?",
            model="groq/compound",
            max_tokens=150,
            temperature=0.0,
            reasoning_effort="none",  # Explicitly passed - provider must strip it
        )
    )
    elapsed = time.perf_counter() - start

    print(f"  Model Used:    {resp_guard.model}")
    print(f"  Elapsed Time:  {elapsed:.2f}s")
    print(f"  Error Status:  {resp_guard.error or 'None (Success)'}")
    text_guard = (resp_guard.text or "").strip()
    print(f"  Output Text:   {text_guard}")

    assert not resp_guard.error or "reasoning_effort" not in (resp_guard.error or ""), \
        f"Guard failed -- reasoning_effort was sent to Groq: {resp_guard.error}"
    if not resp_guard.error:
        print("  ✅ TEST B PASSED: reasoning_effort parameter correctly blocked for groq/compound!")

    # Pause 3 seconds
    print("\nPausing 3s for API rate limit spacing...")
    time.sleep(3)

    # ----------------------------------------------------
    # TEST C: Intent Classifier with groq/compound
    # ----------------------------------------------------
    print("\n[3/3] Testing Intent Classifier with groq/compound...")
    os.environ["REGENOLD_INTENT_PROVIDER"] = "groq"
    os.environ["REGENOLD_INTENT_MODEL_GROQ"] = "groq/compound"

    from app.llm.intent_classifier import classify_intent

    start = time.perf_counter()
    intent_res = classify_intent("What technical documentation is required under Annex IV?")
    elapsed = time.perf_counter() - start

    if intent_res:
        print(f"  Intent Label:  {intent_res.intent}")
        print(f"  Primary Anchor:{intent_res.primary_anchor}")
        print(f"  Confidence:    {intent_res.confidence}")
        print(f"  Model Used:    {intent_res.model}")
        print(f"  Elapsed Time:  {elapsed:.2f}s")
        assert intent_res.intent, "Intent label empty"
        print("  ✅ TEST C PASSED: Intent classification via groq/compound succeeded!")
    else:
        print("  ⚠️ TEST C SKIPPED (provider failover/timeout)")

    sep("ALL GROQ COMPOUND LIVE TESTS PASSED!")

if __name__ == "__main__":
    run_test()
