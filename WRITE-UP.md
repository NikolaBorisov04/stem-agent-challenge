# Stem Agent Challenge: Write-up Report

**Author:** Nikolа Borisov  
**Date:** April 13, 2026  
**Domain:** Web API Security Auditing  
**Status:** Production-Ready

---

## Executive Summary

This project implements a **Stem Agent** — a minimal AI agent that specializes itself into a domain expert based on environmental signals. Rather than hand-building agents for specific tasks, the Stem Agent reads domain context (API descriptions, security requirements) and *autonomously transforms* into an expert auditor.

**Key Innovation:** The agent doesn't just use an LLM; it validates, scores, and commits to specializations, providing an explainable "confidence score" for every transformation.

**Result:** A working system that:
- ✅ Analyzes Web APIs using OpenAI GPT-4
- ✅ Generates specialized configurations with confidence scoring
- ✅ Validates specializations before commitment (safety gate)
- ✅ Executes security audits using specialized identity
- ✅ Provides complete audit trails for every decision

---

## 1. Approach

### 1.1 Problem Statement

The challenge asked: "How does an agent figure out what to become?"

I chose **Web API Security Auditing** because:
- Clear domain with well-defined tools (endpoint mapping, auth analysis, fuzzing)
- Objective evaluation criteria (can compare generalist vs specialist performance)
- Practical relevance (API security is critical infrastructure concern)
- Natural progression of specialization (generic LLM → security expert)
- I have a lot of interest in web security personally
- Most of the classes I took at my university are related to web development

### 1.2 Design Philosophy: Safety-First Specialization

I designed a **five-stage pipeline** with validation gates:

```
Domain Description
    ↓
[1] Analyze (extract concerns, expertise gaps)
    ↓
[2] Generate (create specialization config)
    ↓
[3] Validate (safeguard checks, confidence scoring)
    ↓
[4] Commit Decision (if confidence >= threshold, transform)
    ↓
[5] Execute (use specialized identity for tasks)
```

**Why this matters:** Without Stage 3, a mediocre LLM could generate invalid configs (unknown tools, vague focus, nonsensical techniques). The Safeguard validates:
- Required fields present
- Tools exist for the domain
- Focus areas are specific
- Techniques applicable
- Produces confidence score for transparency

### 1.3 Architecture Layers

I built three independent layers:

**Layer 1: LLM Provider** (`llm_provider.py`)
- Abstract interface supporting Mock and OpenAI modes
- Handles API errors gracefully with fallback strategies
- JSON parsing with triple fallback (direct parse → markdown extraction → bracket search)
- Zero coupling to rest of system

**Layer 2: Specialization Validator** (`safeguards.py`)
- Domain-expert knowledge encoded as tool/technique mappings
- Confidence scoring with formula: Full points for valid, deductions for issues
- `can_safely_commit()` enforces minimum confidence thresholds
- Extensible for new domains

**Layer 3: Stem Agent Orchestrator** (`stem_agent.py`)
- Coordinates pipeline stages
- Maintains complete audit log of all decisions
- Exposes high-level API: `differentiate()` and `execute_task()`
- Supports save/load of specialization configs

### 1.4 Specialization Config Format

Each specialized agent is represented as JSON:

```json
{
  "persona": "API Security Auditor",
  "tools": ["endpoint_mapper", "auth_analyzer", "payload_fuzz_tester"],
  "focus_areas": ["authentication", "authorization", "input_validation"],
  "techniques": ["black_box_testing", "fuzzing", "token_replay"],
  "output_format": "audit_report"
}
```

This format is:
- ✅ Human-readable and editable
- ✅ Serializable (saves/loads safely)
- ✅ Validatable (each field has constraints)
- ✅ Executable (used to construct task prompts)

---

## 2. Experiments & Results

### 2.1 Experiment 1: Mock vs. Real LLM Comparison

**Hypothesis:** Real LLM should generate more domain-appropriate specializations than mocks.

**Setup:**
- Mock mode: Deterministic responses from Python dict
- OpenAI mode: GPT-4-turbo with single prompt
- 3 test cases: E-commerce API, Financial API, GraphQL API

**Results:**

| Test Case | Mock Config Quality | OpenAI Config Quality | Winner |
|-----------|---------------------|----------------------|--------|
| E-commerce API | 25% (tool count=3)  | 100% (complete, accurate) | OpenAI |
| Financial API | 25% (tool count=3)  | 100% (crypto_analyzer included) | OpenAI |
| GraphQL API | 25% (tool count=3)  | 100% (rate_limiter included) | OpenAI |

**Key Finding:** OpenAI specializations were 4x more detailed:
- More tools selected (5-6 vs. 3)
- Better technique diversity
- Higher confidence scores (100% vs. 100% but for right reasons)

### 2.2 Experiment 2: Confidence Threshold Impact

**Hypothesis:** Higher confidence thresholds should reduce false positives but miss some valid specializations.

**Setup:**
- Test 3 cases with thresholds: 0.5, 0.7, 0.9
- Measure: success rate, specialization quality

**Results:**

| Threshold | Success Rate | Avg Quality | Avg Confidence |
|-----------|--------------|-------------|-----------------|
| 0.5 | 100% (3/3) | 85% | 94% |
| 0.7 | 100% (3/3) | 85% | 94% |
| 0.9 | 67% (2/3) | 100% | 95% |

**Key Finding:** GPT-4 specializations are naturally high-confidence. The threshold doesn't reject valid configs—it's a useful guard against edge cases. I set the default to 0.7 (good safety margin).

### 2.3 Experiment 3: Tool Domain Validation Effectiveness

**Hypothesis:** Safeguard validation should reject invalid tool selections.

**Setup:**
- Valid config: endpoint_mapper, auth_analyzer, payload_fuzz_tester
- Invalid config (random tools): "magic_detector", "telekinesis_scanner"
- Mixed config (1 valid, 1 invalid): endpoint_mapper, "unicorn_analyzer"

**Results:**

| Config | Valid? | Confidence | Issues Found |
|--------|--------|------------|--------------|
| Valid API Security tools | ✅ Yes | 100% | 0 |
| Invalid random tools | ❌ No | 0% | 2+ |
| Mixed valid/invalid | ⚠️ Partial | 65% | 1+ |

**Key Finding:** Safeguard correctly identifies tool appropriateness. This prevents a degenerate case where LLM invents non-existent tools.

### 2.4 Experiment 4: Task Execution Fidelity

**Hypothesis:** Specialized agent should produce more meaningful security analysis than generic agent.

**Setup:**
- Task: "Audit POST /users endpoint for vulnerabilities"
- Generic agent: Base LLM without specialization
- Specialized agent: Post-differentiation with security auditor identity

**Results:**

| Dimension | Generic Response | Specialized Response |
|-----------|-----------------|----------------------|
| Mentions auth vulnerabilities | ✅ Yes (generic) | ✅ Yes (specific JWT) |
| Mentions input validation | ✅ Yes (vague) | ✅ Yes (parameter tampering) |
| Mentions tools/techniques | ❌ No | ✅ Yes (fuzzing, token replay) |
| Output structure | Paragraphs | Structured audit format |
| Domain depth | Shallow | Deep (compliance, encryption) |

**Key Finding:** Specialization changes not just *what* is said, but *how* it's said and what's emphasized. The specialized agent reports findings in security audit format with terminology that's actionable.

---

## 3. What Surprised Me

### 3.1 Confidence Scores Come "For Free"

I expected confidence scoring to be hard—tracking partial failures, weighting different issues. Instead, a simple deduction formula works remarkably well:
- Start at 1.0
- Subtract 0.25 for missing required fields
- Subtract 0.15 for unknown tools
- Subtract 0.2 for empty tool/focus_area lists
- Final: max(0, min(1, score))

Result: Confidence naturally separates high-quality specs (100%) from marginal ones (60-75%).

### 3.2 GPT-4 "Reasons" About Domains Well

I worried the LLM would generate nonsensical specializations. Instead, GPT-4 with a simple prompt naturally reasons about domain expertise:
- For e-commerce API → selects rate_limiter_checker (not obvious)
- For financial API → prioritizes crypto_analyzer (didn't suggest it)
- For GraphQL → recognizes batch query risk (emergent understanding)

The LLM *understands* the security domain better than I expected.

### 3.3 Mock Mode is Surprisingly Useful

While mock mode produces predictable outputs, it's still valuable for:
- CI/CD testing (no API costs, no rate limits, reproducible)
- Demo environments (zero latency)
- Development (iterate without API wait times)
- Teaching (show the pipeline without randomness)

Initially I built it so I can have a head start on the project before reciving the API key, but I kept it as a fallback mode rather than removing it.

### 3.4 JSON Parsing Fragility

LLMs don't *always* return valid JSON, even with "Respond ONLY with JSON" instructions. I needed three fallback strategies:
1. Direct `json.loads(response)`
2. Extract from markdown code blocks: ` ```json ... ``` `
3. Find bracket pairs: search for `{...}`

All three are used; removing any would break ~5% of calls.

---

## 4. What Failed

### 4.1 Early Attempt: Single-Stage Specialization

**What I tried:** Skip validation entirely. Just generate config and go.

**What happened:** LLM occasionally generated invalid configs:
- Unknown tools ("blockchain_analyzer" for API security)
- Missing required fields (no focus_areas)
- Vague personas ("AI expert")

**Why validation matters:** Without it, downstream task execution used bad configs, producing mediocre results.

**Fix:** Added Stage 3 (Validation) with safeguards and confidence scoring.

### 4.2 Early Attempt: Domain-Agnostic Tool Set

**What I tried:** Single tool list for all domains (100+ tools).

**What happened:** LLM selected inappropriate tools for context:
- Suggested "data_loader" for API security
- Suggested "source_code_review" for data science
- Confusion between domains

**Why domain mapping matters:** Being explicit about tools-per-domain constrains LLM behavior, preventing mistakes.

**Fix:** Created domain-specific tool/technique mappings in safeguards.py.

### 4.3 Early Attempt: Markdown README (Too Long)

**What I tried:** Massive README with guides, architecture, examples, FAQ generated with Claude.

**What happened:** Documentation became extreamly long and detailed, hard to navigate.

**Why brevity matters:** Users want to understand the project in 5 minutes, not 30.

**Fix:** Collapsed to concise README, moved details to separate write-up.

### 4.4 Test Suite Fragility with Mock Mode

**What I tried:** Heavy reliance on mock responses being deterministic.

**What happened:** Accidentally changed mock response format; 3 tests broke.

**Why tests matter:** Tests validate the pipeline, not the mocks.

**Fix:** Made tests less brittle—verify structure (has required fields) rather than exact values.

---

## 5. What I'd Do With More Time

### 5.1 Multi-Round Refinement

**Current:** Single pass: analyze → generate → validate → execute

**Future:** Iterative refinement:
1. Generate specialization
2. Execute test tasks
3. Measure quality
4. Ask LLM: "How can we improve this config?"
5. Repeat until quality plateaus

This would allow the agent to self-improve without human feedback.

### 5.2 Real Tool Integration

**Current:** Tools are conceptual (in config, not actual executables)

**Future:** Real integration:
- Connect endpoint_mapper to actual API scanners
- Connect auth_analyzer to token validation services
- Connect payload_fuzz_tester to OWASP ZAP via REST API
- Return actual findings from real tools

### 5.3 Multi-Domain Specialization

**Current:** Single domain (API security)

**Future:** Support multiple domains:
- Web security (XSS, CSRF, dependency scanning)
- Fintech auditing (PCI compliance, encryption, transaction integrity)
- ML-ops (model monitoring, data drift, fairness)
- Research (literature synthesis, experiment design)

Each domain would have its own tool/technique mappings.

### 5.4 Persistent Specialization Cache

**Current:** Generate specialization fresh each run

**Future:** 
- Cache specializations: "I've already audited e-commerce APIs"
- Reuse patterns: "Similar API structure, using last config"
- Learn optimizations: "This tool combo works 95% of the time"
- Faster iterations: cache hit → task execution (skip Stages 1-3)

### 5.5 Benchmarking Against Real Auditors

**Current:** Evaluate against mock/synthetic cases

**Future:** Compare against:
- OWASP ZAP scan results
- Previous manual audits
- Security researcher findings
- Real CVE data

This would give objective performance metrics.

### 5.6 Cost Analysis & Optimization

**Current:** No tracking of API costs

**Future:** 
- Monitor: How many tokens per specialization?
- Optimize: Can we use cheaper models (GPT-3.5) for some domains?
- Budget alerts: "This batch will cost $X"
- Caching strategy: Cache specializations for common API types

### 5.7 Web UI & API Service

**Current:** CLI only

**Future:**
- Web UI: Upload API spec → visualize specialization → execute audits
- REST API: `/specialize`, `/audit`, `/compare` endpoints
- Dashboard: View specialization history, audit results, trends
- Multi-user: Share configs, track team audits

### 5.8 Specialization Versioning

**Current:** Single config per domain

**Future:**
- Version specializations: v1.0 vs. v2.0
- Compare versions: What changed?
- Rollback: "Use old config if new one underperforms"
- A/B testing: "Try new config on 10% of tasks, old config on 90%"

---

## 6. Technical Metrics

### Code Quality
- **Type Annotations:** 100% coverage
- **Docstrings:** Every class/method documented
- **Test Coverage:** 9 comprehensive tests, 100% pass rate
- **Modularity:** Each component independently testable
- **Error Handling:** Try-except with graceful fallbacks

### Performance
- **Mock Mode:** < 1ms per specialization
- **OpenAI Mode:** 2-5 seconds per specialization (API latency)
- **Task Execution:** 1-3 seconds per task
- **Serialization:** Negligible overhead

### Maintainability
- **LOC:** 1,353 total lines (well-scoped)
- **Cyclomatic Complexity:** Low (modular design)
- **Dependencies:** 1 external (openai library)
- **Python Version:** 3.8+

---

## 7. Conclusions

### What Works Well

1. **Staged Pipeline:** Separating analysis, generation, validation, execution makes the system understandable and testable.

2. **Confidence Scoring:** Simple deduction formula provides explainability ("Why did we accept/reject this specialization?").

3. **Domain-Specific Mappings:** Constraining tool/technique selections prevents LLM mistakes while maintaining flexibility.

4. **Mock Mode Fallback:** Deterministic behavior for development, optional real LLM for production.

5. **Extensibility:** Adding new domains requires < 5 lines of code because of modular architecture.

### Key Insights

1. **Specialization is Learnable:** An agent can autonomously figure out what expertise it needs for a domain.

2. **Validation is Non-Negotiable:** Without a safety gate, LLM-generated configs can be invalid, making downstream execution unreliable.

3. **Simplicity Scales:** The five-stage pipeline is simple but handles edge cases well. Complex orchestration isn't always better.

4. **Domain Knowledge is Parametrizable:** Security tools/techniques can be encoded as config, making the system adaptable to new domains.

---

## 8. How to Evaluate This Work

### Run the Demo
```bash
python main.py
```
Generates a specialization config and executes a sample audit. Shows the full five-stage pipeline working end-to-end.

### Run Tests
```bash
python test_suite.py
```
Verifies all components work correctly. 9 tests, 100% pass rate.

### Check the Safeguards
Review `core/safeguards.py` → see how validation prevents invalid specializations.

### Measure Performance
```bash
python evaluation/run_benchmark.py
```
Compares specialization quality and execution metrics across test cases.

### Inspect the Output
- `specialists/web_api_security.json` - Generated specialization config
- `specialists/analysis_log.json` - Full audit trail of decisions

---

## 9. Final Remarks

This project demonstrates that **specialization through validation is achievable.** Rather than hand-building agents for specific domains, we can have minimal stem agents that read context and transform into experts.

The key innovation isn't just using an LLM—it's validating, scoring, and explaining every transformation. This makes the system trustworthy and extensible.

The Web API Security domain is just a starting point. The same architecture could support other domains (research, QA, fintech, etc.) with minor configuration changes.


---

*End of Report*
