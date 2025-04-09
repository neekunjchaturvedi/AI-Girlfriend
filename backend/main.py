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
from typing import List, Optional
from pydantic import BaseModel
import uuid

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
try:
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client.userdb
    users_collection = db.users
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")
    raise

# Cache setup
auth_cache = TTLCache(maxsize=100, ttl=300)

# Hugging Face setup
HF_TOKEN = os.getenv("HF_TOKEN")
HUGGINGFACE_REPO_ID = "mistralai/Mistral-7B-Instruct-v0.3"
client = InferenceClient(model=HUGGINGFACE_REPO_ID, token=HF_TOKEN)

# Pydantic models
class Message(BaseModel):
    role: str
    text: str
    timestamp: str

class Chat(BaseModel):
    chat_id: str
    chat_title: str  # New field
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

# System prompt
SYSTEM_PROMPT = """You are an AI assistant.
- Only respond to the latest user query.
- Do NOT provide extra details unless asked explicitly.
- Keep responses short and relevant.
- If uncertain, say "I don't know."
"""

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
    # Handle initial message differently
    if "Hi! I'm the Mistral AI assistant" in prompt:
        return "Hello! I'm ready to help you. Feel free to ask any questions or start a conversation."
        
    formatted_prompt = f"""### System Prompt:
{SYSTEM_PROMPT}

### User Input:
{prompt}

### AI Response:
"""
    try:
        response = client.text_generation(
            formatted_prompt,
            max_new_tokens=150,  # Increased token limit
            temperature=0.7,     # Slightly more creative
            stop_sequences=["### User Input:", "### System Prompt:"]
        )
        return response.strip()
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
    # Check cache
    cached_response = auth_cache.get(code)
    if cached_response:
        return cached_response

    try:
        from urllib.parse import unquote
        final_redirect_uri = unquote(redirect_uri) if redirect_uri else os.getenv("REDIRECT_URI")
        
        # Exchange code for token
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

            # Verify token
            user_info = id_token.verify_oauth2_token(
                response_data["id_token"],
                requests.Request(),
                os.getenv("CLIENT_ID")
            )

            user_data = {
                "user_id": user_info["sub"],  # Add Google OAuth sub as user_id
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "picture": user_info.get("picture", "")
            }

            # Update user in DB
            await users_collection.update_one(
                {"user_id": user_data["user_id"]},  # Change to user_id
                {"$set": user_data},
                upsert=True
            )

            # Create JWT
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
        # Generate chat ID and timestamp
        chat_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Create new chat object without initial messages
        new_chat = {
            "chat_id": chat_id,
            "chat_title": chat_data.chat_title,
            "messages": [],  # Start with empty messages array
            "created_at": timestamp
        }
        
        # Save to database
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
async def add_message(chat_id: str, chat_data: ChatCreate, current_user: str = Depends(get_current_user)):
    timestamp = datetime.utcnow().isoformat()
    
    user_message = Message(
        role="user",
        text=chat_data.message,
        timestamp=timestamp
    )
    
    ai_response = chat_with_mistral(chat_data.message)
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