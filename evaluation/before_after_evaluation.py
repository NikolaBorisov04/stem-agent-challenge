"""
Before/After Evaluation
Compares generic stem agent vs. specialized agent on the same tasks.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import StemAgent, LLMProvider, LLMMode


class BeforeAfterEvaluator:
    """Evaluates stem agent before and after specialization."""

    def __init__(self, use_openai=True):
        """Initialize evaluator."""
        self.api_key = None
        mode = LLMMode.OPENAI if use_openai else LLMMode.MOCK

        if use_openai:
            import os
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                print("⚠️  No OPENAI_API_KEY found, using mock mode")
                mode = LLMMode.MOCK

        self.llm = LLMProvider(mode=mode, api_key=self.api_key if use_openai else None)
        self.results = {
            "before": {},
            "after": {},
            "comparison": {}
        }

    def run_before_evaluation(self, api_description: str, tasks: list) -> dict:
        """
        BEFORE: Generic agent without specialization.
        Tests how the stem agent performs on security audit tasks
        WITHOUT going through specialization.
        """
        print("\n" + "="*70)
        print("BEFORE: Generic Stem Agent (No Specialization)")
        print("="*70)

        agent = StemAgent(llm_provider=self.llm, domain="api_security")

        # Don't specialize - use the stem agent directly
        before_results = {
            "mode": "generic",
            "specialization": None,
            "tasks": []
        }

        for i, task in enumerate(tasks, 1):
            print(f"\n[Task {i}] {task[:60]}...")

            # Generic agent tries to execute without specialization
            result = agent.execute_task(task)

            # Measure quality
            response = result.get("response", "")
            quality = self._measure_response_quality(response, generic=True)

            task_result = {
                "task": task,
                "response_length": len(response),
                "has_persona": "persona" in response.lower(),
                "has_tools": "tool" in response.lower() or "scanning" in response.lower(),
                "has_techniques": "technique" in response.lower() or "test" in response.lower(),
                "quality_score": quality,
                "depth": "shallow" if len(response) < 300 else "moderate" if len(response) < 800 else "deep"
            }
            before_results["tasks"].append(task_result)
            print(f"  Quality: {quality:.0%} | Depth: {task_result['depth']}")

        return before_results

    def run_after_evaluation(self, api_description: str, tasks: list) -> dict:
        """
        AFTER: Specialized agent after differentiation.
        Same tasks, but now with full specialization pipeline.
        """
        print("\n" + "="*70)
        print("AFTER: Specialized Agent (Post-Differentiation)")
        print("="*70)

        agent = StemAgent(llm_provider=self.llm, domain="api_security")

        # Differentiate (5-stage pipeline)
        print("\n[Specialization Pipeline]")
        success, spec_config, validation = agent.differentiate(
            api_description,
            min_confidence=0.7
        )

        after_results = {
            "mode": "specialized",
            "specialization": spec_config if success else None,
            "validation_confidence": validation.confidence,
            "tasks": []
        }

        if not success:
            print("❌ Specialization failed!")
            return after_results

        print(f"\n✅ Specialization successful!")
        print(f"   Persona: {spec_config.get('persona')}")
        print(f"   Tools: {', '.join(spec_config.get('tools', [])[:3])}...")
        print(f"   Confidence: {validation.confidence:.0%}")

        # Now execute same tasks with specialized agent
        print("\n[Task Execution with Specialization]")
        for i, task in enumerate(tasks, 1):
            print(f"\n[Task {i}] {task[:60]}...")

            result = agent.execute_task(task)
            response = result.get("response", "")
            quality = self._measure_response_quality(
                response,
                generic=False,
                spec_config=spec_config
            )

            task_result = {
                "task": task,
                "response_length": len(response),
                "mentions_persona": spec_config.get("persona", "").lower() in response.lower(),
                "mentions_tools": any(
                    tool.lower() in response.lower()
                    for tool in spec_config.get("tools", [])
                ),
                "mentions_techniques": any(
                    tech.lower() in response.lower()
                    for tech in spec_config.get("techniques", [])
                ),
                "quality_score": quality,
                "depth": "shallow" if len(response) < 300 else "moderate" if len(response) < 800 else "deep",
                "actionability": self._measure_actionability(response)
            }
            after_results["tasks"].append(task_result)
            print(f"  Quality: {quality:.0%} | Actionability: {task_result['actionability']}")

        return after_results

    def _measure_response_quality(self, response: str, generic=False, spec_config=None) -> float:
        """Score response quality (0.0 to 1.0)."""
        score = 0.0
        checks = 0

        # Check 1: Length (longer = more detailed)
        checks += 1
        if len(response) > 200:
            score += 0.5
        if len(response) > 800:
            score += 0.5

        # Check 2: Technical depth
        checks += 1
        technical_terms = [
            "authentication", "authorization", "encryption", "jwt",
            "sql", "injection", "cors", "csrf", "xss", "csrf",
            "vulnerability", "exploit", "risk", "compliance"
        ]
        if sum(1 for term in technical_terms if term in response.lower()) >= 3:
            score += 1.0

        # Check 3: Specificity
        checks += 1
        if "endpoint" in response.lower() or "post" in response.lower():
            score += 0.5
        if "tool" in response.lower() or "scanner" in response.lower():
            score += 0.5

        # Check 4: Actionability (Specialized only)
        if not generic and spec_config:
            checks += 1
            techniques = spec_config.get("techniques", [])
            if any(tech.lower() in response.lower() for tech in techniques):
                score += 1.0

        return min(1.0, score / checks)

    def _measure_actionability(self, response: str) -> str:
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

    def compare_results(self, before: dict, after: dict) -> dict:
        """Generate comparison metrics."""
        print("\n" + "="*70)
        print("COMPARISON: Before vs After")
        print("="*70)

        comparison = {}

        # Task-level comparison
        print("\n📊 Task-Level Metrics:")
        print("-" * 70)

        before_qualities = [t.get("quality_score", 0) for t in before.get("tasks", [])]
        after_qualities = [t.get("quality_score", 0) for t in after.get("tasks", [])]

        avg_before_quality = sum(before_qualities) / max(len(before_qualities), 1)
        avg_after_quality = sum(after_qualities) / max(len(after_qualities), 1)

        comparison["quality_improvement"] = avg_after_quality - avg_before_quality
        comparison["quality_improvement_pct"] = (
            (avg_after_quality - avg_before_quality) / max(avg_before_quality, 0.01) * 100
        )

        print(f"Average Quality Score:")
        print(f"  Before: {avg_before_quality:.0%}")
        print(f"  After:  {avg_after_quality:.0%}")
        print(f"  Improvement: +{comparison['quality_improvement_pct']:.0f}%")

        # Response length comparison
        before_lengths = [t.get("response_length", 0) for t in before.get("tasks", [])]
        after_lengths = [t.get("response_length", 0) for t in after.get("tasks", [])]

        avg_before_len = sum(before_lengths) / max(len(before_lengths), 1)
        avg_after_len = sum(after_lengths) / max(len(after_lengths), 1)

        comparison["response_depth"] = {
            "before_avg_chars": int(avg_before_len),
            "after_avg_chars": int(avg_after_len),
            "increase": int(avg_after_len - avg_before_len)
        }

        print(f"\nResponse Depth:")
        print(f"  Before: {avg_before_len:.0f} chars")
        print(f"  After:  {avg_after_len:.0f} chars")
        print(f"  Increase: +{avg_after_len - avg_before_len:.0f} chars")

        # Specialization utilization
        if after.get("specialization"):
            print(f"\nSpecialization Utilization:")
            spec = after["specialization"]
            personas_used = sum(
                1 for t in after.get("tasks", [])
                if t.get("mentions_persona", False)
            )
            tools_used = sum(
                1 for t in after.get("tasks", [])
                if t.get("mentions_tools", False)
            )
            print(f"  Tools mentioned: {tools_used}/{len(after.get('tasks', []))} tasks")
            print(f"  Persona consistency: {personas_used}/{len(after.get('tasks', []))} tasks")

        # Actionability (After only)
        after_actionabilities = [
            t.get("actionability", "low") for t in after.get("tasks", [])
        ]
        high_action = sum(1 for a in after_actionabilities if a == "high")
        med_action = sum(1 for a in after_actionabilities if a == "medium")

        comparison["actionability"] = {
            "high": high_action,
            "medium": med_action,
            "total_tasks": len(after_actionabilities)
        }

        print(f"\nActionability (After):")
        print(f"  High: {high_action}/{len(after_actionabilities)}")
        print(f"  Medium: {med_action}/{len(after_actionabilities)}")

        return comparison

    def run_full_evaluation(self, api_description: str, tasks: list) -> dict:
        """Run complete before/after evaluation."""
        print("\n" + "="*70)
        print("STEM AGENT: BEFORE/AFTER EVALUATION")
        print("="*70)

        before = self.run_before_evaluation(api_description, tasks)
        after = self.run_after_evaluation(api_description, tasks)
        comparison = self.compare_results(before, after)

        full_results = {
            "before": before,
            "after": after,
            "comparison": comparison
        }

        return full_results


def main():
    """Run before/after evaluation."""

    # Sample API for evaluation
    api_description = """
    API: E-commerce Platform REST API
    Endpoints:
    - POST /api/v1/users/login - User authentication with JWT
    - GET /api/v1/products - List products
    - POST /api/v1/orders - Create order
    - GET /api/v1/orders/{id} - Get order details
    - PUT /api/v1/users/profile - Update user profile

    Security concerns:
    - JWT token expiration and refresh logic
    - Rate limiting on authentication endpoints
    - SQL injection in product search
    - CORS configuration
    - Authorization checks on user endpoints
    """

    # Tasks to evaluate
    tasks = [
        "Analyze POST /api/v1/users/login endpoint for authentication vulnerabilities. Look for JWT issues, rate limiting, and brute force protection.",
        "Audit POST /api/v1/orders endpoint. Check for authorization issues, input validation, and transaction integrity.",
        "Review GET /api/v1/products endpoint for SQL injection risks and input sanitization issues."
    ]

    # Run evaluation (default: use OpenAI API if available)
    evaluator = BeforeAfterEvaluator(use_openai=True)
    results = evaluator.run_full_evaluation(api_description, tasks)

    # Save results
    output_path = Path("evaluation/before_after_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print(f"✅ Evaluation complete! Results saved to: {output_path}")
    print("="*70)

    return results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
