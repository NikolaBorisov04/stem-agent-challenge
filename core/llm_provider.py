"""
LLM Provider Module
Handles communication with LLM services (OpenAI or mock mode).
Supports easy switching between mock and real API calls.
"""

import json
import os
from typing import Optional, Any
from enum import Enum


class LLMMode(Enum):
    """Enum for LLM operation modes."""
    MOCK = "mock"
    OPENAI = "openai"


class LLMProvider:
    """
    Wrapper for LLM API calls with mock and production modes.
    Designed for simple plugging-in of real API keys later.
    """

    def __init__(self, mode: LLMMode = LLMMode.MOCK, api_key: Optional[str] = None):
        """
        Initialize LLM Provider.

        Args:
            mode: LLMMode.MOCK for testing, LLMMode.OPENAI for production
            api_key: OpenAI API key (from environment or parameter)
        """
        self.mode = mode
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if self.mode == LLMMode.OPENAI and not self.api_key:
            raise ValueError(
                "OpenAI mode requires OPENAI_API_KEY env var or api_key parameter"
            )

        if self.mode == LLMMode.OPENAI:
            try:
                import openai
                openai.api_key = self.api_key
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package required for OpenAI mode. Install with: pip install openai"
                )

    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Call the LLM (or mock).

        Args:
            system_prompt: System role/instruction
            user_message: User query
            temperature: Sampling temperature (0-1)
            max_tokens: Max response tokens

        Returns:
            LLM response text
        """
        if self.mode == LLMMode.MOCK:
            return self._mock_call(system_prompt, user_message)
        else:
            return self._openai_call(
                system_prompt, user_message, temperature, max_tokens
            )

    def _mock_call(self, system_prompt: str, user_message: str) -> str:
        """
        Generate deterministic mock responses for testing.
        This ensures consistent behavior for CI/CD and development.
        """
        # Use message hash for deterministic responses
        message_hash = hash((system_prompt + user_message)) % 100

        if "analyze" in user_message.lower() and "api" in user_message.lower():
            return json.dumps({
                "persona": "Security Auditor",
                "tools": ["endpoint_mapper", "auth_analyzer", "payload_fuzz_tester"],
                "focus_areas": ["authentication", "authorization", "input_validation"],
                "techniques": ["black_box_testing", "fuzzing", "token_replay"],
                "output_format": "audit_report"
            })

        if "validate" in user_message.lower():
            return json.dumps({
                "is_valid": True,
                "confidence": 0.95,
                "issues": [],
                "recommendations": []
            })

        # Default mock response
        return json.dumps({
            "status": "success",
            "message": "Mock LLM response",
            "hash": message_hash
        })

    def _openai_call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call real OpenAI API.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")

    def parse_json_response(self, response: str) -> dict:
        """
        Safely parse JSON from LLM response.
        Handles cases where LLM returns raw JSON or wrapped in markdown.
        """
        try:
            # Try direct JSON parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                # Last resort: try to find JSON block
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(response[start:end])
            raise ValueError(f"Could not parse JSON from response: {response}")
