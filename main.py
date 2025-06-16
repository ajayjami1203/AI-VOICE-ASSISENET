from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import bcrypt
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path
import motor.motor_asyncio
import os

load_dotenv()

# FastAPI app
app = FastAPI()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client["ai_voice_assistant"]
users_collection = db["users"]
history_collection = db["history"]

# Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in environment variables")
groq_client = Groq(api_key=GROQ_API_KEY)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TextInput(BaseModel):
    text: str
    user_id: str

class HistoryModel(BaseModel):
    user_id: str
    user_input: str
    bot_response: str
    source: str = "chat"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Routes
@app.get("/")
async def home():
    return {"message": "Welcome to AI Voice Assistant API with MongoDB"}

@app.post("/register")
async def register(data: RegisterRequest):
    existing_user = await users_collection.find_one({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = bcrypt.hash(data.password)
    await users_collection.insert_one({
        "username": data.username,
        "email": data.email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    })
    return {"message": "User registered successfully"}

@app.post("/login")
async def login(data: LoginRequest):
    user = await users_collection.find_one({"email": data.email})
    if not user or not bcrypt.verify(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}

@app.post("/ai-response/")
async def ai_response(input_data: TextInput):
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": input_data.text}]
        )
        reply = response.choices[0].message.content

        history_entry = HistoryModel(
            user_id=input_data.user_id,
            user_input=input_data.text,
            bot_response=reply,
            source="chat"
        )
        await history_collection.insert_one(history_entry.dict())
        return {"response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/")
async def upload_file(user_id: str, file: UploadFile = File(...)):
    try:
        upload_dir = Path("uploaded_files")
        upload_dir.mkdir(exist_ok=True)
        file_location = upload_dir / file.filename
        contents = await file.read()
        with open(file_location, "wb") as f:
            f.write(contents)

        input_text = contents.decode("utf-8", errors="ignore")
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": input_text}]
        )
        reply = response.choices[0].message.content

        history_entry = HistoryModel(
            user_id=user_id,
            user_input=input_text,
            bot_response=reply,
            source="upload"
        )
        await history_collection.insert_one(history_entry.dict())

        return {"response": reply, "file_location": str(file_location)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_user_history(user_id: str):
    history_cursor = history_collection.find({"user_id": user_id}).sort("timestamp", -1)
    history = await history_cursor.to_list(length=100)
    return [
        {
            "timestamp": h["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "source": h["source"],
            "user_input": h["user_input"],
            "bot_response": h["bot_response"]
        }
        for h in history
    ]
