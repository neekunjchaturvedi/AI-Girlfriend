# AI Chat Application

A full-stack chat application with AI integration using Mistral-7B model.

## Setup

1. Clone the repository
2. Set up environment variables:
   - Copy `.env.example` to `.env` in both frontend and backend directories
   - Fill in your credentials

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Environment Variables

### Backend
- CLIENT_ID: Google OAuth client ID
- CLIENT_SECRET: Google OAuth client secret
- REDIRECT_URI: OAuth redirect URI
- MONGO_URI: MongoDB connection string
- JWT_SECRET: Secret for JWT tokens
- HF_TOKEN: Hugging Face API token

### Frontend
- REACT_APP_GOOGLE_CLIENT_ID: Google OAuth client ID
- REACT_APP_BACKEND_URL: Backend API URL
- REACT_APP_REDIRECT_URI: OAuth redirect URI

## Features
- Google OAuth authentication
- Real-time chat with AI
- Message history
- Multiple chat sessions
- Responsive design
