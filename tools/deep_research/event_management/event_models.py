from typing import Dict, Any, Union, Literal, Optional, Type, List
from pydantic import BaseModel, field_validator
from datetime import datetime, timezone
from enum import Enum
from dateutil import tz

# Enums
class NodeType(str, Enum):
    ANSWER = "answer"
    VARIABLE_AGGREGATOR = "variable-aggregator"
    TEMPLATE_TRANSFORM = "template-transform"
    IF_ELSE = "if-else"
    LLM = "llm"
    ITERATION = "iteration"

class NodeStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RUNNING = "running"

# Mixin classes for timestamp handling
class WithCreatedAtMixin:
    created_at: Optional[Union[datetime, int, float]] = None

    @field_validator('created_at', mode='before')
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v

class WithFinishedAtMixin:
    finished_at: Optional[Union[datetime, int, float]] = None

    @field_validator('finished_at', mode='before')
    @classmethod
    def parse_finished_at(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v

# Base Models
class BaseEvent(BaseModel):
    """Base class for all event types"""
    type: str
    content: Dict[str, Any]

class BaseNodeContent(BaseModel):
    """Base content model for all node types"""
    id: str
    node_id: str
    node_type: NodeType
    title: str
    index: Optional[int] = None

# Node Type Specific Content
class LLMNodeContent(BaseNodeContent):
    """Content specific to LLM nodes"""
    node_type: Literal[NodeType.LLM] = NodeType.LLM
    model: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    prompt: Optional[Union[str, List[Dict[str, str]]]] = None

class AnswerNodeContent(BaseNodeContent):
    """Content specific to Answer nodes"""
    node_type: Literal[NodeType.ANSWER] = NodeType.ANSWER
    answer: Optional[str] = None

class VariableAggregatorNodeContent(BaseNodeContent):
    """Content specific to Variable Aggregator nodes"""
    node_type: Literal[NodeType.VARIABLE_AGGREGATOR] = NodeType.VARIABLE_AGGREGATOR
    variables: Optional[Dict[str, Any]] = None

class TemplateTransformNodeContent(BaseNodeContent):
    """Content specific to Template Transform nodes"""
    node_type: Literal[NodeType.TEMPLATE_TRANSFORM] = NodeType.TEMPLATE_TRANSFORM
    template: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None

class IfElseNodeContent(BaseNodeContent):
    """Content specific to If-Else nodes"""
    node_type: Literal[NodeType.IF_ELSE] = NodeType.IF_ELSE
    condition: Optional[bool] = None
    condition_result: Optional[Dict[str, Any]] = None

class IterationNodeContent(BaseNodeContent):
    """Content specific to Iteration nodes"""
    node_type: Literal[NodeType.ITERATION] = NodeType.ITERATION
    iteration_count: Optional[int] = None
    current_iteration: Optional[int] = None

# Node-specific content models
class NodeStartContent(BaseNodeContent, WithCreatedAtMixin):
    """Content for node start events"""
    predecessor_node_id: Optional[str] = None
    extras: Dict[str, Any] = {}
    parallel_id: Optional[str] = None
    parallel_start_node_id: Optional[str] = None
    parent_parallel_id: Optional[str] = None
    parent_parallel_start_node_id: Optional[str] = None
    iteration_id: Optional[str] = None
    loop_id: Optional[str] = None
    parallel_run_id: Optional[str] = None
    agent_strategy: Optional[Any] = None

class NodeFinishContent(NodeStartContent, WithFinishedAtMixin):
    """Content for node finish events"""
    outputs: Optional[Dict[str, Any]] = None
    status: Optional[NodeStatus] = None
    error: Optional[str] = None
    elapsed_time: Optional[float] = None
    execution_metadata: Optional[Dict[str, Any]] = None
    total_tokens: Optional[int] = None
    files: Optional[List[Dict[str, Any]]] = None

# Event models
class NodeStartEvent(BaseEvent):
    """Event triggered when a node starts processing"""
    type: Literal["node_start"] = "node_start"
    content: NodeStartContent

class NodeFinishEvent(BaseEvent):
    """Event triggered when a regular node finishes processing"""
    type: Literal["node_finish"] = "node_finish"
    content: NodeFinishContent

class IterationFinishEvent(BaseEvent):
    """Event triggered when an iteration node finishes processing"""
    type: Literal["iteration_finish"] = "iteration_finish"
    content: NodeFinishContent

class WorkflowFinishContent(BaseModel):
    """Content for workflow finish events"""
    id: str
    workflow_id: str
    sequence_number: int
    status: str
    outputs: Dict[str, Any]
    error: Optional[str] = None
    elapsed_time: float
    total_tokens: int
    total_steps: int
    created_by: Dict[str, str]
    created_at: Union[datetime, int, float]
    finished_at: Union[datetime, int, float]
    exceptions_count: int
    files: List[Dict[str, Any]] = []

    @field_validator('created_at', 'finished_at', mode='before')
    @classmethod
    def parse_timestamps(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v

class WorkflowFinishEvent(BaseEvent):
    """Event triggered when a workflow finishes"""
    type: Literal["workflow_finish"] = "workflow_finish"
    content: Dict[str, Any]  # Will contain WorkflowFinishContent

# Union type for all Dify events
DifyEvent = Union[NodeStartEvent, NodeFinishEvent, WorkflowFinishEvent]
