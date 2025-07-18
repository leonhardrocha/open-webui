# event_handler.py
from typing import Dict, Any, Optional
from event_models import parse_dify_event, DifyEvent
from event_emitter import EventEmitter
from event_handler_registry import IEventHandler, EventHandlerRegistry

class DifyEventHandler(IEventHandler):
    def __init__(self, event_emitter: EventEmitter):
        self.event_emitter = event_emitter
        self.event_type_map = {
            "node_start": self._handle_node_start,
            "node_finish": self._handle_node_finish,
            "iteration_start": self._handle_iteration_start,
            "iteration_finish": self._handle_iteration_finish,
            "workflow_finish": self._handle_workflow_finish,
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

    async def _handle_node_start(self, event: 'NodeStartEvent'):
        """Handle node start event"""
        content = event.content
        await self.event_emitter.progress_update(
            f"Starting {content.node_type} node: {content.title}"
        )

    async def _handle_node_finish(self, event: 'NodeFinishEvent'):
        """Handle node finish event"""
        content = event.content
        if content.error:
            await self.event_emitter.error_update(
                f"Error in {content.node_type} node: {content.error}"
            )
        else:
            await self.event_emitter.progress_update(
                f"Completed {content.node_type} node: {content.title}"
            )

    async def _handle_iteration_start(self, event: 'IterationStartEvent'):
        """Handle iteration start event"""
        content = event.content
        await self.event_emitter.progress_update(
            f"Starting iteration: {content.title}"
        )

    async def _handle_iteration_finish(self, event: 'IterationFinishEvent'):
        """Handle iteration finish event"""
        content = event.content
        await self.event_emitter.progress_update(
            f"Completed iteration: {content.title} "
            f"({content.steps} steps in {content.elapsed_time:.2f}s)"
        )

    async def _handle_workflow_finish(self, event: 'WorkflowFinishEvent'):
        """Handle workflow finish event"""
        content = event.content
        if content.error:
            await self.event_emitter.error_update(
                f"Workflow failed: {content.error}"
            )
        else:
            answer = content.outputs.get('answer', '')
            await self.event_emitter.success_update(
                f"Workflow completed successfully in {content.elapsed_time:.2f}s\n\n"
                f"Answer: {answer[:500]}{'...' if len(answer) > 500 else ''}"
            )