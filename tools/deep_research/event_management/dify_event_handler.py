# event_handler.py
from typing import Dict, Any, Optional
from .event_models import (
    DifyEvent, 
    NodeStartEvent, 
    NodeFinishEvent, 
    WorkflowFinishEvent, 
    parse_dify_event
)
from .event_emitter import EventEmitter
from .event_handler_registry import IEventHandler

class DifyEventHandler(IEventHandler):
    def __init__(self, event_emitter: EventEmitter):
        self.event_emitter = event_emitter
        self.event_map = {
            "node_start": NodeStartEvent,
            "node_finish": NodeFinishEvent,
            "iteration_finish": NodeFinishEvent,
            "workflow_finish": WorkflowFinishEvent,
        }

    def is_event_type_supported(self, event_type: str) -> bool:
        return event_type in self.event_type_map

    async def handle(self, event_data: Dict[str, Any]):

        """Handle a Dify event"""
        
        try:
            # Parse the event using our models
            event = parse_dify_event(event_data)            
            
            if not self.is_event_type_supported(event.type):
                raise ValueError(f"Unsupported event type: {event.type}")
            handler = self.event_type_map.get(event.type)
            if handler:
                await handler(event)
                
        except Exception as e:
            await self.event_emitter.error_update(
                f"Error processing event: {str(e)}"
            )
            raise

    def parse_dify_event(self, event_data: Dict[str, Any]) -> DifyEvent:
        """Parse raw event data into appropriate event model."""
        event_type = event_data.get("type")
        if event_type not in self.event_map:
            raise ValueError(f"Unknown event type: {event_type}")

        # Get the model class for this event
        model_class = self.event_map[event_type]
        
        # Let Pydantic handle the content model selection based on node_type
        return model_class.model_validate(event_data)