#!/usr/bin/env python3
# tools/deep_research/tests/test_event_parsing.py

import os
import sys

# Add the tools/deep_research directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any

from event_management.event_models import (
    NodeStartEvent,
    NodeFinishEvent,
    WorkflowFinishEvent,
    NodeType,
    NodeStatus
)
from event_management.dify_event_handler import DifyEventHandler
from event_management.event_emitter import EventEmitter
from tests.mocks import (
    NODE_START_EVENT_JSON,
    NODE_FINISH_LLM_JSON,
    NODE_FINISH_IF_ELSE_JSON,
    NODE_FINISH_VARIABLE_AGGREGATOR_JSON,
    NODE_FINISH_TEMPLATE_TRANSFORM_JSON,
    ITERATION_FINISH_EVENT_JSON,
    WORKFLOW_FINISH_EVENT_JSON,
    MockEventEmitter
)

# Create a test instance of DifyEventHandler
@pytest.fixture
def event_handler():
    mock_emitter = MockEventEmitter(request_info_data={"test": "data"})
    event_emitter = EventEmitter(event_emitter=mock_emitter)
    return DifyEventHandler(event_emitter)

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

@pytest.mark.asyncio
@pytest.mark.parametrize("event_json,expected_type,expected_node_type", TEST_EVENTS)
async def test_parse_dify_event(event_json: str, expected_type: type, expected_node_type: NodeType, event_handler):
    """Test that parse_dify_event returns the correct event type with valid data."""
    # Parse the JSON string to a dictionary
    event_data = json.loads(event_json)

    # Parse the event using the event handler's async handle method
    event = await event_handler.handle(event_data)
    
    # Check the event type
    assert isinstance(event, expected_type)
    
    # For node events, verify the node type if expected
    if expected_node_type is not None:
        assert event.content.node_type == expected_node_type

@pytest.mark.asyncio
async def test_parse_node_start_event(event_handler):
    """Test parsing of node_start event with specific validations."""
    event = await event_handler.handle(json.loads(NODE_START_EVENT_JSON))
    assert isinstance(event, NodeStartEvent)
    assert event.content.node_type == NodeType.ANSWER
    assert event.content.created_at is not None  # Check that created_at is set

@pytest.mark.asyncio
async def test_parse_node_finish_event(event_handler):
    """Test parsing of node_finish event with specific validations."""
    event = await event_handler.handle(json.loads(NODE_FINISH_LLM_JSON))
    assert isinstance(event, NodeFinishEvent)
    assert event.content.node_type == NodeType.LLM
    assert event.content.status == NodeStatus.SUCCEEDED
    assert event.content.elapsed_time > 0

@pytest.mark.asyncio
async def test_parse_workflow_finish_event(event_handler):
    """Test parsing of workflow_finish event with specific validations."""
    event = await event_handler.handle(json.loads(WORKFLOW_FINISH_EVENT_JSON))
    assert isinstance(event, WorkflowFinishEvent)
    # Access status from the content dictionary since WorkflowFinishEvent.content is a dict
    assert event.content.get("status") == "succeeded"
    assert event.content.get("total_tokens") > 0

@pytest.mark.asyncio
async def test_parse_invalid_event_type(event_handler):
    """Test that parsing an unknown event type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown event type: invalid_type"):
        await event_handler.handle({"type": "invalid_type", "content": {}})

@pytest.mark.asyncio
async def test_parse_missing_required_fields(event_handler):
    """Test that parsing with missing required fields raises appropriate errors."""
    # Missing content
    with pytest.raises(ValueError):
        await event_handler.handle({"type": "node_start"})
    
    # Invalid content type
    with pytest.raises(ValueError):
        await event_handler.handle({"type": "node_start", "content": "not a dict"})

@pytest.mark.asyncio
async def test_timestamp_parsing(event_handler):
    """Test that timestamps are properly parsed into datetime objects."""
    # Test with node_start event (integer timestamp)
    event = await event_handler.handle(json.loads(NODE_START_EVENT_JSON))
    # The model should parse the timestamp into a datetime object
    assert isinstance(event.content.created_at, datetime)
    # Verify it's timezone-aware
    assert event.content.created_at.tzinfo == timezone.utc
    
    # Test with workflow_finish event (datetime handling)
    wf_event = await event_handler.handle(json.loads(WORKFLOW_FINISH_EVENT_JSON))
    # For workflow_finish, content is a dict with string timestamps
    assert "finished_at" in wf_event.content
    # The raw value should be preserved in the dict
    assert isinstance(wf_event.content["finished_at"], int) or isinstance(wf_event.content["finished_at"], float)