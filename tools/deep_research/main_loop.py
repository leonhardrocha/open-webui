from event_management.dify_event_handler import DifyEventHandler
from event_management.event_handler_registry import EventHandlerRegistry
from event_management.event_emitter import EventEmitter
from typing import Dict, Any, Optional
from tests.mocks import MockEventEmitter, WORKFLOW_FINISH_EVENT_JSON
import json
import asyncio

async def main_loop(*args, **kwargs):
    
    request_info_data = {
        "chat_id": "123456789",
        "message_id": "987654321"
    }
    __event_emitter__ = MockEventEmitter(request_info_data)
    event_handler_registry = EventHandlerRegistry()
    event_emitter = EventEmitter(event_emitter=__event_emitter__)
    dify_event_handler = DifyEventHandler(event_emitter)
    event_handler_registry.register("workflow_finish", dify_event_handler)
    # Save all handlers to YAML
    event_handler_registry.save_to_yaml() 
    await dify_event_handler.handle(json.loads(WORKFLOW_FINISH_EVENT_JSON))


# When you receive an event from Dify
async def handle_dify_event(raw_event: Dict[str, Any], chat_id: str, message_id: str):
    await event_handler.handle_event(raw_event, chat_id, message_id)

if __name__ == "__main__":
    asyncio.run(main_loop())


       