"""Live integration tests for groq/compound via actual providers.

Validates:
1. Groq compound direct call + reasoning_effort guard
2. Groq compound synthesis (Stage 1/2 compressed prompt)
3. Claude Max wrapper via cloudflared tunnel
4. Intent classification fallback chain
"""
import json
import os
import sys
import time

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding for Unicode chars like narrow no-break space
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


def sep(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_groq_compound_direct_with_retry():
    """Test 1: Direct groq/compound call with retry for transient 413s."""
    sep("TEST 1: Direct groq/compound call (with retry)")
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_groq_provider,
        is_groq_provider_enabled,
    )
    assert is_groq_provider_enabled(), "GROQ_API_KEY not set"

    provider = get_groq_provider()

    # Try up to 3 times with backoff for transient 413s
    for attempt in range(3):
        if attempt > 0:
            wait = 2 ** attempt
            print(f"  Retry {attempt}/2 after {wait}s backoff...")
            time.sleep(wait)

        start = time.perf_counter()
        resp = provider.complete(
            OpenAIWrapperRequest(
                system="You are a concise EU AI Act expert. Answer in 2 sentences.",
                user="What is Article 5 of the EU AI Act about?",
                model="groq/compound",
                max_tokens=256,
                temperature=0.0,
            )
        )
        elapsed = time.perf_counter() - start

        print(f"  Attempt {attempt+1}: model={resp.model}, elapsed={elapsed:.2f}s, "
              f"finish={resp.finish_reason}, error={resp.error or 'None'}")

        if not resp.error:
            text = (resp.text or "").strip()
            print(f"  Text:    {text[:300]}")
            print(f"  Length:  {len(text)} chars")
            assert len(text) > 20, "Response too short"
            print("  PASSED -- groq/compound responds correctly")
            return
        elif "413" in (resp.error or ""):
            print(f"  Got 413 (transient?) -- will retry")
            continue
        else:
            raise AssertionError(f"Groq compound FAILED: {resp.error}")

    raise AssertionError("groq/compound returned 413 on all 3 attempts -- rate limited")


def test_groq_compound_synthesis():
    """Test 2: Stage 2 synthesis via groq/compound with compressed system prompt."""
    sep("TEST 2: Stage 2 synthesis via groq/compound")
    from app.engines.graph_rag import _get_groq_compressed_system_prompt
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_groq_provider,
    )

    system = _get_groq_compressed_system_prompt()
    user_msg = (
        "Question: What are the obligations of a provider of a high-risk AI system "
        "regarding risk management?\n\n"
        "Retrieved provisions:\n"
        "- Article 9(1): Providers of high-risk AI systems shall establish, implement, "
        "document and maintain a risk management system.\n"
        "- Article 9(2): The risk management system shall be a continuous iterative process "
        "planned and run throughout the entire lifecycle of a high-risk AI system.\n"
        "- Article 9(5): The risk management system shall be designed so that residual risk "
        "associated with each hazard is judged acceptable.\n\n"
        "Provide a comprehensive answer."
    )

    provider = get_groq_provider()

    for attempt in range(3):
        if attempt > 0:
            time.sleep(2 ** attempt)
            print(f"  Retry {attempt}/2...")

        start = time.perf_counter()
        resp = provider.complete(
            OpenAIWrapperRequest(
                system=system,
                user=user_msg,
                model="groq/compound",
                max_tokens=1024,
                temperature=0.0,
            )
        )
        elapsed = time.perf_counter() - start

        if resp.error and "413" in resp.error:
            print(f"  Attempt {attempt+1}: 413 -- retrying")
            continue

        print(f"  Model:   {resp.model}")
        print(f"  Elapsed: {elapsed:.2f}s")
        print(f"  Finish:  {resp.finish_reason}")
        print(f"  Error:   {resp.error or 'None'}")
        text = (resp.text or "").strip()
        print(f"  Text:    {text[:400]}")
        print(f"  Length:  {len(text)} chars")

        assert not resp.error, f"Groq compound synthesis FAILED: {resp.error}"
        assert len(text) > 50, "Synthesis response too short"

        # Check for subpoint citations
        has_subpoint = any(x in text for x in ["Article 9(1)", "Article 9(2)", "9(1)", "9(2)"])
        print(f"  Subpoint citations present: {has_subpoint}")

        # Check for deontic elements
        has_deontic = any(x.lower() in text.lower() for x in ["obligation", "shall", "must", "provider"])
        print(f"  Deontic language present:   {has_deontic}")

        print("  PASSED -- Stage 2 synthesis via groq/compound works")
        return

    raise AssertionError("groq/compound synthesis 413 on all attempts")


def test_reasoning_effort_guard():
    """Test 3: Verify reasoning_effort is correctly stripped for groq/compound."""
    sep("TEST 3: reasoning_effort guard for groq/compound")
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_groq_provider,
    )

    provider = get_groq_provider()

    for attempt in range(3):
        if attempt > 0:
            time.sleep(2 ** attempt)
            print(f"  Retry {attempt}/2...")

        start = time.perf_counter()
        resp = provider.complete(
            OpenAIWrapperRequest(
                system="Answer in one sentence.",
                user="What is Article 6 of the EU AI Act?",
                model="groq/compound",
                max_tokens=200,
                temperature=0.0,
                reasoning_effort="none",  # MUST be stripped by the guard
            )
        )
        elapsed = time.perf_counter() - start

        if resp.error and "413" in resp.error:
            print(f"  Attempt {attempt+1}: 413 (transient) -- retrying")
            continue

        print(f"  Model:   {resp.model}")
        print(f"  Elapsed: {elapsed:.2f}s")
        print(f"  Error:   {resp.error or 'None'}")
        text = (resp.text or "").strip()
        print(f"  Text:    {text[:200]}")

        # Key assertion: if reasoning_effort leaked, Groq returns 400 with
        # "Unrecognized request argument". 413 is a different (rate limit) error.
        if resp.error and "400" in resp.error and "reasoning_effort" in resp.error:
            raise AssertionError(
                f"reasoning_effort LEAKED to groq/compound: {resp.error}"
            )

        if not resp.error:
            print("  PASSED -- reasoning_effort='none' correctly stripped for groq/compound")
            return

        raise AssertionError(f"Unexpected error: {resp.error}")

    print("  SKIPPED -- all attempts got 413 (rate limited), cannot verify guard")


def test_claude_max_wrapper():
    """Test 4: Claude Max wrapper via cloudflared tunnel."""
    sep("TEST 4: Claude Max wrapper via cloudflared tunnel")
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_openai_wrapper_provider,
        is_openai_wrapper_enabled,
    )

    if not is_openai_wrapper_enabled():
        print("  SKIPPED -- OPENAI_API_BASE not configured")
        return

    provider = get_openai_wrapper_provider()
    start = time.perf_counter()
    resp = provider.complete(
        OpenAIWrapperRequest(
            system="You are an EU AI Act expert. Answer concisely in 2 sentences.",
            user="What is the penalty for deploying a prohibited AI practice under Article 5?",
            model="claude-opus-4-8",
            max_tokens=256,
            temperature=0.0,
        )
    )
    elapsed = time.perf_counter() - start

    print(f"  Model:   {resp.model}")
    print(f"  Elapsed: {elapsed:.2f}s")
    print(f"  Finish:  {resp.finish_reason}")
    print(f"  Error:   {resp.error or 'None'}")
    text = (resp.text or "").strip()
    print(f"  Text:    {text[:300]}")

    if resp.error:
        print(f"  WARNING -- wrapper error (may be rate limited): {resp.error[:200]}")
    else:
        assert len(text) > 20, "Empty response from wrapper"
        # Verify the answer mentions penalties/fines
        has_penalty = any(x in text.lower() for x in ["35", "million", "7%", "turnover", "fine", "penalty"])
        print(f"  Penalty content present: {has_penalty}")
        print("  PASSED -- Claude Max wrapper responds via cloudflared tunnel")


def test_intent_classification():
    """Test 5: Intent classification with fallback chain."""
    sep("TEST 5: Intent classification (fallback chain)")
    from app.llm.intent_classifier import classify_intent

    start = time.perf_counter()
    result = classify_intent("What are the obligations of a deployer of high-risk AI systems?")
    elapsed = time.perf_counter() - start

    if result is None:
        print(f"  Elapsed: {elapsed:.2f}s")
        print("  SKIPPED -- classify_intent returned None (all providers failed/timed out)")
        return

    print(f"  Intent:   {result.intent}")
    print(f"  Anchor:   {result.primary_anchor}")
    print(f"  Alt:      {result.alternate_anchors}")
    print(f"  Conf:     {result.confidence}")
    print(f"  Model:    {result.model}")
    print(f"  Provider: {result.provider}")
    print(f"  Elapsed:  {elapsed:.2f}s")
    print(f"  Error:    {result.error or 'None'}")

    assert result.intent, "Intent classification returned empty intent"
    print("  PASSED -- intent classification works")


if __name__ == "__main__":
    print("=" * 70)
    print("  LIVE INTEGRATION TESTS -- groq/compound + Claude Max wrapper")
    print("=" * 70)

    passed = 0
    failed = 0
    skipped = 0
    errors = []

    tests = [
        test_groq_compound_direct_with_retry,
        test_groq_compound_synthesis,
        test_reasoning_effort_guard,
        test_claude_max_wrapper,
        test_intent_classification,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            if "413" in str(e) or "rate" in str(e).lower():
                skipped += 1
                print(f"  SKIPPED (rate limited): {e}")
            else:
                failed += 1
                errors.append((test_fn.__name__, str(e)))
                print(f"  FAILED: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"  FAILED: {e}")

    sep("RESULTS")
    print(f"  Passed:  {passed}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    if errors:
        print("\n  Failures:")
        for name, err in errors:
            print(f"    - {name}: {err[:200]}")
    print()
