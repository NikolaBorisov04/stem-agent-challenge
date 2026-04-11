#!/usr/bin/env python
"""
Test Suite for Stem Agent
Validates all components and integration.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core import StemAgent, LLMProvider, LLMMode, SpecializationSafeguard


def test_llm_provider_mock():
    """Test LLM Provider in mock mode."""
    print("🧪 Test 1: LLM Provider (Mock Mode)")

    llm = LLMProvider(mode=LLMMode.MOCK)

    # Test API call
    response = llm.call(
        system_prompt="You are a test assistant",
        user_message="analyze this api security",
    )

    assert response, "LLM response is empty"
    assert isinstance(response, str), "Response is not a string"
    print("   ✓ Mock LLM call works")

    # Test JSON parsing
    try:
        parsed = llm.parse_json_response(response)
        assert isinstance(parsed, dict), "Parsed response is not a dict"
        print("   ✓ JSON parsing works")
    except ValueError:
        print("   ⚠ JSON parsing (expected for some mock responses)")

    print("   ✅ LLM Provider tests passed\n")


def test_safeguards():
    """Test safeguard validation."""
    print("🧪 Test 2: Safeguard Validation")

    safeguard = SpecializationSafeguard(domain="api_security")

    # Test valid config
    valid_config = {
        "persona": "Security Auditor",
        "tools": ["endpoint_mapper", "auth_analyzer"],
        "focus_areas": ["authentication", "authorization"],
        "output_format": "audit_report",
        "techniques": ["fuzzing", "token_replay"],
    }

    result = safeguard.validate(valid_config)
    assert result.is_valid, "Valid config marked as invalid"
    assert result.confidence >= 0.8, "Confidence too low for valid config"
    print(f"   ✓ Valid config accepted (confidence: {result.confidence:.1%})")

    # Test invalid config (missing required fields)
    invalid_config = {
        "persona": "Security Auditor",
        # Missing tools, focus_areas, output_format
    }

    result = safeguard.validate(invalid_config)
    assert not result.is_valid, "Invalid config marked as valid"
    assert len(result.issues) > 0, "No issues reported for invalid config"
    print(f"   ✓ Invalid config rejected ({len(result.issues)} issues found)")

    # Test can_safely_commit
    can_commit = safeguard.can_safely_commit(valid_config, min_confidence=0.7)
    assert can_commit, "Should allow commit for valid config"
    print("   ✓ Commit decision logic works")

    print("   ✅ Safeguard tests passed\n")


def test_stem_agent_initialization():
    """Test Stem Agent initialization."""
    print("🧪 Test 3: Stem Agent Initialization")

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    assert agent.domain == "api_security", "Domain not set correctly"
    assert agent.specialization_config is None, "Should start with no specialization"
    assert isinstance(agent.analysis_log, list), "Analysis log should be a list"
    print("   ✓ Agent initializes correctly")

    print("   ✅ Initialization tests passed\n")


def test_domain_analysis():
    """Test domain analysis."""
    print("🧪 Test 4: Domain Analysis")

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    domain_desc = "REST API for e-commerce with JWT auth"
    analysis = agent.analyze_domain(domain_desc)

    assert isinstance(analysis, dict), "Analysis should be a dict"
    print(f"   ✓ Domain analysis returned: {list(analysis.keys())}")

    assert len(agent.analysis_log) > 0, "Analysis log should be populated"
    assert agent.analysis_log[0]["type"] == "domain_analysis", "Log entry not recorded"
    print("   ✓ Analysis logged")

    print("   ✅ Analysis tests passed\n")


def test_specialization_generation():
    """Test specialization generation."""
    print("🧪 Test 5: Specialization Generation")

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    domain_desc = "REST API with authentication endpoints"
    spec_config = agent.generate_specialization(domain_desc)

    assert isinstance(spec_config, dict), "Config should be a dict"
    assert agent.specialization_config is not None, "Config not stored in agent"
    print(f"   ✓ Generated specialization: {list(spec_config.keys())}")

    assert len(agent.analysis_log) > 1, "Should have logged specialization"
    print("   ✓ Specialization logged")

    print("   ✅ Specialization tests passed\n")


def test_differentiation_pipeline():
    """Test full differentiation pipeline."""
    print("🧪 Test 6: Differentiation Pipeline")

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    domain_desc = "REST API for payment processing"
    success, config, validation = agent.differentiate(
        domain_desc,
        min_confidence=0.5,  # Lower threshold for testing
    )

    assert isinstance(success, bool), "Success should be boolean"
    assert isinstance(validation.confidence, float), "Confidence should be float"
    assert isinstance(validation.issues, list), "Issues should be a list"
    print(f"   ✓ Differentiation result: success={success}, confidence={validation.confidence:.1%}")

    if success:
        assert config is not None, "Config should not be None on success"
        print(f"   ✓ Generated persona: {config.get('persona', 'Unknown')}")

    print("   ✅ Differentiation tests passed\n")


def test_task_execution():
    """Test task execution with specialization."""
    print("🧪 Test 7: Task Execution")

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    # First specialize
    domain_desc = "REST API with authentication"
    agent.differentiate(domain_desc, min_confidence=0.5)

    # Then execute task
    task = "Analyze POST /api/login for vulnerabilities"
    result = agent.execute_task(task)

    assert result["success"], "Task execution should succeed"
    assert "persona" in result, "Result should contain persona"
    assert "response" in result, "Result should contain response"
    print(f"   ✓ Task executed successfully")
    print(f"   ✓ Response preview: {str(result['response'])[:80]}...")

    print("   ✅ Task execution tests passed\n")


def test_save_load_specialization():
    """Test saving and loading specialization."""
    print("🧪 Test 8: Save/Load Specialization")

    import tempfile
    import os

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    # Generate specialization
    domain_desc = "REST API with auth"
    agent.differentiate(domain_desc, min_confidence=0.5)

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        # Save
        save_success = agent.save_specialization(temp_path)
        assert save_success, "Save should succeed"
        assert os.path.exists(temp_path), "File should be created"
        print(f"   ✓ Specialization saved")

        # Load
        agent2 = StemAgent(llm_provider=llm, domain="api_security")
        load_success = agent2.load_specialization(temp_path)
        assert load_success, "Load should succeed"
        assert agent2.specialization_config is not None, "Config should be loaded"
        print(f"   ✓ Specialization loaded")

        # Verify content
        assert agent.specialization_config == agent2.specialization_config, \
            "Loaded config should match original"
        print(f"   ✓ Content verified")

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    print("   ✅ Save/Load tests passed\n")


def test_analysis_logging():
    """Test analysis logging."""
    print("🧪 Test 9: Analysis Logging")

    llm = LLMProvider(mode=LLMMode.MOCK)
    agent = StemAgent(llm_provider=llm, domain="api_security")

    initial_log_length = len(agent.get_analysis_log())

    # Perform operations
    domain_desc = "Simple REST API"
    agent.differentiate(domain_desc, min_confidence=0.5)
    agent.execute_task("Audit this endpoint")

    # Check log grew
    final_log_length = len(agent.get_analysis_log())
    assert final_log_length > initial_log_length, "Log should grow"
    print(f"   ✓ Log entries: {final_log_length}")

    # Verify log structure
    log = agent.get_analysis_log()
    for entry in log:
        assert "timestamp" in entry, "Log entry missing timestamp"
        assert "type" in entry, "Log entry missing type"
    print(f"   ✓ Log structure valid")

    print("   ✅ Logging tests passed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("🧪 STEM AGENT TEST SUITE")
    print("=" * 70 + "\n")

    tests = [
        test_llm_provider_mock,
        test_safeguards,
        test_stem_agent_initialization,
        test_domain_analysis,
        test_specialization_generation,
        test_differentiation_pipeline,
        test_task_execution,
        test_save_load_specialization,
        test_analysis_logging,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ Assertion failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            failed += 1

    # Summary
    print("=" * 70)
    print(f"📊 TEST SUMMARY: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        return True
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
