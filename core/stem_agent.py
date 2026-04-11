"""
Stem Agent Module
Core logic for analyzing a domain and differentiating into a specialized agent.
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime

from .llm_provider import LLMProvider, LLMMode
from .safeguards import SpecializationSafeguard, SafeguardResult


class StemAgent:
    """
    A minimal AI agent that:
    1. Reads signals from its environment (a domain/task)
    2. Analyzes the domain
    3. Transforms into a specialized agent
    4. Saves its identity as a configuration
    5. Executes tasks using that identity
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None, domain: str = "api_security"):
        """
        Initialize the Stem Agent.

        Args:
            llm_provider: LLMProvider instance (creates default mock if None)
            domain: The target domain for specialization
        """
        self.llm_provider = llm_provider or LLMProvider(mode=LLMMode.MOCK)
        self.domain = domain
        self.safeguard = SpecializationSafeguard(domain=domain)
        self.specialization_config: Optional[Dict] = None
        self.analysis_log: list = []

    def analyze_domain(self, domain_description: str) -> Dict:
        """
        Analyze the given domain and determine specialization needs.

        Args:
            domain_description: Description of the domain/API/task

        Returns:
            Analysis results as a dictionary
        """
        prompt = f"""You are analyzing a domain/API to determine what specialization an AI agent needs.

Domain/API Description:
{domain_description}

Please analyze this and provide:
1. Key security concerns
2. Required expertise areas
3. Relevant tools needed
4. Testing techniques applicable

Respond in JSON format with keys: concerns, expertise_areas, required_tools, techniques"""

        response = self.llm_provider.call(
            system_prompt="You are an expert AI system analyzer.",
            user_message=prompt,
        )

        try:
            analysis = self.llm_provider.parse_json_response(response)
        except ValueError:
            # Fallback for mock responses
            analysis = json.loads(response) if "{" in response else {}

        self.analysis_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "domain_analysis",
            "domain": self.domain,
            "analysis": analysis,
        })

        return analysis

    def generate_specialization(self, domain_description: str) -> Dict:
        """
        Generate a specialized agent configuration based on domain analysis.

        Args:
            domain_description: Description of the domain

        Returns:
            Specialization configuration dict
        """
        # First, analyze the domain
        analysis = self.analyze_domain(domain_description)

        prompt = f"""Based on the following analysis, generate a specialized agent configuration.

Analysis:
{json.dumps(analysis, indent=2)}

Generate a JSON configuration for a specialized {self.domain} agent with:
- persona: A clear role description
- tools: List of specific tools (choose from: endpoint_mapper, auth_analyzer, payload_fuzz_tester, rate_limiter_checker, crypto_analyzer, token_validator, sql_injection_detector, xss_detector, cors_checker, api_gateway_analyzer)
- focus_areas: Key areas to focus on
- techniques: Testing/analysis techniques to use
- output_format: Format for reports (audit_report, vulnerability_list, or json)

Respond ONLY with valid JSON."""

        response = self.llm_provider.call(
            system_prompt=(
                f"You are designing a specialized {self.domain} agent. "
                "Be precise and practical."
            ),
            user_message=prompt,
            temperature=0.6,
        )

        try:
            spec_config = self.llm_provider.parse_json_response(response)
        except ValueError:
            spec_config = json.loads(response) if "{" in response else {}

        self.specialization_config = spec_config

        self.analysis_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "specialization_generated",
            "config": spec_config,
        })

        return spec_config

    def validate_specialization(self, spec_config: Dict) -> SafeguardResult:
        """
        Run safeguards to validate the specialization.

        Args:
            spec_config: The specialization configuration to validate

        Returns:
            SafeguardResult with validation details
        """
        result = self.safeguard.validate(spec_config)

        self.analysis_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "safeguard_validation",
            "result": {
                "is_valid": result.is_valid,
                "confidence": result.confidence,
                "issues": result.issues,
                "recommendations": result.recommendations,
            },
        })

        return result

    def differentiate(
        self,
        domain_description: str,
        min_confidence: float = 0.7,
    ) -> tuple[bool, Optional[Dict], SafeguardResult]:
        """
        Main differentiation pipeline: analyze → generate → validate → commit.

        Args:
            domain_description: Description of the domain/API
            min_confidence: Minimum confidence for safeguard validation

        Returns:
            Tuple of (success: bool, config: Optional[Dict], validation_result: SafeguardResult)
        """
        print(f"\n🌱 Stem Agent starting differentiation for domain: {self.domain}")

        # Step 1: Generate specialization
        print("📊 Analyzing domain and generating specialization...")
        spec_config = self.generate_specialization(domain_description)
        print(f"✓ Generated specialization config")

        # Step 2: Validate with safeguards
        print("🛡️  Running safeguard validation...")
        validation_result = self.validate_specialization(spec_config)

        if validation_result.issues:
            print(f"⚠️  Safeguard Issues:")
            for issue in validation_result.issues:
                print(f"   - {issue}")

        if validation_result.recommendations:
            print(f"💡 Recommendations:")
            for rec in validation_result.recommendations:
                print(f"   - {rec}")

        print(f"📈 Validation Confidence: {validation_result.confidence:.1%}")

        # Step 3: Decide whether to commit
        can_commit = self.safeguard.can_safely_commit(
            spec_config, min_confidence=min_confidence
        )

        if can_commit:
            self.specialization_config = spec_config
            print(f"✅ Differentiation successful! Agent specialized as: {spec_config.get('persona', 'Unknown')}")
            self.analysis_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "differentiation_committed",
            })
            return True, spec_config, validation_result
        else:
            print(f"❌ Specialization failed safeguard checks (confidence: {validation_result.confidence:.1%} < {min_confidence:.1%})")
            self.analysis_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "differentiation_rejected",
                "reason": f"Low confidence: {validation_result.confidence}",
            })
            return False, None, validation_result

    def save_specialization(self, filepath: str) -> bool:
        """
        Save the specialization config to a JSON file.

        Args:
            filepath: Path to save the config to

        Returns:
            True if successful, False otherwise
        """
        if not self.specialization_config:
            print("❌ No specialization to save. Run differentiate() first.")
            return False

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(self.specialization_config, f, indent=2)
            print(f"💾 Specialization saved to: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to save specialization: {e}")
            return False

    def load_specialization(self, filepath: str) -> bool:
        """
        Load a specialization config from a JSON file.

        Args:
            filepath: Path to load the config from

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, "r") as f:
                self.specialization_config = json.load(f)
            print(f"📖 Specialization loaded from: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to load specialization: {e}")
            return False

    def execute_task(self, task_description: str) -> Dict:
        """
        Execute a task using the specialized agent's identity.

        Args:
            task_description: The task to execute

        Returns:
            Task result dictionary
        """
        if not self.specialization_config:
            return {
                "success": False,
                "error": "Agent not specialized. Call differentiate() first.",
            }

        persona = self.specialization_config.get("persona", "Unknown")
        tools = ", ".join(self.specialization_config.get("tools", []))
        focus_areas = ", ".join(self.specialization_config.get("focus_areas", []))

        prompt = f"""You are a {persona} specialized in {focus_areas}.
You have access to these tools: {tools}.

Task: {task_description}

Provide a detailed analysis or report."""

        response = self.llm_provider.call(
            system_prompt=f"You are a {persona}. Be thorough and practical.",
            user_message=prompt,
        )

        result = {
            "success": True,
            "persona": persona,
            "task": task_description,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }

        self.analysis_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "task_executed",
            "task": task_description,
            "result": result,
        })

        return result

    def get_analysis_log(self) -> list:
        """
        Get the full analysis log for evaluation/debugging.

        Returns:
            List of all logged events
        """
        return self.analysis_log
