"""
Comprehensive Before/After Evaluation
Compares:
- BEFORE: Vanilla LLM (no specialization, no framework)
- AFTER: Specialized Stem Agent (with 5-stage pipeline)
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import StemAgent, LLMProvider, LLMMode


def evaluate_vanilla_llm(llm_provider, tasks: list) -> dict:
    """
    BEFORE: Use vanilla LLM directly without specialization/framework.
    Shows what raw LLM responses look like without guided specialization.
    """
    print("\n" + "="*70)
    print("BEFORE: Vanilla LLM (No Specialization, No Framework)")
    print("="*70)

    results = {
        "mode": "vanilla_llm",
        "tasks": []
    }

    for i, task in enumerate(tasks, 1):
        print(f"\n[Task {i}] {task[:60]}...")

        # Direct LLM call - no specialization, no framework
        response = llm_provider.call(
            system_prompt="You are a security expert. Answer the following question about API security.",
            user_message=task,
            temperature=0.7,
            max_tokens=2000
        )

        quality_score = measure_quality(response, specialized=False)
        actionability = measure_actionability(response)

        task_result = {
            "task": task,
            "response_length": len(response),
            "quality_score": quality_score,
            "depth": get_depth_category(len(response)),
            "actionability": actionability,
            "response_preview": response[:200]
        }
        results["tasks"].append(task_result)
        print(f"  Quality: {quality_score:.0%} | Actionability: {actionability}")

    return results


def evaluate_specialized_agent(llm_provider, api_description: str, tasks: list) -> dict:
    """
    AFTER: Use Stem Agent with full 5-stage specialization pipeline.
    Shows specialized agent performance with validated specialization.
    """
    print("\n" + "="*70)
    print("AFTER: Specialized Stem Agent (5-Stage Pipeline)")
    print("="*70)

    agent = StemAgent(llm_provider=llm_provider, domain="api_security")

    # Run differentiation pipeline
    print("\n[Differentiation Pipeline]")
    success, spec_config, validation = agent.differentiate(api_description, min_confidence=0.7)

    results = {
        "mode": "specialized_agent",
        "success": success,
        "specialization": spec_config,
        "validation_confidence": validation.confidence,
        "tasks": []
    }

    if not success:
        print("❌ Specialization failed")
        return results

    print(f"\n✅ Specialized as: {spec_config.get('persona')}")
    print(f"   Tools: {', '.join(spec_config.get('tools', [])[:3])}...")

    # Execute tasks with specialized agent
    print("\n[Task Execution]")
    for i, task in enumerate(tasks, 1):
        print(f"\n[Task {i}] {task[:60]}...")

        result = agent.execute_task(task)
        response = result.get("response", "")

        quality_score = measure_quality(response, specialized=True, spec_config=spec_config)
        actionability = measure_actionability(response)

        task_result = {
            "task": task,
            "response_length": len(response),
            "quality_score": quality_score,
            "depth": get_depth_category(len(response)),
            "actionability": actionability,
            "uses_specialized_tools": any(
                tool.lower() in response.lower()
                for tool in spec_config.get("tools", [])
            ),
            "response_preview": response[:200]
        }
        results["tasks"].append(task_result)
        print(f"  Quality: {quality_score:.0%} | Actionability: {actionability}")

    return results


def measure_quality(response: str, specialized=False, spec_config=None) -> float:
    """Score response quality (0.0 to 1.0)."""
    score = 0.0
    max_score = 0.0

    # Check 1: Length
    max_score += 1.0
    if len(response) > 200:
        score += 0.5
    if len(response) > 800:
        score += 0.5

    # Check 2: Technical depth
    max_score += 1.0
    technical_terms = [
        "authentication", "authorization", "encryption", "jwt",
        "sql", "injection", "cors", "xss", "vulnerability",
        "exploit", "risk", "compliance", "token"
    ]
    term_count = sum(1 for term in technical_terms if term in response.lower())
    score += min(1.0, term_count / 3)

    # Check 3: Specific recommendations
    max_score += 1.0
    rec_terms = ["implement", "fix", "use", "configure", "enable", "patch"]
    if any(term in response.lower() for term in rec_terms):
        score += 1.0

    # Check 4: Specialized tool usage
    if specialized and spec_config:
        max_score += 1.0
        tools = spec_config.get("tools", [])
        if any(tool.lower() in response.lower() for tool in tools):
            score += 1.0

    return min(1.0, score / max_score) if max_score > 0 else 0.0


def measure_actionability(response: str) -> str:
    """Measure how actionable the findings are."""
    action_terms = [
        "use", "implement", "fix", "apply", "configure",
        "enable", "disable", "update", "patch", "recommend"
    ]
    action_count = sum(1 for term in action_terms if term in response.lower())

    if action_count >= 3:
        return "high"
    elif action_count >= 1:
        return "medium"
    else:
        return "low"


def get_depth_category(length: int) -> str:
    """Categorize response depth by character count."""
    if length < 300:
        return "shallow"
    elif length < 800:
        return "moderate"
    else:
        return "deep"


def generate_comparison(before: dict, after: dict) -> dict:
    """Generate detailed comparison."""
    print("\n" + "="*70)
    print("COMPARISON: Before vs After")
    print("="*70)

    comparison = {}

    # Quality comparison
    before_qualities = [t["quality_score"] for t in before["tasks"]]
    after_qualities = [t["quality_score"] for t in after["tasks"]]

    avg_before = sum(before_qualities) / len(before_qualities)
    avg_after = sum(after_qualities) / len(after_qualities)

    comparison["quality_before"] = avg_before
    comparison["quality_after"] = avg_after
    comparison["quality_improvement"] = avg_after - avg_before
    comparison["quality_improvement_pct"] = (
        ((avg_after - avg_before) / max(avg_before, 0.01)) * 100
    )

    print(f"\n📊 Response Quality:")
    print(f"  Before: {avg_before:.0%}")
    print(f"  After:  {avg_after:.0%}")
    print(f"  Improvement: +{comparison['quality_improvement_pct']:.0f}%")

    # Depth comparison
    before_lengths = [t["response_length"] for t in before["tasks"]]
    after_lengths = [t["response_length"] for t in after["tasks"]]

    avg_before_len = sum(before_lengths) / len(before_lengths)
    avg_after_len = sum(after_lengths) / len(after_lengths)

    comparison["depth_before_chars"] = int(avg_before_len)
    comparison["depth_after_chars"] = int(avg_after_len)
    comparison["depth_increase"] = int(avg_after_len - avg_before_len)

    print(f"\n📝 Response Depth:")
    print(f"  Before: {avg_before_len:.0f} chars average")
    print(f"  After:  {avg_after_len:.0f} chars average")
    print(f"  Increase: +{avg_after_len - avg_before_len:.0f} chars (+{(avg_after_len/max(avg_before_len, 1) - 1)*100:.0f}%)")

    # Actionability comparison
    before_action = [t["actionability"] for t in before["tasks"]]
    after_action = [t["actionability"] for t in after["tasks"]]

    before_high = sum(1 for a in before_action if a == "high")
    after_high = sum(1 for a in after_action if a == "high")

    comparison["actionability_before_high"] = before_high
    comparison["actionability_after_high"] = after_high

    print(f"\n⚡ Actionability:")
    print(f"  Before: {before_high}/{len(before_action)} tasks high-actionability")
    print(f"  After:  {after_high}/{len(after_action)} tasks high-actionability")

    # Specialization benefit
    if after.get("specialization"):
        print(f"\n🎯 Specialization Details:")
        print(f"  Persona: {after['specialization'].get('persona')}")
        print(f"  Tools Selected: {len(after['specialization'].get('tools', []))}")
        print(f"  Validation Confidence: {after['validation_confidence']:.0%}")

    return comparison


def main():
    """Run comprehensive before/after evaluation."""

    # Sample API description
    api_description = """
    API: E-commerce Platform REST API
    Endpoints:
    - POST /api/v1/users/login - User authentication with JWT
    - GET /api/v1/products - List products
    - POST /api/v1/orders - Create order
    - GET /api/v1/orders/{id} - Get order details
    - PUT /api/v1/users/profile - Update user profile

    Security requirements:
    - JWT-based authentication
    - Rate limiting (100 req/min per IP)
    - SQL parameterized queries
    - CORS enabled for specified domains
    """

    # Tasks to evaluate
    tasks = [
        "Analyze POST /api/v1/users/login for authentication vulnerabilities. Consider JWT issues, rate limiting, and brute force attacks.",
        "Audit POST /api/v1/orders for authorization and data validation issues.",
        "Review GET /api/v1/products for SQL injection risks."
    ]

    # Initialize LLM (auto-detect OpenAI API)
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    mode = LLMMode.OPENAI if api_key else LLMMode.MOCK
    llm = LLMProvider(mode=mode, api_key=api_key if api_key else None)

    # Run evaluations
    print("\n" + "="*70)
    print("STEM AGENT BEFORE/AFTER EVALUATION")
    print("Domain: Web API Security Auditing")
    print("="*70)

    before = evaluate_vanilla_llm(llm, tasks)
    after = evaluate_specialized_agent(llm, api_description, tasks)
    comparison = generate_comparison(before, after)

    # Compile results
    full_results = {
        "metadata": {
            "domain": "api_security",
            "evaluation_type": "vanilla_vs_specialized",
            "tasks_count": len(tasks)
        },
        "before": before,
        "after": after,
        "comparison": comparison
    }

    # Save results
    output_path = Path("evaluation/before_after_comparison.json")
    with open(output_path, "w") as f:
        json.dump(full_results, f, indent=2)

    print("\n" + "="*70)
    print(f"✅ Evaluation complete!")
    print(f"   Results saved to: {output_path}")
    print("="*70)

    return full_results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
