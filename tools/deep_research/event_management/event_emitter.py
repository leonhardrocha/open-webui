import logging
from typing import Callable, Any, Optional, Dict


class EventEmitter:
    """
    EventEmitter is a utility class for emitting events to OpenWebUI frontend.
    
    It provides methods for emitting progress, error, and success events to the OpenWebUI frontend.
    Events are sent as JSON objects with the following format:
    {
        "type": "status",
        "data": {
            "status": <status>,
            "description": <description>,
            "done": <done>,
            "hidden": <hidden>
        }
    }
    
    :param event_emitter: A callback function for emitting events to the OpenWebUI frontend.
    :param debug: If True, sets the logging level to DEBUG, otherwise sets it to INFO.
    """
    def __init__(
        self, event_emitter: Callable[[dict], Any] = None, debug: bool = False
    ):
        self.event_emitter = event_emitter
        self.debug = debug
        self.logger = logging.getLogger()
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        # Prevent adding multiple handlers if already configured by basicConfig
        if not self.logger.handlers:
            handler = logging.FileHandler("event_emitter.log")
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def progress_update(self, description: str):
        """Sends an 'in_progress' status update to OpenWebUI."""
        await self.emit(description, status="in_progress", done=False, hidden=False)
        self.logger.info(f"Progress: {description}")

    async def error_update(self, description: str):
        """Sends an 'error' status update to OpenWebUI."""
        await self.emit(description, status="error", done=True, hidden=False)
        self.logger.error(f"Error: {description}")

    async def success_update(self, description: str):
        """Sends a 'success' status update to OpenWebUI."""
        await self.emit(description, status="success", done=True, hidden=True)
        self.logger.info(f"Success: {description}")

    async def emit(
        self,
        description: str = "Unknown State",
        status: str = "Unknown",
        done: bool = False,
        hidden: bool = False,
    ):
        """Emits a status event to the OpenWebUI frontend."""
        if self.event_emitter:
            event = {
                "type": "status",
                "data": {
                    "status": status,
                    "description": description,
                    "done": done,
                    "hidden": hidden,
                },
            }
            await self.event_emitter(event)
            self.logger.debug(f"EventEmitter: {event}")

    def get_closure_info(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves closure variables from a function, specifically looking for a dictionary.
        Used to extract chat_id and message_id from the external event_emitter closure.
        A mock implementation:
        class MockEventEmitter:
            def __init__(self, request_info_data):
                self._request_info = request_info_data # The data to be captured

            def __call__(self, event_data):
                # In a real Open WebUI environment, this would send an event to the UI
                print(f"Emitting event: {event_data}")

            @property
            def __closure__(self):
                # This is where the magic happens for demonstration
                # In a real scenario, the __closure__ would be naturally created
                # if MockEventEmitter was a nested function or had a cell object
                # for _request_info. For demonstration, we're simulating it.
                class Cell:
                    def __init__(self, content):
                        self.cell_contents = content
                return (Cell(self._request_info),)

        """
        if hasattr(self.event_emitter, "__closure__") and self.event_emitter.__closure__:
            for cell in self.event_emitter.__closure__:
                if isinstance(request_info := cell.cell_contents, dict):
                    # self.logger.debug(f"Closure info found: {request_info}")
                    return request_info
        self.logger.debug("No dictionary found in function closure.")
        return None
