# Environment flag inventory — every flag `app/` reads

**Generated** by `scripts/generate_env_flag_inventory.py`. Do not hand-edit —
regenerate instead. `CLAUDE.md`'s env table stays the curated, load-bearing
subset with the measurement history; this file is the exhaustive index.

⚠ **The code default is what the deployed service runs.**
`railway.toml [deploy.envs]` has never applied (Railway's `[deploy]` schema has
no `envs` key), and `.env` is gitignored so the container ships no dotenv. A
Railway *service variable* set from the dashboard overrides these and is invisible
here — that is the only override path.

**298** flags read across `app/`. **62** appear in the `CLAUDE.md` table. **87** are default-ON and undocumented there.

## ⚠ Flags read with MORE THAN ONE default

Two call sites disagreeing about a default is the *one concept, two
definitions* defect — whichever site runs first decides the behaviour.

| Flag | Defaults seen | Sites |
| --- | --- | --- |
| `COHERE_API_KEY` | `''`, `None` | `app/engines/cohere_rerank.py:386`, `app/engines/cohere_rerank.py:352`, `app/engines/external_embeddings.py:190`, `app/engines/external_embeddings.py:252` |
| `NEO4J_AUTO_SEED` | `''`, `None` | `app/main.py:334`, `app/main.py:526` |
| `NEO4J_URI` | `'bolt://localhost:7687'`, `None` | `app/graph/client.py:101`, `app/graph/schema_initializer.py:14`, `app/main.py:228`, `app/main.py:516`, `app/main.py:1478` |
| `OPENAI_API_BASE` | `''`, `None` | `app/engines/_graph_rag_impl.py:2061`, `app/engines/external_embeddings.py:132`, `app/engines/external_embeddings.py:209`, `app/llm/openai_wrapper_provider.py:312`, `app/llm/openai_wrapper_provider.py:422`, `app/main.py:116`, `app/main.py:1097` |
| `OPENAI_API_KEY` | `'dummy'`, `None` | `app/engines/external_embeddings.py:209`, `app/engines/external_embeddings.py:274`, `app/llm/openai_wrapper_provider.py:425` |
| `P2P_GRAPH_RAG_PROVIDER` | `''`, `None` | `app/engines/_graph_rag_impl.py:217`, `app/engines/_graph_rag_impl.py:1755`, `app/engines/_graph_rag_impl.py:2090`, `app/engines/_graph_rag_impl.py:9864`, `app/engines/query_expansion.py:215`, `app/llm/openai_wrapper_provider.py:387`, `app/main.py:33`, `app/main.py:111`, `app/main.py:1073`, `app/routes/regenold.py:1609` |
| `REGENOLD_EXTERNAL_EMBEDDING_MODEL` | `'embed-english-v3.0'`, `'text-embedding-3-small'` | `app/engines/external_embeddings.py:148`, `app/engines/external_embeddings.py:259`, `app/engines/external_embeddings.py:281` |
| `REGENOLD_INDEX_WARMUP` | `''`, `None` | `app/main.py:710`, `app/main.py:893` |
| `REGENOLD_REF_SEM_THRESHOLD` | `''`, `'0.45'` | `app/engines/_graph_rag_impl.py:7474`, `app/integrations/regenold/grounded_prose.py:1184` |

## Default-ON and absent from the `CLAUDE.md` table

Each of these shapes live behaviour on every request with no entry in the
curated table. Listed so the gap is explicit rather than implied.

`REGENOLD_ADAPTIVE_REF_CLAMP`, `REGENOLD_AI_USECASE_RESCUE`, `REGENOLD_ANNEX_APPLICABILITY_SEED`, `REGENOLD_ANNEX_III_INFRA_GUARD`, `REGENOLD_ANNEX_I_ROUTE_EXCLUSIVITY`, `REGENOLD_ASSISTANT_ANCHOR_INHERIT`, `REGENOLD_AUTO_SEED_LEADER_ONLY`, `REGENOLD_CAP_EXPANSION`, `REGENOLD_CHAIN_COLLAPSE`, `REGENOLD_CHALLENGE_BREVITY`, `REGENOLD_CITATION_FORM`, `REGENOLD_CITE_CONSISTENCY`, `REGENOLD_CLAMP_BODY_RESCUE`, `REGENOLD_CLARA_VERDICT`, `REGENOLD_COMPLEXITY_ABBREV_FIX`, `REGENOLD_CURATED_REF_PROTECT`, `REGENOLD_DEFINITIONAL_ART3_GENERALIZE`, `REGENOLD_DEFINITION_QTYPE_PRECEDENCE`, `REGENOLD_DEFINITION_REF`, `REGENOLD_DENOISER_BEDROCK`, `REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH`, `REGENOLD_DENOISE_SALVAGE`, `REGENOLD_EMBEDDINGS_INDEX`, `REGENOLD_ENTITY_BOOST`, `REGENOLD_ENUM_GUARD`, `REGENOLD_EXTRACT_CITED_ONLY`, `REGENOLD_EXTRACT_LIST`, `REGENOLD_FACT_CARRY_FORWARD`, `REGENOLD_FIDELITY_TIER_NEGATION`, `REGENOLD_FINES_AUTHORITY_SEED`, `REGENOLD_FRAMES_REWRITER_BREAKER`, `REGENOLD_FUSION_WORTHY_STRICT`, `REGENOLD_GENERAL_ANSWER`, `REGENOLD_GRAPH_2HOP_FULL_CAP`, `REGENOLD_HEALTHZ_PROBE_ANTHROPIC`, `REGENOLD_HRAIS_EXPAND`, `REGENOLD_HRAIS_LISTING_BUDGET`, `REGENOLD_INTERCEPT_LEAF_COLLAPSE`, `REGENOLD_KB_PRIMARY_RETRIEVAL`, `REGENOLD_LEAF_BODY_SIGNAL`, `REGENOLD_LEXY_LLM_GATE`, `REGENOLD_LOWER_RISK_VERDICTS`, `REGENOLD_MEDTECH`, `REGENOLD_MULTI_ARTICLE_ENTITIES`, `REGENOLD_NOISE_SUPPRESS`, `REGENOLD_OBLIGATION_ENUM_OPUS`, `REGENOLD_ONTOLOGY_HOP`, `REGENOLD_PROSE_NAMED_REFS`, `REGENOLD_PUSHBACK_REF_FREEZE`, `REGENOLD_QA_LEAD_RANK`, `REGENOLD_QA_REF_BUDGET`, `REGENOLD_QA_TRIM`, `REGENOLD_QUERY_DENOISER`, `REGENOLD_R265_INTERCEPT_RECONCILE`, `REGENOLD_REASK_FOCUS`, `REGENOLD_REFS_RECONCILE`, `REGENOLD_REF_COLLAPSE_LEAF_TO_HEAD`, `REGENOLD_REF_DESCRIBE_AUG`, `REGENOLD_REF_DESCRIBE_REPLACE`, `REGENOLD_REF_PROMOTE_LEAF_TO_HEAD`, `REGENOLD_REF_RECOVERY`, `REGENOLD_REPAIR_ELISION`, `REGENOLD_ROLE_DUTY_SEED`, `REGENOLD_ROLE_DUTY_ZRF`, `REGENOLD_SAFETY_GATE`, `REGENOLD_SCENARIO_QA_DEMOTE`, `REGENOLD_SCOPE_STICKINESS`, `REGENOLD_SEMANTIC_CONTRACT`, `REGENOLD_STAGE2_FIDELITY`, `REGENOLD_STRIP_DASHES`, `REGENOLD_STRIP_HEDGE`, `REGENOLD_STRIP_META`, `REGENOLD_STRIP_PREAMBLE`, `REGENOLD_STRIP_RETRIEVAL_META`, `REGENOLD_STRIP_SECTION_HEADERS`, `REGENOLD_SUBPARAGRAPH_ATTRIBUTION`, `REGENOLD_SUBPOINT_DESCRIBER`, `REGENOLD_SUBPOINT_EMIT`, `REGENOLD_SUBPOINT_EXISTENCE_FLOOR`, `REGENOLD_SUBPOINT_KEEP_PARENT`, `REGENOLD_SURFACE_PROSE_SUBPOINTS`, `REGENOLD_TONE_GUARD`, `REGENOLD_TOPIC_FILTER`, `REGENOLD_TURBOQUANT_DENSE`, `REGENOLD_USER_REF_MINIMALITY`, `REGENOLD_VERBATIM_ANSWER`, `REGENOLD_VERBATIM_REFS_RECONCILE`

## Full inventory, by pipeline stage

### Route — scope gate, citation post-passes, response shaping

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `REGENOLD_ADAPTIVE_REF_CLAMP` | **ON** | `app/routes/regenold.py:5081` `_adaptive_clamp_enabled()` | — |
| `REGENOLD_ANNEX_APPLICABILITY_SEED` | **ON** | `app/routes/regenold.py:962` `_apply_annex_applicability_seed()` | — |
| `REGENOLD_ANNEX_I_ROUTE_EXCLUSIVITY` | **ON** | `app/routes/regenold.py:5528` `_annex_i_route_exclusivity_enabled()` | — |
| `REGENOLD_ANNEX_III_INFRA_GUARD` | **ON** | `app/routes/regenold.py:5484` `_r317_annex_iii_guard_enabled()` | — |
| `REGENOLD_ANSWER_NO_CAP` | **ON** | `app/routes/regenold.py:8351` `regenold_eu_ai_act_ask()` | yes |
| `REGENOLD_ANSWER_TEMPLATE` | OFF | `app/routes/regenold.py:9864` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_ASSISTANT_ANCHOR_INHERIT` | **ON** | `app/routes/regenold.py:1009` `_apply_assistant_anchor_inheritance()` | — |
| `REGENOLD_CHAIN_COLLAPSE` | **ON** | `app/routes/regenold.py:5912` `_collapse_hrais_chain()` | — |
| `REGENOLD_CITABLE_BASE_GUARD` | **ON** | `app/routes/regenold.py:3825` `_citable_base_guard_enabled()` | yes |
| `REGENOLD_CITE_CONSISTENCY` | **ON** | `app/routes/regenold.py:10631` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_CLAMP_BODY_RESCUE` | **ON** | `app/routes/regenold.py:5233` `_clamp_body_rescue_enabled()` | — |
| `REGENOLD_CLAMP_PAIR_RESCUE` | OFF | `app/routes/regenold.py:5122` `_clamp_pair_rescue_enabled()` | — |
| `REGENOLD_CLARA_VERDICT` | **ON** | `app/routes/regenold.py:8896` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_COLLAPSE_PARENT_REFS` | OFF | `app/routes/regenold.py:3411` `_collapse_parent_refs()` | — |
| `REGENOLD_COMPONENT_D_CITABLE_ONLY` | OFF | `app/routes/regenold.py:3779` `_component_d_citable_only_enabled()` | yes |
| `REGENOLD_CURATED_REF_PROTECT` | **ON** | `app/routes/regenold.py:6260` `_curated_ref_protect_enabled()` | — |
| `REGENOLD_DEFINITION_REF` | **ON** | `app/routes/regenold.py:9565` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_DENOISE_SALVAGE` | **ON** | `app/routes/regenold.py:6865` `_is_denoise_salvage_enabled()` | — |
| `REGENOLD_DENOISER_BEDROCK` | **ON** | `app/routes/regenold.py:7119` `_denoiser_bedrock_enabled()` | — |
| `REGENOLD_DENOISER_MODEL_BEDROCK` | `eu.anthropic.claude-sonnet-4-6` | `app/routes/regenold.py:7278` `_rewrite_multiturn_query()` | — |
| `REGENOLD_DENOISER_MODEL_GROQ` | *required* | `app/routes/regenold.py:7256` `_rewrite_multiturn_query()` | — |
| `REGENOLD_DENOISER_TIMEOUT` | `3.0` | `app/routes/regenold.py:7350` `_rewrite_multiturn_query()` | — |
| `REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH` | **ON** | `app/routes/regenold.py:7105` `_denoiser_truncation_fallthrough_enabled()` | — |
| `REGENOLD_DENOISER_TRUNCATION_VOCAB` | OFF | `app/routes/regenold.py:7095` `_denoiser_truncation_vocab_enabled()` | — |
| `REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY` | **ON** | `app/routes/regenold.py:3809` `_deterministic_prose_consistency_enabled()` | yes |
| `REGENOLD_DYNAMIC_GROUNDING` | *required* | `app/routes/regenold.py:10239` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_EXTRACT_CITED_ONLY` | **ON** | `app/routes/regenold.py:2723` `_extract_cited_only_enabled()` | — |
| `REGENOLD_EXTRACT_EMBEDDINGS` | OFF | `app/routes/regenold.py:2888` `_try_extractive_answer()` | — |
| `REGENOLD_EXTRACT_LIST` | **ON** | `app/routes/regenold.py:2711` `_extract_qtypes_enabled()` | — |
| `REGENOLD_FACT_CARRY_FORWARD` | **ON** | `app/routes/regenold.py:1100` `_apply_fact_state_carry_forward()` | — |
| `REGENOLD_FINAL_REF_CLAMP` | OFF | `app/routes/regenold.py:5837` `_final_ref_clamp()` | yes |
| `REGENOLD_FINES_AUTHORITY_SEED` | **ON** | `app/routes/regenold.py:830` `_apply_fines_authority_seed()` | — |
| `REGENOLD_GENERAL_ANSWER` | **ON** | `app/routes/regenold.py:6322` `_general_answer_enabled()` | — |
| `REGENOLD_HRAIS_EXPAND` | **ON** | `app/routes/regenold.py:9176` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_HRAIS_LISTING_BUDGET` | **ON** | `app/routes/regenold.py:9099` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_INTERCEPT_LEAF_COLLAPSE` | **ON** | `app/routes/regenold.py:10780` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_LEAF_BODY_SIGNAL` | **ON** | `app/routes/regenold.py:3530` `_leaf_body_signal_enabled()` | — |
| `REGENOLD_LOWER_RISK_VERDICTS` | **ON** | `app/routes/regenold.py:8265` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_MAX_QUESTION_CHARS` | *(empty)* | `app/routes/regenold.py:2499` `_max_question_chars()` | — |
| `REGENOLD_MEDTECH_HOP` | OFF | `app/routes/regenold.py:382` `_medtech_hop_enabled()` | — |
| `REGENOLD_MINIMAL_REF_BUDGET` | OFF | `app/routes/regenold.py:3848` `_minimal_ref_budget_enabled()` | yes |
| `REGENOLD_NLI_KEEP_THRESHOLD` | `0.05` | `app/routes/regenold.py:10971` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_NLI_VERIFY` | OFF | `app/routes/regenold.py:10956` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_NOISE_SUPPRESS` | **ON** | `app/routes/regenold.py:3300` `_suppress_noise_anchors()` | — |
| `REGENOLD_ONE_PER_HEAD_CAP` | OFF | `app/routes/regenold.py:5258` `_one_per_head_cap_enabled()` | — |
| `REGENOLD_ONTOLOGY_HOP` | **ON** | `app/routes/regenold.py:396` `_apply_ontology_hops()` | — |
| `REGENOLD_PARENT_COLLAPSE` | OFF | `app/routes/regenold.py:1204` `_parent_collapse_enabled()` | yes |
| `REGENOLD_PROHIBITION_CONTRADICTION_GUARD` | **ON** | `app/routes/regenold.py:1547` `_prohibition_contradiction_guard_enabled()` | yes |
| `REGENOLD_PROSE_NAMED_REFS` | **ON** | `app/routes/regenold.py:10280` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_PUSHBACK_REF_FREEZE` | **ON** | `app/routes/regenold.py:4310` `_pushback_ref_freeze_enabled()` | — |
| `REGENOLD_QA_REF_BUDGET` | **ON** | `app/routes/regenold.py:9241` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_QA_TRIM` | **ON** | `app/routes/regenold.py:8435` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_QUERY_DENOISER` | **ON** | `app/routes/regenold.py:6799` `_is_query_denoiser_enabled()` | — |
| `REGENOLD_R265_INTERCEPT_RECONCILE` | **ON** | `app/routes/regenold.py:10248` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_R368_WIRE_GUARD` | **ON** | `app/routes/regenold.py:1222` `_r368_wire_guard_enabled()` | yes |
| `REGENOLD_REASK_FOCUS` | **ON** | `app/routes/regenold.py:6919` `_is_reask_focus_enabled()` | — |
| `REGENOLD_REF_CLAMP_SCENARIO_BUDGET` | *required* | `app/routes/regenold.py:5130` `_scenario_clamp_budget()` | — |
| `REGENOLD_REF_COLLAPSE_LEAF_TO_HEAD` | **ON** | `app/routes/regenold.py:1244` `_ref_collapse_leaf_to_head_enabled()` | — |
| `REGENOLD_REF_DESCRIBE_AUG` | **ON** | `app/routes/regenold.py:10050` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_REF_GRANULARITY` | `auto` | `app/routes/regenold.py:3491` `_ref_granularity_mode()` | — |
| `REGENOLD_REF_PROMOTE_LEAF_TO_HEAD` | **ON** | `app/routes/regenold.py:1267` `_ref_promote_leaf_to_head_enabled()` | — |
| `REGENOLD_REF_RECOVERY_TIER` | *required* | `app/routes/regenold.py:4183` `_ref_recovery_tier_enabled()` | — |
| `REGENOLD_REFBUDGET_PER_INTENT` | OFF | `app/routes/regenold.py:9263` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_REFS_RECONCILE` | **ON** | `app/routes/regenold.py:10253` `regenold_eu_ai_act_ask()` *(+1 more)* | — |
| `REGENOLD_RISK_FRAMEWORK_REFS` | **ON** | `app/routes/regenold.py:4056` `_risk_framework_refs_enabled()` | yes |
| `REGENOLD_ROLE_DUTY_NOUN_SEED` | OFF | `app/routes/regenold.py:591` `_detect_role_duty_seed()` | — |
| `REGENOLD_ROLE_DUTY_SEED` | **ON** | `app/routes/regenold.py:612` `_apply_role_duty_seed()` | — |
| `REGENOLD_SCENARIO_QA_DEMOTE` | **ON** | `app/routes/regenold.py:3875` `_scenario_qa_demote_enabled()` | — |
| `REGENOLD_STAGE2_CHAR_CAP` | `600` | `app/routes/regenold.py:10509` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_STAGE2_CONCISENESS_BACKSTOP` | OFF | `app/routes/regenold.py:2447` `_stage2_conciseness_backstop_enabled()` | — |
| `REGENOLD_STAGE2_HARD_FAIL` | OFF | `app/routes/regenold.py:1176` `_stage2_hard_fail_enabled()` | — |
| `REGENOLD_STAGE2_REF_AUGMENT` | OFF | `app/routes/regenold.py:10128` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_SUBPOINT_EMIT` | **ON** | `app/routes/regenold.py:8707` `regenold_eu_ai_act_ask()` *(+1 more)* | — |
| `REGENOLD_SUBPOINT_EXISTENCE_FLOOR` | **ON** | `app/routes/regenold.py:1188` `_subpoint_existence_floor_enabled()` | — |
| `REGENOLD_SUBPOINT_KEEP_PARENT` | **ON** | `app/routes/regenold.py:3166` `_reemit_parents_for_subpoints()` | — |
| `REGENOLD_SURFACE_PROSE_SUBPOINTS` | **ON** | `app/routes/regenold.py:10703` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_TIER_EXCLUSIVITY` | OFF | `app/routes/regenold.py:5671` `_tier_exclusivity_enabled()` | — |
| `REGENOLD_TONE_GUARD` | **ON** | `app/routes/regenold.py:9882` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_TOPIC_FILTER` | **ON** | `app/routes/regenold.py:6240` `_topic_filter_enabled()` | — |
| `REGENOLD_TRUST_PROXY` | *(empty)* | `app/routes/regenold.py:2553` module level | — |
| `REGENOLD_VERBATIM_ANSWER` | **ON** | `app/routes/regenold.py:10447` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_VERBATIM_REFS_RECONCILE` | **ON** | `app/routes/regenold.py:10483` `regenold_eu_ai_act_ask()` | — |
| `REGENOLD_WRONG_FRAMEWORK_GENERAL` | OFF | `app/routes/regenold.py:6352` `_general_answer_reason_ok()` | — |

### Engine — retrieval, rerank, expansion, Stage-2 generation

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `COHERE_API_BASE` | *(empty)* | `app/engines/cohere_rerank.py:178` `_rerank_url()` | — |
| `COHERE_API_KEY` | *(empty)* | `app/engines/cohere_rerank.py:386` `rerank_documents()` *(+3 more)* | — |
| `COHERE_RERANK_URL` | *(empty)* | `app/engines/cohere_rerank.py:175` `_rerank_url()` | — |
| `OPENAI_API_BASE` | *(empty)* | `app/engines/_graph_rag_impl.py:2061` `_stage2_fallback_provider_available()` *(+6 more)* | — |
| `OPENAI_API_KEY` | *required* | `app/engines/external_embeddings.py:209` `_get_provider()` *(+2 more)* | — |
| `P2P_GRAPH_RAG_COMPLEX_MODEL` | *required* | `app/engines/_graph_rag_impl.py:693` `_resolve_complex_model()` | — |
| `P2P_GRAPH_RAG_ENABLE_STAGE2` | **ON** | `app/engines/_graph_rag_impl.py:2244` `_stage2_polish_enabled()` | yes |
| `P2P_GRAPH_RAG_PROVIDER` | *required* | `app/engines/_graph_rag_impl.py:217` `_graph_rag_provider()` *(+9 more)* | yes |
| `REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS` | **ON** | `app/engines/risk_classification.py:387` `annexiii_recall_supplements_enabled()` | yes |
| `REGENOLD_ANSWER_FIRST` | OFF | `app/engines/_graph_rag_impl.py:9549` `_claude_max_enhance_answer()` | — |
| `REGENOLD_ANSWER_VERIFY` | OFF | `app/engines/faithfulness_verify.py:102` `faithfulness_verify_enabled()` | — |
| `REGENOLD_ART50_CHAT_ANCHOR` | OFF | `app/engines/risk_classification.py:159` `art50_chatbot_anchor_enabled()` | — |
| `REGENOLD_BEDROCK_COMPLEX_MODEL` | *(empty)* | `app/engines/_graph_rag_impl.py:810` `_bedrock_complete_for_graph_rag()` *(+1 more)* | yes |
| `REGENOLD_BEDROCK_FALLBACK_CHAIN` | *(empty)* | `app/engines/_graph_rag_impl.py:840` `_bedrock_complete_for_graph_rag()` | yes |
| `REGENOLD_BEDROCK_FALLBACK_MODEL` | *(empty)* | `app/engines/_graph_rag_impl.py:10126` `_claude_max_enhance_answer()` | yes |
| `REGENOLD_BEDROCK_MAX_TOKENS` | `4096` | `app/engines/_graph_rag_impl.py:868` `_bedrock_complete_for_graph_rag()` *(+1 more)* | yes |
| `REGENOLD_BEDROCK_MODEL` | *required* | `app/engines/_graph_rag_impl.py:802` `_bedrock_complete_for_graph_rag()` | yes |
| `REGENOLD_BEDROCK_STAGE1_MODEL` | *(empty)* | `app/engines/_graph_rag_impl.py:826` `_bedrock_complete_for_graph_rag()` | — |
| `REGENOLD_BEDROCK_STAGE2_MODEL` | *(empty)* | `app/engines/_graph_rag_impl.py:821` `_bedrock_complete_for_graph_rag()` | yes |
| `REGENOLD_BEDROCK_STAGE2_TIMEOUT_S` | `180` | `app/engines/_graph_rag_impl.py:869` `_bedrock_complete_for_graph_rag()` | yes |
| `REGENOLD_BM25_FALLBACK_K` | *(empty)* | `app/engines/_graph_rag_impl.py:2824` `_bm25_fallback_k()` | — |
| `REGENOLD_CAP_EXPANSION` | **ON** | `app/engines/graph_expand_2hop.py:305` `is_enabled()` *(+1 more)* | — |
| `REGENOLD_CHALLENGE_IS_COMPLEX` | **ON** | `app/engines/_graph_rag_impl.py:474` `_challenge_is_complex_enabled()` | yes |
| `REGENOLD_CHALLENGE_OBJECTION` | **ON** | `app/engines/_graph_rag_impl.py:492` `_challenge_objection_enabled()` | yes |
| `REGENOLD_CITABLE_CONCEPT_ANCHORS` | **ON** | `app/engines/_graph_rag_impl.py:8600` `_citable_concept_anchors_enabled()` | yes |
| `REGENOLD_CITABLE_UNIVERSE_BLOCK` | **ON** | `app/engines/_graph_rag_impl.py:8577` `_citable_universe_enabled()` | yes |
| `REGENOLD_CLARA_FAILURE_THRESHOLD` | `3` | `app/engines/clara_logic.py:625` module level | — |
| `REGENOLD_CLARA_FAILURE_WINDOW` | `60` | `app/engines/clara_logic.py:626` module level | — |
| `REGENOLD_CLARA_MODEL` | `claude-haiku-4-5-20251001` | `app/engines/clara_logic.py:628` module level | — |
| `REGENOLD_CLARA_TIMEOUT` | `3.0` | `app/engines/clara_logic.py:627` module level | — |
| `REGENOLD_COHERE_RERANK` | OFF | `app/engines/cohere_rerank.py:350` `rerank_enabled()` | yes |
| `REGENOLD_COHERE_RERANK_MODEL` | *(empty)* | `app/engines/cohere_rerank.py:280` `_effective_model()` | — |
| `REGENOLD_COMPLEX_GATE_WIDE` | OFF | `app/engines/question_complexity.py:254` `_gate_wide_enabled()` | — |
| `REGENOLD_COMPLEX_SENTENCE_CAP` | `5` | `app/engines/_graph_rag_impl.py:9933` `_claude_max_enhance_answer()` *(+1 more)* | — |
| `REGENOLD_COMPLEXITY_ABBREV_FIX` | **ON** | `app/engines/question_complexity.py:175` `_anchor_strip_enabled()` | — |
| `REGENOLD_CROSS_REF_SNIPPET_CHARS` | *(empty)* | `app/engines/semantic_layer.py:334` `_cross_ref_snippet_budget()` | yes |
| `REGENOLD_CURATED_SKIP_CHALLENGE_EXEMPT` | **ON** | `app/engines/_graph_rag_impl.py:6041` `_curated_skip_challenge_exempt_enabled()` | yes |
| `REGENOLD_CURATED_STAGE2_SKIP` | **ON** | `app/engines/_graph_rag_impl.py:6051` `_curated_stage2_skip_enabled()` | yes |
| `REGENOLD_DEFINITION_QTYPE_PRECEDENCE` | **ON** | `app/engines/sentence_index.py:484` `_definitional_precedence_enabled()` | — |
| `REGENOLD_DEFINITIONAL_ART3_GENERALIZE` | **ON** | `app/engines/_graph_rag_impl.py:3041` `_deterministic_parse()` | — |
| `REGENOLD_DEFINITIONAL_STAGE2_SKIP` | **ON** | `app/engines/_graph_rag_impl.py:5998` `_definitional_stage2_skip_enabled()` | yes |
| `REGENOLD_ENTITY_BOOST` | **ON** | `app/engines/entity_extractor.py:525` `is_enabled()` | — |
| `REGENOLD_EXTERNAL_EMBEDDING_MODEL` | `text-embedding-3-small` | `app/engines/external_embeddings.py:148` `_openai_negative_key()` *(+2 more)* | — |
| `REGENOLD_EXTERNAL_EMBEDDINGS` | *(empty)* | `app/engines/external_embeddings.py:100` `_opt_in_mode()` | — |
| `REGENOLD_FIDELITY_TIER_NEGATION` | **ON** | `app/engines/stage2_fidelity.py:210` `tier_negation_enabled()` | — |
| `REGENOLD_FRAMES_REWRITER_BREAKER` | **ON** | `app/engines/frames_rewriter.py:55` `_breaker_enabled()` | — |
| `REGENOLD_FRAMES_REWRITER_BREAKER_COOLDOWN_S` | `300` | `app/engines/frames_rewriter.py:72` `_breaker_cooldown_s()` | — |
| `REGENOLD_FRAMES_REWRITER_BREAKER_FAILS` | `2` | `app/engines/frames_rewriter.py:65` `_breaker_threshold()` | — |
| `REGENOLD_FUSION_FAST_TIMEOUT` | `25` | `app/engines/fusion.py:222` `_fast_timeout_seconds()` | — |
| `REGENOLD_FUSION_GATE` | `complex` | `app/engines/fusion.py:213` `fusion_gate()` | — |
| `REGENOLD_FUSION_JUDGE` | `deterministic` | `app/engines/fusion.py:477` `fusion_judge_mode()` | — |
| `REGENOLD_FUSION_JUDGE_MODEL` | *(empty)* | `app/engines/fusion.py:228` `_judge_model()` | — |
| `REGENOLD_FUSION_MIN_CANDIDATES` | `2` | `app/engines/fusion.py:233` `_min_candidates()` | — |
| `REGENOLD_FUSION_MODEL_GROQ` | *(empty)* | `app/engines/fusion.py:146` `_panel_registry()` | — |
| `REGENOLD_FUSION_MODEL_SONNET` | *(empty)* | `app/engines/fusion.py:140` `_panel_registry()` | — |
| `REGENOLD_FUSION_PANEL` | *(empty)* | `app/engines/fusion.py:288` `_enabled_panel()` | — |
| `REGENOLD_FUSION_STAGE2` | OFF | `app/engines/fusion.py:186` `fusion_stage2_enabled()` | — |
| `REGENOLD_FUSION_TIMEOUT` | `60` | `app/engines/fusion.py:241` `_timeout_seconds()` | — |
| `REGENOLD_FUSION_WORTHY_STRICT` | **ON** | `app/engines/question_complexity.py:299` `_fusion_worthy_strict()` | — |
| `REGENOLD_GRAPH_2HOP` | *(empty)* | `app/engines/graph_expand_2hop.py:95` `_env_enabled()` | — |
| `REGENOLD_GRAPH_2HOP_FULL_CAP` | **ON** | `app/engines/graph_expand_2hop.py:114` `_full_cap_enabled()` | — |
| `REGENOLD_GRAPH_AWARE` | *(empty)* | `app/engines/graph_aware_retrieval.py:92` `_env_enabled()` | — |
| `REGENOLD_GRAPH_EXPANSION` | OFF | `app/engines/_graph_rag_impl.py:7494` `_populate_semantic_statements()` | — |
| `REGENOLD_GRAPH_PPR` | OFF | `app/engines/graph_ppr.py:28` `is_ppr_available()` | — |
| `REGENOLD_GRAPH_SEMANTIC_LAYERS` | **ON** | `app/engines/graph_semantic.py:169` `semantic_layers_enabled()` | yes |
| `REGENOLD_GRAPH_VECTOR_RECALL` | *required* | `app/engines/vector_recall.py:68` `is_enabled()` | yes |
| `REGENOLD_GROUNDING_MAX_REFS` | *(empty)* | `app/engines/_graph_rag_impl.py:7964` `_grounding_max_refs()` | — |
| `REGENOLD_GROUNDING_REF_CHARS` | *(empty)* | `app/engines/_graph_rag_impl.py:7980` `_grounding_ref_budget()` | — |
| `REGENOLD_GROUNDING_TEXT` | **ON** | `app/engines/_graph_rag_impl.py:7924` `_grounding_text_enabled()` | yes |
| `REGENOLD_KB_PRIMARY_RETRIEVAL` | **ON** | `app/engines/_graph_rag_impl.py:7270` `_kb_primary_retrieval_enabled()` | — |
| `REGENOLD_KG_CONTEXT` | **ON** | `app/engines/kg_context.py:145` `kg_context_enabled()` | yes |
| `REGENOLD_KG_LOCAL_MIRROR` | **ON** | `app/engines/kg_context.py:758` `kg_local_mirror_enabled()` | yes |
| `REGENOLD_LOGIC_RAG` | *(empty)* | `app/engines/_graph_rag_impl.py:11131` `ask_compliance_question()` | — |
| `REGENOLD_LOGIC_RAG_BUDGET` | `12` | `app/engines/logic_rag.py:57` `_logic_rag_budget_seconds()` | — |
| `REGENOLD_LOGIC_RAG_MAX_NODES` | `6` | `app/engines/logic_rag.py:41` `_max_dag_nodes()` | — |
| `REGENOLD_LOGIC_RAG_MODEL` | `claude-opus-4-8` | `app/engines/logic_rag.py:93` `_call_llm()` | — |
| `REGENOLD_LOGIC_RAG_TIMEOUT` | `15` | `app/engines/logic_rag.py:99` `_call_llm()` | — |
| `REGENOLD_MEDTECH` | **ON** | `app/engines/_graph_rag_impl.py:11175` `ask_compliance_question()` *(+1 more)* | — |
| `REGENOLD_MULTI_ARTICLE_ENTITIES` | **ON** | `app/engines/_graph_rag_impl.py:2809` `_multi_article_entities_enabled()` | — |
| `REGENOLD_NLI_API` | *required* | `app/engines/crag_nli_verifier.py:157` `score_batch()` | — |
| `REGENOLD_OBLIGATION_ENUM_OPUS` | **ON** | `app/engines/question_complexity.py:289` `_obligation_enum_opus_enabled()` | — |
| `REGENOLD_OPENROUTER_FALLBACK_CHAIN` | *(empty)* | `app/engines/_graph_rag_impl.py:1584` `_openrouter_complete_for_graph_rag()` | yes |
| `REGENOLD_OPENROUTER_MAX_TOKENS` | *required* | `app/engines/_graph_rag_impl.py:1576` `_openrouter_complete_for_graph_rag()` | — |
| `REGENOLD_OPENROUTER_ROUTING` | *(empty)* | `app/engines/_graph_rag_impl.py:1507` `_openrouter_routing_suffix()` | yes |
| `REGENOLD_OPUS_FOR_ALL` | OFF | `app/engines/_graph_rag_impl.py:719` `_opus_for_all_enabled()` | — |
| `REGENOLD_PATH_RAG` | OFF | `app/engines/path_rag.py:30` `is_pathrag_available()` | — |
| `REGENOLD_PPR_DAMPING` | `0.85` | `app/engines/graph_ppr.py:86` `ppr_candidates()` | — |
| `REGENOLD_PPR_MAX_ITER` | `20` | `app/engines/graph_ppr.py:85` `ppr_candidates()` | — |
| `REGENOLD_PROVENANCE_IN_PROMPT` | OFF | `app/engines/kg_context.py:158` `_provenance_in_prompt_enabled()` | — |
| `REGENOLD_QA_LEAD_RANK` | **ON** | `app/engines/_graph_rag_impl.py:6163` `_qa_lead_rank_enabled()` | — |
| `REGENOLD_QUERY_EXPANSION` | OFF | `app/engines/_graph_rag_impl.py:3096` `_deterministic_parse()` *(+1 more)* | yes |
| `REGENOLD_QUERY_EXPANSION_MODEL` | *(empty)* | `app/engines/query_expansion.py:114` `_paraphrase_model()` | yes |
| `REGENOLD_REF_RECOVERY` | **ON** | `app/engines/_graph_rag_impl.py:2841` `_keyword_scan_refs()` *(+1 more)* | — |
| `REGENOLD_REF_RECOVERY_KW` | *required* | `app/engines/_graph_rag_impl.py:2840` `_keyword_scan_refs()` | — |
| `REGENOLD_REF_SEM_THRESHOLD` | `0.45` | `app/engines/_graph_rag_impl.py:7474` `_populate_semantic_statements()` *(+1 more)* | — |
| `REGENOLD_RERANK_KG_CANDIDATES` | OFF | `app/engines/cohere_rerank.py:129` `rerank_kg_candidates_enabled()` | yes |
| `REGENOLD_RERANK_KG_HOPS` | **ON** | `app/engines/cohere_rerank.py:149` `rerank_kg_hops()` | yes |
| `REGENOLD_RERANK_REQUEST_BUDGET` | *(empty)* | `app/engines/cohere_rerank.py:264` `reset_request_budget()` | — |
| `REGENOLD_RISK_CLASS_ANNEX` | OFF | `app/engines/risk_classification.py:95` `annex_iii_risk_class_anchor_enabled()` | yes |
| `REGENOLD_ROLE_DUTY_ZRF` | **ON** | `app/engines/zero_retrieval_fallback.py:339` `_role_duty_seed_enabled()` | — |
| `REGENOLD_ROLE_OBLIGATION_CONTEXT` | OFF | `app/engines/kg_context.py:175` `role_obligation_context_enabled()` | yes |
| `REGENOLD_SEMANTIC_CONTRACT` | **ON** | `app/engines/semantic_validator.py:92` `is_enabled()` | — |
| `REGENOLD_SEMANTIC_COORDINATES` | **ON** | `app/engines/graph_semantic.py:220` `semantic_coordinates_enabled()` | yes |
| `REGENOLD_SEMANTIC_GLOSS` | OFF | `app/engines/graph_semantic.py:146` `gloss_layers_enabled()` | yes |
| `REGENOLD_STAGE1_MODEL_GEMINI` | `gemini-2.5-flash` | `app/engines/_graph_rag_impl.py:2376` `_llm_parse_query()` | — |
| `REGENOLD_STAGE1_MODEL_GROQ` | *required* | `app/engines/_graph_rag_impl.py:2348` `_llm_parse_query()` | — |
| `REGENOLD_STAGE2_ANSWER_HEADROOM` | *(empty)* | `app/engines/_graph_rag_impl.py:546` `_stage2_answer_headroom()` | — |
| `REGENOLD_STAGE2_COMPLEX_MODEL_OPENROUTER` | *(empty)* | `app/engines/_graph_rag_impl.py:1526` `_openrouter_model()` | yes |
| `REGENOLD_STAGE2_FIDELITY` | **ON** | `app/engines/stage2_fidelity.py:148` `fidelity_guard_enabled()` | — |
| `REGENOLD_STAGE2_FIDELITY_MODE` | `fallback` | `app/engines/stage2_fidelity.py:159` `fidelity_mode()` | — |
| `REGENOLD_STAGE2_MODEL_GEMINI` | `gemini-2.5-flash` | `app/engines/_graph_rag_impl.py:1780` `_stage2_complete()` *(+2 more)* | — |
| `REGENOLD_STAGE2_MODEL_GROQ` | *required* | `app/engines/_graph_rag_impl.py:2562` `_llm_generate_answer()` | — |
| `REGENOLD_STAGE2_MODEL_OPENROUTER` | *(empty)* | `app/engines/_graph_rag_impl.py:1525` `_openrouter_model()` | yes |
| `REGENOLD_STAGE2_SIMPLE_SKIP` | OFF | `app/engines/_graph_rag_impl.py:2281` `_stage2_simple_skip_enabled()` | — |
| `REGENOLD_STAGE2_TRUNCATION_GUARD` | **ON** | `app/engines/_graph_rag_impl.py:10194` `_stage2_truncation_guard_enabled()` | yes |
| `REGENOLD_STAGE2_VERDICT_GUARD` | **ON** | `app/engines/_graph_rag_impl.py:1391` `_openai_wrapper_complete_for_graph_rag()` *(+1 more)* | yes |
| `REGENOLD_STAGE2_WEB_SEARCH` | OFF | `app/engines/web_search.py:31` `is_web_search_enabled()` | — |
| `REGENOLD_SUFFICIENT_CONTEXT` | *required* | `app/engines/sufficient_context.py:98` `sufficient_context_enabled()` | yes |
| `REGENOLD_SUFFICIENT_CONTEXT_MAX_HOPS` | `3` | `app/engines/sufficient_context.py:113` `max_sub_queries()` | — |
| `REGENOLD_SYNTHESIS_MODEL_GROQ` | *required* | `app/engines/_graph_rag_impl.py:1308` `_openai_wrapper_complete_for_graph_rag()` | — |
| `REGENOLD_TURBOQUANT_DENSE` | **ON** | `app/engines/turboquant_index.py:76` `is_enabled()` | — |
| `REGENOLD_TURBOQUANT_OUTLIER_BIT_WIDTH` | `4` | `app/engines/turboquant_index.py:455` `_build()` | — |
| `REGENOLD_TURBOQUANT_OUTLIER_CHANNELS` | `13` | `app/engines/turboquant_index.py:454` `_build()` | — |
| `REGENOLD_VECTOR_MIN_SIM` | `0.35` | `app/engines/vector_recall.py:149` `recall_articles_with_provenance()` | yes |
| `REGENOLD_VECTOR_RERANK` | *(empty)* | `app/engines/vector_rerank.py:76` `is_enabled()` | — |
| `REGENOLD_VERIFY_MAX_REFS` | *(empty)* | `app/engines/faithfulness_verify.py:110` `_max_refs()` | — |
| `REGENOLD_VERIFY_REF_CHARS` | *(empty)* | `app/engines/faithfulness_verify.py:118` `_ref_chars()` | — |

### Data — knowledge base, BM25, prompts

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `REGENOLD_ANSWER_COVERAGE` | **ON** | `app/data/graph_rag_prompts.py:1100` `answer_coverage_enabled()` | yes |
| `REGENOLD_CHALLENGE_BREVITY` | **ON** | `app/data/graph_rag_prompts.py:830` `challenge_brevity_enabled()` | — |
| `REGENOLD_COMPLETENESS_VERIFIER` | OFF | `app/data/graph_rag_prompts.py:937` `completeness_verifier_enabled()` | yes |
| `REGENOLD_EMBEDDINGS_INDEX` | **ON** | `app/data/kb_search.py:947` `top_articles_by_relevance()` *(+1 more)* | — |
| `REGENOLD_GRAPH_FUSE_SLACK` | OFF | `app/data/kb_search.py:1213` `top_articles_by_relevance()` | — |
| `REGENOLD_MAX_HOP2` | `5` | `app/data/kb_search.py:1183` `top_articles_by_relevance()` | — |
| `REGENOLD_MINIMAL_COMPOSER` | OFF | `app/data/graph_rag_prompts.py:464` `resolve_answer_system()` | — |
| `REGENOLD_ONTOLOGY_RISK_DOCS` | **ON** | `app/data/kb_search.py:233` `_ontology_risk_docs_enabled()` | yes |
| `REGENOLD_PROMPT_V2` | **ON** | `app/data/graph_rag_prompts.py:1183` `_prompt_v2_enabled()` | yes |
| `REGENOLD_REF_MINIMALITY` | OFF | `app/data/graph_rag_prompts.py:437` `ref_minimality_enabled()` | — |
| `REGENOLD_REF_PARTITION` | OFF | `app/data/graph_rag_prompts.py:885` `user_ref_partition_enabled()` | yes |
| `REGENOLD_REF_UNCERTAINTY` | **ON** | `app/data/graph_rag_prompts.py:582` `user_ref_uncertainty_enabled()` | yes |
| `REGENOLD_RRF_FUSION` | OFF | `app/data/kb_search.py:631` `_rrf_fusion_enabled()` | — |
| `REGENOLD_SCORE_FUSION` | OFF | `app/data/kb_search.py:611` `_score_fusion_enabled()` | — |
| `REGENOLD_SCORE_FUSION_ALPHA` | `0.3` | `app/data/kb_search.py:703` `_fuse_dense()` | — |
| `REGENOLD_SUBPARAGRAPH_ATTRIBUTION` | **ON** | `app/data/graph_rag_prompts.py:628` `subparagraph_attribution_enabled()` | — |
| `REGENOLD_USER_REF_MINIMALITY` | **ON** | `app/data/graph_rag_prompts.py:809` `user_ref_minimality_enabled()` | — |

### LLM transport — providers, fallback chains, judges

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | *(empty)* | `app/llm/bedrock_client.py:197` `_resolve_credentials()` *(+1 more)* | — |
| `AWS_BEDROCK_API_KEY` | *(empty)* | `app/llm/bedrock_client.py:130` `_resolve_bearer_token()` *(+2 more)* | — |
| `AWS_DEFAULT_REGION` | *(empty)* | `app/llm/bedrock_client.py:233` `_resolve_region()` | — |
| `AWS_REGION` | *(empty)* | `app/llm/bedrock_client.py:234` `_resolve_region()` | — |
| `AWS_SECRET_ACCESS_KEY` | *(empty)* | `app/llm/bedrock_client.py:198` `_resolve_credentials()` *(+1 more)* | — |
| `AWS_SESSION_TOKEN` | *(empty)* | `app/llm/bedrock_client.py:204` `_resolve_credentials()` | — |
| `BEDROCK_DEFAULT_MODEL` | *(empty)* | `app/llm/bedrock_client.py:242` `_resolve_default_model()` | — |
| `BEDROCK_MAX_POOL_CONNECTIONS` | `50` | `app/llm/bedrock_client.py:261` module level | — |
| `BEDROCK_REGION` | *(empty)* | `app/llm/bedrock_client.py:232` `_resolve_region()` | yes |
| `BEDROCK_TIMEOUT_SECONDS` | `60` | `app/llm/bedrock_client.py:260` module level | — |
| `GEMINI_API_BASE` | *(empty)* | `app/llm/openai_wrapper_provider.py:926` `get_gemini_provider()` | — |
| `GEMINI_API_KEY` | *(empty)* | `app/llm/openai_wrapper_provider.py:910` `is_gemini_provider_enabled()` *(+1 more)* | — |
| `GEMINI_TIMEOUT_SECONDS` | `60` | `app/llm/openai_wrapper_provider.py:930` `get_gemini_provider()` | — |
| `GROQ_API_BASE` | *(empty)* | `app/llm/openai_wrapper_provider.py:875` `get_groq_provider()` | — |
| `GROQ_API_KEY` | *(empty)* | `app/llm/openai_wrapper_provider.py:828` `is_groq_provider_enabled()` *(+1 more)* | — |
| `GROQ_TIMEOUT_SECONDS` | `60` | `app/llm/openai_wrapper_provider.py:879` `get_groq_provider()` | — |
| `OPENAI_MAX_RETRY_AFTER` | `8` | `app/llm/openai_wrapper_provider.py:234` module level | — |
| `OPENAI_TIMEOUT_SECONDS` | `60` | `app/llm/openai_wrapper_provider.py:477` `__init__()` | — |
| `REGENOLD_BEDROCK_WRAPPER_FALLBACK` | **ON** | `app/llm/bedrock_client.py:1010` `wrapper_fallback_enabled()` | yes |
| `REGENOLD_GROQ_DEFAULT_MODEL` | *(empty)* | `app/llm/openai_wrapper_provider.py:818` `default_groq_model()` | — |
| `REGENOLD_INTENT_CACHE_MAX` | `2048` | `app/llm/intent_classifier.py:402` module level | — |
| `REGENOLD_INTENT_FAILURE_THRESHOLD` | `3` | `app/llm/intent_classifier.py:403` module level | — |
| `REGENOLD_INTENT_FAILURE_WINDOW` | `60` | `app/llm/intent_classifier.py:405` module level | — |
| `REGENOLD_INTENT_MODEL` | *(empty)* | `app/llm/intent_classifier.py:381` `intent_model()` | yes |
| `REGENOLD_INTENT_MODEL_GEMINI` | `gemini-2.5-flash` | `app/llm/intent_classifier.py:758` `_resolve_intent_provider()` *(+1 more)* | — |
| `REGENOLD_INTENT_MODEL_GROQ` | *(empty)* | `app/llm/intent_classifier.py:398` `intent_groq_model()` | — |
| `REGENOLD_INTENT_MODEL_MISTRAL` | `mistral-large-latest` | `app/llm/intent_classifier.py:762` `_resolve_intent_provider()` *(+1 more)* | — |
| `REGENOLD_INTENT_PROVIDER` | *(empty)* | `app/llm/openai_wrapper_provider.py:852` `is_groq_intent_provider_enabled()` | — |
| `REGENOLD_INTENT_TIMEOUT` | `3.5` | `app/llm/intent_classifier.py:401` module level | — |
| `REGENOLD_WRAPPER_MODEL_ALIAS` | OFF | `app/llm/openai_wrapper_provider.py:123` `_model_alias_enabled()` | — |

### Graph — Neo4j / embedded backend

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `NEO4J_ENABLED` | *(empty)* | `app/graph/client.py:110` `_should_activate()` | — |
| `NEO4J_PASSWORD` | *required* | `app/graph/schema_initializer.py:16` `_driver()` | — |
| `NEO4J_URI` | *required* | `app/graph/client.py:101` `_should_activate()` *(+4 more)* | — |
| `NEO4J_USER` | `neo4j` | `app/graph/schema_initializer.py:15` `_driver()` | — |
| `REGENOLD_GRAPH_BACKEND` | *required* | `app/graph/embedded_graph.py:366` `graph_backend()` | yes |
| `REGENOLD_GRAPH_BREAKER` | *(empty)* | `app/graph/timeouts.py:190` `_breaker_enabled()` | — |
| `REGENOLD_GRAPH_TIMEOUT_MS` | *(empty)* | `app/graph/timeouts.py:149` `resolve_graph_timeout_ms()` | yes |

### Integrations — scope classifier, models, email

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `REGENOLD_AI_USECASE_RESCUE` | **ON** | `app/integrations/regenold/scope.py:2793` `_describes_regulated_ai_use()` | — |
| `REGENOLD_APP_URL` | *(empty)* | `app/integrations/regenold/email.py:62` `_app_url()` | — |
| `REGENOLD_CITATION_FORM` | **ON** | `app/integrations/regenold/models.py:1621` `normalise_answer_for_regenold()` | — |
| `REGENOLD_CITATION_GUARD` | *(empty)* | `app/integrations/regenold/citation_guard.py:63` `is_enabled()` | — |
| `REGENOLD_ENUM_GUARD` | **ON** | `app/integrations/regenold/answer_normaliser.py:166` `enumeration_guard_enabled()` | — |
| `REGENOLD_HARD_CHAR_CAP` | OFF | `app/integrations/regenold/models.py:1664` `normalise_answer_for_regenold()` | — |
| `REGENOLD_LEXY_GATE_TIMEOUT` | *(empty)* | `app/integrations/regenold/lexy_gate.py:59` `_gate_timeout()` | — |
| `REGENOLD_LEXY_LLM_GATE` | **ON** | `app/integrations/regenold/lexy_gate.py:82` `_gate_enabled()` | — |
| `REGENOLD_MAX_ANSWER_SENTENCES` | *(empty)* | `app/integrations/regenold/models.py:1355` `normalise_answer_for_regenold()` | — |
| `REGENOLD_QA_LENGTH_CAP` | `400` | `app/integrations/regenold/models.py:1400` `normalise_answer_for_regenold()` | — |
| `REGENOLD_R89A_FORCE_APPEND` | OFF | `app/integrations/regenold/grounded_prose.py:1484` `augment_with_ref_descriptions()` | — |
| `REGENOLD_REF_DESCRIBE_REPLACE` | **ON** | `app/integrations/regenold/grounded_prose.py:1385` `augment_with_ref_descriptions()` | — |
| `REGENOLD_REPAIR_ELISION` | **ON** | `app/integrations/regenold/answer_normaliser.py:973` `repair_elided_citation_anchors()` | — |
| `REGENOLD_SAFETY_GATE` | **ON** | `app/integrations/regenold/lexy_gate.py:225` `_safety_gate_enabled()` | — |
| `REGENOLD_SCOPE_STICKINESS` | **ON** | `app/integrations/regenold/scope.py:3958` `classify_conversation()` | — |
| `REGENOLD_STRIP_DASHES` | **ON** | `app/integrations/regenold/models.py:1677` `normalise_answer_for_regenold()` *(+1 more)* | — |
| `REGENOLD_STRIP_HEDGE` | **ON** | `app/integrations/regenold/answer_normaliser.py:576` `strip_hedge_opener()` | — |
| `REGENOLD_STRIP_META` | **ON** | `app/integrations/regenold/answer_normaliser.py:892` `strip_meta_commentary()` *(+1 more)* | — |
| `REGENOLD_STRIP_PREAMBLE` | **ON** | `app/integrations/regenold/models.py:1572` `normalise_answer_for_regenold()` | — |
| `REGENOLD_STRIP_RETRIEVAL_META` | **ON** | `app/integrations/regenold/answer_normaliser.py:836` `strip_retrieval_meta()` | — |
| `REGENOLD_STRIP_SECTION_HEADERS` | **ON** | `app/integrations/regenold/answer_normaliser.py:692` `strip_section_headers()` | — |
| `REGENOLD_SUBPOINT_DESCRIBER` | **ON** | `app/integrations/regenold/grounded_prose.py:452` `_subpoint_describer_clause()` | — |
| `REGENOLD_USER_DB_URL` | *(empty)* | `app/integrations/regenold/user_store.py:415` `_select_backend()` | — |

### Evidence store — audit chain

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `REGENOLD_AUDIT_CAP` | `10000` | `app/evidence/store.py:95` module level | — |

### Application — boot, health, misc

| Flag | Default | Read at | In `CLAUDE.md` |
| --- | --- | --- | --- |
| `NEO4J_AUTO_SEED` | *required* | `app/main.py:334` `_auto_seed_disabled_by_env()` *(+1 more)* | yes |
| `REGENOLD_AUTO_SEED_LEADER_ONLY` | **ON** | `app/main.py:544` `_maybe_auto_seed_neo4j()` | — |
| `REGENOLD_GRAPH_BOOT_PROBE_S` | `3` | `app/main.py:581` `_maybe_auto_seed_neo4j()` *(+1 more)* | — |
| `REGENOLD_HEALTHZ_PROBE` | OFF | `app/main.py:973` `_healthz_probe_enabled()` | — |
| `REGENOLD_HEALTHZ_PROBE_ANTHROPIC` | **ON** | `app/main.py:1212` `healthz_llm()` | — |
| `REGENOLD_HEALTHZ_PROBE_MODEL` | *(empty)* | `app/main.py:1131` `healthz_llm()` | — |
| `REGENOLD_HEALTHZ_PROBE_TIMEOUT` | *(empty)* | `app/main.py:1145` `healthz_llm()` | — |
| `REGENOLD_INDEX_WARMUP` | *required* | `app/main.py:710` `_index_warmup_disabled_by_env()` *(+1 more)* | — |
| `REGENOLD_SKIP_STARTUP_LOG` | *required* | `app/main.py:86` `_log_llm_provider_status()` *(+2 more)* | — |
| `REGENOLD_WORKER_INDEX` | *(empty)* | `app/main.py:545` `_maybe_auto_seed_neo4j()` | — |

