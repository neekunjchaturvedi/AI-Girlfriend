from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv
import motor.motor_asyncio
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import JWTError, jwt
from datetime import datetime, timedelta
import httpx
import logging
from cachetools import TTLCache
from huggingface_hub import InferenceClient
from typing import List, Optional, Dict
from pydantic import BaseModel
import uuid

from utils.memory_manager import MemoryManager
from utils.sentiment_analyzer import SentimentAnalyzer
from utils.prompt_builder import PromptBuilder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT & Auth configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/google", auto_error=False)

# MongoDB setup
def get_database_client():
    try:
        # Direct connection string with retryWrites and proper timeout settings
        connection_string = os.getenv("MONGO_URI")
        if not connection_string:
            raise ValueError("MONGO_URI environment variable is not set")
            
        client = motor.motor_asyncio.AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            retryWrites=True,
            retryReads=True,
            maxPoolSize=50,
            minPoolSize=10
        )
        return client
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        raise

try:
    client = get_database_client()
    db = client.userdb  # Use your database name
    users_collection = db.users
except Exception as e:
    logger.error(f"Failed to initialize MongoDB: {e}")
    raise

# Cache setup
auth_cache = TTLCache(maxsize=100, ttl=300)

# Hugging Face setup
HF_TOKEN = os.getenv("HF_TOKEN")
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

# Initialize new components
memory_manager = MemoryManager()
sentiment_analyzer = SentimentAnalyzer()
prompt_builder = PromptBuilder()

# Pydantic models
class Message(BaseModel):
    role: str
    text: str
    timestamp: str
    sentiment: Optional[Dict] = None

class Chat(BaseModel):
    chat_id: str
    chat_title: str
    messages: List[Message]
    created_at: str

class ChatCreate(BaseModel):
    message: Optional[str] = None
    chat_title: Optional[str] = "New Chat"

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str
    chats: List[Chat] = []
    relationship_stage: str = "acquaintance"
    personality_traits: List[str] = ["caring", "empathetic", "playful"]

# System prompt
SYSTEM_PROMPT = """You are an AI companion with specific personality traits:
- Be natural and engaging
- Keep responses concise and meaningful
- Respond based on the current relationship stage
- Show emotional awareness
- Be consistent in personality"""

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return email
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def chat_with_mistral(prompt: str) -> str:
    formatted_prompt = f"""### Instructions:
{prompt}

### Response:"""
    
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = httpx.post(
            HUGGINGFACE_API_URL,
            headers=headers,
            json={"inputs": formatted_prompt, "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "top_p": 0.9,
                "presence_penalty": 0.6,
                "frequency_penalty": 0.6
            }}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error from Hugging Face API")
            
        return response.json()[0]["generated_text"].strip()
    except Exception as e:
        logger.error(f"Mistral API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating AI response")

# API Routes
@app.get("/api/auth/login")
async def login_url():
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={os.getenv('CLIENT_ID')}&redirect_uri={os.getenv('REDIRECT_URI')}&scope=openid%20profile%20email&prompt=consent"
    }

@app.get("/oauth2callback")
async def auth_callback(code: str, redirect_uri: str = None):
    cached_response = auth_cache.get(code)
    if cached_response:
        return cached_response

    try:
        from urllib.parse import unquote
        final_redirect_uri = unquote(redirect_uri) if redirect_uri else os.getenv("REDIRECT_URI")
        
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "redirect_uri": final_redirect_uri,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=token_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                }
            )
            
            response_data = response.json()
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Authentication failed: {response_data.get('error_description', response_data.get('error', 'Unknown error'))}"
                )
            
            if 'id_token' not in response_data:
                raise HTTPException(status_code=400, detail="Invalid OAuth response")

            user_info = id_token.verify_oauth2_token(
                response_data["id_token"],
                requests.Request(),
                os.getenv("CLIENT_ID")
            )

            user_data = {
                "user_id": user_info["sub"],
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "picture": user_info.get("picture", "")
            }

            await users_collection.update_one(
                {"user_id": user_data["user_id"]},
                {"$set": user_data},
                upsert=True
            )

            access_token = create_access_token(data={"sub": user_data["email"]})
            
            response_payload = {
                "access_token": access_token,
                "user": user_data,
                "token_type": "bearer"
            }
            
            auth_cache[code] = response_payload
            return response_payload

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Chat routes
@app.post("/api/chat/new")
async def create_new_chat(chat_data: ChatCreate, current_user: str = Depends(get_current_user)):
    try:
        chat_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        new_chat = {
            "chat_id": chat_id,
            "chat_title": chat_data.chat_title,
            "messages": [],
            "created_at": timestamp
        }
        
        result = await users_collection.update_one(
            {"email": current_user},
            {"$push": {"chats": new_chat}},
            upsert=True
        )
        
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to save chat")
        
        return new_chat

    except Exception as e:
        logger.error(f"Error creating new chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/{chat_id}/message")
async def add_message(
    chat_id: str,
    chat_data: ChatCreate,
    current_user: str = Depends(get_current_user)
):
    timestamp = datetime.utcnow().isoformat()
    
    user = await users_collection.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    sentiment = await sentiment_analyzer.analyze(chat_data.message)
    memories = await memory_manager.get_relevant_memories(user["user_id"], chat_data.message)
    
    system_prompt = prompt_builder.build_prompt(
        relationship_stage=user.get("relationship_stage", "acquaintance"),
        memories=memories,
        sentiment=sentiment,
        personality_traits=user.get("personality_traits", ["caring", "empathetic"])
    )

    user_message = Message(
        role="user",
        text=chat_data.message,
        timestamp=timestamp,
        sentiment=sentiment
    )
    
    ai_response = chat_with_mistral(f"{system_prompt}\n\nUser: {chat_data.message}")
    
    bot_message = Message(
        role="bot",
        text=ai_response,
        timestamp=datetime.utcnow().isoformat()
    )
    
    await users_collection.update_one(
        {"email": current_user, "chats.chat_id": chat_id},
        {"$push": {"chats.$.messages": {"$each": [user_message.dict(), bot_message.dict()]}}}
    )
    
    return {
        "messages": [user_message.dict(), bot_message.dict()]
    }

@app.get("/api/chats")
async def get_chats(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})
    return {"chats": user.get("chats", [])}

@app.delete("/api/chat/{chat_id}")
async def delete_chat(chat_id: str, current_user: str = Depends(get_current_user)):
    result = await users_collection.update_one(
        {"email": current_user},
        {"$pull": {"chats": {"chat_id": chat_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}

@app.post("/api/analyze-sentiment")
async def analyze_sentiment(
    message: str,
    current_user: str = Depends(get_current_user)
):
    sentiment = sentiment_analyzer.analyze(message)
    return sentiment

@app.post("/api/store-memory")
async def store_memory(
    memory: str,
    current_user: str = Depends(get_current_user)
):
    try:
        # Get user info to use user_id instead of email
        user = await users_collection.find_one({"email": current_user})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        memory_manager.add_memory(user["user_id"], memory)
        return {"status": "success", "message": "Memory stored successfully"}
    except Exception as e:
        logger.error(f"Error storing memory: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store memory")

@app.get("/api/memories")
async def get_memories(query: str, current_user: str = Depends(get_current_user)):
    try:
        user = await users_collection.find_one({"email": current_user})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        memories = await memory_manager.get_relevant_memories(user["user_id"], query)
        return {"memories": memories or []}  # Ensure we always return a list
    except Exception as e:
        logger.error(f"Error retrieving memories: {str(e)}")
        return {"memories": []}  # Return empty list on error

@app.post("/api/update-relationship")
async def update_relationship(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    try:
        body = await request.json()
        stage = body.get("stage")
        if not stage or stage not in prompt_builder.RELATIONSHIP_STAGES:
            raise HTTPException(status_code=400, detail="Invalid relationship stage")
            
        result = await users_collection.update_one(
            {"email": current_user},
            {"$set": {"relationship_stage": stage}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {"status": "success", "stage": stage}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request body")

# Add health check endpoint
@app.get("/health")
async def health_check():
    try:
        # Ping MongoDB
        await client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")