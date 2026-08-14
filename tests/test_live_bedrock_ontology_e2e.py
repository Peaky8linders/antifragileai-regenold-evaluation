"""Live End-to-End Statutory QA and Adversarial Evaluation on AWS Bedrock.

Tests Claude Opus 4.6 (eu.anthropic.claude-opus-4-6-v1) and
Claude Sonnet 4.6 (eu.anthropic.claude-sonnet-4-6) live via the Bedrock Converse API
across six complex EU AI Act regulatory scenarios:
  * Scenario A: Prohibited AI (Art. 5(1)(e) untargeted facial scraping vs Art. 5(1)(f) emotion recognition in workplace).
  * Scenario B: Annex III High-Risk recruitment bias (Art. 10 data governance + Art. 14 human oversight + ISO 23894 control).
  * Scenario C: Clinical patient triage distribution drift (Art. 9 risk management + Art. 72 post-market monitoring).
  * Scenario D: GPAI Frontier Model with Systemic Risk (>= 10^25 FLOPs, Art. 55) vs Open-Source Carve-Out (Art. 53(2)).
  * Scenario E: Biometric Conformity Assessment Route (Annex VI internal control vs Annex VII notified body).
  * Scenario F: FRIA 6-Step Workflow (Art. 27) and Serious Incident 72h reporting deadline SLA (Art. 73).

Evaluates model grounding, exact provision citations, latency, input/output token usage,
and strict conformance with the typed ontology and `validate_legal_triple`.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time
from typing import Any

import pytest

# ⚠ NOTHING MAY MUTATE os.environ AT MODULE SCOPE IN THIS FILE.
#
# This module previously ran, at import (i.e. pytest COLLECTION) time:
#     os.environ["REGENOLD_TEST_ALLOW_LIVE"] = "1"
#     load_dotenv(override=True)
#
# `tests/conftest.py` neutralises NEO4J_URI / NEO4J_PASSWORD / GROQ_API_KEY /
# COHERE_API_KEY / GEMINI_API_KEY / MISTRAL_API_KEY / P2P_GRAPH_RAG_API_KEY so
# that no unit test is decided by a real credential — and it honours
# REGENOLD_TEST_ALLOW_LIVE=1 as an escape hatch. Setting that hatch at module
# scope therefore disarmed the safety net for the ENTIRE pytest session, and
# `load_dotenv(override=True)` then re-injected the live values. Measured by
# importing conftest then this module in sequence:
#     after conftest : NEO4J_URI=''            GROQ=False  P2P_KEY=False
#     after this file: NEO4J_URI='neo4j+s://0644b854…'  GROQ=True   P2P_KEY=True
# `0644b854` is the SHARED production Aura instance.
#
# Collection-time os.environ mutations are NOT reverted by monkeypatch, so every
# module collected after this one ran against live Aura, live Groq and the live
# wrapper tunnel. CLAUDE.md already records what that costs: the same commit
# measured 63 vs 92 failures depending only on GROQ_API_KEY. And it pointed the
# test process at the production graph while this same working tree bumped
# SEED_VERSION — hard rule #12 territory.
#
# The live env is now built INSIDE the fixture below, per-test, and the whole
# module is skipped unless the operator opts in for that invocation.
pytestmark = pytest.mark.skipif(
    os.getenv("REGENOLD_LIVE_E2E", "").strip().lower() not in {"1", "true", "yes", "on"},
    reason=(
        "live Bedrock/Aura e2e — set REGENOLD_LIVE_E2E=1 to run. Kept out of the "
        "default suite: it needs real credentials, real network and real spend, "
        "and it must never decide a deterministic gate."
    ),
)

# Reconfigure stdout for utf-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.data.ontology import (
    ANNEX_III_REGISTRY,
    CONFORMITY_ROUTE_REGISTRY,
    FRIA_REGISTRY,
    GPAI_REGISTRY,
    PRACTICE_REGISTRY,
    RISK_CONTROL_REGISTRY,
    RISK_SCENARIO_REGISTRY,
    SERIOUS_INCIDENT_REGISTRY,
    ActorRole,
    ConformityRoute,
    RiskClass,
    resolve_conformity_path,
    validate_legal_triple,
)
from app.llm.bedrock_client import (
    BedrockProvider,
    BedrockRequest,
    BedrockResponse,
    check_connectivity_and_permissions,
    is_bedrock_provider_enabled,
    resolve_bedrock_model,
)

logger = logging.getLogger(__name__)

# Test targets
TARGET_MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
]

# Track live metrics across session
SESSION_RESULTS: list[dict[str, Any]] = []


@pytest.fixture(autouse=True, scope="module")
def _ensure_live_bedrock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load the live credentials for THIS TEST ONLY, then hand them back.

    ``monkeypatch`` is what makes this safe: every var set here is reverted when
    the test ends, so a live run cannot leak credentials into the modules pytest
    collects afterwards. The previous version did this at module scope with a
    bare ``os.environ[...] = ...`` + ``load_dotenv(override=True)``, which is
    NOT reverted by anything and contaminated the whole session.

    ``override=False`` (the default) is also deliberate: it fills in values
    conftest blanked without stomping anything the operator set explicitly for
    this invocation.
    """
    from dotenv import dotenv_values  # noqa: PLC0415

    monkeypatch.setenv("REGENOLD_TEST_ALLOW_LIVE", "1")
    for key, value in (dotenv_values() or {}).items():
        if value is not None and not os.environ.get(key, "").strip():
            monkeypatch.setenv(key, value)
    if not is_bedrock_provider_enabled():
        pytest.skip("AWS Bedrock credentials not found in environment — skipping live e2e tests.")


def _invoke_and_record(
    provider: BedrockProvider,
    prompt: str,
    system: str,
    model: str,
    scenario_name: str,
    max_tokens: int = 2048,
) -> BedrockResponse:
    """Helper to invoke Bedrock, record live telemetry, and print formatted diagnostics."""
    t0 = time.monotonic()
    req = BedrockRequest(
        user=prompt,
        system=system,
        model=model,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    resp = provider.complete(req)
    wall_ms = int((time.monotonic() - t0) * 1000)

    record = {
        "scenario": scenario_name,
        "model_requested": model,
        "model_resolved": resp.model,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "elapsed_ms": resp.elapsed_ms,
        "wall_ms": wall_ms,
        "finish_reason": resp.finish_reason,
        "has_error": bool(resp.error),
        "error": resp.error,
        "text_preview": resp.text[:200] if resp.text else "",
    }
    SESSION_RESULTS.append(record)

    print(f"\n{'=' * 70}")
    print(f"[{scenario_name}] Model: {model} -> {resp.model}")
    print(f"Tokens: {resp.input_tokens} in / {resp.output_tokens} out | Bedrock API: {resp.elapsed_ms}ms (Wall: {wall_ms}ms) | Finish: {resp.finish_reason}")
    print(f"{'-' * 70}")
    if resp.error:
        print(f"ERROR: {resp.error}")
    else:
        print(f"Response Preview:\n{resp.text[:350]}...\n")

    return resp


class TestLiveBedrockModelCatalogAndAliases:
    """Verify alias mapping and live connectivity of Claude Opus 4.6 and Sonnet 4.6."""

    def test_alias_resolution(self) -> None:
        opus_resolved = resolve_bedrock_model("claude-opus-4-6")
        assert opus_resolved == "eu.anthropic.claude-opus-4-6-v1", (
            f"Expected 'eu.anthropic.claude-opus-4-6-v1', got {opus_resolved!r}"
        )

        sonnet_resolved = resolve_bedrock_model("claude-sonnet-4-6")
        assert sonnet_resolved == "eu.anthropic.claude-sonnet-4-6", (
            f"Expected 'eu.anthropic.claude-sonnet-4-6', got {sonnet_resolved!r}"
        )

    def test_live_connectivity_opus_4_6(self) -> None:
        probe = check_connectivity_and_permissions(model_id="eu.anthropic.claude-opus-4-6-v1")
        assert probe.get("status") == "ok", f"Opus 4.6 connectivity probe failed: {probe}"
        assert probe.get("model") == "eu.anthropic.claude-opus-4-6-v1"
        assert probe.get("output_tokens", 0) > 0

    def test_live_connectivity_sonnet_4_6(self) -> None:
        probe = check_connectivity_and_permissions(model_id="eu.anthropic.claude-sonnet-4-6")
        assert probe.get("status") == "ok", f"Sonnet 4.6 connectivity probe failed: {probe}"
        assert probe.get("model") == "eu.anthropic.claude-sonnet-4-6"
        assert probe.get("output_tokens", 0) > 0


class TestLiveBedrockRegulatoryScenarios:
    """End-to-End statutory QA & ontology grounding validation across 6 rich regulatory scenarios."""

    SYSTEM_PROMPT = (
        "You are an authoritative EU AI Act legal compliance expert and statutory reasoning engine. "
        "Provide direct, structured, and precise statutory citations (e.g. Art. 5(1)(e), Art. 5(1)(f), "
        "Art. 9, Art. 10, Art. 14, Art. 27, Art. 43, Art. 51(2), Art. 53(2), Art. 55, Art. 72, Art. 73, "
        "Annex III, Annex VI, Annex VII). Answer each point directly, thoroughly, and concisely."
    )

    @pytest.mark.parametrize("model", TARGET_MODELS)
    def test_scenario_a_prohibited_ai(self, model: str) -> None:
        """Scenario A: Prohibited AI (Art. 5(1)(e) untargeted facial scraping vs Art. 5(1)(f) emotion recognition)."""
        prompt = (
            "Analyze the following two AI use cases under Article 5 (Prohibited AI Practices) of the EU AI Act:\n"
            "1. Untargeted scraping of facial images from the internet or CCTV footage to create/expand facial recognition databases.\n"
            "2. Emotion recognition of natural persons in workplace or educational institutions.\n\n"
            "For each use case:\n"
            "a) State the exact prohibition provision under Article 5(1) (specify sub-paragraph e or f).\n"
            "b) Detail any statutory exceptions (medical/safety carve-outs) or clarify if the prohibition is absolute.\n"
            "c) For emotion recognition, explain the regulatory status (Annex III(1)(c) high-risk / Art. 50(3) transparency) if deployed outside workplace/education."
        )

        provider = BedrockProvider()
        resp = _invoke_and_record(provider, prompt, self.SYSTEM_PROMPT, model, "Scenario A: Prohibited AI", max_tokens=2048)

        assert not resp.error, f"Bedrock error: {resp.error}"
        text = resp.text

        # Statutory citation checks
        assert re.search(r"5\s*\(\s*1\s*\)\s*\(\s*e\s*\)", text, re.IGNORECASE) or "5(1)(e)" in text or "5.1.e" in text, (
            "Model failed to cite Art. 5(1)(e) for untargeted facial scraping"
        )
        assert re.search(r"5\s*\(\s*1\s*\)\s*\(\s*f\s*\)", text, re.IGNORECASE) or "5(1)(f)" in text or "5.1.f" in text, (
            "Model failed to cite Art. 5(1)(f) for emotion recognition in workplace"
        )
        assert any(term in text.lower() for term in ["prohibit", "unacceptable", "banned"]), (
            "Model failed to classify practices as prohibited"
        )
        assert any(term in text.lower() for term in ["medical", "safety"]), (
            "Model failed to mention medical or safety exceptions for emotion recognition"
        )
        assert "annex iii" in text.lower() or "high-risk" in text.lower() or "high risk" in text.lower(), (
            "Model failed to note that outside workplace/education emotion recognition is high-risk under Annex III"
        )

        # Ontology validation
        practice_e = PRACTICE_REGISTRY["facial_recognition_database"]
        practice_f = PRACTICE_REGISTRY["emotion_recognition_workplace"]
        assert practice_e.sub_paragraph == "5.1.e"
        assert practice_f.sub_paragraph == "5.1.f"
        assert validate_legal_triple("Art. 5", ActorRole.PROVIDER, RiskClass.PROHIBITED)
        assert validate_legal_triple("Art. 5", ActorRole.DEPLOYER, RiskClass.PROHIBITED)

    @pytest.mark.parametrize("model", TARGET_MODELS)
    def test_scenario_b_annex_iii_recruitment_bias(self, model: str) -> None:
        """Scenario B: Annex III High-Risk recruitment bias (Art. 10 data governance + Art. 14 human oversight + ISO 23894)."""
        prompt = (
            "A provider deploys an AI system for automated CV screening and candidate ranking (Annex III(4)(a)). "
            "An internal audit detects sampling bias and historical demographic disparity in the training data.\n\n"
            "Explain:\n"
            "1. The statutory risk classification under Annex III Point 4(a) (Employment & worker management).\n"
            "2. The mandatory data governance requirements under Article 10 (bias detection, dataset representativeness, and mitigation).\n"
            "3. The human oversight requirements under Article 14 (prevention of automation bias, intervention, and override capability).\n"
            "4. The corresponding technical risk controls aligned with ISO/IEC 23894 or demographic parity regularization."
        )

        provider = BedrockProvider()
        resp = _invoke_and_record(provider, prompt, self.SYSTEM_PROMPT, model, "Scenario B: Recruitment Bias", max_tokens=2048)

        assert not resp.error, f"Bedrock error: {resp.error}"
        text = resp.text

        # Statutory citation checks
        assert "annex iii" in text.lower() and ("4" in text or "recruitment" in text.lower() or "employment" in text.lower())
        assert "art" in text.lower() and "10" in text, "Model failed to cite Art. 10 data governance"
        assert "art" in text.lower() and "14" in text, "Model failed to cite Art. 14 human oversight"
        assert any(term in text.lower() for term in ["governance", "bias", "representative", "mitigat"]), (
            "Model failed to articulate data governance and bias mitigation requirements"
        )
        assert any(term in text.lower() for term in ["override", "automation bias", "human oversight", "intervention", "human-in-the-loop"]), (
            "Model failed to articulate human oversight requirements"
        )

        # Ontology validation
        scenario = RISK_SCENARIO_REGISTRY["sampling_bias_recruitment"]
        assert "Art. 10" in scenario.statutory_violation
        assert "Annex III" in scenario.statutory_violation
        assert "demographic_parity_regularization" in scenario.required_controls
        assert "counterfactual_fairness_audit" in scenario.required_controls

        control_dp = RISK_CONTROL_REGISTRY["demographic_parity_regularization"]
        assert "ISO/IEC 23894:2023 §8.2" in control_dp.standards_ref

        assert validate_legal_triple("Art. 10", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 14", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 15", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 26", ActorRole.DEPLOYER, RiskClass.HIGH_RISK_ANNEX_III)

    @pytest.mark.parametrize("model", TARGET_MODELS)
    def test_scenario_c_clinical_triage_distribution_drift(self, model: str) -> None:
        """Scenario C: Clinical patient triage distribution drift (Art. 9 risk management + Art. 72 post-market monitoring)."""
        prompt = (
            "An emergency medical department operates an AI system for clinical patient prioritization and emergency triage (Annex III(5)(d)). "
            "Post-deployment covariate shift in incoming patient demographics leads to distribution drift and urgency misclassifications.\n\n"
            "Detail the provider's statutory obligations under:\n"
            "1. Article 9 (Continuous risk management system throughout lifecycle, testing against operational drift).\n"
            "2. Article 72 (Post-market monitoring system, continuous telemetry, and corrective action plans).\n"
            "3. Article 14 (Human oversight and clinician override protocols).\n"
            "4. Article 17 (Quality Management System updates)."
        )

        provider = BedrockProvider()
        resp = _invoke_and_record(provider, prompt, self.SYSTEM_PROMPT, model, "Scenario C: Clinical Triage Drift", max_tokens=2048)

        assert not resp.error, f"Bedrock error: {resp.error}"
        text = resp.text

        # Statutory citation checks
        assert "9" in text and "art" in text.lower(), "Model failed to cite Art. 9 risk management"
        assert "72" in text and "art" in text.lower(), "Model failed to cite Art. 72 post-market monitoring"
        assert "14" in text and "art" in text.lower(), "Model failed to cite Art. 14 human oversight"
        assert any(term in text.lower() for term in ["annex iii", "5(d)", "essential services", "triage", "emergency"]), (
            "Model failed to anchor triage system in Annex III"
        )
        assert any(term in text.lower() for term in ["post-market", "telemetry", "drift", "corrective", "monitor"]), (
            "Model failed to address post-market monitoring requirements"
        )

        # Ontology validation
        scenario = RISK_SCENARIO_REGISTRY["unmonitored_drift_clinical_triage"]
        assert "Art. 9" in scenario.statutory_violation
        assert "Art. 72" in scenario.statutory_violation
        assert "Art. 14" in scenario.statutory_violation
        assert "runtime_drift_telemetry_monitoring" in scenario.required_controls
        assert "human_in_the_loop_override_gate" in scenario.required_controls

        assert validate_legal_triple("Art. 9", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 72", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 17", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)

    @pytest.mark.parametrize("model", TARGET_MODELS)
    def test_scenario_d_gpai_frontier_vs_opensource_carveout(self, model: str) -> None:
        """Scenario D: GPAI Frontier Model with Systemic Risk (>= 10^25 FLOPs, Art. 55) vs Open-Source Carve-Out (Art. 53(2))."""
        prompt = (
            "Provide a concise, direct statutory comparison of governance obligations for two General-Purpose AI (GPAI) model providers under Articles 51–55 of the EU AI Act:\n"
            "1. Model Alpha: A proprietary frontier multimodal foundation model trained with cumulative compute >= 10^25 FLOPs. "
            "Detail why Model Alpha triggers systemic risk under Article 51(2) and list the Article 55 obligations "
            "(model evaluations, adversarial red-teaming, incident reporting to AI Office, cybersecurity, Annex XIII energy doc).\n"
            "2. Model Beta: An open-source GPAI model released under a free and open license with public weights, trained with compute below 10^25 FLOPs. "
            "Detail the Article 53(2) open-source carve-out: what obligations Model Beta is exempt from (Annex XI technical doc, Annex XII downstream info), "
            "and what obligations Model Beta still must fulfill (Article 53(1)(c) copyright policy and Article 53(1)(d) training data summary)."
        )

        provider = BedrockProvider()
        resp = _invoke_and_record(provider, prompt, self.SYSTEM_PROMPT, model, "Scenario D: GPAI Frontier vs Open-Source", max_tokens=2048)

        assert not resp.error, f"Bedrock error: {resp.error}"
        text = resp.text

        # Statutory citation checks
        assert "51" in text or "55" in text, "Model failed to cite GPAI systemic articles (Art. 51 / Art. 55)"
        assert "53" in text, "Model failed to cite Art. 53 GPAI obligations"
        assert "10^25" in text or "1025" in text or "10²⁵" in text or "flops" in text.lower(), (
            "Model failed to reference 10^25 FLOPs compute threshold"
        )
        assert any(term in text.lower() for term in ["red-team", "red team", "adversarial", "systemic risk"]), (
            "Model failed to mention systemic risk adversarial red-teaming"
        )
        assert "53(2)" in text or "53 (2)" in text or "carve-out" in text.lower() or "exempt" in text.lower(), (
            "Model failed to mention Art. 53(2) open source exemption"
        )
        assert any(term in text.lower() for term in ["copyright", "53(1)(c)", "training data summary", "53(1)(d)", "summary"]), (
            "Model failed to mention retained copyright policy or training data summary duties for open-source GPAI"
        )

        # Ontology validation
        gpai_frontier = GPAI_REGISTRY["systemic_gpai_frontier"]
        gpai_oss = GPAI_REGISTRY["standard_gpai_open_source"]

        assert gpai_frontier.has_systemic_risk is True
        assert gpai_frontier.training_compute_flops >= 1.0e25
        assert "Art. 55" in gpai_frontier.mandatory_obligations
        assert "Annex XIII" in gpai_frontier.mandatory_obligations

        assert gpai_oss.is_open_source is True
        assert gpai_oss.technical_doc_annex == ""
        assert gpai_oss.downstream_info_annex == ""
        assert "Art. 53" in gpai_oss.mandatory_obligations

        assert validate_legal_triple("Art. 53", ActorRole.PROVIDER, RiskClass.GPAI)
        assert validate_legal_triple("Art. 55", ActorRole.PROVIDER, RiskClass.GPAI_SYSTEMIC)
        assert validate_legal_triple("Annex XI", ActorRole.PROVIDER, RiskClass.GPAI)
        assert validate_legal_triple("Annex XIII", ActorRole.PROVIDER, RiskClass.GPAI_SYSTEMIC)

    @pytest.mark.parametrize("model", TARGET_MODELS)
    def test_scenario_e_biometric_conformity_assessment_route(self, model: str) -> None:
        """Scenario E: Biometric Conformity Assessment Route (Annex VI internal control vs Annex VII notified body)."""
        prompt = (
            "A provider develops a high-risk AI system for remote biometric identification / categorisation under Annex III Point 1.\n\n"
            "Under Article 43 (Conformity assessment) of the EU AI Act:\n"
            "1. Explain the conditions under which the provider may follow the Internal Control conformity assessment procedure "
            "set out in Annex VI (e.g. where harmonised standards or common specifications have been fully applied).\n"
            "2. Explain when the provider is MANDATED to undergo third-party Notified Body conformity assessment under Annex VII "
            "(e.g. absence, partial application, or lack of harmonised standards).\n"
            "3. What role and operational obligations apply to Notified Bodies under Articles 31-34 and Annex VII?"
        )

        provider = BedrockProvider()
        resp = _invoke_and_record(provider, prompt, self.SYSTEM_PROMPT, model, "Scenario E: Conformity Assessment", max_tokens=2048)

        assert not resp.error, f"Bedrock error: {resp.error}"
        text = resp.text

        # Statutory citation checks
        assert "43" in text and "art" in text.lower(), "Model failed to cite Art. 43 conformity assessment"
        assert "annex vi" in text.lower(), "Model failed to cite Annex VI internal control"
        assert "annex vii" in text.lower(), "Model failed to cite Annex VII notified body"
        assert any(term in text.lower() for term in ["harmonised standard", "harmonized standard", "common specification"]), (
            "Model failed to discuss harmonised standards as gate between Annex VI and Annex VII"
        )
        assert any(term in text.lower() for term in ["notified body", "third-party", "third party", "notified bodies"]), (
            "Model failed to discuss Notified Body role"
        )

        # Ontology validation
        route_internal = CONFORMITY_ROUTE_REGISTRY["annex_vi_internal_control"]
        route_nb = CONFORMITY_ROUTE_REGISTRY["annex_vii_notified_body"]

        assert route_internal.requires_notified_body is False
        assert route_nb.requires_notified_body is True

        assert resolve_conformity_path("biometrics", uses_harmonised_standards=True, is_biometric=True) == ConformityRoute.ANNEX_VI_INTERNAL_CONTROL
        assert resolve_conformity_path("biometrics", uses_harmonised_standards=False, is_biometric=True) == ConformityRoute.ANNEX_VII_NOTIFIED_BODY

        assert validate_legal_triple("Art. 43", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Annex VI", ActorRole.PROVIDER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Annex VII", ActorRole.NOTIFIED_BODY, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 31", ActorRole.NOTIFIED_BODY, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 33", ActorRole.NOTIFIED_BODY, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 34", ActorRole.NOTIFIED_BODY, RiskClass.HIGH_RISK_ANNEX_III)

    @pytest.mark.parametrize("model", TARGET_MODELS)
    def test_scenario_f_fria_and_serious_incident_sla(self, model: str) -> None:
        """Scenario F: FRIA (Art. 27) and the Article 73 reporting deadlines.

        ⚠ REWRITTEN 2026-08-14 — this test used to be INVERTED VALIDATION.

        The prompt asserted the wrong law to the model ("under Article 73(3)
        (immediately and at latest within 72 hours)") and the assertions then
        REQUIRED the model to repeat it (``assert "72" in text ... "Model failed
        to cite 72 hours"``). Two compounding faults: it LED the model with a
        fabricated deadline — 72 hours is GDPR Art. 33, absent from the AI Act —
        and it graded conformity to that fabrication. A model that answered
        CORRECTLY (10 days for death, 2 days for infrastructure) FAILED the test.

        The prompt is now neutral: it asks the question without supplying an
        answer, which is the only way the response carries information about the
        model. The assertions check the ACT's figures.
        """
        prompt = (
            "Analyse two obligations under Regulation (EU) 2024/1689:\n"
            "Part 1: Article 27 Fundamental Rights Impact Assessment (FRIA)\n"
            "- Which deployer categories must perform a FRIA before putting a high-risk AI system into service?\n"
            "- Outline the mandatory assessment steps, including submission of the summary to the Market Surveillance Authority.\n\n"
            "Part 2: Article 73 serious-incident reporting deadlines\n"
            "- State the reporting deadline where the serious incident is the death of a person.\n"
            "- State the reporting deadline for a widespread infringement or a serious and irreversible "
            "disruption of critical infrastructure.\n"
            "- State the general reporting deadline for any other serious incident.\n"
            "Give the paragraph of Article 73 that each deadline comes from."
        )

        provider = BedrockProvider()
        resp = _invoke_and_record(provider, prompt, self.SYSTEM_PROMPT, model, "Scenario F: FRIA & Incident SLA", max_tokens=2048)

        assert not resp.error, f"Bedrock error: {resp.error}"
        text = resp.text

        # Statutory citation checks
        assert "27" in text and "art" in text.lower(), "Model failed to cite Art. 27 FRIA"
        assert "73" in text and "art" in text.lower(), "Model failed to cite Art. 73 serious incident reporting"
        # The Act's real figures: 73(4) death = 10 days, 73(3) widespread
        # infringement / critical-infrastructure = 2 days, 73(2) general = 15 days.
        assert "10" in text, "Model failed to state the 10-day Art. 73(4) death deadline"
        assert ("two day" in text.lower() or "2 day" in text.lower()), (
            "Model failed to state the 2-day Art. 73(3) deadline"
        )
        assert "15" in text and ("day" in text.lower() or "calendar" in text.lower()), (
            "Model failed to cite 15 days reporting deadline for general serious incidents"
        )
        assert "72" not in text, (
            "Model stated a 72-hour deadline — that is GDPR Art. 33, not AI Act Art. 73"
        )
        assert any(term in text.lower() for term in ["public", "authority", "body", "deployer", "insurance", "credit"]), (
            "Model failed to identify relevant deployer categories subject to FRIA"
        )
        assert any(term in text.lower() for term in ["market surveillance", "notif", "summary", "authority"]), (
            "Model failed to mention submission of FRIA summary to market surveillance authority"
        )

        # Ontology validation
        fria = FRIA_REGISTRY["fria_public_and_essential"]
        assert len(fria.required_steps) == 6
        assert "Art. 27" in fria.governing_articles

        death_incident = SERIOUS_INCIDENT_REGISTRY["death_of_a_person"]
        infra_incident = SERIOUS_INCIDENT_REGISTRY["widespread_infringement_or_infrastructure"]
        gen_incident = SERIOUS_INCIDENT_REGISTRY["general_serious_incident"]
        assert death_incident.deadline_hours == 240  # Art. 73(4) — 10 days
        assert infra_incident.deadline_hours == 48   # Art. 73(3) — 2 days
        assert gen_incident.deadline_hours == 360    # Art. 73(2) — 15 days

        assert validate_legal_triple("Art. 27", ActorRole.DEPLOYER, RiskClass.HIGH_RISK_ANNEX_III)
        assert validate_legal_triple("Art. 26", ActorRole.DEPLOYER, RiskClass.HIGH_RISK_ANNEX_III)


def test_print_live_evaluation_summary() -> None:
    """Consolidated summary reporter printing a clean markdown table of all live test telemetry."""
    if not SESSION_RESULTS:
        print("\nNo live test results collected in this session.")
        return

    print("\n" + "=" * 95)
    print(" LIVE BEDROCK EVALUATION SUMMARY — CLAUDE OPUS 4.6 & SONNET 4.6")
    print("=" * 95)
    print(f"{'Scenario':<38} | {'Model':<16} | {'Tokens (In/Out)':<15} | {'Bedrock ms':<10} | {'Status'}")
    print("-" * 95)

    total_in = 0
    total_out = 0
    total_ms = 0

    for r in SESSION_RESULTS:
        status_str = "OK" if not r["has_error"] else f"ERR: {r['error']}"
        tokens_str = f"{r['input_tokens']}/{r['output_tokens']}"
        model_short = "opus-4-6" if "opus" in r["model_requested"] else "sonnet-4-6"
        print(f"{r['scenario']:<38} | {model_short:<16} | {tokens_str:<15} | {r['elapsed_ms']:<10} | {status_str}")
        total_in += r["input_tokens"]
        total_out += r["output_tokens"]
        total_ms += r["elapsed_ms"]

    print("-" * 95)
    print(f"{'TOTALS / AVERAGES':<38} | {len(SESSION_RESULTS)} runs          | {total_in}/{total_out} tokens    | {total_ms} ms total")
    avg_latency = total_ms / len(SESSION_RESULTS) if SESSION_RESULTS else 0
    print(f"Average Bedrock Latency per Call: {avg_latency:.1f} ms")
    print("=" * 95 + "\n")
