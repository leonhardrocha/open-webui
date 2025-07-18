# tools/deep_research/tests/test_event_parsing.py

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any

from ..event_management.event_models import (
    parse_dify_event,
    NodeStartEvent,
    NodeFinishEvent,
    WorkflowFinishEvent,
    NodeType,
    NodeStatus
)
from .mocks import (
    NODE_START_EVENT_JSON,
    NODE_FINISH_LLM_JSON,
    NODE_FINISH_IF_ELSE_JSON,
    NODE_FINISH_VARIABLE_AGGREGATOR_JSON,
    NODE_FINISH_TEMPLATE_TRANSFORM_JSON,
    ITERATION_FINISH_EVENT_JSON,
    WORKFLOW_FINISH_EVENT_JSON
)

# Test data
TEST_EVENTS = [
    (NODE_START_EVENT_JSON, NodeStartEvent, NodeType.ANSWER),
    (NODE_FINISH_LLM_JSON, NodeFinishEvent, NodeType.LLM),
    (NODE_FINISH_IF_ELSE_JSON, NodeFinishEvent, NodeType.IF_ELSE),
    (NODE_FINISH_VARIABLE_AGGREGATOR_JSON, NodeFinishEvent, NodeType.VARIABLE_AGGREGATOR),
    (NODE_FINISH_TEMPLATE_TRANSFORM_JSON, NodeFinishEvent, NodeType.TEMPLATE_TRANSFORM),
    (ITERATION_FINISH_EVENT_JSON, NodeFinishEvent, NodeType.ITERATION),
    (WORKFLOW_FINISH_EVENT_JSON, WorkflowFinishEvent, None)
]

@pytest.mark.parametrize("event_json,expected_type,expected_node_type", TEST_EVENTS)
def test_parse_dify_event(event_json: str, expected_type: type, expected_node_type: NodeType):
    """Test that parse_dify_event returns the correct event type with valid data."""
    # Parse the JSON string to a dictionary
    event_data = json.loads(event_json)
    
    # Parse the event
    event = parse_dify_event(event_data)
    
    # Verify the event type
    assert isinstance(event, expected_type)
    
    # For node events, verify the node type
    if expected_node_type is not None:
        assert event.content.node_type == expected_node_type.value

def test_parse_node_start_event():
    """Test parsing of node_start event with specific validations."""
    event = parse_dify_event(json.loads(NODE_START_EVENT_JSON))
    
    assert isinstance(event, NodeStartEvent)
    assert event.type == "node_start"
    assert event.content.node_type == "answer"
    assert isinstance(event.content.created_at, datetime)
    assert event.content.created_at.tzinfo == timezone.utc

def test_parse_node_finish_event():
    """Test parsing of node_finish event with specific validations."""
    event = parse_dify_event(json.loads(NODE_FINISH_LLM_JSON))
    
    assert isinstance(event, NodeFinishEvent)
    assert event.type == "node_finish"
    assert event.content.node_type == "llm"
    assert isinstance(event.content.finished_at, datetime)
    assert event.content.finished_at.tzinfo == timezone.utc
    assert event.content.status == NodeStatus.SUCCEEDED
    assert event.content.elapsed_time > 0

def test_parse_workflow_finish_event():
    """Test parsing of workflow_finish event with specific validations."""
    event = parse_dify_event(json.loads(WORKFLOW_FINISH_EVENT_JSON))
    
    assert isinstance(event, WorkflowFinishEvent)
    assert event.type == "workflow_finish"
    assert "workflow_id" in event.content
    assert "status" in event.content
    assert "outputs" in event.content
    assert "total_tokens" in event.content

def test_parse_invalid_event_type():
    """Test that parsing an unknown event type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown event type: invalid_type"):
        parse_dify_event({"type": "invalid_type", "content": {}})

def test_parse_missing_required_fields():
    """Test that parsing with missing required fields raises appropriate errors."""
    # Missing content
    with pytest.raises(ValueError):
        parse_dify_event({"type": "node_start"})
    
    # Missing type
    with pytest.raises(ValueError, match="Unknown event type: None"):
        parse_dify_event({"content": {}})

def test_timestamp_parsing():
    """Test that timestamps are properly parsed into datetime objects."""
    # Test with node_start event (integer timestamp)
    event = parse_dify_event(json.loads(NODE_START_EVENT_JSON))
    assert isinstance(event.content.created_at, datetime)
    assert event.content.created_at.tzinfo == timezone.utc
    
    # Test with node_finish event (should have both created_at and finished_at)
    event = parse_dify_event(json.loads(NODE_FINISH_LLM_JSON))
    assert isinstance(event.content.created_at, datetime)
    assert isinstance(event.content.finished_at, datetime)
    assert event.content.finished_at > event.content.created_at
    assert event.content.created_at.tzinfo == timezone.utc
    assert event.content.finished_at.tzinfo == timezone.utc