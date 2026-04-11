"""
Main Entry Point
Orchestrates the Stem Agent differentiation and task execution flow.
"""

import json
import os
import sys
from pathlib import Path

from core import StemAgent, LLMProvider, LLMMode


def load_sample_api_description() -> str:
    """Load a sample API description for demo purposes."""
    return """
    API: E-commerce Platform REST API
    Description: A public-facing REST API for an e-commerce platform
    Endpoints:
    - GET /api/v1/products: List all products
    - GET /api/v1/products/{id}: Get product details
    - POST /api/v1/cart: Add item to shopping cart
    - POST /api/v1/orders: Create a new order
    - GET /api/v1/orders/{id}: Get order status
    - POST /api/v1/users/login: User authentication
    - GET /api/v1/users/profile: Get user profile
    - POST /api/v1/users/profile: Update user profile

    Security Requirements:
    - JWT-based authentication
    - Rate limiting (100 requests/minute per IP)
    - CORS enabled for specific domains
    - All endpoints require HTTPS
    - Database: PostgreSQL with parameterized queries

    Known Concerns:
    - Need to audit for SQL injection vulnerability
    - Verify JWT token expiration logic
    - Check rate limiting implementation
    - Validate CORS configuration
    - Ensure proper authorization checks on endpoints
    """


def main():
    """Main execution flow."""

    # Configuration
    USE_MOCK_LLM = True
    DOMAIN = "api_security"
    CONFIG_DIR = Path("specialists")
    CONFIG_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("🌱 STEM AGENT CHALLENGE - Web API Security Auditor")
    print("=" * 70)

    # Step 1: Initialize LLM Provider
    print(f"\n[1/5] Initializing LLM Provider (mode: {'MOCK' if USE_MOCK_LLM else 'OpenAI'})...")
    try:
        llm_mode = LLMMode.MOCK if USE_MOCK_LLM else LLMMode.OPENAI
        llm_provider = LLMProvider(mode=llm_mode)
        print("✓ LLM Provider initialized")
    except ValueError as e:
        print(f"✗ Failed to initialize LLM: {e}")
        return False

    # Step 2: Create Stem Agent
    print(f"\n[2/5] Creating Stem Agent for domain: {DOMAIN}...")
    agent = StemAgent(llm_provider=llm_provider, domain=DOMAIN)
    print("✓ Stem Agent created")

    # Step 3: Load domain description
    print(f"\n[3/5] Loading domain description...")
    domain_description = load_sample_api_description()
    print("✓ Domain description loaded")
    print(f"   Sample: {domain_description[:100]}...")

    # Step 4: Run differentiation pipeline
    print(f"\n[4/5] Running differentiation pipeline...")
    success, spec_config, validation_result = agent.differentiate(
        domain_description,
        min_confidence=0.7
    )

    if not success:
        print("\n❌ Differentiation failed. Try again with different parameters.")
        return False

    # Step 5: Save specialization and execute sample task
    print(f"\n[5/5] Saving specialization and executing task...")

    # Save config
    config_path = CONFIG_DIR / "web_api_security.json"
    agent.save_specialization(str(config_path))

    # Execute a sample security audit task
    print("\n📋 Executing sample security audit task...")
    task = """
    Analyze this API endpoint for security vulnerabilities:
    POST /api/v1/users/profile
    - Accepts: username, email, password
    - No explicit rate limiting
    - Uses Bearer token authentication
    - Updates user profile in PostgreSQL
    """

    task_result = agent.execute_task(task)
    print(f"\n📝 Task Result:")
    print(f"   Persona: {task_result.get('persona')}")
    print(f"   Response Preview: {task_result.get('response', '')[:200]}...")

    # Save analysis log
    log_path = CONFIG_DIR / "analysis_log.json"
    with open(log_path, "w") as f:
        json.dump(agent.get_analysis_log(), f, indent=2)
    print(f"\n📊 Analysis log saved to: {log_path}")

    print("\n" + "=" * 70)
    print("✅ STEM AGENT CHALLENGE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 Outputs:")
    print(f"   - Specialization Config: {config_path}")
    print(f"   - Analysis Log: {log_path}")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
