# pipeline.py
# title: DIFY Manifold Pipe
# authors: xuzhougeng
# author_url: https://github.com/xuzhougeng
# funding_url: https://github.com/open-webui
# version: 0.1.2
# description: This pipeline is used for DIFY's API interface to interact with DIFY's API.


import os
import requests
import json
import time
from typing import List, Union, Generator, Iterator, Optional, Callable, Any, Dict, AsyncGenerator
from pydantic import BaseModel, Field
from open_webui.utils.misc import pop_system_message
from open_webui.config import UPLOAD_DIR
import base64
import tempfile
import asyncio
import dotenv
import aiohttp


# (EventEmitter class definition as provided in the template notes)
class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None):
        self.event_emitter = event_emitter

    async def progress_update(self, description: str):
        await self.emit(description)

    async def error_update(self, description: str):
        await self.emit(description, "error", True)

    async def success_update(self, description: str):
        await self.emit(description, "success", True)

    async def emit(
        self,
        description: str = "Unknown State",
        status: str = "in_progress",
        done: bool = False,
    ):
        if self.event_emitter:
            await self.event_emitter(
                {
                    "type": "status",
                    "data": {
                        "status": status,
                        "description": description,
                        "done": done,
                    },
                }
            )



class Tools:
    """
    Tools class for OpenWebUI pipelines.
    This class is often expected by OpenWebUI even if no specific tools are defined.
    It can contain functions that act as external tools or functionalities
    that the pipeline might call.
    """

    class Valves(BaseModel):
        # Environment variable settings
        DIFY_BASE_URL: str = Field(
            default="http://localhost/v1",
            description="Optional: Base URL for the Dify API (default: http://localhost/v1).",
        )
        WEBUI_BASE_URL: str = Field(
            default="http://localhost/v1",
            description="Optional: Base URL for the OpenWebUI API (default: http://localhost:3000/).",
        )
        DIFY_USER: str = Field(
            default="",
            description="Optional: Username used in Dify workflow, defaults to user´s email.",
        )
        DIFY_KEY: str = Field(default="", description="Your Dify API Key.")
        WEBUI_KEY: str = Field(default="", description="Your OpenWebUI API Key.")

    def __init__(self):
        self.citation = True
        self.type = "manifold"
        self.id = "deep_research"
        self.name = "Deep Research"

        # Initialize valves with environment variables, providing a default DIFY_KEY for testing
        self.valves = self.Valves(
            **{
                "DIFY_KEY": os.getenv("DIFY_KEY", "app-05EAqfax9bXXxUuT9EgMao6p"),
                "WEBUI_KEY": os.getenv("WEBUI_KEY", "app-05EAqfax9bXXxUuT9EgMao6p"),
                "DIFY_BASE_URL": os.getenv("DIFY_BASE_URL", "http://localhost/v1"),
                "WEBUI_BASE_URL": os.getenv("WEBUI_BASE_URL", "http://localhost:3000/"),
                "DIFY_USER": os.getenv("DIFY_USER", "leonardo_rocha"),
            }
        )

        self.openwebui = OpenWebUIHelper(self.valves)
        self.dify = DifyHelper(self.valves)        
        self.dify.load_state()

    async def research_stream(
        self, 
        query: str,
        __event_emitter__: Optional[Callable[[dict], Any]] = None) -> str:
        """
        Researches based on the input string.   
        
        :param query: The query to research.
        :return: The research result.
        """
        event_emitter = EventEmitter(__event_emitter__)
        await event_emitter.progress_update("Researching...")
        
        if not self.valves.DIFY_KEY:
            error_result = "Error: DIFY_KEY is not set"
            await event_emitter.error_update(error_result)
            return error_result
        
        try:
            result_parts = []
            async for chunk in self.dify.send_chat_message(query):
                if chunk.get('type') == 'message':
                    result_parts.append(chunk.get('content', ''))
                elif chunk.get('type') == 'error':
                    error_result = f"Error: {chunk.get('message', 'Unknown error occurred')}"
                    await event_emitter.error_update(error_result)
                    return error_result
            
            if not result_parts:
                error_result = "Error: No response content received"
                await event_emitter.error_update(error_result)
                return error_result
                
            result = ''.join(result_parts)
            await event_emitter.success_update("Researching complete.")
            return result
            
        except Exception as e:
            error_result = f"Error during research: {str(e)}"
            await event_emitter.error_update(error_result)
            return error_result

    async def research(
        self, 
        query: str,
        __event_emitter__: Optional[Callable[[dict], Any]] = None) -> str:
        """
        Researches based on the input string.   
        
        :param query: The query to research.
        :return: The research result.
        """
        event_emitter = EventEmitter(__event_emitter__)
        await event_emitter.progress_update("Researching...")
        if self.valves.DIFY_KEY is None:
            error_result = "Error: DIFY_KEY is not set"
            await event_emitter.error_update(error_result)
            return error_result
        else:
            result = await self.dify.send_chat_message(query)
            if result is None:
                error_result = "Error: Could not get completion"
                await event_emitter.error_update(error_result)
                return error_result
            else:
                await event_emitter.success_update("Researching complete.")
                return result
    
class OpenWebUIHelper:

    def __init__(self, valves: Tools.Valves):
        self.valves = valves

    async def get_models(self) -> Optional[List[Dict[str, Any]]]:
            """
            Get the list of models from the Dify API.
            
            :return: The list of models or None if there was an error.
            """
            response = requests.get(
                url=f"{self.valves.WEBUI_BASE_URL}/api/models",
                headers={
                    "Authorization": f"Bearer {self.valves.WEBUI_KEY}",
                },
            )
            if response.status_code != 200:
                error_result = f"Error: {response.text}"
                return None
            else:
                result = response.json()
                return result["models"]

    async def get_completion(self, query: str) -> Optional[str]:
        """
        Posts to the Dify API to get the completion of the query.
        
        :param query: The query to get the completion of.
        :return: The completion or None if there was an error.
        """
        response = requests.post(
            url=f"{self.valves.DIFY_BASE_URL}/api/chat/completions",
            headers={
                "Authorization": f"Bearer {self.valves.DIFY_KEY}",
            },
            json=query
        )    
        if response.status_code != 200:
            return None
        else:
            return response["choices"][0]["message"]["content"]


class DifyHelper:

    def __init__(self, valves: Tools.Valves):
        # Storage format for mapping OpenWebUI chat/message IDs to Dify IDs:
        # {
        #   "chat_id_1": {
        #     "dify_conversation_id": "xxx",
        #     "messages": [{"chat_message_id_1": "dify_message_id_1"}, ...]
        #   }
        # }
        self.valves = valves
        self.chat_message_mapping = {}

        # Storage format for keeping track of the Dify model used per chat:
        # {
        #   "chat_id_1": "gpt-3.5-turbo",
        #   "chat_id_2": "gpt-4"
        # }
        self.dify_chat_model = {}

        # Storage format for mapping OpenWebUI file IDs to Dify file IDs:
        # {
        #   "chat_id_1": {
        #     "file_id1":{
        #       "local_file_path": "/path/to/file1.pdf",
        #       "dify_file_id": "dify_file_123",
        #       "file_name": "file1.pdf"
        #     },
        #     "file_id2":{
        #       "local_file_path": "/path/to/file2.jpg",
        #       "dify_file_id": "dify_file_456",
        #       "file_name": "file2.jpg"
        #     }
        #   }
        # }
        self.dify_file_list = {}

        self.data_cache_dir = "data/dify"

    def get_file_extension(self, file_name: str) -> str:
        """
        Gets the file extension.
        os.path.splitext(file_name) returns a tuple, the first element is the filename, the second is the extension.
        """
        return os.path.splitext(file_name)[1].strip(".")

    # Black magic: get closure variables from __event_emitter__
    def get_closure_info(self, func):
        """
        Retrieves closure variables from a function, specifically looking for a dictionary.
        This is used to extract chat_id and message_id from the __event_emitter__ closure.
        """
        if hasattr(func, "__closure__") and func.__closure__:
            for cell in func.__closure__:
                if isinstance(cell.cell_contents, dict):
                    return cell.cell_contents
        return None

    async def send_chat_message(
        self,
        query: str,
        user: Optional[str] = None,
        conversation_id: Optional[str] = None,
        response_mode: str = "streaming",
        inputs: Optional[dict] = None,
        files: Optional[List[dict]] = None,
        auto_generate_name: bool = True,
        event_emitter: Optional[Callable[[dict], Any]] = None
    ) -> AsyncGenerator[dict, None]:
        """Sends a chat message to the Dify API and handles the streaming response.

        Args:
            query: User input/question content.
            user: User identifier.
            conversation_id: Optional conversation ID to continue a conversation.
            response_mode: Response mode, 'streaming' (default) or 'blocking'.
            inputs: Dictionary of input variables for the app.
            files: List of file objects to include in the request.
            auto_generate_name: Whether to auto-generate conversation title.
            event_emitter: Optional callback function to emit events.

        Yields:
            Dictionary containing event data from the streaming response.
        """
        user = user or self.valves.DIFY_USER
        endpoint = f"{self.valves.DIFY_BASE_URL}/chat-messages"
        headers = {
            "Authorization": f"Bearer {self.valves.DIFY_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "query": query,
            "user": user,
            "response_mode": response_mode,
            "inputs": inputs or {},
            "auto_generate_name": auto_generate_name,
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
            
        if files:
            payload["files"] = files
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        error_msg = error_data.get('message', 'Unknown error occurred')
                        yield {
                            'event': 'error',
                            'message': f"API request failed with status {response.status}: {error_msg}"
                        }
                        return
                    
                    # For blocking mode, just return the JSON response
                    if response_mode == "blocking":
                        result = await response.json()
                        yield result
                        return
                    
                    # For streaming mode, process the SSE stream
                    buffer = ""
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                            
                        if line.startswith('data: '):
                            try:
                                event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                                event_type = event_data.get('event', 'message')
                                
                                # Handle different event types
                                self.handle_event(event_data, event_type, streaming = True)

                            except json.JSONDecodeError as e:
                                print(f"Failed to parse event data: {line}")
                                continue
                    
        except asyncio.TimeoutError:
            yield {
                'event': 'error',
                'message': 'Request timed out after 5 minutes'
            }
        except aiohttp.ClientError as e:
            yield {
                'event': 'error',
                'message': f"HTTP client error: {str(e)}"
            }
        except Exception as e:
            yield {
                'event': 'error',
                'message': f"Unexpected error: {str(e)}"
            }

    def handle_event(self, event_data: dict, event_type: str):
        """Handle different event types"""
        if event_type == 'message':
            yield {
                'type': 'message',
                'task_id': event_data.get('task_id'),
                'message_id': event_data.get('message_id'),
                'conversation_id': event_data.get('conversation_id'),
                'content': event_data.get('answer', ''),
                'created_at': event_data.get('created_at')
            }
        elif event_type == 'message_end':
            yield {
                'type': 'message_end',
                'task_id': event_data.get('task_id'),
                'message_id': event_data.get('message_id'),
                'conversation_id': event_data.get('conversation_id'),
                'metadata': event_data.get('metadata', {}),
                'usage': event_data.get('usage', {}),
                'retriever_resources': event_data.get('retriever_resources', [])
            })
        elif event_type == 'error':
            yield {
                'type': 'error',
                'status': event_data.get('status'),
                'code': event_data.get('code'),
                'message': event_data.get('message')
            }
        # Add more event handlers as needed
    

    def save_state(self):
        """Persists Dify related state variables to file."""
        os.makedirs(self.data_cache_dir, exist_ok=True)

        # Save chat_message_mapping to a JSON file
        chat_mapping_file = os.path.join(
            self.data_cache_dir, "chat_message_mapping.json"
        )
        with open(chat_mapping_file, "w", encoding="utf-8") as f:
            json.dump(self.chat_message_mapping, f, ensure_ascii=False, indent=2)

        # Save chat_model to a JSON file
        chat_model_file = os.path.join(self.data_cache_dir, "chat_model.json")
        with open(chat_model_file, "w", encoding="utf-8") as f:
            json.dump(self.dify_chat_model, f, ensure_ascii=False, indent=2)

        # Save file_list to a JSON file
        file_list_file = os.path.join(self.data_cache_dir, "file_list.json")
        with open(file_list_file, "w", encoding="utf-8") as f:
            json.dump(self.dify_file_list, f, ensure_ascii=False, indent=2)

    def load_state(self):
        """Loads Dify related state variables from files."""
        try:
            # Load chat_message_mapping.json
            chat_mapping_file = os.path.join(
                self.data_cache_dir, "chat_message_mapping.json"
            )
            if os.path.exists(chat_mapping_file):
                with open(chat_mapping_file, "r", encoding="utf-8") as f:
                    self.chat_message_mapping = json.load(f)
            else:
                self.chat_message_mapping = {}

            # Load chat_model.json
            chat_model_file = os.path.join(self.data_cache_dir, "chat_model.json")
            if os.path.exists(chat_model_file):
                with open(chat_model_file, "r", encoding="utf-8") as f:
                    self.dify_chat_model = json.load(f)
            else:
                self.dify_chat_model = {}

            # Load file_list.json
            file_list_file = os.path.join(self.data_cache_dir, "file_list.json")
            if os.path.exists(file_list_file):
                with open(file_list_file, "r", encoding="utf-8") as f:
                    self.dify_file_list = json.load(f)
            else:
                self.dify_file_list = {}

        except Exception as e:
            print(f"Failed to load Dify state files: {e}")
            # Use empty dictionaries if loading fails
            self.chat_message_mapping = {}
            self.dify_chat_model = {}
            self.dify_file_list = {}

    def get_models(self):
        """
        Retrieves the list of DIFY models.
        (Future improvement: add code to fetch directly from Ollama)
        """
        return [
            {"id": "deepseek-r1", "name": "deepseek-r1"},
        ]

    def upload_file(self, user_id: str, file_path: str, mime_type: str) -> str:
        """
        This function is responsible for uploading files to the DIFY server and returning the file ID.
        """
        url = f"{self.valves.DIFY_BASE_URL}/files/upload"
        headers = {
            "Authorization": f"Bearer {self.valves.DIFY_KEY}",
        }

        file_name = os.path.basename(file_path)

        files = {
            # File field: (filename, file object, MIME type)
            "file": (file_name, open(file_path, "rb"), mime_type),
            # Regular form field: (None, value)
            "user": (None, user_id),
        }

        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()  # Raise an exception for HTTP errors

        file_id = response.json()["id"]

        # Optional: print response
        return file_id

    def is_doc_file(self, file_path: str) -> bool:
        """
        Checks if the file is a document file.
        Supported types: 'TXT', 'MD', 'MARKDOWN', 'PDF', 'HTML', 'XLSX', 'XLS', 'DOCX', 'CSV', 'EML', 'MSG', 'PPTX', 'PPT', 'XML', 'EPUB'.
        """
        file_extension = get_file_extension(file_path).upper()
        if file_extension in [
            "PDF",
            "XLSX",
            "XLS",
            "DOCX",
            "EML",
            "MSG",
            "PPTX",
            "PPT",
            "XML",
            "EPUB",
        ]:
            return True

        return False

    def is_text_file(self, mime_type: str) -> bool:
        """
        Checks if the file is a text file based on its MIME type.
        """
        if "text" in mime_type:
            return True
        return False

    def is_audio_file(self, file_path: str) -> bool:
        """
        Checks if the file is an audio file.
        Supported types: 'MP3', 'M4A', 'WAV', 'WEBM', 'AMR'.
        """
        if get_file_extension(file_path).upper() in [
            "MP3",
            "M4A",
            "WAV",
            "WEBM",
            "AMR",
        ]:
            return True
        return False

    def is_video_file(self, file_path: str) -> bool:
        """
        Checks if the file is a video file.
        Supported types: 'MP4', 'MOV', 'MPEG', 'MPGA'.
        """
        if get_file_extension(file_path).upper() in ["MP4", "MOV", "MPEG", "MPGA"]:
            return True
        return False

    def is_image_file(self, file_path: str) -> bool:
        """
        Checks if the file is an image file.
        Supported types: 'JPG', 'JPEG', 'PNG', 'GIF', 'WEBP', 'SVG'.
        """
        if get_file_extension(file_path).upper() in [
            "JPG",
            "JPEG",
            "PNG",
            "GIF",
            "WEBP",
            "SVG",
        ]:
            return True
        return False

    def upload_text_file(self, user_id: str, file_path: str) -> str:
        """
        Uploads a text file to the server, adding the filename as the first line.
        Supported types: plain text files.

        Args:
            file_path: Path to the text file.
            user_id: User ID.

        Returns:
            str: The ID of the uploaded file.
        """
        try:
            # Get original filename
            filename = os.path.basename(file_path)

            # Read original file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Create new content with filename marker
            new_content = f"#{filename}\n{content}"

            # Create a temporary file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".txt", mode="w", encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(new_content)
                temp_file_path = tmp_file.name

            try:
                # Upload the file
                file_id = self.upload_file(user_id, temp_file_path, "text/plain")
                return file_id
            finally:
                # Clean up the temporary file
                os.remove(temp_file_path)

        except UnicodeDecodeError:
            raise ValueError("File encoding is not UTF-8 format")
        except Exception as e:
            raise ValueError(f"Failed to process text file: {str(e)}")

    def upload_images(self, image_data_base64: str, user_id: str) -> str:
        """
        Uploads base64 encoded images to the DIFY server, returning the image path.
        Supported types: 'JPG', 'JPEG', 'PNG', 'GIF', 'WEBP', 'SVG'.
        """
        try:
            # Remove the data URL scheme prefix if present
            if image_data_base64.startswith("data:"):
                # Extract the base64 data after the comma
                image_data_base64 = image_data_base64.split(",", 1)[1]

            # Decode base64 image data
            image_data = base64.b64decode(image_data_base64)

            # Create and save temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(image_data)
                temp_file_path = tmp_file.name
            try:
                file_id = self.upload_file(user_id, temp_file_path, "image/png")
            finally:
                os.remove(temp_file_path)
            return file_id
        except Exception as e:
            raise ValueError(f"Failed to process base64 image data: {str(e)}")

    def pipes(self) -> List[dict]:
        """Returns the list of available DIFY models."""
        return self.get_models()

    def pipe(
        self,
        body: dict,
        __event_emitter__: dict = None,
        __user__: Optional[dict] = None,
        __task__=None,
    ) -> Union[str, Generator, Iterator]:
        """Handles chat requests."""

        # Get model name
        model_name = body["model"][body["model"].find(".") + 1 :]

        # Handle special tasks like title or tag generation
        if __task__ is not None:
            if __task__ == "title_generation":
                return model_name
            elif __task__ == "tags_generation":
                return f'{{"tags":[{model_name}]}}'

        # Get current user
        current_user = self.valves.DIFY_USER if __user__ is None else __user__["email"]

        # Process system messages and regular messages
        system_message, messages = pop_system_message(body["messages"])
        print(f"system_message:{system_message}")
        print(f"messages:{messages}, {len(messages)}")

        # Get chat_id and message_id from event_emitter
        cell_contents = self.get_closure_info(__event_emitter__)
        try:
            chat_id = cell_contents["chat_id"]
            message_id = cell_contents["message_id"]
        except Exception as e:
            print(f"{cell_contents=}")
            raise ValueError(f"Failed to get chat_id  or message_id: {str(e)}")

        # Handle conversation model and context
        parent_message_id = None
        # Modify conversation history processing logic in the pipe function
        if len(messages) == 1:
            # New conversation logic remains unchanged
            self.dify_chat_model[chat_id] = model_name
            self.chat_message_mapping[chat_id] = {
                "dify_conversation_id": "",
                "messages": [],
            }
            self.dify_file_list[chat_id] = {}
        else:
            # Check if history exists
            if chat_id in self.chat_message_mapping:
                # First, validate the model
                if chat_id in self.dify_chat_model:
                    if self.dify_chat_model[chat_id] != model_name:
                        raise ValueError(
                            f"Cannot change model in an existing conversation. This conversation was started with {self.dify_chat_model[chat_id]}"
                        )
                else:
                    # If somehow the model is not recorded (exceptional case), record the current model
                    self.dify_chat_model[chat_id] = model_name

                chat_history = self.chat_message_mapping[chat_id]["messages"]
                current_msg_index = len(messages) - 1  # Index of the current message

                # If not the first message, get the previous message's dify_id as parent
                if current_msg_index > 0 and len(chat_history) >= current_msg_index:
                    previous_msg = chat_history[current_msg_index - 1]
                    parent_message_id = list(previous_msg.values())[0]

                    # Crucial modification: truncate message history after the current position
                    self.chat_message_mapping[chat_id]["messages"] = chat_history[
                        :current_msg_index
                    ]

        # Get the last message as query
        message = messages[-1]
        query = ""
        inputs = {"model": model_name}
        file_list = []

        # Process message content
        if isinstance(message.get("content"), list):
            for item in message["content"]:
                if item["type"] == "text":
                    query += item["text"]
                if item["type"] == "image_url":
                    upload_file_id = self.upload_images(
                        item["image_url"]["url"], current_user
                    )
                    upload_file_dict = {
                        "type": "image",
                        "transfer_method": "local_file",
                        "url": "",
                        "upload_file_id": upload_file_id,
                    }
                    file_list.append(upload_file_dict)
        else:
            query = message.get("content", "")

        # Process file uploads
        if "upload_files" in body:
            for file in body["upload_files"]:
                if file["type"] != "file":
                    continue

                file_id = file["id"]
                if (
                    chat_id in self.dify_file_list
                    and file_id in self.dify_file_list[chat_id]
                ):
                    file_list.append(self.dify_file_list[chat_id][file_id])
                    continue

                # Get file information and upload
                if "collection_name" in file:
                    file_path = os.path.join(UPLOAD_DIR, file["file"]["filename"])
                else:
                    file_path = file["file"]["path"]
                file_mime_type = file["file"]["meta"]["content_type"]

                upload_file_dict = {
                    "transfer_method": "local_file",
                    "url": "",
                }

                # Process different file types
                if self.is_doc_file(file_path):
                    upload_file_id = self.upload_file(current_user, file_path, file_mime_type)
                    upload_file_dict.update(
                        {"type": "document", "upload_file_id": upload_file_id}
                    )
                elif self.is_text_file(file_mime_type):
                    upload_file_id = self.upload_text_file(current_user, file_path)
                    upload_file_dict.update(
                        {"type": "document", "upload_file_id": upload_file_id}
                    )
                elif self.is_audio_file(file_path):
                    upload_file_id = self.upload_file(current_user, file_path, file_mime_type)
                    upload_file_dict.update(
                        {"type": "audio", "upload_file_id": upload_file_id}
                    )
                elif self.is_image_file(file_path):
                    upload_file_id = self.upload_file(current_user, file_path, file_mime_type)
                    upload_file_dict.update(
                        {"type": "image", "upload_file_id": upload_file_id}
                    )



if __name__ == "__main__":
    
    dotenv.load_dotenv()
    token = os.getenv("DIFY_KEY", None)
    if token is None:
        raise ValueError("DIFY_KEY is not set")
    tools = Tools()
    query = {
        "inputs": {},
        "query": "What are the specs of the iPhone 13 Pro Max?",
        "response_mode": "streaming",
        "conversation_id": "",
        "user": "abc-123",
        "files": [
            {
                "type": "image",
                "transfer_method": "remote_url",
                "url": "https://cloud.dify.ai/logo/logo-site.png"
            }
        ]
    }

    result = asyncio.run(tools.research_stream(query))
    print(result)