# R290 — deep code review of the Gemini graph_rag modularization (f08fbd3)

6 specialist lanes + adversarial verification of every finding (60 agents). **44 confirmed**, 9 refuted. Raised-vs-confirmed severity: 14 CRITICAL raised -> 4 confirmed (the skeptic pass downgraded 10).

| # | Severity | Finding | File |
| - | -------- | ------- | ---- |
| 1 | CRITICAL | The entire new sub-package is DEAD CODE on the request path (R256 trap), and its parser DIVERGES from the live one | `app/engines/graph_rag/__init__.py` |
| 2 | CRITICAL | Entire new graph_rag sub-package is dead code — zero callers on the request path (R256/R286 repeat) | `app/engines/graph_rag/risk_engine/__init__.py` |
| 3 | CRITICAL | parser/deterministic.deterministic_parse is a 92-LOC reduction of the 445-LOC live parser and loses ALL entity extractio | `app/engines/graph_rag/parser/deterministic.py` |
| 4 | CRITICAL | R256 trap: all 18 new tests certify code that is never invoked on the live request path (14/14 functions DEAD) | `tests/test_graph_rag_subpackage.py` |
| 5 | IMPORTANT | mock.patch / monkeypatch teardown PERMANENTLY POISONS _impl — cross-test contamination the proxy has no __delattr__ for | `app/engines/graph_rag/__init__.py` |
| 6 | IMPORTANT | importlib.reload(app.engines.graph_rag) corrupts _impl's module identity (__name__/__file__/__package__/__spec__) | `app/engines/graph_rag/__init__.py` |
| 7 | IMPORTANT | `pkg.config` shadows the `config` SUBMODULE with a GraphRAGConfig instance — dotted submodule access raises AttributeErr | `app/engines/graph_rag/__init__.py` |
| 8 | IMPORTANT | delattr on the proxy is silently ineffective AND desyncs: the attribute is resurrected by __getattr__ while _impl keeps  | `app/engines/graph_rag/__init__.py` |
| 9 | IMPORTANT | The shipped test file exercises none of the proxy semantics it exists to guarantee, and no test proves the new code is o | `tests/test_graph_rag_subpackage.py` |
| 10 | IMPORTANT | Exported `deterministic_parse` is a gutted 92-line copy of the 445-line live parser and returns ZERO entities | `app/engines/graph_rag/parser/deterministic.py` |
| 11 | IMPORTANT | config.py invents four env-var names that exist nowhere else and flips three documented defaults, including R285's delib | `app/engines/graph_rag/config.py` |
| 12 | IMPORTANT | Module proxy sync is one-directional and its __dict__ contents are import-order-dependent (266 vs 81 names) | `app/engines/graph_rag/__init__.py` |
| 13 | IMPORTANT | risk_engine/exemptions.py broadens the Article 6(3) Neo4j guard to fire on essentially every high-risk question, and its | `app/engines/graph_rag/risk_engine/exemptions.py` |
| 14 | IMPORTANT | citation_verifier.extract_citations diverges from the live inline block in a reference-ADDING direction (R281/R142.1 haz | `app/engines/graph_rag/generators/citation_verifier.py` |
| 15 | IMPORTANT | risk_engine/exemptions.evaluate_ast_exemptions fires its Neo4j Cypher on a far broader gate than the live Article 6(3) b | `app/engines/graph_rag/risk_engine/exemptions.py` |
| 16 | IMPORTANT | The _GraphRAGModule proxy syncs only package->impl; impl->package is stale, and the route has 6 lazy `from app.engines.g | `app/engines/graph_rag/__init__.py` |
| 17 | IMPORTANT | llm_parser.llm_parse_query is a stub that silently returns the deterministic parse, standing in for a 118-line LLM funct | `app/engines/graph_rag/parser/llm_parser.py` |
| 18 | IMPORTANT | app/engines/graph_rag/__init__.py and _graph_rag_impl.py form a circular import that happens to work only because of sub | `app/engines/graph_rag/__init__.py` |
| 19 | IMPORTANT | The entire new sub-package is DEAD CODE — zero call-sites on the request path (R256/R286 repeat) | `app/engines/graph_rag/__init__.py` |
| 20 | IMPORTANT | `deterministic_parse` is not a refactor — it is a gutted rewrite that loses 95% of extracted entities (135/135 disagreem | `app/engines/graph_rag/parser/deterministic.py` |
| 21 | IMPORTANT | Groq truncation rewrite is behaviour-CHANGING for len(user) <= 10000: it discards up to 2500 chars the old code kept, an | `app/engines/_graph_rag_impl.py` |
| 22 | IMPORTANT | `evaluate_ast_exemptions` and `enrich_context` widen their trigger gates well beyond the baseline blocks they replace | `app/engines/graph_rag/risk_engine/exemptions.py` |
| 23 | IMPORTANT | deterministic_parse (new) returns EMPTY entities on 6/6 real questions where the live parser returns the correct anchors | `app/engines/graph_rag/parser/deterministic.py` |
| 24 | IMPORTANT | Module proxy: reverse sync is broken and patch teardown leaks attributes | `app/engines/graph_rag/__init__.py` |
| 25 | IMPORTANT | compute_confidence duplicated verbatim — a load-bearing function now has two copies that can drift silently | `app/engines/graph_rag/pipeline.py` |
| 26 | IMPORTANT | risk_engine detectors match bare high-frequency substrings — the over-broad shadowing pattern R77/R54.1 removed | `app/engines/graph_rag/risk_engine/annex_iii.py` |
| 27 | IMPORTANT | The forked deterministic_parse is a DEGRADED reimplementation — loses role anchors, Art. 3 rescue, and MedTech routing o | `app/engines/graph_rag/parser/deterministic.py` |
| 28 | IMPORTANT | Rename breaks 3 source-inspection guards and makes inspect.getsource on the engine 99.51% blind (future negative guards  | `tests/test_r127_trace_latency.py` |
| 29 | IMPORTANT | Working tree is DIRTY (15 modified files) including an UNCOMMITTED wire reference change Art. 47 -> Art. 48 | `app/engines/_graph_rag_impl.py` |
| 30 | MINOR | The eager copy loop produces an import-order-dependent snapshot: 266 names vs 81, so the module's attribute surface is n | `app/engines/graph_rag/__init__.py` |
| 31 | MINOR | Sync is one-way only: patching _impl is invisible through the package, contradicting the proxy's stated purpose | `app/engines/graph_rag/__init__.py` |
| 32 | MINOR | Late submodule imports inject module objects into _impl's global namespace | `app/engines/graph_rag/__init__.py` |
| 33 | MINOR | The ENTIRE new graph_rag/ sub-package is dead on the request path — 0/14 callables execute on a live /ask (R256/R286 sil | `app/engines/graph_rag/__init__.py` |
| 34 | MINOR | config.py is a shadow feature-flag registry: 4 of 11 flags name env vars that exist nowhere, and sufficient_context defa | `app/engines/graph_rag/config.py` |
| 35 | MINOR | extract_citations name-collides with an unrelated live function of the same name and incompatible signature | `app/engines/graph_rag/generators/citation_verifier.py` |
| 36 | MINOR | pipeline.compute_confidence duplicates the load-bearing _compute_confidence; values agree today (0/200 combos differ) bu | `app/engines/graph_rag/pipeline.py` |
| 37 | MINOR | `mock.patch('app.engines.graph_rag.X')` permanently LEAKS a MagicMock into the live `_graph_rag_impl` module | `app/engines/graph_rag/__init__.py` |
| 38 | MINOR | `config.py` invents four env-var names that exist nowhere in the engine and inverts one default — a shadow config that s | `app/engines/graph_rag/config.py` |
| 39 | MINOR | Proxy staleness is import-order dependent: 81 of 235 symbols are frozen snapshots, 154 are live, and patching `_graph_ra | `app/engines/graph_rag/__init__.py` |
| 40 | MINOR | A failure in ANY of the 8 unreachable sub-modules hard-kills the /ask route and app boot | `app/engines/graph_rag/__init__.py` |
| 41 | MINOR | config.py is a second source of truth for feature flags that CONTRADICTS the live engine on 3 of 7 knobs | `app/engines/graph_rag/config.py` |
| 42 | MINOR | extract_citations (new) breaks the internal reference format, inverts gap-id precedence, and invents phantom citations | `app/engines/graph_rag/generators/citation_verifier.py` |
| 43 | MINOR | test_config_flags is a pure tautology — it cannot fail, and passes green while 2/4 gates diverge and 3 env names are fab | `tests/test_graph_rag_subpackage.py` |
| 44 | MINOR | Latent: reverse import order leaves 185 names uncopied and mock.patch NEVER restores — MagicMock leaks permanently into  | `app/engines/graph_rag/__init__.py` |

---

## Confirmed findings in detail

### 1. [CRITICAL] The entire new sub-package is DEAD CODE on the request path (R256 trap), and its parser DIVERGES from the live one

**File:** `app/engines/graph_rag/__init__.py`:14

**Failure scenario:** A maintainer reads `app/engines/graph_rag/parser/deterministic.py`, sees it is the package's `deterministic_parse`, and fixes a retrieval bug there (e.g. adds a keyword mapping). The bench and the wire are unchanged — the live path calls `_impl._deterministic_parse` at `_graph_rag_impl.py:1630`. Identical to R256 (silently inert port) and R286 (dead GraphRAG port). Concretely today: ask "What are the obligations of deployers of high-risk AI systems?" — the new parser returns `[]` (no anchors at all) while the live one returns `['Art. 26','Art. 27']`. Anything wired to the new copy would ship a zero-anchor answer for the single most common question shape in the benchmark.

**Verifier verdict** (confidence high): CONFIRMED, and two claims are understated. (1) Deadness reproduced exactly: instrumenting all 14 leaf functions in their defining modules and running 5 real ask_compliance_question() calls under provider=cli gives TOTAL sub-package invocations: 0, while all 5 questions answer normally (conf 0.7-0.85). (2) Import graph confirms it structurally: the only production importer is _graph_rag_impl.py:1125 `from app.engines.graph_rag.models import GraphQuery, GraphContext` (byte-identical at deployed f08fbd3); the sole importer of the other 17 symbols is the agent's own tests/test_graph_rag_subpackage.py. Zero production call sites (the one `extract_citations` grep hit is an unrelated function defined at app/graph/knowledge_graph.py:90). (3) SHADOWED=0 verified — the public/private name split means the _impl.__dict__ copy loop overwrites nothing, and _impl's internal calls to the `_`-prefixed tw

**Suggested fix:** Either (a) DELETE the sub-package modules and keep only `models.py` (the sole thing `_impl` actually imports), or (b) make `_impl` import each function from the sub-package and delete its private twin — but only after byte-for-byte porting the real bodies and A/B-ing on the live pairwise judge, because the current copies are behaviourally WRONG (3/5 divergences). Do not leave a second, diverging implementation of `_deterministic_parse` / `_compute_confidence` in the tree. Whatever is chosen, add

### 2. [CRITICAL] Entire new graph_rag sub-package is dead code — zero callers on the request path (R256/R286 repeat)

**File:** `app/engines/graph_rag/risk_engine/__init__.py`:3

**Failure scenario:** POST /api/v1/regenold/eu-ai-act/ask with any question the new modules claim to handle (e.g. "Is emotion recognition in the workplace prohibited?"). Verified live via TestClient: HTTP 200, refs ['Article 5','Article 5.1.f','Article 50.3','Annex III.1.c','Annex III.4'] — produced entirely by _graph_rag_impl.py. Setting a breakpoint / counter in app/engines/graph_rag/risk_engine/prohibited.py::is_prohibited_inquiry records ZERO invocations for any request. The ~1000 LOC of "risk tiering" ships to production and executes never.

**Verifier verdict** (confidence high): Confirmed by independent, stronger reproduction. (1) The cited line is accurate: app/engines/graph_rag/risk_engine/__init__.py:3 exports is_prohibited_inquiry. (2) Repo-wide grep across app/, scripts/, evals/ finds exactly ONE cross-boundary import — _graph_rag_impl.py:1125 `from app.engines.graph_rag.models import GraphQuery, GraphContext` (dataclasses only); every other reference is intra-package or in tests/test_graph_rag_subpackage.py. (3) A sys.settrace/threading.settrace probe filtering on co_filename under app/engines/graph_rag/ (bypass-proof — catches calls regardless of name binding, unlike the finding's in_impl_dict check) recorded ZERO executions across 8 TestClient requests hand-picked to hit every claimed capability (Art 5 prohibited, MDR/MedTech, Art 6(3) exemptions, GPAI Art 51, Art 50 transparency, Art 6(1) harmonized product, Annex III, social scoring). All 8 returned HT

**Suggested fix:** Either (a) wire the modules for real — replace the corresponding private copies in _graph_rag_impl.py with delegating calls and prove it with a live ?include_reasoning=true probe plus an evals.harness.ab_judge run, or (b) delete the risk_engine/, medtech/, retrieval/, generators/, parser/, pipeline/, config/ modules and keep only models.py (the one piece actually imported). Do not leave a parallel unreferenced implementation on main. Add a test that asserts each new module has at least one impor

### 3. [CRITICAL] parser/deterministic.deterministic_parse is a 92-LOC reduction of the 445-LOC live parser and loses ALL entity extraction on 6/7 probe questions

**File:** `app/engines/graph_rag/parser/deterministic.py`:19

**Failure scenario:** Question: "What are the obligations of deployers of high-risk AI systems?" (a core competition shape). LIVE _deterministic_parse returns entities ['Art. 26','Art. 27'] and dimension_hint 'deployer_obligations' — those entities are what surface Article 26/27 on the wire (the live probe for this exact question returned references ['Article 26','Article 27','Article 13','Article 86',...]). The new parser returns entities=[] and dimension_hint=None. Wiring it would delete the deployer-obligation anchor entirely and hand the question to BM25 alone — the precise wrong-Article cascade R77-I2 and R252 were written to fix.

**Verifier verdict** (confidence high): CONFIRMED. I tried to refute this from five angles and every one corroborated it.

(1) The cited code says what the finding claims. app/engines/graph_rag/__init__.py:14-36 binds 15 new symbols; the loop at :39-42 copies _impl.__dict__ over the package globals. I verified collisions in Python: only GraphQuery/GraphContext collide, and they are the SAME objects because _graph_rag_impl.py:1125 does `from app.engines.graph_rag.models import GraphQuery, GraphContext`. The route imports only 4 names (app/routes/regenold.py:76-81), all resolving to _graph_rag_impl objects.

(2) No other consumer. 0 references to any of the 14 callables anywhere in app/, evals/, scripts/ — verified on BOTH the working tree and the committed f08fbd3 (git grep). The 3 `extract_citations` hits are an unrelated function at app/graph/knowledge_graph.py:90.

(3) Reproduced with a live probe (see proof): 66 distinct _g

**Suggested fix:** Delete this module, or rename it to something that cannot be mistaken for the parser (e.g. `parse_explicit_article_refs`) and document that it handles only literal article/annex mentions. A real extraction of _deterministic_parse must move the 506-entry keyword map and the R63/R81/R127/R268 logic with it, and must be gated by a byte-identical davidath assert-baseline run before it can be called.

### 4. [CRITICAL] R256 trap: all 18 new tests certify code that is never invoked on the live request path (14/14 functions DEAD)

**File:** `tests/test_graph_rag_subpackage.py`:1

**Failure scenario:** A future session reads '18/18 passing, 100% backward compatible', treats the subpackage as validated, and completes the migration by wiring parser/risk_engine into the request path. The suite stays green because it only ever tested the fork. Live answers immediately regress (see finding R290-T2 for the measured entity losses).

**Verifier verdict** (confidence high): I tried to refute this and could not; my independent probe is stronger than the finder's. Using sys.settrace 'call' events (catches ANY entry into the package, incl. helpers/genexprs/lazy imports — strictly stronger than the finder's named-function wrappers), 5 real questions through ask_compliance_question() executed 63 distinct _graph_rag_impl.py functions (tracer demonstrably works: _deterministic_parse x5, _compute_confidence x5, _retrieve_from_kb x5) and ZERO code objects from app/engines/graph_rag/. The live path calls impl's own _deterministic_parse (line 1630) and _compute_confidence (line 7699); the subpackage versions are forks. Grep confirms the only non-package-internal import is _graph_rag_impl.py:1125 'from app.engines.graph_rag.models import GraphQuery, GraphContext', and I verified impl.GraphQuery IS models.GraphQuery (models.py is genuinely live; the finding scoped this 

**Suggested fix:** Either (a) re-point tests/test_graph_rag_subpackage.py at the LIVE functions in app/engines/_graph_rag_impl.py (_deterministic_parse, _compute_confidence, ...) so it becomes real coverage, or (b) delete the unused subpackages and keep only models.py (the one faithful, live-imported extraction). Do NOT leave 18 green tests standing over dead code — that is the false green light that authorises the regressing migration.

### 5. [IMPORTANT] mock.patch / monkeypatch teardown PERMANENTLY POISONS _impl — cross-test contamination the proxy has no __delattr__ for

**File:** `app/engines/graph_rag/__init__.py`:54

**Failure scenario:** A test does `with mock.patch.object(graph_rag, '_compute_confidence', lambda ctx: 0.1):` under any import order where `_compute_confidence` is not in `pkg.__dict__` (or any `mock.patch(..., create=True)` / `monkeypatch.setattr(..., raising=False)` under ANY order). The context manager exits, pytest reports green — and every subsequent test in the session runs against `_impl._compute_confidence` still bound to the lambda. Confidence 0.1 < the R78.1 cache floor (0.3) and < the R87-E Stage-2 floor (0.5), so every later test silently exercises the no-cache / no-polish branch, and a real regression in the caching or Stage-2 gate would be masked. The failure surfaces as an unrelated test failing later, or worse, as a NON-failure that hides a live bug.

**Verifier verdict** (confidence high): CONFIRMED as a real latent bug, but the failure scenario is overstated. The guard at app/engines/graph_rag/__init__.py:56 (`if hasattr(_impl, name) or not name.startswith("__")`) is genuinely wrong: every module already has __name__/__file__/__package__/__spec__/__loader__/__doc__, so the first clause always fires and renders the author's own dunder-exclusion clause dead code. I reproduced the exact corruption: after importlib.reload(pkg), _impl.__name__ becomes 'app.engines.graph_rag', _impl.__file__ points at graph_rag/__init__.py, __package__ and __spec__.name are likewise overwritten, and the _GraphRAGModule class identity breaks (isinstance(pkg, old_cls) == False). __path__ is correctly not forwarded, and line 60 is safe on fresh import ('__class__' in impl.__dict__ == False) but becomes True after reload — my inspect.isclass scan of _impl.__dict__ picked up a bogus ('__class__', 'a

**Suggested fix:** Add a `__delattr__` to `_GraphRAGModule` that mirrors the delete into `_impl.__dict__.pop(name, None)`. Better: drop the eager copy loop entirely so EVERY name resolves through `__getattr__`/`__setattr__` (one consistent path), and add the `__delattr__`. Then add a regression test that asserts `_impl.__dict__` is unchanged after a `mock.patch.object(create=True)` round-trip.

### 6. [IMPORTANT] importlib.reload(app.engines.graph_rag) corrupts _impl's module identity (__name__/__file__/__package__/__spec__)

**File:** `app/engines/graph_rag/__init__.py`:56

**Failure scenario:** Any code path that reloads the package — a test using `importlib.reload` to re-read an env-var-driven module constant (CLAUDE.md documents an 'override-model-via-env reload path' pattern in `tests/test_intent_groq_routing.py`), a dev REPL, or a hot-reload dev server — leaves `sys.modules['app.engines._graph_rag_impl'].__name__ == 'app.engines.graph_rag'` and `.__file__` pointing at `graph_rag/__init__.py`. Downstream: `pickle` of anything defined in `_impl` resolves to the wrong module, `cls.__module__` on classes created after the reload is wrong, and tracebacks/`inspect.getsourcefile` point at the wrong file. Reload also mints a NEW `_GraphRAGModule` class object, so any cached `isinstance` check against the old class breaks.

**Verifier verdict** (confidence high): The defect is REAL: app/engines/graph_rag/__init__.py:54-57 forwards __setattr__ into _impl.__dict__ but supplies no __delattr__, so any teardown path that uses delattr (mock.patch when local=False, monkeypatch.undo after raising=False) removes the name from pkg.__dict__ only and leaves the fake permanently in _impl.__dict__. I reproduced all three poison directions directly.

But the CRITICAL grade is wrong, and the finding's own headline failure scenario is FALSE against this repo. (1) The stated scenario -- mock.patch.object(graph_rag, '_compute_confidence') leaking into later tests -- does NOT occur: the real suite imports pkg-first, so the copy loop at lines 39-42 puts all 235 non-dunder names into pkg.__dict__, mock computes local=True, and restore goes through the forwarding __setattr__. My pytest plugin over the three files that actually patch _compute_confidence/_deterministic_a

**Suggested fix:** Invert the guard so dunders are NEVER forwarded: `if not name.startswith('__') and not name.startswith('_abc_'): _impl.__dict__[name] = value`. Module metadata must stay per-module. (The current `hasattr(_impl, name) or ...` clause is backwards — `hasattr` is True for exactly the dunders you must not copy.)

### 7. [IMPORTANT] `pkg.config` shadows the `config` SUBMODULE with a GraphRAGConfig instance — dotted submodule access raises AttributeError

**File:** `app/engines/graph_rag/__init__.py`:15

**Failure scenario:** `import app.engines.graph_rag.config` followed by `app.engines.graph_rag.config.env_enabled("X")` raises `AttributeError: 'GraphRAGConfig' object has no attribute 'env_enabled'` — the classic import-vs-attribute split. Any tooling that walks the package (Sphinx autodoc, a coverage plugin, `pkgutil.iter_modules` + getattr, a future refactor script) breaks on this one name. Separately, if anyone ever swaps `_stage2_polish_enabled()` for `config.stage2_polish_enabled`, `P2P_GRAPH_RAG_ENABLE_STAGE2=0` (the documented R77 rollback) stops working because the property reads a different variable name entirely — Stage-2 would fire regardless.

**Verifier verdict** (confidence high): Mechanism CONFIRMED by execution, exactly as described. `_GraphRAGModule` (app/engines/graph_rag/__init__.py:45-57) defines `__getattr__` + `__setattr__` but no `__delattr__` (verified: `'__delattr__' in type(pkg).__dict__` is False). `delattr(pkg, X)` removes X from pkg.__dict__ only; `_impl.__dict__[X]` survives; the next `pkg.X` misses the instance dict, falls to `__getattr__`, and resurrects the stale `_impl` value; `hasattr` stays True. The finding's read of the code and of the runtime behaviour is accurate.

I found the consequence is MORE severe than the finding states. The finding frames it as a benign no-op. But `unittest.mock.patch.__exit__` calls `delattr` on its `local=False` branch, and its restore fallback is gated on `not hasattr(target, attr)` -- which the resurrection defeats. My probe showed the Mock then leaks PERMANENTLY into `_impl` (the module that actually executes

**Suggested fix:** Rename the singleton (`from app.engines.graph_rag.config import config as graph_rag_config`) or move it into `models`/a `settings` name so the submodule attribute survives. Independently: delete `config.py` along with the rest of the dead sub-package (PROXY-1), or fix its env-var names to the real ones and add them to `_engine_cache_key` before anything reads it.

### 8. [IMPORTANT] delattr on the proxy is silently ineffective AND desyncs: the attribute is resurrected by __getattr__ while _impl keeps the value

**File:** `app/engines/graph_rag/__init__.py`:48

**Failure scenario:** A test (or teardown, or a feature-flag cleanup) does `delattr(app.engines.graph_rag, '_SOME_CACHE')` expecting the module-level cache to be gone. It reports no error, `hasattr` still returns True, the stale object is still served, and `_impl` — the module that actually runs — never lost it. This is the read-side mirror of PROXY-2: PROXY-2 is 'delete removes it from the wrong place', this is 'delete removes it from nowhere observable'.

**Verifier verdict** (confidence high): Confirmed on every testable claim; I could not refute it. The cycle is real (graph_rag/__init__.py:11 imports _impl; _graph_rag_impl.py:1125 imports back into app.engines.graph_rag.models), and I reproduced the divergent snapshot exactly in fresh interpreters: pkg-first -> 266 names / 0 missing; _impl-first -> 81 names / 185 missing (incl. _deterministic_parse, _compute_confidence, ask_compliance_question). Neither order crashes and the class swap succeeds in both, so it is invisible.

Critically, I verified the harm is genuinely ORDER-DEPENDENT, which is what makes this more than a restatement of PROXY-2: mock.patch('app.engines.graph_rag._deterministic_parse') gives local=True in the 266 order (clean teardown, _impl restored pristine) but local=False in the 81 order, where teardown calls delattr -- and the proxy overrides __setattr__ but NOT __delattr__, so the name is removed only fro

**Suggested fix:** Implement `__delattr__` on `_GraphRAGModule` that removes from both dicts and raises `AttributeError` if present in neither:
```python
def __delattr__(self, name):
    found = name in self.__dict__ or name in _impl.__dict__
    self.__dict__.pop(name, None)
    _impl.__dict__.pop(name, None)
    if not found:
        raise AttributeError(name)
```

### 9. [IMPORTANT] The shipped test file exercises none of the proxy semantics it exists to guarantee, and no test proves the new code is on the request path

**File:** `tests/test_graph_rag_subpackage.py`:1

**Failure scenario:** The suite stays green through any of PROXY-1 through PROXY-6. Specifically: delete the entire `__setattr__` forwarding block from `_GraphRAGModule` and all 18 tests still pass, because none of them touch the proxy. Equally, `deterministic_parse` returning `[]` for 'obligations of deployers of high-risk AI systems' (PROXY-1) is not caught, because no test compares it to `_impl._deterministic_parse`.

**Verifier verdict** (confidence high): Every factual claim about the test file is accurate and I reproduced the stated failure scenario exactly. tests/test_graph_rag_subpackage.py is 8 classes / 18 tests with zero occurrences of _impl, _graph_rag_impl, ask_compliance_question, monkeypatch or setattr; its sole patch() targets the unrelated app.graph.client.get_graph_client. Neutering the proxy forwarding leaves all 18 tests green (exit 0). Crucially, the finding's strongest claim -- that no test proves the new code is REACHED -- is not hypothetical: I proved the sub-package IS unreached. app/engines/_graph_rag_impl.py:1125 imports only GraphQuery/GraphContext from the package; ask_compliance_question calls its own twins _deterministic_parse (:1630) and _compute_confidence (:7699), and 7 of 8 probed sub-package functions have zero callers outside app/engines/graph_rag/ (the 3 extract_citations hits are an unrelated function in 

**Suggested fix:** Add a proxy-contract test module asserting, at minimum: (1) `monkeypatch.setattr(pkg, X)` flips a real `_impl`-internal call chain; (2) teardown leaves `impl.__dict__` byte-identical to a pre-test snapshot, including for `mock.patch(create=True)`; (3) `delattr(pkg, X)` removes it from both; (4) a call-counter assertion that each sub-package function is actually invoked during `ask_compliance_question()`; (5) an equivalence test `deterministic_parse(q) == _impl._deterministic_parse(q)` over the d

### 10. [IMPORTANT] Exported `deterministic_parse` is a gutted 92-line copy of the 445-line live parser and returns ZERO entities

**File:** `app/engines/graph_rag/parser/deterministic.py`:19

**Failure scenario:** Behavioural diff on three ordinary competition questions (same input, both parsers):

  Q: What are the obligations of importers of high-risk AI systems?
     impl entities: ['Art. 23']   new entities: []
  Q: Is emotion recognition in the workplace prohibited?
     impl entities: ['Art. 5', 'Art. 50']   new entities: []
  Q: What must technical documentation contain?
     impl entities: ['Art. 11']   new entities: []

Any future wiring of the package's `deterministic_parse` (which is precisely what the refactor advertises) drops every keyword-derived entity, so the engine loses the Art. 23 importer anchor, the Art. 5/50 emotion pair and the Art. 11 technical-documentation anchor. That is a total collapse of reference correctness on the axis the competition scores hardest.

**Verifier verdict** (confidence high): Every factual claim verified, and I reproduced one MORE defect than claimed — but the CRITICAL grade is wrong because the failure scenario is not live.

CONFIRMED: parser/deterministic.py:19 is a 92-line function vs impl's 445 (inspect.getsource). parser/__init__.py:3 exports it in __all__ as the package's canonical parser. All three quoted questions diverge exactly as claimed (['Art. 23']->[], ['Art. 5','Art. 50']->[], ['Art. 11']->[]). BONUS I proved behaviourally what the finding only inferred from the regex: the new _MULTI_ARTICLE_MENTION_RE regresses R268.1 — "What do Articles 9, 10, and 15 require?" gives impl ['Art. 9','Art. 10','Art. 15'] vs new ['Art. 9','Art. 10'], silently dropping Art. 15 on the Oxford-comma shape CLAUDE.md documents as a fixed bug.

REFUTED (severity): the gutted parser is NOT on the live wire. I instrumented both parsers with call counters and drove the rea

**Suggested fix:** Delete app/engines/graph_rag/parser/deterministic.py, or make it a thin `from app.engines._graph_rag_impl import _deterministic_parse as deterministic_parse` re-export so there is exactly one parser. If a genuine extraction is wanted, MOVE the 445-line body (not a rewrite) and delete the original in the same commit, gated by an evals.bench.runner --assert-baseline byte-identical check plus a live ab_judge run.

### 11. [IMPORTANT] config.py invents four env-var names that exist nowhere else and flips three documented defaults, including R285's deliberately reverted REGENOLD_VERIFY_VERDICT

**File:** `app/engines/graph_rag/config.py`:29

**Failure scenario:** An operator sets STAGE2_POLISH_ENABLED=0 on Railway to disable Stage-2 polish (the name the new config advertises). Nothing happens — the live gate reads P2P_GRAPH_RAG_ENABLE_STAGE2 — so Opus Stage-2 keeps firing on every request while the operator believes it is off. Conversely, the moment any code path is switched to `config.verify_verdict_enabled` / `config.logic_rag_enabled`, production silently turns ON two gates the team measured and turned OFF, with no cache-key entry (none of these names are in app/routes/regenold.py::_engine_cache_key), so pre-flip cached answers are served alongside post-flip ones.

**Verifier verdict** (confidence high): Every code-level claim is verified and the divergence is reproduced at runtime. config.py:29-46 invents four env names (STAGE2_PROVIDER_ENABLED, STAGE2_POLISH_ENABLED, STAGE2_SIMPLE_SKIP_ENABLED, REGENOLD_GRAPH_RAG_V2) that a repo-wide grep proves exist at exactly 4 lines, all inside config.py, and nowhere in app/, scripts/, tests/, evals/, railway.toml or docs. Three defaults diverge from the live engine, reproduced empirically under default env: verify_verdict new=True/live=False, sufficient_context new=False/live=True, logic_rag new=True/live=False. The verify_verdict case is the worst: _graph_rag_impl.py:2290-2296 carries an explicit docstring saying "R285: a prior commit flipped this to default-ON with no A/B, contradicting this docstring and CLAUDE.md hard rule #6. Restored to OFF... ships ON only if that A/B holds" - config.py:46 silently re-asserts the exact reverted value in a n

**Suggested fix:** Rename the four properties to read the ACTUAL env vars (P2P_GRAPH_RAG_ENABLE_STAGE2, REGENOLD_STAGE2_SIMPLE_SKIP, REGENOLD_ANSWER_V2) and restore the real defaults (verify_verdict "0", logic_rag OFF-unless-exactly-"1", sufficient_context default ON). Better: have config.py delegate to the existing `_graph_rag_impl` gate functions so there is one source of truth. Any flag that later gets wired must be added to _engine_cache_key per the R30/R56/R79/R263.2 doctrine.

### 12. [IMPORTANT] Module proxy sync is one-directional and its __dict__ contents are import-order-dependent (266 vs 81 names)

**File:** `app/engines/graph_rag/__init__.py`:39

**Failure scenario:** A test (or a future hot-swap) does `monkeypatch.setattr('app.engines._graph_rag_impl._two_stage_generate', fake)` and then exercises the route, which reaches the engine through `app.engines.graph_rag`. The patch is silently ignored — the proxy's snapshot still holds the real function — so the test passes against unpatched production code. Symmetrically, any mock.patch(create=True) on the proxy leaks its MagicMock into _graph_rag_impl.__dict__ after teardown, poisoning every later test in the same process.

**Verifier verdict** (confidence high): All four technical claims reproduced exactly, and one is worse than stated. But the stated failure scenario cannot occur today, so it is a latent hazard + false docstring, not a live defect.

VERIFIED TRUE:
1. Snapshot is import-order-dependent: package-first 266 names, impl-first 81, impl 235 both ways (exact numbers matched).
2. Sync is one-directional: setattr on impl is invisible to the proxy (gr attr is-check False, still the original); setattr on proxy propagates to impl (True). The line-4 docstring claim of mock.patch synchronization is only half-true.
3. Code at __init__.py:39-42 (snapshot), :48-52 (__getattr__ fires only on lookup miss), :54-57 (__setattr__ writes into _impl.__dict__), and there is genuinely no __delattr__ override.
4. The teardown leak is BROADER than the finding claims: it does NOT require create=True. mock.patch.__exit__ takes the delattr branch whenever is_l

**Suggested fix:** Drop the snapshot loop entirely and rely solely on __getattr__ (delete lines 38-42), so every lookup is live. Add a __delattr__ that mirrors deletion into _impl. Break the import cycle by having _graph_rag_impl.py import from a leaf module that does not live under the graph_rag package (e.g. app/engines/graph_rag_models.py), which also removes the import-order dependence.

### 13. [IMPORTANT] risk_engine/exemptions.py broadens the Article 6(3) Neo4j guard to fire on essentially every high-risk question, and its 6(3) detector regresses the R60.1-hardened live one

**File:** `app/engines/graph_rag/risk_engine/exemptions.py`:33

**Failure scenario:** Detector regression, measured on the same input:

  Q: "Is there a high-risk exception for a narrow procedural task?"
     new  is_article_6_3_inquiry -> False
     live _detect_article_6_3_inquiry -> True

Guard over-fire: with the broadened condition, a plain question like "What are the obligations for high-risk AI systems?" (risk_context='high') runs the article_6_3 Cypher on every request and, on any ast_scenario key marked true, appends `Art. 6(3)(x)` citations plus +3 nodes_traversed / +2 edges_followed to a question that never asked about the derogation. The nodes_traversed inflation is not cosmetic — pipeline/_compute_confidence buckets on it, and confidence < 0.3 blocks caching (R78.1) while < 0.5 skips Stage-2 (R87-E). Additionally the new module drops the multi-turn flatten slice, so a prior conversation turn containing "article 6(3)" re-triggers the derogation branch on an un

**Verifier verdict** (confidence high): Every factual claim verified by reading the code and running probes. samd_rules.py:9-14 does contain the 24-keyword tuple including the non-medical tokens "saas", "device", "triage"; _graph_rag_impl.py:7419 does use a hard-coded inline 5-keyword tuple; context_seeder.py:28 does widen the article regex. The divergence is real and in fact WORSE than claimed: I measured 4/6 false positives, not 2 (the finder missed "device placed on the market" and "emergency call triage"). standards_map.py is confirmed a clean 8-line re-export, so the finder's "no diverging data table" caveat is also correct.

The one thing that bounds impact: the failure scenario is LATENT, not live. I spied on enrich_context during a real ask_compliance_question() call for both false-positive questions and got ZERO invocations; grep confirms the live engine imports ONLY app.engines.graph_rag.models from the new subpackag

**Suggested fix:** Do not ship a second Article 6(3) detector — import _graph_rag_impl._detect_article_6_3_inquiry. Revert the guard to the narrow `"Annex III" in query.entities or query.risk_context == "high_risk_annex_iii"` form, or gate the broadened arms behind an env flag and A/B them with evals.harness.ab_judge before default-ON. Note: the new copy's `len(k) >= 4` substring guard at line 56 is a genuine improvement over the live version's unbounded `k.lower() in text.lower()` — port that fix INTO _graph_rag_

### 14. [IMPORTANT] citation_verifier.extract_citations diverges from the live inline block in a reference-ADDING direction (R281/R142.1 hazard if wired)

**File:** `app/engines/graph_rag/generators/citation_verifier.py`:35

**Failure scenario:** GraphContext(obligations=[{"article": "Art. 26", "text": "deployer duty"}]) — an obligation dict with no `id` and no `obligation_id`, which is exactly the shape the Antifragile/curated dynamic-injection paths build (see _graph_rag_impl.py:7462-7470 and 7484-7489, which DO set an id, and the semantic/KB fallback rows that may not). Live code emits [] (zero citations). New code emits one citation with a synthetic node_id 'Art. 26:deployer duty' and article_ref 'Article 26'. If this module is ever wired, every id-less context row becomes an extra wire reference — the precision-destroying direction the R281 clamp and the R287 leaf-collapse were built to fight.

**Verifier verdict** (confidence high): CONFIRMED as a genuine, reproduced behavioral divergence, at the claimed IMPORTANT severity — but with two corrections to the finding's framing.

VERIFIED CORRECT: (1) The code reads exactly as quoted at both sites (citation_verifier.py:35-39 or-chain synthesis; _graph_rag_impl.py:7603 dict.get-default, :7619 inverted gap precedence). (2) All four claimed divergences reproduce when running the real function. (3) The impact claim holds — routes/regenold.py:6095 turns rag_res.citations into wire `references` candidates, so an extra CitationNode is an extra wire reference, the precision-destroying direction R281/R287 fight. (4) I found a FIFTH divergence the finding missed, same adding direction: an obligation with `id` present-but-EMPTY is skipped live (dict.get returns the present empty string) but the or-chain falls through to obligation_id and emits a citation.

CORRECTION 1 (the findin

**Suggested fix:** If this module is intended to replace the inline block, it must be byte-behaviour-identical first: restore `oid = obl.get('id', obl.get('obligation_id', ''))` (drop the synthetic-id fallback), restore `gid = gap.get('obligation_id', gap.get('id', ''))`, and restore the digit-only article_ref upgrade. Then land it as a pure extraction with a per-row A/B against the current wire references before any behaviour change. Until then it is a divergent copy of a rubric-critical function.

### 15. [IMPORTANT] risk_engine/exemptions.evaluate_ast_exemptions fires its Neo4j Cypher on a far broader gate than the live Article 6(3) block (4/6 probe questions)

**File:** `app/engines/graph_rag/risk_engine/exemptions.py`:33

**Failure scenario:** Question: "What are the obligations for high-risk AI systems?" — the LIVE parser yields entities ['Art. 6', 'Art. 13', ...] and risk_context 'high'. Live gate: False (no 'Annex III' entity, risk_context != 'high_risk_annex_iii') -> no graph call. New gate: True (two of its disjuncts hit) -> issues the article_6_3 Cypher against Neo4j Aura on a plain obligations question. On the production stack (Railway -> Aura) that is an added round-trip on the most common question shape, and — because the live block lacks the answer_dict early-exit and the >=4 substring guard — wiring the new gate without the new guards would additionally widen the false-positive-exemption surface.

**Verifier verdict** (confidence high): Every factual claim checks out against the reviewed commit's actual bytes, and I reproduced the divergence exactly (6/7, identical entity lists to the claimed proof). But I also ran the decisive adversarial test the finding did not: I poisoned every new sub-package symbol to raise and ran the full engine — it completed with correct live refs and ZERO new-package calls, proving the module is dead code, so this is not a live-wire regression and does not merit CRITICAL. It is not MINOR either: `_impl` has no `deterministic_parse` attribute, so the `__init__.py:40-42` copy loop does not shadow it (`pkg.deterministic_parse is NEW` -> True), meaning the publicly re-exported API documented as "100% backward compatible" silently resolves to a parser that returns entities=[] for any question not literally naming an article number. The finding was correctly framed as conditional ("Wiring it would 

**Suggested fix:** Decide which gate is correct and make ONE of them authoritative. If the widened gate is intended, it needs a latency measurement against Aura and an ab_judge A/B; if not, narrow exemptions.py to the live condition. Independently, port the two defensive guards the new module already contains (`and text`, `len(k) >= 4`) back into the LIVE block at _graph_rag_impl.py:7536 — that is a real bug fix currently stranded in dead code.

### 16. [IMPORTANT] The _GraphRAGModule proxy syncs only package->impl; impl->package is stale, and the route has 6 lazy `from app.engines.graph_rag import ...` sites that read the stale copy

**File:** `app/engines/graph_rag/__init__.py`:48

**Failure scenario:** A future test or fix does `monkeypatch.setattr(app.engines._graph_rag_impl, '_two_stage_generate', fake)` (the natural target now that the file is named _graph_rag_impl.py). impl-internal callers use the fake; the route's lazy `from app.engines.graph_rag import ...` at regenold.py:5913 still binds the ORIGINAL. The test passes while the route path is unpatched — a silent false-green of exactly the kind CLAUDE.md records for R256. Symmetrically, any hotfix that reassigns an impl module attribute at runtime is invisible to those six route call sites.

**Verifier verdict** (confidence high): Every factual claim verified against the committed blob (git show f08fbd3:app/engines/graph_rag/config.py) and reproduced by execution. The 4 env names (STAGE2_PROVIDER_ENABLED, STAGE2_POLISH_ENABLED, STAGE2_SIMPLE_SKIP_ENABLED, REGENOLD_GRAPH_RAG_V2) have ZERO uses anywhere in the repo, while the real gates P2P_GRAPH_RAG_ENABLE_STAGE2 / REGENOLD_STAGE2_SIMPLE_SKIP / REGENOLD_ANSWER_V2 each have 2 real uses. The sufficient_context default is genuinely reversed. The finding also UNDER-reports: a fifth divergence exists at config.py:46, verify_verdict_enabled defaults "1" while R285 explicitly reverted REGENOLD_VERIFY_VERDICT to 0 ("flipped on with no A/B, which its own docstring forbids"), so anything reading this config silently re-applies the change R285 reverted. However the finding's own "currently harmless" caveat is CORRECT and I verified it exhaustively: the only two config.<flag> 

**Suggested fix:** Drop the eager dict copy and rely solely on __getattr__ (delete __init__.py:38-42). With an empty package __dict__ for impl names, every lookup delegates live to _impl and both directions stay in sync automatically; __setattr__ can then keep writing through for the mock-patch case. Add a test that patches _graph_rag_impl and asserts the package observes it.

### 17. [IMPORTANT] llm_parser.llm_parse_query is a stub that silently returns the deterministic parse, standing in for a 118-line LLM function

**File:** `app/engines/graph_rag/parser/llm_parser.py`:102

**Failure scenario:** A later change calls parser.llm_parse_query believing it is the Stage-1 LLM parse. Every question silently takes the deterministic path (and, per DEAD-04, the entity-less reduced one), Stage-1 LLM parsing is disabled with no error and no log line, and the only symptom is degraded entities — indistinguishable from a provider outage. This is the R256 'silently inert' shape at function granularity.

**Verifier verdict** (confidence high): CONFIRMED. All three mechanical claims reproduce exactly under the REAL production import order. I attacked this from four angles and it held.

WHAT I CONFIRMED (reproduced, not reasoned):
1. `__init__.py:39-42` copies `_impl.__dict__` into package globals once at import. Under `import app.main` (the production entrypoint) that copies 266 names.
2. `__getattr__` (48-52) fires 0 times for pre-existing names — I instrumented `type(pkg).__getattr__` with a spy and got 0 calls for `ask_compliance_question` and `_deterministic_parse`. The fallback truly only rescues post-import additions.
3. `__setattr__` (54-57) syncs pkg->impl (True); impl->pkg does NOT (False). Under app.main, patching impl and reading `getattr(pkg, name)` — which is exactly what the route's lazy `from app.engines.graph_rag import ...` compiles to — returns the ORIGINAL for `general_classification_verdict_refs`, `_detect_r

**Suggested fix:** Delete it, or make it raise NotImplementedError so a future caller fails loudly instead of degrading silently. If a facade is wanted, delegate to _graph_rag_impl._llm_parse_query rather than reimplementing a stub.

### 18. [IMPORTANT] app/engines/graph_rag/__init__.py and _graph_rag_impl.py form a circular import that happens to work only because of submodule-import ordering

**File:** `app/engines/graph_rag/__init__.py`:11

**Failure scenario:** models.py (or any module it grows a dependency on) later imports anything from app.engines.graph_rag's top level — e.g. `from app.engines.graph_rag.config import config`, which is itself fine, but `from app.engines.graph_rag import something` would not be. At that point the import raises ImportError/AttributeError at process start, i.e. the app fails to boot rather than degrading. The window is invisible in tests because the cycle resolves today.

**Verifier verdict** (confidence high): CORE CLAIM REPRODUCED AND TRUE — but the severity is overstated, and three supporting claims are wrong.

VERIFIED TRUE (I reproduced it independently, not by trusting the lane):
I installed spies on all 15 re-exported sub-package callables and drove 8 real `ask_compliance_question` calls (deployer obligations, medical triage, emotion-recognition prohibition, GPAI systemic, Article 13, MDR/Art 6(1), Art 6(3) exemption, Art 50 deepfake). Result: `SUB-PACKAGE CALLABLES HIT: {}` — zero. Meanwhile every answer came back non-empty (161–2356 chars, confidence 0.7–0.85, 3–13 citations). Greps confirm the only real wiring is `_graph_rag_impl.py:1125` importing `GraphQuery, GraphContext` from `.models`. I also confirmed the `__init__.py:37-40` copy-loop does NOT shadow the re-exports (none of `config/deterministic_parse/extract_citations/compute_confidence/enrich_context/is_prohibited_inquiry` exi

**Suggested fix:** Move models.py out of the cycle — e.g. app/engines/graph_rag_models.py or app/models.py — so _graph_rag_impl.py can import it without touching the package that imports _graph_rag_impl. Alternatively keep models.py but add a module-level comment documenting the cycle and forbidding top-level package imports inside it.

### 19. [IMPORTANT] The entire new sub-package is DEAD CODE — zero call-sites on the request path (R256/R286 repeat)

**File:** `app/engines/graph_rag/__init__.py`:16

**Failure scenario:** Runtime spy installed on all 15 sub-package callables, then 5 real EU AI Act questions driven through `ask_compliance_question` ("What are the obligations of deployers of high-risk AI systems?", medical-triage classification, emotion-recognition prohibition, GPAI systemic risk, Article 13). ACTUAL OUTPUT: `SUBPACKAGE CALLABLES HIT DURING 5 REAL ENGINE CALLS:\n  {}  <-- NONE.` The refactor claims to modularize the engine but ships ~1000 LOC of parallel, never-executed logic while `_graph_rag_impl.py` keeps running the original 7731-LOC path unchanged. This is verbatim the R256 ("silently inert") and R286 ("DEAD on every request") failure mode the project has already been bitten by twice.

**Verifier verdict** (confidence high): The code analysis is accurate — I reproduced all 5 divergences byte-for-byte against the baseline transcribed from 4c67ab2. But the CRITICAL grade is wrong because `extract_citations` is DEAD CODE with zero production callers, so none of it reaches the live wire. `grep -rn "extract_citations" app/` returns only two re-export lines plus an unrelated same-named function in app/graph/knowledge_graph.py:90. A runtime spy over 3 real `ask_compliance_question` calls recorded CALL COUNT = 0, and the live wire still emitted the internal canonical form (`article_ref='Art. 50'`, `'Art. 26'`, `'Annex III'`). The inline citation block in `_graph_rag_impl.py` is byte-identical to baseline (content-anchored compare: 1238 == 1238 chars), retaining the original `oid = obl.get("id", obl.get("obligation_id",""))` and `gid = gap.get("obligation_id", gap.get("id",""))` precedence. An identity check confirme

**Suggested fix:** Either wire the sub-package (with a live probe + `ab_judge` gate per hard rule #6, one module at a time), or delete it. Do not leave ~1000 LOC of unexercised shadow logic named after the real functions on `main` — the next agent that "finishes the refactor" will swap in BEQ-2/BEQ-3 and take production down. At minimum add an import-time assertion or a test that FAILS while the modules have no production importer.

### 20. [IMPORTANT] `deterministic_parse` is not a refactor — it is a gutted rewrite that loses 95% of extracted entities (135/135 disagreement)

**File:** `app/engines/graph_rag/parser/deterministic.py`:19

**Failure scenario:** Corpus of 135 unique REAL questions (davidath `evals/bench/data/qa_pairs.json` + `evals/regenold/scenarios_paper_singleturn_v4` / `_tricky_v4` / `medtech_graphrag_v124` / `tricky_v2` / `graphrag_benchmark`). Every single one disagrees.

Concrete failing input — "A vendor builds a facial-recognition database by indiscriminately scraping images from the internet and CCTV footage. Is this a prohibited practice under the EU AI Act?":
  ORIG entities = `['Art. 5']`   NEW entities = `[]`

"An AI system is used as a safety component to manage the supply of electricity on a national grid. How is it classified and under which article?":
  ORIG entities = `['Art. 6', 'Annex I']`   NEW entities = `[]`

If this is ever wired in, `query.entities` is empty for 91% of questions -> `_retrieve_from_kb` finds nothing -> `zero_retrieval_fallback` ships the `Article 1/2/3` floor. That is EXACTLY the R78.1 p

**Verifier verdict** (confidence high): CONFIRMED, and the consequence is sharper than the finding claimed. The cycle is exactly as described: app/engines/graph_rag/__init__.py:11 imports _impl, and app/engines/_graph_rag_impl.py:1125 imports back with `from app.engines.graph_rag.models import GraphQuery, GraphContext` (present in committed f08fbd3, verified via git show). models.py imports only app.models.CitationNode, so it resolves today for exactly the reason stated.

I did not have to rely on the finding's speculative "models.py later grows a dependency" scenario, because the cycle already produces a REPRODUCIBLE order-dependent defect. The eager copy loop at __init__.py:39-42 snapshots _impl.__dict__, and the cycle makes that snapshot order-dependent: package-first yields 266 public names, impl-first yields 81 (impl has only executed through line 1125 when __init__ runs the copy). The 185 missing names fall back to the p

**Suggested fix:** Do not present this as `deterministic_parse`. Either (a) delete it, or (b) rename it to something that cannot be mistaken for the real parser (`_explicit_ref_scan`) and make it delegate to `_graph_rag_impl._deterministic_parse` for everything else. Any real extraction must be gated behind an env flag with a davidath `--assert-baseline` + `easyhard_ab` run, since `intent` also feeds `_needs_stage2_enhancement` (R84: `gap_analysis`/`cross_framework` always fire Stage-2), so the reordering silently

### 21. [IMPORTANT] Groq truncation rewrite is behaviour-CHANGING for len(user) <= 10000: it discards up to 2500 chars the old code kept, and silently fixes an old prompt-doubling bug — shipped unflagged and un-A/B'd on a live fallback path

**File:** `app/engines/_graph_rag_impl.py`:645

**Failure scenario:** Measured over 5 realistic multi-article Stage-2 calls (spy on `_openai_wrapper_complete_for_graph_rag`, wrapper pointed at a dead port so nothing goes out): real `len(user)` values were `[5975, 6139, 11206, 13436, 17914]`. Two of five land in the `<=8000` band, where the OLD code sent Groq a 11996-char duplicated message with a false `[TRUNCATED]` marker and the NEW sends 5975 clean. The `8001-10000` band did not appear in this n=5 sample but sits inside the observed range (6139 .. 11206), so it is reachable — and there the NEW silently drops up to 2500 chars of grounding.

Direction of harm depends on the band: the `<=8000` change is a genuine improvement (the model no longer sees the prompt twice), the `8001-10000` change is grounding LOSS. Neither was flagged in the commit, neither is env-gated, and neither was A/B'd — on a path that fires whenever the Claude Max wrapper falls back to

**Verifier verdict** (confidence high): The MECHANISM is real and I reproduced it verbatim; the FAILURE SCENARIO's premise is false, so CRITICAL is overstated.

CONFIRMED: (1) app/engines/graph_rag/__init__.py:38-42 (boot-time snapshot) and :54-57 (__setattr__ write-through) are quoted accurately; there is no __delattr__ override. (2) With impl-first import order, mock.patch('app.engines.graph_rag._compute_confidence') permanently installs a MagicMock into the live _impl module — my probe output matched theirs exactly, including "RESTORED CORRECTLY: False" and the live engine returning 0.99. (3) The 81-vs-235 count is exactly right; root cause is the circular import at _graph_rag_impl.py:1125 (1125 lines into a 7731-line file), so an impl-first import snapshots a partially-initialised module and the remaining 154 names are never copied back. (4) _compute_confidence (line 7699), _two_stage_generate (6844), _deterministic_answer

**Suggested fix:** Keep the `<=8000` fix (it is unambiguously correct — the old code doubled the prompt), but restore no-loss behaviour in the 8001-10000 band: `elif len(user) > 8000: groq_user = user` (no truncation needed — 8000 chars is well inside gpt-oss-120b's context). Env-gate the change and note it in the commit; a Stage-2 grounding change on the Groq fallback belongs behind an `easyhard_ab`/`ab_judge` gate per hard rule #6.

### 22. [IMPORTANT] `evaluate_ast_exemptions` and `enrich_context` widen their trigger gates well beyond the baseline blocks they replace

**File:** `app/engines/graph_rag/risk_engine/exemptions.py`:33

**Failure scenario:** AST: a plain "What are the obligations for high-risk AI systems?" sets `risk_context='high'`, so the new gate fires a Neo4j round-trip on a question the baseline never touched, and any substring overlap between an answer key and an Article 6(3) point text injects an `Art. 6(3)(x)` citation the baseline never emitted — added references on the R281 precision-critical axis, plus per-request graph latency.

MedTech: `is_medtech_inquiry` matches "saas" and "device", so "Our SaaS lets enterprise customers configure a CV-screening AI for their hiring. Are we the provider or are they?" — an HR/role-ambiguity question with nothing medical about it — is classified as a MedTech inquiry and gets ISO 14971 / IEC 62304 bridging context injected into the Stage-2 prompt. The regex widening additionally fires on "art. 9" / "art 9" which the baseline's `\barticle N\b` did not match.

**Verifier verdict** (confidence high): Every claim verified independently, and I strengthened the finding's weakest point. (1) The diff is real and correctly attributed: f08fbd3's TRUE parent is 029dcb0 (not the 4c67ab2 the orchestrator cited), and 029dcb0 still had the old `prefix_len/suffix_len` form — so this commit introduced it. HEAD (17b16d1, R290) still carries it; Procfile confirms top-level app/ is the live copy. (2) I reproduced the arithmetic from scratch — all 11 rows of the finding's table match exactly, including `user[-0:]==user[0:]` duplication at len==8000 (16046 chars out for 8000 in) and the negative-suffix_len slice below 8000, and I verified OLD was genuinely LOSSLESS for 8000<len(user)<=10000 (reconstructed string == original). (3) The guard is unconditional in practice: len(ANSWER_GENERATE_SYSTEM)==51110, so len(system)+len(user)>11000 fires on every Groq fallback call. (4) The finding's weakest claim w

**Suggested fix:** Restore the baseline gates verbatim if these are meant to be extractions. If the widening is intentional, split it out as its own env-gated change with an `easyhard_ab` run — the AST widening in particular ADDS wire references, which is the exact class R281/R142.1 measured as rubric-negative, and it adds an unconditional Neo4j read to the hot path.

### 23. [IMPORTANT] deterministic_parse (new) returns EMPTY entities on 6/6 real questions where the live parser returns the correct anchors

**File:** `app/engines/graph_rag/parser/deterministic.py`:19

**Failure scenario:** A future session, told the engine is 'modularized', calls `from app.engines.graph_rag import deterministic_parse` (the un-underscored, public-looking name) instead of `_deterministic_parse`. Every natural-language question then parses to zero entities -> `_retrieve_from_kb` gets no seed anchors -> the R47-E zero-retrieval Art. 1/2/3 floor fires on essentially every request. That is the R78.1 production outage shape, arrived at by a plausible one-line import.

**Verifier verdict** (confidence high): The CORE CLAIM IS TRUE and I independently reproduced it by execution trace, not grep: 21 of 21 instrumented functions across all 14 new sub-package modules fired ZERO times across 14 real ask_compliance_question calls. Only models.py is reachable (via the single import at _graph_rag_impl.py:1125), and that extraction is byte-faithful to the pre-refactor dataclasses, so the refactor is genuinely a behavioural no-op.

BUT TWO PARTS OF THE FINDING ARE WRONG, which is why it is not CRITICAL:

(1) The named failure scenario is falsified. It claims "ask the live route 'Is an AI system that detects tumours in X-ray images high-risk?' and no ISO 14971 / IEC 62304 bridging context is produced, because enrich_context has no caller." MedTech bridging IS LIVE at _graph_rag_impl.py:7415-7440 (gated REGENOLD_MEDTECH, using the pre-existing app.data.medtech_standards.MEDTECH_STANDARD_MAP). My recorder

**Suggested fix:** Delete parser/deterministic.py, or rename the export to something unmistakably non-substitutable (e.g. `explicit_article_refs_only`) and add a docstring stating it is NOT the engine parser and is missing the keyword-entity map. Same applies to `llm_parse_query`, which is a stub that just calls deterministic_parse (llm_parser.py:102-106) despite its name promising LLM parsing.

### 24. [IMPORTANT] Module proxy: reverse sync is broken and patch teardown leaks attributes

**File:** `app/engines/graph_rag/__init__.py`:45

**Failure scenario:** (B) is the live one: 200 test files patch app.engines.graph_rag. Any `mock.patch(..., create=True)` or `monkeypatch.setattr(..., raising=False)` on a name the module did not previously have leaves that attribute permanently set on BOTH modules for the rest of the pytest session, silently changing behaviour for every later test — the cross-test pollution the project's autouse conftest fixtures exist to prevent. (A) means a maintainer who patches the impl path (the natural target now that the file is named _graph_rag_impl.py) gets a green test that proved nothing.

**Verifier verdict** (confidence high): All three factual divergences are REAL and I reproduced every one against the live code. But two material corrections to the finding: (1) The stated failure MECHANISM is false. I ran `reference_from_article_ref` and `_clamp_ref_head` — both accept `Art. N` and `Article N` and produce IDENTICAL output ('Art. 26'/'Article 26' both -> 'Article 26'; 'Art. 13(1)(a)'/'Article 13(1)(a)' both -> 'Article 13.1.a'). models.py:459 documents this verbatim ("Article-prefix accepted"). The primary reference path (regenold.py:6095) routes every article_ref through that function, so it is format-agnostic. HOWEVER, the finder missed a call site that IS format-sensitive: regenold.py:2125 passes article_ref raw into `select_answer_sentence`, which returns a sentence for 'Art. 26' and None for 'Article 26' — so the extractive-QA path would silently go dead if wired, via a path the finding never named. The h

**Suggested fix:** Drop the snapshot copy (line 38-42) entirely and rely solely on `__getattr__` for delegation — that makes reverse sync correct by construction and removes the import-order hazard. Add `__delattr__` that mirrors the delete into `_impl.__dict__`. Simplest alternative: skip the proxy and make graph_rag/__init__.py do `from app.engines._graph_rag_impl import *` plus an explicit re-export list, accepting that patch targets move to the impl path.

### 25. [IMPORTANT] compute_confidence duplicated verbatim — a load-bearing function now has two copies that can drift silently

**File:** `app/engines/graph_rag/pipeline.py`:12

**Failure scenario:** They agree today, so nothing breaks now. The failure is on the next edit: a session tuning the confidence bands edits one copy (most likely the clean, public-looking pipeline.py one, or the impl one without noticing the duplicate), the two silently diverge, and whichever is wired determines caching and Stage-2 routing. Given the copy dropped the docstring explaining the 0.2/0.3/0.5 semantics, an editor of pipeline.py has no signal that 0.3 is a cache boundary and 0.5 is a Stage-2 boundary.

**Verifier verdict** (confidence high): Root cause is real and I reproduced all three mechanics: __init__.py:40-42 is a one-time snapshot copy and lines 45-57 override __getattr__/__setattr__ but NOT __delattr__. (A) reverse sync is broken (patch impl -> gr reads stale). (B) delete-path teardown leaks into _impl.__dict__ permanently. (C) impl-first import yields gr=81 vs 266 dict entries.

BUT the finding is materially wrong in three places and I am downgrading its urgency accordingly:

1. Its claimed LIVE trigger for (B) has ZERO instantiations. grep -rnE "create=True" over tests/ app/ evals/ scripts/ = 0 matches. grep for setattr(..., raising=False) = 0 matches (every raising=False in the repo is monkeypatch.delenv on ENV VARS, not module attributes). A real-pytest probe shows missing_from_gr_dict=0 and clean restore. So "(B) is the live one" is unsupported.

2. Claim C's consequence ("half-populated module") is FALSIFIED. A

**Suggested fix:** Delete pipeline.py's copy. If the extraction is wanted, do it properly: move the function to pipeline.py WITH its full docstring and have _graph_rag_impl.py import it (`from app.engines.graph_rag.pipeline import compute_confidence as _compute_confidence`), so there is exactly one definition. Same applies to `extract_citations` (L1-I3) — but that one must be made byte-identical first.

### 26. [IMPORTANT] risk_engine detectors match bare high-frequency substrings — the over-broad shadowing pattern R77/R54.1 removed

**File:** `app/engines/graph_rag/risk_engine/annex_iii.py`:8

**Failure scenario:** Latent — nothing calls these. If wired as classification gates, `is_annex_iii_inquiry("What are the obligations of importers of high-risk AI systems?")` returns True and would steer the answer to Annex III instead of Article 23, reproducing the R77 ref-miss cluster. `is_harmonized_product_inquiry("What is in Annex III?")` returns True because "annex i" is a substring of "annex iii".

**Verifier verdict** (confidence high): Every factual claim verified by reading the code at HEAD (17b16d1) and reproducing it. annex_iii.py:9-15 does match bare "high risk"/"high-risk"/"employment"/"judicial" via plain `in`; transparency.py:10 matches bare "transparency"; harmonized_product.py:10 matches bare "annex i" via plain `in`; prohibited.py:11-25 is indeed the only module using re.search with boundaries. Both named failing inputs reproduce, plus two the finding did not claim ("Annex II", "Annex IV" also match "annex i" by containment - a plain bug, not just over-breadth). The R77-I2 / R54.1-C2 precedent is accurately cited from CLAUDE.md. I searched repo-wide for a downstream guard and found none, because there is no downstream: grep for all seven detector names returns only their definitions, two __init__ re-exports, and the test file. The finding is honest that it is latent, and I confirmed that: an instrumented live

**Suggested fix:** If these modules survive at all, replace the `in` scans with word-boundary regexes (as prohibited.py already does) and drop the bare tier words "high risk"/"high-risk"/"transparency"/"employment", keeping only multi-token AI-Act-specific forms. Anchor "annex i" as `\bannex i\b`.

### 27. [IMPORTANT] The forked deterministic_parse is a DEGRADED reimplementation — loses role anchors, Art. 3 rescue, and MedTech routing on 4/6 questions

**File:** `app/engines/graph_rag/parser/deterministic.py`:1

**Failure scenario:** Wire parser/deterministic.py in (the stated point of the refactor) and 'What are the obligations of deployers of high-risk AI systems?' retrieves ZERO entities instead of ['Art. 26','Art. 27']. The engine falls through to BM25/anchor recovery, the deployer article is never grounded, and the R72 reconcile then drops the undescribed citation — exactly the wrong-Article cascade R77-I2 and R81-N were built to fix. Reference correctness on operator-obligation questions collapses.

**Verifier verdict** (confidence high): CONFIRMED on every factual claim, with one material correction to the failure scenario.

VERIFIED TRUE:
1. `test_config_flags` (tests/test_graph_rag_subpackage.py:49-53) is a pure tautology. `env_enabled` returns `os.getenv(...).strip().lower() in (...)` — an `in` expression, which is always `bool`. I ran it with garbage: 'banana'->False(bool), ''->False(bool), ' On '->True(bool). `isinstance(x, bool)` therefore holds for EVERY possible wrong value, so the test cannot fail regardless of which env var a property reads or what it defaults to.
2. The 3 fabricated env names are real at the reviewed commit. `git grep -ln STAGE2_PROVIDER_ENABLED|STAGE2_POLISH_ENABLED|STAGE2_SIMPLE_SKIP_ENABLED f08fbd3 -- app/ tests/ evals/ scripts/` returns ONLY `app/engines/graph_rag/config.py` for all three. Meanwhile railway.toml:69 sets the real `P2P_GRAPH_RAG_ENABLE_STAGE2 = "1"` and railway.toml:187 sets

**Suggested fix:** Do not wire any of the forked parser/risk_engine/generators modules. If the modularisation is to proceed, MOVE the live 557-line _deterministic_parse into the subpackage (a true extraction with a byte-identical davidath A/B per CLAUDE.md hard rule #6) rather than hand-writing a 111-line substitute. Until then, delete the forks so no one mistakes them for the engine.

### 28. [IMPORTANT] Rename breaks 3 source-inspection guards and makes inspect.getsource on the engine 99.51% blind (future negative guards pass vacuously)

**File:** `tests/test_r127_trace_latency.py`:180

**Failure scenario:** A future round adds a guard of the shape `assert "deprecated prompt string" not in inspect.getsource(graph_rag)` to prove a removal. It searches the 60-line proxy, finds nothing, and passes — while the string is still live in all 7731 lines of _graph_rag_impl.py. The guard certifies a removal that never happened, silently, forever. This is precisely how R256/R286-class regressions ship green.

**Verifier verdict** (confidence high): Every mechanical claim reproduced with executed A/B controls. (1) app/engines/graph_rag/__init__.py:38-42 is exactly the copy loop cited, and app/engines/_graph_rag_impl.py:1125 is a genuine COLUMN-0 module-level `from app.engines.graph_rag.models import GraphQuery, GraphContext` — the cycle is real, not inferred. (2) Reverse order reproduces the finding's numbers verbatim: impl globals 244 / proxy __dict__ 90 / 185 uncopied, with ask_compliance_question, _two_stage_generate, _deterministic_answer, _compute_confidence all absent from proxy.__dict__ but reachable via the line 48 __getattr__ fallback. Normal order gives 244/275/0. (3) `grep -c '__delattr__' app/engines/graph_rag/__init__.py` returns 0 — the override really is missing. (4) The mock.patch leak reproduces under a clean same-target A/B: reverse order `is_local=False` -> delattr path -> `impl after stop: MagicMock`; normal orde

**Suggested fix:** Point every source-inspection guard at the implementation module, not the proxy: `import app.engines._graph_rag_impl as _impl; src = inspect.getsource(_impl)`. Fix the hard-coded path at test_r127_trace_latency.py:180 to Path('app/engines/_graph_rag_impl.py'). Then add a meta-guard asserting len(inspect.getsource(_impl).splitlines()) > 1000 so any future re-split that re-hides the engine fails loudly instead of silently emptying every source assertion.

### 29. [IMPORTANT] Working tree is DIRTY (15 modified files) including an UNCOMMITTED wire reference change Art. 47 -> Art. 48

**File:** `app/engines/_graph_rag_impl.py`:4702

**Failure scenario:** A reviewer runs the suite on the dirty tree, sees 103 failures, and attributes them to f08fbd3 — the commit is actually responsible for 3. Conversely the Art. 47->48 change is a live wire-reference edit (Art. 47 = EU declaration of conformity, Art. 48 = CE marking) sitting uncommitted with no A/B; if committed unnoticed it changes the retention-question citation list on the production wire, which CLAUDE.md hard rule #6 requires an ab_judge gate for.

**Verifier verdict** (confidence high): CONFIRMED as filed, but ALREADY REMEDIATED — I could not reproduce the failure because commit 17b16d1 landed after the finding and reverted exactly this edit.

I tried hard to refute it and could not. Every factual claim checks out:

(a) NOT a defect in the reviewed commit. `git show f08fbd3:app/engines/_graph_rag_impl.py` line 4702 reads `"Art. 47"`. The finding states this itself and is correct to.

(b) The uncommitted `Art. 47 -> Art. 48` edit WAS real. I cannot see the vanished working tree, but the corroboration is decisive: commit 17b16d1's message says verbatim "Art. 18 retention: 'Article 48' -> 'Article 47'. Art. 47 IS the EU declaration of conformity; Art. 48 is CE marking", and `git show --numstat 17b16d1` shows exactly 2 insertions / 2 deletions on that file — matching the two citation reverts (the other being Art. 71(2) -> Art. 49(2)). An independent actor saw the same edit 

**Suggested fix:** Do not treat the dirty-tree 103-failure run as the commit's baseline; the authoritative numbers are PARENT 69 -> COMMIT 72 (+3, all source-inspection). Identify the owner of the Art. 47 -> Art. 48 edit and either commit it behind an env gate with the required gold-bearing A/B, or revert it. Separately, chase the 1 order-dependent test (104 vs 103 across identical runs) — flaky rows undermine every future byte-identical claim.

### 30. [MINOR] The eager copy loop produces an import-order-dependent snapshot: 266 names vs 81, so the module's attribute surface is non-deterministic

**File:** `app/engines/graph_rag/__init__.py`:39

**Failure scenario:** Someone adds `import app.engines._graph_rag_impl` to a diagnostic script, a new conftest fixture, or a module imported before the app (e.g. an eval harness that wants to poke the impl directly). Under pytest that module may be collected first, and the whole session silently switches to the 81-name snapshot. Nothing fails immediately — but every `mock.patch('app.engines.graph_rag._deterministic_parse')` in the 27 existing patch sites now takes the `local=False` branch and leaves `_impl._deterministic_parse` bound to a MagicMock after teardown, cascading unrelated failures (or, worse, green tests running against a mock).

**Verifier verdict** (confidence high): Both mechanical claims are TRUE and I reproduced them by execution, but the severity is overstated and one supporting premise is false, so I downgrade IMPORTANT -> MINOR.

VERIFIED TRUE (executed):
1. Shadowing. `__init__.py:15` rebinds `pkg.config` from the submodule to the `GraphRAGConfig()` singleton (`config.py:57`). Probe output: `pkg.config is module? False -> GraphRAGConfig`, while `models/pipeline/parser/risk_engine/medtech/retrieval/generators` all remain modules. `sys.modules['app.engines.graph_rag.config']` still holds the real module -> split-brain name, exactly as claimed. Understated by the finding: `import app.engines.graph_rag.config as x` ALSO binds x to the instance (py3.7+ getattr-first), so even the as-form is poisoned.
2. Env divergence, proven executably not just by name-reading: with `P2P_GRAPH_RAG_ENABLE_STAGE2=0` (the documented R77 rollback), live `_impl._stage2

**Suggested fix:** Delete the eager copy loop at `:39-42` entirely and let `__getattr__` serve everything — that makes the surface order-independent AND removes the snapshot/staleness class of bug. (It must land together with the PROXY-2 `__delattr__` fix, because without the copy loop EVERY name becomes `local=False` for `mock.patch` and the poisoning would go from latent to universal.) Failing that, add a module-level guard that raises if `_impl` is not fully initialised when the copy loop runs (e.g. assert a se

### 31. [MINOR] Sync is one-way only: patching _impl is invisible through the package, contradicting the proxy's stated purpose

**File:** `app/engines/graph_rag/__init__.py`:3

**Failure scenario:** A test patches the implementation module directly (`monkeypatch.setattr(app.engines._graph_rag_impl, '_deterministic_parse', fake)`) — a perfectly reasonable thing to do now that the file exists and is where the code lives. `_impl`-internal calls see the fake, but anything that reads `app.engines.graph_rag._deterministic_parse` (including `tests/test_two_stage_pipeline.py:106-109`, which resolves the name off the package) sees the ORIGINAL. Two halves of the same test then disagree about which function is live, producing a test that passes for the wrong reason or fails inexplicably.

**Verifier verdict** (confidence high): Every factual claim verified, and I reproduced the failure end-to-end rather than by simulation. (1) Code reads as claimed at app/engines/graph_rag/__init__.py:54-57 — the `or not name.startswith("__")` clause makes the `hasattr` clause redundant, so ALL non-dunder setattrs are written into `_impl.__dict__`; the class swap is at :60; there is no ModuleType guard or allowlist anywhere in the file. (2) I upgraded the proof from the finding's synthetic setattr to a REAL import: evicting `app.engines.graph_rag.pipeline` from sys.modules and re-importing it made CPython's own importlib `setattr(parent_module, child, module)` inject the module object into `_impl.__dict__` (False -> True, type=module). (3) The hypothesized collision name is real: `_impl.logger` is defined at _graph_rag_impl.py:52 and used at 68 call sites; appending a scratchpad dir to `g.__path__` and running an ordinary `impo

**Suggested fix:** Document the one-way contract explicitly in the docstring ("patch the PACKAGE, never `_graph_rag_impl` directly"), and enforce it with a lint/test that fails on `patch("app.engines._graph_rag_impl...")`. Removing the eager copy loop (PROXY-6) makes the read side live in both directions and removes the asymmetry for free.

### 32. [MINOR] Late submodule imports inject module objects into _impl's global namespace

**File:** `app/engines/graph_rag/__init__.py`:56

**Failure scenario:** A future submodule is added whose name collides with an `_impl` module-level global — e.g. `app/engines/graph_rag/logger.py` or `.../settings.py` or `.../config.py` if it were ever imported lazily. The first lazy `import app.engines.graph_rag.logger` anywhere in the process silently rebinds `_impl.logger` from the `logging.Logger` to a module object, and the next `logger.warning(...)` inside `_impl` raises `AttributeError: module has no attribute 'warning'` — from a call site that has nothing to do with the import.

**Verifier verdict** (confidence high): The MECHANISM is real and I reproduced it verbatim: __setattr__ (:54-57) syncs pkg->_impl only; __getattr__ (:48-52) fires only for names absent from pkg.__dict__, and :39-42 eagerly copies 266 names, so setattr(_impl,'_normalise',sentinel) leaves pkg._normalise pointing at the ORIGINAL. The docstring at :3-4 ('synchronizes') genuinely over-promises. BUT the finding's IMPACT case fails on four independent counts, so IMPORTANT is overstated. (1) Nothing does it: grep -rn "_graph_rag_impl" over the whole repo returns hits only inside the proxy's own __init__.py (lines 4,11,46) plus one docs file; grep over tests/ returns NOTHING. Zero tests and zero production modules import or patch _impl, so the failure scenario is hypothetical. (2) The cited evidence is misattributed: tests/test_two_stage_pipeline.py:106-109 patches "app.engines.graph_rag._deterministic_parse" -- the PACKAGE, i.e. the d

**Suggested fix:** Skip forwarding when the value is a submodule of this package: `if isinstance(value, types.ModuleType) and value.__name__.startswith(__name__ + '.'): return` before the `_impl.__dict__[name] = value` line.

### 33. [MINOR] The ENTIRE new graph_rag/ sub-package is dead on the request path — 0/14 callables execute on a live /ask (R256/R286 silently-inert trap)

**File:** `app/engines/graph_rag/__init__.py`:16

**Failure scenario:** Live in-process probe (deterministic env OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli), 7 real POSTs to /api/v1/regenold/eu-ai-act/ask, each deliberately chosen to hit a different new module (Article 5 prohibition, Annex III triage, Article 6(3) exemption, GPAI Article 51, Article 50 transparency, MDR/Annex I medtech, deployer obligations). All returned HTTP 200 with correct references. Result: 0/14 new-package callables executed. The bad outcome is not a wrong answer — it is ~1000 LOC + 18 green tests + a commit message asserting a shipped risk-tiering/MedTech architecture that is inert, so any future round that 'improves' these modules will measure zero effect and mis-attribute it to the change being neutral.

**Verifier verdict** (confidence high): The code-level divergence is REAL and I reproduced it exactly (4/6 probe questions), but the stated failure scenario is REFUTED: evaluate_ast_exemptions is never called on the request path, so it fires zero Neo4j Cypher in production.

CONFIRMED (read + reproduced):
- exemptions.py:33-38 gate has 4 disjuncts vs the live 2-disjunct gate at _graph_rag_impl.py:7505. My probe against the live _deterministic_parse reproduced the claimed table line-for-line: 4/6 diverge.
- Vocabulary claim correct: _graph_rag_impl.py:1710 emits risk_context="high"; "high_risk_annex_iii" is never produced by the parser and reaches query.risk_context only via request.risk_level (line 7357). app/routes/regenold.py:5803-5805 explicitly declines to send it ("do not force a tenant-specific risk_level or answers payload here").
- Live guard gaps correct: _graph_rag_impl.py:7524 is `if v is True and (k.lower() in text

**Suggested fix:** Do not leave this as-is. Either (a) revert the sub-package and keep only the _graph_rag_impl rename + the two genuine fixes in the diff (default_groq_model(), Groq truncation), or (b) wire ONE module at a time behind its own env gate with a live probe proving execution and an ab_judge A/B per CLAUDE.md hard rule #6. Whichever path, add a CI guard that fails when a module under app/engines/graph_rag/ has zero non-test importers — that is the mechanical version of the R256/R286 lesson.

### 34. [MINOR] config.py is a shadow feature-flag registry: 4 of 11 flags name env vars that exist nowhere, and sufficient_context defaults OFF against the R110.1 default-ON

**File:** `app/engines/graph_rag/config.py`:29

**Failure scenario:** An operator sets P2P_GRAPH_RAG_ENABLE_STAGE2=0 to disable Stage-2 polish (the documented rollback). A future round routes a Stage-2 decision through config.stage2_polish_enabled, which reads STAGE2_POLISH_ENABLED — unset — and returns its "1" default. Stage-2 stays ON despite the operator's rollback. Same class of failure for the sufficient-context gate, which would silently flip a default-ON feature OFF on every deploy that does not set the var — the exact R80.2/R110.1 trap, reintroduced.

**Verifier verdict** (confidence high): The CODE claims are all true and I verified each one: llm_parser.py:102-106 is a 5-line unconditional delegation to deterministic_parse with a docstring claiming LLM parsing and a comment claiming an "if provider disabled" branch that does not exist; it is publicly exported at parser/__init__.py:4,8 and graph_rag/__init__.py:16-20; and it has ZERO call sites in app/, tests/, evals/, scripts/ (grep -rnE "[^_a-zA-Z]llm_parse_query\s*\(" returns only the def line). It is also the only parser export the new test file omits (tests/test_graph_rag_subpackage.py:11-12 imports deterministic_parse and extract_json_object and exercises them at 57-80; llm_parse_query appears nowhere).

HOWEVER the stated failure scenario is REFUTED, so severity stays at the lane's MINOR and must not be escalated:

(1) The "live counterpart" it allegedly stands in for is ITSELF dead. `grep -rn "_llm_parse_query" app/

**Suggested fix:** Delete config.py, or make every property delegate to the single authoritative gate function that already exists (_stage2_polish_enabled, _stage2_simple_skip_enabled, sufficient_context_enabled, ...) instead of re-reading os.getenv with a second set of names and defaults. Add a test asserting each config property is identical to its authoritative counterpart across set/unset/0/1.

### 35. [MINOR] extract_citations name-collides with an unrelated live function of the same name and incompatible signature

**File:** `app/engines/graph_rag/generators/citation_verifier.py`:23

**Failure scenario:** A developer (or an agent) writing citation-handling code imports the wrong extract_citations. Passing a GraphContext to the knowledge_graph version, or a string to the new one, produces a TypeError at best; with the new one, passing a str makes `getattr(context, 'obligations', None) or []` return [] on both loops and yields an empty citation list with no error — a silent zero-citation result.

**Verifier verdict** (confidence high): Every factual claim is accurate and I reproduced the exact failure mode. Two distinct callables named extract_citations now exist with incompatible signatures (knowledge_graph.py:90 takes str->list[ProvisionId]; citation_verifier.py:23 takes GraphContext->list[CitationNode]), both importable under that bare name, and `A is B` is False. The claimed asymmetry is real: passing a str to the new one returns [] silently (getattr(str,'obligations',None) or [] -> []) while passing a non-str to the old one raises TypeError. The collision is genuinely NEW — `git show 4c67ab2:app/engines/graph_rag.py | grep extract_citations` is empty. I also checked the _impl.__dict__ copy loop in __init__.py:38-41 that runs after the import and could have shadowed the binding; it does not, because _graph_rag_impl.py contains no extract_citations. However three facts cap severity at MINOR, matching the lane's own 

**Suggested fix:** Rename the new one to something unambiguous — e.g. `citations_from_context` — and drop it from the top-level app.engines.graph_rag re-export list.

### 36. [MINOR] pipeline.compute_confidence duplicates the load-bearing _compute_confidence; values agree today (0/200 combos differ) but the copy is unanchored drift risk

**File:** `app/engines/graph_rag/pipeline.py`:12

**Failure scenario:** There is no failure today; both functions return identical values for every reachable GraphContext. The risk is forward-looking and concrete: someone tunes the confidence ladder in pipeline.py (the file that looks like the modern home for it), the live path keeps using _compute_confidence, and the change measures as a no-op — or worse, someone later wires pipeline.py and the two thresholds R78.1 (cache floor 0.3) and R87-E (Stage-2 floor 0.5) silently move caching and Stage-2 eligibility for every request.

**Verifier verdict** (confidence high): Every claim verified; could not refute on any of 6 angles. (1) Code matches: pipeline.py:12-24 reproduces the _graph_rag_impl.py:7699-7731 ladder branch-for-branch (degraded->0.2, nodes==0->0.3, nodes<5->0.5, gaps|satisfied->0.85, obligations>=3->0.85, else 0.7), with a one-line docstring that drops the issue-#55 + R127 reasoning. (2) Both thresholds the dropped comment cites are REAL live gates: _MIN_CACHEABLE_CONFIDENCE = 0.3 at routes/regenold.py:288 (consumed 5860) and REGENOLD_STAGE2_MIN_CONFIDENCE at routes/regenold.py:1406/1459/1479 — so the comment is load-bearing documentation. (3) Dead confirmed: clean grep gives exactly 4 bare `compute_confidence` hits (def, __init__ re-export, 2 in the new test) — zero production callers — and a live 7-request trace shows 7 live fires / 0 new fires. (4) No guard exists: the ONLY test on the copy (test_graph_rag_subpackage.py:168-176) asserts 

**Suggested fix:** Delete pipeline.compute_confidence and, if the package should expose it, re-export the live one (`from app.engines._graph_rag_impl import _compute_confidence as compute_confidence`). If the copy is kept, add a test asserting the two functions agree across the enumerated grid so drift fails CI, and carry the issue-#55 / R78.1 / R87-E comments across.

### 37. [MINOR] `mock.patch('app.engines.graph_rag.X')` permanently LEAKS a MagicMock into the live `_graph_rag_impl` module

**File:** `app/engines/graph_rag/__init__.py`:54

**Failure scenario:** `import app.engines._graph_rag_impl` first (the order most existing tests use), then `with mock.patch('app.engines.graph_rag._compute_confidence', return_value=0.99): ...`. After the `with` block exits, the LIVE engine module still holds the MagicMock: `impl._compute_confidence(GraphContext())` returns `0.99`.

`_compute_confidence` is exactly the load-bearing function CLAUDE.md flags: R78.1 refuses to CACHE a response with confidence < 0.3, and R87-E SKIPS Stage-2 polish when confidence < 0.5. A leaked mock returning a constant makes every subsequent test in the process cache and Stage-2-route incorrectly — silent, order-dependent, green-looking corruption of the regression guard itself.

**Verifier verdict** (confidence high): The code-text observation is accurate — llm_parser.py:102-106 IS a 4-statement stub whose docstring ("using LLM, with fallback to extract_json_object") describes neither behaviour. That is a genuine, if cosmetic, defect. But the claimed severity and EVERY harm mechanism in the failure scenario are refuted.

(1) The stub shadows nothing. `_impl` has no attribute `llm_parse_query` (no underscore) — the `__init__.py:39-42` copy-loop skips only dunders, so `_llm_parse_query` IS copied from `_impl`. Probe: `gr._llm_parse_query is impl._llm_parse_query` -> True. The real ~120-line parser (_graph_rag_impl.py:1150, branching on openai_wrapper/groq/anthropic, calling _extract_json_object at 1244) is intact and reachable at its original name.

(2) The stub is called 0 times on the live path. Tripwires on BOTH the stub and the real function across 3 representative questions: STUB=0, REAL=0. All 3 r

**Suggested fix:** Add a matching `__delattr__` to `_GraphRAGModule` that also removes/restores the name in `_impl.__dict__`, and drop the eager snapshot copy at `__init__.py:38-42` entirely so EVERY name resolves through `__getattr__` (uniform, live, and `mock.patch` then always takes the `delattr` path symmetrically). Better: delete the proxy and make `app/engines/graph_rag.py` a plain `from app.engines._graph_rag_impl import *` re-export module, or just don't rename the file.

### 38. [MINOR] `config.py` invents four env-var names that exist nowhere in the engine and inverts one default — a shadow config that silently contradicts the real gates

**File:** `app/engines/graph_rag/config.py`:29

**Failure scenario:** An operator or a future round reads `graph_rag.config` as the authoritative feature-flag surface and sets `STAGE2_POLISH_ENABLED=0` expecting to disable Stage-2 polish. Nothing happens — the real gate is `P2P_GRAPH_RAG_ENABLE_STAGE2` (`_graph_rag_impl.py:1031`) and Stage-2 keeps firing on every request. Likewise `REGENOLD_GRAPH_RAG_V2=0` does not roll back R284's answer-v2 verdict fix (the real switch is `REGENOLD_ANSWER_V2=0`, documented as the "instant rollback" at `_graph_rag_impl.py:2261`). Reading `config.sufficient_context_enabled` reports OFF while the bounded multi-hop gate is actually ON in production.

None of these names are in `_engine_cache_key` either (`app/routes/regenold.py`), so if they ever WERE wired they would violate the R30/R56/R79/R263.2 cache-poisoning doctrine on day one.

**Verifier verdict** (confidence high): The finding's factual claims are verbatim-accurate for the reviewed commit, but its impact claim is refuted and it is largely already fixed. (1) CONFIRMED at f08fbd3: `git show f08fbd3:app/engines/graph_rag/config.py` reproduces the quoted block exactly — four invented env names plus REGENOLD_SUFFICIENT_CONTEXT defaulting "0" (vs R110.1 ON) and REGENOLD_VERIFY_VERDICT defaulting "1" (vs R285's revert to 0). (2) BUT f08fbd3 is NOT the tip: `git rev-parse origin/main` = 17b16d1 ("R290 — review the graph_rag modularization"), which rewrote config.py (+37 lines) with explicit R290 comments fixing these exact defects. Railway deploys main, so the LIVE state is already corrected — verified at runtime: config.stage2_polish_enabled now agrees with impl._stage2_polish_enabled(), config.sufficient_context_enabled (True) agrees with sufficient_context.sufficient_context_enabled(), and config.verify

**Suggested fix:** Make `GraphRAGConfig` delegate to the real gate functions (`_graph_rag_impl._stage2_polish_enabled`, `_answer_v2_enabled`, `sufficient_context.sufficient_context_enabled`, ...) rather than re-declaring env names. If it must own its own names, add a test that asserts each literal appears in the engine AND in `_engine_cache_key`.

### 39. [MINOR] Proxy staleness is import-order dependent: 81 of 235 symbols are frozen snapshots, 154 are live, and patching `_graph_rag_impl` directly is invisible through `graph_rag`

**File:** `app/engines/graph_rag/__init__.py`:38

**Failure scenario:** 1. `with mock.patch('app.engines._graph_rag_impl._compute_confidence', ...)` — the standard way the existing suite patches the engine — is INVISIBLE through `app.engines.graph_rag`, which is what `app/routes/regenold.py:77` imports from. A test that patches `_impl` and drives the route asserts against unpatched behaviour and passes for the wrong reason.
2. Which of the two behaviours you get depends on module import order within the pytest process, so the same test can pass alone and fail (or silently no-op) in a full-suite run. Combined with BEQ-4, the leak-prone symbol set is precisely the 154 that are NOT in the dict.

**Verifier verdict** (confidence high): The MECHANISM is real and I reproduced it, but the severity, the headline numbers, and BOTH failure scenarios are wrong.

CONFIRMED: __init__.py:38-42 is verbatim as quoted. The circular import is real (__init__.py:11 <-> _graph_rag_impl.py:1125). Import order does change the copy count: ORDER A (graph_rag first) = 266 attrs in __dict__; ORDER B (_impl first) = 81. Reverse-patching _impl IS invisible through graph_rag in ORDER A (gr_sees_mock=False).

REFUTED #1 - the headline numbers are INVERTED for the order that actually runs. "81 frozen / 154 live" describes ORDER B. Every real execution is ORDER A (266 in __dict__): pytest alone, pytest with other modules, pytest running ONLY the _impl-importing test files, and `import app.main` (production boot). In ORDER A essentially everything is frozen - but it is also the SAFER order, because mock.patch sees local=True and teardown restores c

**Suggested fix:** Drop the eager copy loop at `__init__.py:38-42` so every attribute resolves live through `__getattr__` (uniform, order-independent, and makes `mock.patch` teardown symmetric). Break the circular import by having `_graph_rag_impl` define the dataclasses itself or import them from a leaf module outside the `graph_rag` package (e.g. `app/engines/graph_rag_models.py`).

### 40. [MINOR] A failure in ANY of the 8 unreachable sub-modules hard-kills the /ask route and app boot

**File:** `app/engines/graph_rag/__init__.py`:14

**Failure scenario:** Simulated a broken sub-module (`app.engines.graph_rag.risk_engine.gpai` raising ImportError, e.g. a typo or a bad `from app.graph.schema import ...` — the literal R286 mistake) via a meta_path hook, then `import app.routes.regenold`:

  RESULT: *** ROUTE IMPORT FAILED *** ImportError: simulated broken submodule (typo / bad import)
          -> the whole /ask endpoint (and app boot) is dead.

A one-character typo in gpai.py — a file that is never executed by any request — takes the entire production API down on the next deploy.

**Verifier verdict** (confidence high): REAL but MUCH smaller than claimed, and its stated harm is already remediated on the live branch.

ACCURATE AGAINST THE REVIEWED COMMIT: `git show f08fbd3:app/engines/graph_rag/config.py` confirms the finding verbatim (verify_verdict="1", sufficient_context="0", logic_rag="1", 4 invented env names).

STALE AGAINST WHAT IS LIVE: HEAD is 17b16d1 (R290) and `git rev-parse HEAD origin/main` shows both at 17b16d1 — the branch Railway deploys already contains a fix. `git diff f08fbd3 HEAD -- app/engines/graph_rag/config.py` shows R290 corrected 5 of 7 issues, with comments citing the same reasoning as this finding. Re-running the finding's own table on HEAD gives 1 of 7 divergences, not 3: verify_verdict OK, sufficient_ctx OK, logic_rag still DIVERGES. Of the 4 invented names, 3 are fixed (STAGE2_PROVIDER_ENABLED now delegates to _stage2_provider_enabled(); STAGE2_POLISH_ENABLED -> P2P_GRAPH_R

**Suggested fix:** Preferred: delete the unreachable modules (see L1-C1); the blast radius then disappears. If they must stay, wrap the 7 non-`models` re-export imports in a single `try: ... except Exception: logger.warning(...)` block so a broken optional module degrades to "re-export absent" instead of "no API". `models` may stay unguarded — the live engine genuinely needs it — but note that even that is a new import-time dependency the pre-refactor file did not have.

### 41. [MINOR] config.py is a second source of truth for feature flags that CONTRADICTS the live engine on 3 of 7 knobs

**File:** `app/engines/graph_rag/config.py`:18

**Failure scenario:** Today this is latent because nothing on the request path reads `config`. The moment anyone wires a single `config.*` property — the obvious next step given the commit's stated intent — the engine silently flips REGENOLD_VERIFY_VERDICT ON (emitting false 'Prohibited' verdicts on legitimate high-risk systems, the exact harm R285's docstring warns about), turns SUFFICIENT_CONTEXT OFF, and turns LOGIC_RAG ON. None of that would show on davidath (all three are Stage-2 / live-path only), so it would ship undetected — the R285 pattern verbatim.

**Verifier verdict** (confidence high): All four equivalence claims independently re-verified and hold; the only actionable item is one unused import, so MINOR stands. Corrections to the finding's framing (not its conclusion): (1) 'three hardcoded literals' is scope-ambiguous — exactly 3 within graph_rag.py (655/1232/1440), but 9 repo-wide (fusion.py:114, lexy_gate.py:294, intent_classifier.py:348, main.py:745, regenold.py:4442, regenold.py:5058); the repo's own cache-key comment at regenold.py:1338 says 'nine'. All nine model env vars are registered (regenold.py:1350-1358), which is stronger than claimed. (2) Two of the four verified surfaces are DEAD duplicates — pipeline.compute_confidence and parser/llm_parser.extract_json_object have zero callers; the live wire uses _impl._compute_confidence (called impl:6993, impl:7640) and _impl._extract_json_object (called impl:1244). Verifying the new copies proves nothing about the w

**Suggested fix:** Delete app/engines/graph_rag/config.py. There is already a config module (app/config.py) and 100+ env gates living beside the code they gate; a second, partial, contradicting registry is strictly negative. If a centralised gate registry is genuinely wanted, it must (a) delegate to the existing `_env_enabled` helpers rather than re-implement defaults, (b) use the REAL env var names, and (c) be added to _engine_cache_key at the same time.

### 42. [MINOR] extract_citations (new) breaks the internal reference format, inverts gap-id precedence, and invents phantom citations

**File:** `app/engines/graph_rag/generators/citation_verifier.py`:10

**Failure scenario:** If wired, every CitationNode.article_ref arrives pre-converted to 'Article 26'. The route's downstream passes are built on the internal form — `reference_from_article_ref`, `_surface_anchor_citations`, `_collapse_parent_refs`, `_clamp_ref_head`, and the R274 curated-ref protection all match on `Art. N`. Refs would silently fail to match, collapse, or be protected. Item (3) additionally emits citations the live path deliberately drops, inflating the reference list — the over-citation regression the R281 clamp and R287 leaf-collapse exist to fight (official scorecard: pred:gold 2.23x).

**Verifier verdict** (confidence high): The code description is accurate and verified: app/engines/graph_rag/pipeline.py:12-24 is a line-for-line copy of _graph_rag_impl.py:7699-7731 (identical branches and constants 0.2/0.3/0.5/0.85/0.85/0.7) with the issue-#55 + R127 rationale docstring stripped, and it IS re-exported at package top level (__init__.py:36) alongside the live _compute_confidence. Both cited downstream thresholds are real (_MIN_CACHEABLE_CONFIDENCE = 0.3 at app/routes/regenold.py:288; the Stage-2 gate `if _ctx_conf < _stage2_min_conf` at _graph_rag_impl.py:6994).

BUT the finding's failure scenario is NOT reachable, so the severity is over-graded. It claims "the two silently diverge, and whichever is wired determines caching and Stage-2 routing." The pipeline copy is dead and cannot become the wired one by editing pipeline.py: the two functions have DIFFERENT NAMES, and the live callers (_graph_rag_impl.py:6993

**Suggested fix:** Delete citation_verifier.py, or (if the extraction is genuinely wanted) make it a verbatim move: drop `_format_article_ref` entirely, restore `gap.get("obligation_id", gap.get("id",""))` precedence, drop the synthesised-id fallback, then replace the inline block at _graph_rag_impl.py:7596-7632 with a call to it and prove byte-identity on the davidath bench. A 'refactor' that changes the wire format is not a refactor.

### 43. [MINOR] test_config_flags is a pure tautology — it cannot fail, and passes green while 2/4 gates diverge and 3 env names are fabricated

**File:** `tests/test_graph_rag_subpackage.py`:49

**Failure scenario:** Someone edits GraphRAGConfig (or migrates the engine onto it) and points a gate at the wrong env var or flips a default. test_config_flags stays green because isinstance(x, bool) holds for every possible wrong value. On a Railway deploy that reads STAGE2_PROVIDER_ENABLED — a variable nobody has ever set — the gate silently takes its hardcoded default instead of honouring P2P_GRAPH_RAG_ENABLE_STAGE2.

**Verifier verdict** (confidence high): Every technical claim is accurate and I reproduced all of them, but the severity is overstated on three independent grounds. (1) ALREADY FIXED ON MAIN: HEAD is 17b16d1, a child of the reviewed commit f08fbd3; `git diff f08fbd3 17b16d1` shows exactly those 3 files repaired with comments naming the same failure modes the finding describes, and all 3 cited tests now pass (3 passed in 0.16s). The concrete breakage is a transient state of an intermediate commit, not a live defect. (2) THE FINDING CONCEDES ITS OWN CONCRETE PART IS HARMLESS — "All three existing guards assert PRESENCE, so they fail loudly"; its actual claimed impact is a speculative FUTURE hazard. (3) THAT FUTURE HAZARD IS CONTRADICTED BY THE REPO'S EXISTING CONVENTION — the decisive rebuttal. The suite's only negative getsource assertion (tests/test_r109_answer_quality.py:131, `assert "narrow profiling support" not in src`) is

**Suggested fix:** Replace isinstance assertions with value assertions that pin the actual contract, e.g. `monkeypatch.delenv('REGENOLD_SUFFICIENT_CONTEXT', raising=False); assert cfg.sufficient_context_enabled is sufficient_context_enabled()` — i.e. assert the new config AGREES WITH the live gate function. Add a lint that every env name read by config.py appears at least once elsewhere in app/ or railway.toml (mirrors the existing ARTICLE_EXISTENCE import-time self_check pattern). Broaden test_compute_confidence 

### 44. [MINOR] Latent: reverse import order leaves 185 names uncopied and mock.patch NEVER restores — MagicMock leaks permanently into _impl

**File:** `app/engines/graph_rag/__init__.py`:40

**Failure scenario:** Anyone adds `import app.engines._graph_rag_impl` to a module that loads before app.engines.graph_rag — the natural next step when 'completing the migration'. From then on any test that patches an uncopied name (e.g. _get_anthropic_client, _two_stage_generate) leaves a MagicMock permanently in _impl.__dict__. Every subsequent test in the process silently exercises the mock instead of the engine: mass vacuous passes with no error, and the corruption is order-dependent so it reproduces only in full-suite runs.

**Verifier verdict** (confidence high): CONFIRMED as stated, including its own "pre-existing, not introduced by f08fbd3" framing — which I verified more rigorously than the reporter did. app/routes/regenold.py:5847 is `rag_res = ask_compliance_question(rag_req)` at 8-space indent inside `if rag_res is None:`, with no enclosing try (only narrow try blocks at 5566/ValidationError and 5638 precede it in the handler that starts at 5489), and app/main.py registers no catch-all Exception handler (only RateLimitExceeded + SlowAPIMiddleware). I reproduced the 500 on 5/5 injected faults. I tried twice to refute: (1) searched for a downstream guard — none exists, and in fact the route carries an explicit "never 500 the route" doctrine at ~20 other sites (1994, 2106, 3070), which strengthens rather than refutes the finding; (2) tested whether the refactor introduced a NEW exception surface via its one new request-path dependency (_graph_

**Suggested fix:** Add a __delattr__ override to _GraphRAGModule that mirrors the delete into _impl.__dict__ (symmetric with __setattr__ at line 54). Better: break the cycle so order cannot matter — move the GraphQuery/GraphContext import in _graph_rag_impl.py:1125 to import the submodule directly (`from app.engines.graph_rag import models` is still cyclic; import a neutral module such as app.engines.graph_rag_models instead), or have __init__ re-run the copy loop lazily. Add a regression test that imports _graph_
