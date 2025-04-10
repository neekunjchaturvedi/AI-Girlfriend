import httpx
import numpy as np
from typing import List, Dict
import json
import os
import faiss
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, index_dir='memories'):
        self.api_url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
        self.headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}
        self.dimension = 384
        self.index_dir = index_dir
        self.user_indices = {}
        self.user_memories = {}
        
        os.makedirs(self.index_dir, exist_ok=True)

    async def get_embedding(self, text: str) -> np.ndarray:
        """Get embeddings from HuggingFace API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={"inputs": text}
                )
                
                if response.status_code != 200:
                    raise Exception("API request failed")
                    
                embeddings = response.json()
                return np.array(embeddings[0])
        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}")
            return np.zeros(self.dimension)

    async def add_memory(self, user_id: str, memory_text: str) -> None:
        """Add a new memory for a specific user"""
        if user_id not in self.user_indices:
            self.user_indices[user_id] = faiss.IndexFlatL2(self.dimension)
            self.user_memories[user_id] = []

        embedding = await self.get_embedding(memory_text)
        self.user_indices[user_id].add(np.array([embedding]).astype('float32'))
        self.user_memories[user_id].append(memory_text)
        
        await self.save_memories(user_id)

    async def get_relevant_memories(self, user_id: str, query: str, k: int = 3) -> List[str]:
        """Get relevant memories for a specific user"""
        if user_id not in self.user_indices:
            await self.load_memories(user_id)
            
        index = self.user_indices.get(user_id)
        memories = self.user_memories.get(user_id, [])
        
        if not memories or not index:
            return []

        query_vector = await self.get_embedding(query)
        D, I = index.search(np.array([query_vector]).astype('float32'), min(k, len(memories)))
        
        return [memories[i] for i in I[0] if i < len(memories)]

    async def save_memories(self, user_id: str) -> None:
        """Save user memories to disk"""
        if user_id not in self.user_indices:
            return

        file_path = os.path.join(self.index_dir, f'{user_id}.json')
        
        try:
            data = {
                'memories': self.user_memories[user_id],
                'index_data': faiss.serialize_index(self.user_indices[user_id]).tobytes().hex()
            }
            with open(file_path, 'w') as f:
                json.dump(data, f)
            logger.info(f"Saved memories for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving memories for user {user_id}: {str(e)}")

    async def load_memories(self, user_id: str) -> bool:
        """Load user memories from disk"""
        file_path = os.path.join(self.index_dir, f'{user_id}.json')
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.user_memories[user_id] = data['memories']
                    index_bytes = bytes.fromhex(data['index_data'])
                    self.user_indices[user_id] = faiss.deserialize_index(index_bytes)
                logger.info(f"Loaded memories for user {user_id}")
                return True
            else:
                self.user_indices[user_id] = faiss.IndexFlatL2(self.dimension)
                self.user_memories[user_id] = []
                logger.info(f"Created new index for user {user_id}")
                return False
        except Exception as e:
            logger.error(f"Error loading memories for user {user_id}: {str(e)}")
            self.user_indices[user_id] = faiss.IndexFlatL2(self.dimension)
            self.user_memories[user_id] = []
            return False
