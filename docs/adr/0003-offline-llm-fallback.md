# ADR 0003 — LLM with mandatory offline fallback (graceful degradation)

**Status:** accepted · 2026-11-16

**Context.** LLMs add explanation quality and robustness to unseen phrasings, but paid APIs
violate the budget, and free APIs rate-limit/fail. A demo that 500s when Gemini throttles is
worse than a dumber pipeline that always answers.

**Decision.** The LLM is an *enhancement, not a dependency*. `GEMINI_API_KEY` unset or any
error ⇒ deterministic `FallbackExplainer` (pattern/keyword + red-flag library) answers in the
same `LLMVerdict` schema. Output is always validated by Pydantic before use.

**Trade-offs.**
- ✅ Always-available; identical interface; LLM failure is a metric, not an outage.
- ✅ Fallback explanations cite the same red-flag library → consistent UX.
- ❌ Fallback prose is templated and less fluent; keyword coverage has blind spots
     (see model card). Mitigation: red-flag library is versioned and tested.
- ❌ Two paths to maintain — kept honest by the golden-set test (`make evaluate`).

**Rejected alternatives.** Hard dependency on paid API (cost/privacy); no LLM at all
(weaker explanations on novel phrasing); LLM-only with no ML (slower, costlier per call).

**Revisit when.** A free, reliable, hosted LLM endpoint is available → promote it to primary,
keep the fallback as circuit-breaker.
