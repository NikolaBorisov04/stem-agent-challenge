"""
Safeguards Module
Validates specialization configurations before they are committed.
Ensures the stem agent's transformation is logical and safe.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class SafeguardResult:
    """Result of a safeguard validation check."""
    is_valid: bool
    confidence: float  # 0.0 to 1.0
    issues: List[str]
    recommendations: List[str]


class SpecializationSafeguard:
    """
    Validates that a specialized agent config:
    1. Is logically consistent
    2. Has required fields
    3. Doesn't invent tools that don't exist
    4. Focus areas align with the domain
    5. Techniques are applicable to the domain
    """

    # Known tool categories for various domains
    VALID_TOOLS = {
        "api_security": {
            "endpoint_mapper",
            "auth_analyzer",
            "payload_fuzz_tester",
            "rate_limiter_checker",
            "crypto_analyzer",
            "token_validator",
            "sql_injection_detector",
            "xss_detector",
            "cors_checker",
            "api_gateway_analyzer",
        },
        "web_security": {
            "xss_detector",
            "sql_injection_detector",
            "csrf_validator",
            "csp_analyzer",
            "auth_mechanism_checker",
            "dependency_scanner",
        },
        "data_science": {
            "data_loader",
            "feature_extractor",
            "model_trainer",
            "result_visualizer",
        },
    }

    VALID_TECHNIQUES = {
        "api_security": {
            "black_box_testing",
            "fuzzing",
            "token_replay",
            "parameter_tampering",
            "schema_validation",
            "traffic_analysis",
        },
        "web_security": {
            "payload_injection",
            "dom_analysis",
            "network_interception",
            "source_code_review",
        },
        "data_science": {
            "statistical_analysis",
            "visualization",
            "model_evaluation",
            "feature_engineering",
        },
    }

    REQUIRED_FIELDS = ["persona", "tools", "focus_areas", "output_format"]

    def __init__(self, domain: str = "api_security"):
        """
        Initialize safeguard with domain context.

        Args:
            domain: The specialized domain (e.g., "api_security")
        """
        self.domain = domain
        self.valid_tools = self.VALID_TOOLS.get(domain, set())
        self.valid_techniques = self.VALID_TECHNIQUES.get(domain, set())

    def validate(self, spec_config: Dict) -> SafeguardResult:
        """
        Validate a specialization configuration.

        Args:
            spec_config: The specialized agent config dict

        Returns:
            SafeguardResult with validation details
        """
        issues = []
        recommendations = []
        confidence = 1.0

        # Check 1: Required fields
        for field in self.REQUIRED_FIELDS:
            if field not in spec_config:
                issues.append(f"Missing required field: {field}")
                confidence -= 0.25

        # Check 2: Tools validation
        if "tools" in spec_config:
            tools = spec_config["tools"]
            if not isinstance(tools, list):
                issues.append("'tools' must be a list")
                confidence -= 0.2
            else:
                unknown_tools = set(tools) - self.valid_tools
                if unknown_tools:
                    issues.append(
                        f"Unknown tools for {self.domain}: {unknown_tools}. "
                        f"Valid tools: {self.valid_tools}"
                    )
                    confidence -= 0.15
                if len(tools) == 0:
                    issues.append("At least one tool must be specified")
                    confidence -= 0.2
                elif len(tools) > 10:
                    recommendations.append(
                        f"Many tools specified ({len(tools)}). "
                        "Consider focusing on the most essential ones."
                    )

        # Check 3: Focus areas consistency
        if "focus_areas" in spec_config:
            focus_areas = spec_config["focus_areas"]
            if not isinstance(focus_areas, list):
                issues.append("'focus_areas' must be a list")
                confidence -= 0.2
            elif len(focus_areas) == 0:
                issues.append("At least one focus area must be specified")
                confidence -= 0.2

        # Check 4: Techniques validation
        if "techniques" in spec_config:
            techniques = spec_config["techniques"]
            if not isinstance(techniques, list):
                issues.append("'techniques' must be a list")
                confidence -= 0.15
            else:
                unknown_techniques = set(techniques) - self.valid_techniques
                if unknown_techniques:
                    recommendations.append(
                        f"Unknown techniques: {unknown_techniques}. "
                        "These might be custom but verify they are applicable."
                    )

        # Check 5: Persona consistency
        if "persona" in spec_config:
            persona = spec_config["persona"]
            if not isinstance(persona, str) or len(persona.strip()) == 0:
                issues.append("'persona' must be a non-empty string")
                confidence -= 0.15

        # Check 6: Output format validation
        if "output_format" in spec_config:
            output_format = spec_config["output_format"]
            valid_formats = {"audit_report", "vulnerability_list", "json", "xml", "csv"}
            if output_format not in valid_formats:
                recommendations.append(
                    f"Unusual output format: {output_format}. "
                    f"Standard options: {valid_formats}"
                )

        # Ensure confidence doesn't go below 0
        confidence = max(0.0, min(1.0, confidence))

        is_valid = len(issues) == 0 and confidence >= 0.5

        return SafeguardResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            recommendations=recommendations,
        )

    def can_safely_commit(self, spec_config: Dict, min_confidence: float = 0.7) -> bool:
        """
        Determine if specialization is safe to commit.

        Args:
            spec_config: The specialized config
            min_confidence: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            True if safe to commit, False otherwise
        """
        result = self.validate(spec_config)
        return result.is_valid and result.confidence >= min_confidence
