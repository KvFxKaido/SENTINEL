"""
Tests for SENTINEL 2D API.

Phase 1 Success Criteria:
- Python tests still pass
- Can drive game entirely via HTTP/WebSocket
- State persists between requests
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

# Import API components
from src.api.server import create_app, SentinelAPI
from src.api.schemas import (
    GameStateResponse,
    ActionRequest,
    ActionResponse,
    DialogueRequest,
    DialogueResponse,
    ActionType,
    Position,
    LocationType,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_manager():
    """Create a mock CampaignManager."""
    manager = MagicMock()
    manager.current = None
    manager.list_campaigns.return_value = []
    return manager


@pytest.fixture
def mock_agent():
    """Create a mock SentinelAgent."""
    agent = MagicMock()
    agent.is_available = True
    agent.backend_info = {
        "available": True,
        "backend": "mock",
        "model": "test-model",
        "supports_tools": True,
    }
    agent.respond.return_value = "Mock response from agent"
    return agent


@pytest.fixture
def api_client(tmp_path):
    """Create a test client for the API."""
    # Create temporary campaigns directory
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    
    # Create app with test configuration
    app = create_app(
        campaigns_dir=str(campaigns_dir),
        backend="auto",
        local_mode=True,
    )
    
    return TestClient(app)


@pytest.fixture
def api_with_campaign(tmp_path):
    """Create API client with a loaded campaign."""
    from src.state import CampaignManager, MemoryCampaignStore
    from src.state.schema import Campaign, CampaignMeta, Character, SocialEnergy, Background

    # Create in-memory store with test campaign
    store = MemoryCampaignStore()

    # Create test campaign
    campaign = Campaign(
        meta=CampaignMeta(
            id="test-campaign",
            name="Test Campaign",
            session_count=1,
        ),
        characters=[
            Character(
                id="test-char",
                name="Test Character",
                background=Background.OPERATIVE,
                social_energy=SocialEnergy(current=50, max=100),
                credits=100,
            )
        ],
    )
    store.save(campaign)
    
    # Create manager with test store
    manager = CampaignManager(store)
    manager.load_campaign("test-campaign")
    
    # Create app
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    
    app = create_app(
        campaigns_dir=str(campaigns_dir),
        backend="auto",
        local_mode=True,
    )
    
    # Replace manager with our test manager
    app.state.api.manager = manager
    
    return TestClient(app)


# -----------------------------------------------------------------------------
# Health Check Tests
# -----------------------------------------------------------------------------

class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check_returns_ok(self, api_client):
        """Health check should return ok status."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["service"] == "sentinel-2d-api"


# -----------------------------------------------------------------------------
# State Endpoint Tests
# -----------------------------------------------------------------------------

class TestStateEndpoint:
    """Tests for GET /state endpoint."""
    
    def test_state_without_campaign(self, api_client):
        """State endpoint should work without loaded campaign."""
        response = api_client.get("/state")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["campaign"] is None
        assert data["character"] is None
        assert "version" in data
        assert "timestamp" in data
    
    def test_state_with_campaign(self, api_with_campaign):
        """State endpoint should return full state with campaign."""
        response = api_with_campaign.get("/state")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["campaign"] is not None
        assert data["campaign"]["id"] == "test-campaign"
        assert data["character"] is not None
        assert data["character"]["name"] == "Test Character"
    
    def test_state_includes_version(self, api_client):
        """State should include version for optimistic updates."""
        response = api_client.get("/state")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], int)


# -----------------------------------------------------------------------------
# Action Endpoint Tests
# -----------------------------------------------------------------------------

class TestActionEndpoint:
    """Tests for POST /action endpoint."""
    
    def test_action_without_campaign(self, api_client):
        """Action should fail without loaded campaign."""
        response = api_client.post("/action", json={
            "action_type": "move",
            "position": {"x": 10, "y": 20},
            "state_version": 0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "No campaign loaded" in data["error"]
    
    def test_move_action(self, api_with_campaign):
        """Move action should update position."""
        response = api_with_campaign.post("/action", json={
            "action_type": "move",
            "position": {"x": 10, "y": 20},
            "state_version": 0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["success"] is True
        assert "position" in data["results"][0]["changes"]
    
    def test_interact_action_without_target(self, api_with_campaign):
        """Interact action should fail without target."""
        response = api_with_campaign.post("/action", json={
            "action_type": "interact",
            "state_version": 0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["success"] is False
        assert "No target" in data["results"][0]["message"]
    
    def test_state_version_conflict(self, api_with_campaign):
        """Action should fail if state version is stale."""
        # First, get current state to bump version
        api_with_campaign.post("/action", json={
            "action_type": "move",
            "position": {"x": 5, "y": 5},
            "state_version": 0,
        })
        
        # Now try with old version
        response = api_with_campaign.post("/action", json={
            "action_type": "move",
            "position": {"x": 10, "y": 10},
            "state_version": 0,  # Stale version
        })
        data = response.json()
        assert data["ok"] is False
        assert "stale" in data["error"].lower()
    
    def test_action_increments_turn_number(self, api_with_campaign):
        """Successful action should increment turn number."""
        response1 = api_with_campaign.post("/action", json={
            "action_type": "wait",
            "state_version": 0,
        })
        turn1 = response1.json()["turn_number"]
        
        response2 = api_with_campaign.post("/action", json={
            "action_type": "wait",
            "state_version": 1,
        })
        turn2 = response2.json()["turn_number"]
        
        assert turn2 > turn1


# -----------------------------------------------------------------------------
# Dialogue Endpoint Tests
# -----------------------------------------------------------------------------

class TestDialogueEndpoint:
    """Tests for POST /dialogue endpoint."""
    
    def test_dialogue_without_campaign(self, api_client):
        """Dialogue should fail without loaded campaign."""
        response = api_client.post("/dialogue", json={
            "npc_id": "test-npc",
            "context": "Testing",
            "state_version": 0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "No campaign loaded" in data["error"]
    
    def test_dialogue_with_invalid_npc(self, api_with_campaign):
        """Dialogue should fail with invalid NPC ID."""
        response = api_with_campaign.post("/dialogue", json={
            "npc_id": "nonexistent-npc",
            "context": "Testing",
            "state_version": 0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


# -----------------------------------------------------------------------------
# Campaign Management Tests
# -----------------------------------------------------------------------------

class TestCampaignManagement:
    """Tests for campaign management endpoints."""
    
    def test_list_campaigns_empty(self, api_client):
        """List campaigns should return empty list initially."""
        response = api_client.get("/campaigns")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["campaigns"] == []
    
    def test_load_nonexistent_campaign(self, api_client):
        """Loading nonexistent campaign should fail."""
        response = api_client.post("/campaigns/nonexistent/load")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
    
    def test_save_without_campaign(self, api_client):
        """Save should fail without loaded campaign."""
        response = api_client.post("/campaigns/save")
        assert response.status_code == 200
        data = response.json()
        # Should succeed but do nothing
        assert data["ok"] is True


# -----------------------------------------------------------------------------
# WebSocket Tests
# -----------------------------------------------------------------------------

class TestWebSocket:
    """Tests for WebSocket endpoint."""
    
    def test_websocket_connection(self, api_client):
        """WebSocket should accept connections."""
        with api_client.websocket_connect("/updates") as websocket:
            # Should receive initial state
            data = websocket.receive_json()
            assert data["type"] == "initial_state"
    
    def test_websocket_ping_pong(self, api_client):
        """WebSocket should respond to ping."""
        with api_client.websocket_connect("/updates") as websocket:
            # Receive initial state
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"


# -----------------------------------------------------------------------------
# Schema Validation Tests
# -----------------------------------------------------------------------------

class TestSchemas:
    """Tests for API schema validation."""
    
    def test_action_request_validation(self):
        """ActionRequest should validate correctly."""
        # Valid request
        request = ActionRequest(
            action_type=ActionType.MOVE,
            position=Position(x=10, y=20),
            state_version=0,
        )
        assert request.action_type == ActionType.MOVE
        assert request.position.x == 10
    
    def test_action_request_invalid_type(self):
        """ActionRequest should reject invalid action type."""
        with pytest.raises(ValueError):
            ActionRequest(
                action_type="invalid_type",
                state_version=0,
            )
    
    def test_game_state_response_structure(self):
        """GameStateResponse should have correct structure."""
        response = GameStateResponse(
            ok=True,
            version=1,
            timestamp=datetime.now(),
        )
        assert response.ok is True
        assert response.version == 1
        assert response.campaign is None


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_state_action_state_cycle(self, api_with_campaign):
        """Complete cycle: get state, perform action, verify state changed."""
        # Get initial state
        state1 = api_with_campaign.get("/state").json()
        version1 = state1["version"]
        
        # Perform action
        action_response = api_with_campaign.post("/action", json={
            "action_type": "move",
            "position": {"x": 100, "y": 200},
            "state_version": version1,
        })
        assert action_response.json()["success"] is True
        
        # Get new state
        state2 = api_with_campaign.get("/state").json()
        version2 = state2["version"]
        
        # Version should have incremented
        assert version2 > version1
    
    def test_multiple_actions_sequence(self, api_with_campaign):
        """Multiple actions should execute in sequence."""
        version = 0
        
        for i in range(5):
            response = api_with_campaign.post("/action", json={
                "action_type": "wait",
                "state_version": version,
            })
            data = response.json()
            assert data["success"] is True
            version = data["state_version"]
        
        # Final turn number should be 5
        assert data["turn_number"] == 5


# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_json(self, api_client):
        """Invalid JSON should return error."""
        response = api_client.post(
            "/action",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_required_fields(self, api_client):
        """Missing required fields should return error."""
        response = api_client.post("/action", json={
            # Missing action_type and state_version
        })
        assert response.status_code == 422


# -----------------------------------------------------------------------------
# Performance Tests
# -----------------------------------------------------------------------------

class TestPerformance:
    """Basic performance tests."""
    
    def test_state_endpoint_response_time(self, api_client):
        """State endpoint should respond quickly."""
        import time
        
        start = time.time()
        for _ in range(10):
            api_client.get("/state")
        elapsed = time.time() - start
        
        # Should complete 10 requests in under 1 second
        assert elapsed < 1.0
    
    def test_action_endpoint_response_time(self, api_with_campaign):
        """Action endpoint should respond quickly."""
        import time
        
        version = 0
        start = time.time()
        for _ in range(10):
            response = api_with_campaign.post("/action", json={
                "action_type": "wait",
                "state_version": version,
            })
            version = response.json()["state_version"]
        elapsed = time.time() - start
        
        # Should complete 10 actions in under 2 seconds
        assert elapsed < 2.0
