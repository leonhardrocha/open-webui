# event_handler.py
from typing import Dict, Any
from event_management.event_models import (
    DifyEvent, 
    NodeStartEvent, 
    NodeFinishEvent, 
    IterationFinishEvent,
    WorkflowFinishEvent
)
from event_management.event_emitter import EventEmitter
from event_management.event_handler_registry import IEventHandler

class DifyEventHandler(IEventHandler):
    def __init__(self, event_emitter: EventEmitter):
        self.event_emitter = event_emitter
        self.event_map = {
            "node_start": NodeStartEvent,
            "node_finish": NodeFinishEvent,
            "iteration_finish": IterationFinishEvent,
            "workflow_finish": WorkflowFinishEvent,
        }
        self.event_type_map = {}  # Initialize event_type_map

    def is_event_type_supported(self, event_type: str) -> bool:
        return event_type in self.event_type_map

    async def handle(self, event_data: Dict[str, Any]):
        """Handle a Dify event asynchronously.
        
        Args:
            event_data: The raw event data to process
            
        Returns:
            The parsed event object
        """
        try:
            # Parse the event using our models (synchronous operation)
            event = self.parse_dify_event(event_data)
            
            # Get the appropriate handler for this event type if any
            handler = self.event_type_map.get(event.type)
            if handler:
                # If there's a handler, await it
                await handler(event)
                
            return event
                
        except Exception as e:
            # Emit error status
            await self.event_emitter.emit(
                "status",
                {
                    "status": "error",
                    "description": f"Error processing event: {str(e)}",
                    "done": True,
                    "hidden": False
                }
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