from dify_event_handler import DifyEventHandler
from event_handler_registry import EventHandlerRegistry
from event_emitter import EventEmitter
from typing import Dict, Any, Optional
from mocks import MockEventEmitter, WORKFLOW_FINISH_EVENT


def main_loop(*args, **kwargs):
    
    pass    


# When you receive an event from Dify
async def handle_dify_event(raw_event: Dict[str, Any], chat_id: str, message_id: str):
    await event_handler.handle_event(raw_event, chat_id, message_id)

if __name__ == "__main__":

    request_info_data = {
        "chat_id": "123456789",
        "message_id": "987654321"
    }
    __event_emitter__ = MockEventEmitter(request_info_data)
    event_handler_registry = EventHandlerRegistry()
    event_emitter = EventEmitter()
    dify_event_handler = DifyEventHandler(event_emitter)
    event_handler_registry.register("workflow_finish", dify_event_handler)

    event_handler_registry.save_to_yaml() 
    event_handler_registry.handle(WORKFLOW_FINISH_EVENT)

    main_loop()

# Save all handlers to YAML
       