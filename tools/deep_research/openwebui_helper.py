from typing import Optional, Dict, List, Any, AsyncGenerator
from pydantic import BaseModel
from .dify_client import IDifyClient, DifyAPIResponse
from .models import Conversation, MessageContent, DifyFile

class OpenWebUIHelper:
    def __init__(self, dify_client: IDifyClient, cache_dir: str = "~/.dify/cache"):
        self.client = dify_client
        self.cache_dir = cache_dir
        self.conversations: Dict[str, Conversation] = {}
        self.files: Dict[str, Dict[str, DifyFile]] = {}
        
    async def send_message(
        self,
        chat_id: str,
        message: str,
        files: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Send a message to Dify and return the response"""
        conversation = self.conversations.get(chat_id)
        
        response = await self.client.send_message(
            message=message,
            conversation_id=conversation.id if conversation else None,
            files=files
        )
        
        if not response.success:
            raise Exception(f"Failed to send message: {response.error}")
            
        # Update conversation state
        if not conversation:
            conversation = Conversation(
                id=response.data['conversation_id'],
                title=response.data.get('title', 'New Conversation'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.conversations[chat_id] = conversation
            
        return response.data
        
    async def stream_message(
        self,
        chat_id: str,
        message: str,
        files: Optional[List[Dict]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a message to Dify and yield responses"""
        conversation = self.conversations.get(chat_id)
        
        async for chunk in self.client.stream_message(
            message=message,
            conversation_id=conversation.id if conversation else None,
            files=files
        ):
            yield chunk
            
            # Update conversation state on the first chunk
            if 'conversation_id' in chunk and not conversation:
                conversation = Conversation(
                    id=chunk['conversation_id'],
                    title=chunk.get('title', 'New Conversation'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.conversations[chat_id] = conversation