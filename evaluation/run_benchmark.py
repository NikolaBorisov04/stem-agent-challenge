"""
Evaluation Module: run_benchmark.py
Compares Before (Stem) and After (Specialized) performance.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import StemAgent, LLMProvider, LLMMode


@dataclass
class BenchmarkMetrics:
    """Container for benchmark metrics."""
    specialization_quality: float
    safeguard_confidence: float
    task_completion_success: bool
    execution_time: float


class SpecializationBenchmark:
    """
    Evaluates Stem Agent specialization quality and task execution.
    Compares performance before and after specialization.
    """

    def __init__(self, llm_provider: LLMProvider = None):
        """Initialize benchmark runner."""
        self.llm_provider = llm_provider or LLMProvider(mode=LLMMode.MOCK)
        self.results: Dict[str, Dict] = {}

    def evaluate_specialization_quality(
        self, spec_config: Dict, expected_spec: Dict = None
    ) -> float:
        """
        Score the quality of a specialization.

        Returns:
            Quality score 0.0 to 1.0
        """
        score = 0.0
        checks = 0

        # Check 1: Required fields present
        required = ["persona", "tools", "focus_areas", "output_format"]
        for field in required:
            checks += 1
            if field in spec_config:
                score += 0.25

        # Check 2: Tools list not empty
        checks += 1
        if isinstance(spec_config.get("tools"), list) and len(spec_config["tools"]) > 0:
            score += 0.25

        # Check 3: Focus areas specificity
        checks += 1
        focus_areas = spec_config.get("focus_areas", [])
        if isinstance(focus_areas, list) and len(focus_areas) > 0:
            score += 0.25

        # Check 4: Reasonable number of tools (2-8)
        checks += 1
        tool_count = len(spec_config.get("tools", []))
        if 2 <= tool_count <= 8:
            score += 0.25

        return min(1.0, score / max(checks, 1))

    def run_benchmark_on_test_case(self, test_case: Dict) -> Dict:
        """
        Run benchmark on a single test case.

        Args:
            test_case: Test case from test_cases.json

        Returns:
            Benchmark result dictionary
        """
        test_id = test_case.get("id", "unknown")
        test_name = test_case.get("name", "unknown")
        domain_desc = test_case.get("description", "")

        print(f"\n📊 Running benchmark: {test_id} - {test_name}")

        # Create agent
        agent = StemAgent(llm_provider=self.llm_provider, domain="api_security")

        # Run differentiation
        import time
        start_time = time.time()

        success, spec_config, validation_result = agent.differentiate(domain_desc)
        execution_time = time.time() - start_time

        # Evaluate specialization quality
        quality_score = self.evaluate_specialization_quality(spec_config)

        # Compile results
        result = {
            "test_id": test_id,
            "test_name": test_name,
            "differentiation_success": success,
            "execution_time_seconds": execution_time,
            "specialization_quality": quality_score,
            "safeguard_confidence": validation_result.confidence,
            "safeguard_issues": validation_result.issues,
            "safeguard_recommendations": validation_result.recommendations,
            "generated_config": spec_config if success else None,
        }

        self.results[test_id] = result
        print(f"   ✓ Quality Score: {quality_score:.1%}")
        print(f"   ✓ Safeguard Confidence: {validation_result.confidence:.1%}")
        print(f"   ✓ Execution Time: {execution_time:.2f}s")

        return result

    def run_all_benchmarks(self, test_cases: List[Dict]) -> Dict:
        """
        Run benchmarks on all test cases.

        Args:
            test_cases: List of test case dictionaries

        Returns:
            Aggregated benchmark results
        """
        print("=" * 70)
        print("🧪 STEM AGENT BENCHMARK SUITE")
        print("=" * 70)

        all_results = []
        for test_case in test_cases:
            result = self.run_benchmark_on_test_case(test_case)
            all_results.append(result)

        # Compute aggregate metrics
        successful_runs = sum(1 for r in all_results if r["differentiation_success"])
        avg_quality = sum(r["specialization_quality"] for r in all_results) / max(
            len(all_results), 1
        )
        avg_confidence = sum(r["safeguard_confidence"] for r in all_results) / max(
            len(all_results), 1
        )
        avg_time = sum(r["execution_time_seconds"] for r in all_results) / max(
            len(all_results), 1
        )

        summary = {
            "total_tests": len(all_results),
            "successful_runs": successful_runs,
            "success_rate": successful_runs / max(len(all_results), 1),
            "avg_specialization_quality": avg_quality,
            "avg_safeguard_confidence": avg_confidence,
            "avg_execution_time_seconds": avg_time,
            "detailed_results": all_results,
        }

        return summary

    def print_summary(self, summary: Dict):
        """Pretty-print benchmark summary."""
        print("\n" + "=" * 70)
        print("📈 BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Runs: {summary['successful_runs']}/{summary['total_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Avg Quality Score: {summary['avg_specialization_quality']:.1%}")
        print(f"Avg Safeguard Confidence: {summary['avg_safeguard_confidence']:.1%}")
        print(f"Avg Execution Time: {summary['avg_execution_time_seconds']:.2f}s")
        print("=" * 70)


def main():
    """Run benchmark suite."""

    # Load test cases
    test_cases_path = Path(__file__).parent / "test_cases.json"
    with open(test_cases_path) as f:
        data = json.load(f)
        test_cases = data.get("test_cases", [])

    if not test_cases:
        print("No test cases found.")
        return False

    # Run benchmarks
    benchmark = SpecializationBenchmark(
        llm_provider=LLMProvider(mode=LLMMode.MOCK)
    )
    summary = benchmark.run_all_benchmarks(test_cases)

    # Print summary
    benchmark.print_summary(summary)

    # Save results
    output_path = Path(__file__).parent / "benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 Results saved to: {output_path}")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
