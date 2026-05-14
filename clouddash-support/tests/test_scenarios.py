import pytest
from agents.orchestrator import Orchestrator
import os
import json

@pytest.fixture
def orchestrator():
    """Returns a fresh Orchestrator instance for each test."""
    return Orchestrator()

def test_single_agent_technical(orchestrator):
    """Test routing to technical agent and getting a KB-backed response."""
    response = orchestrator.chat("My CloudDash alerts stopped firing after I updated my AWS integration credentials. I'm on the Pro plan.")
    
    assert response is not None
    assert len(response) > 0
    assert "[Source: KB-" in response
    assert orchestrator.current_agent == "technical_support"

def test_cross_agent_handover(orchestrator):
    """Test switching from one agent to another and verifying the handover log."""
    # First message should go to technical support (SSO integration)
    res1 = orchestrator.chat("Can you check if the SSO integration issue I reported last week has been resolved?")
    first_agent = orchestrator.current_agent
    
    # Second message should go to billing (upgrade)
    res2 = orchestrator.chat("Great, now I want to upgrade from Pro to Enterprise.")
    second_agent = orchestrator.current_agent
    
    # Verify agents changed
    assert first_agent != second_agent
    assert second_agent == "billing"
    
    # Verify handover log exists and contains this handover
    assert os.path.exists("handover_log.jsonl")
    
    found_handover = False
    with open("handover_log.jsonl", "r") as f:
        lines = f.readlines()
        for line in reversed(lines):
            log_entry = json.loads(line)
            if log_entry["source_agent"] == first_agent and log_entry["target_agent"] == second_agent:
                found_handover = True
                break
                
    assert found_handover

def test_escalation(orchestrator):
    """Test that angry customers are routed to escalation and summarized."""
    response = orchestrator.chat("I've been charged twice for April. I need an immediate refund and I want to speak to a manager.")
    
    assert "--- ESCALATION SUMMARY ---" in response
    assert "Priority" in response
    assert orchestrator.current_agent == "escalation"

def test_kb_failure(orchestrator):
    """Test that the agent handles unsupported features gracefully."""
    response = orchestrator.chat("Does CloudDash support integration with Datadog?")
    
    response_lower = response.lower()
    assert any(phrase in response_lower for phrase in ["escalate", "feature request", "not available", "do not have", "cannot find"])
    # Ensure it doesn't hallucinate a fake KB
    assert "[Source: KB-" not in response or "not found" in response_lower
