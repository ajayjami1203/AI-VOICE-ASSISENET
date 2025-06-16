from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import bcrypt
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path
import json
import os

load_dotenv()

# FastAPI app
app = FastAPI()

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

# File paths
USERS_FILE = "users.json"
HISTORY_FILE = "history.json"

# Helper functions to read and write JSON files
def read_json_file(file_path):
    if not Path(file_path).exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)

def write_json_file(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, default=str, indent=4)

# Routes
@app.get("/")
async def home():
    return {"message": "Welcome to AI Voice Assistant API with JSON file storage"}

@app.post("/register")
async def register(data: RegisterRequest):
    users = read_json_file(USERS_FILE)
    existing_user = next((user for user in users if user["email"] == data.email), None)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = bcrypt.hash(data.password)
    new_user = {
        "username": data.username,
        "email": data.email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    }
    users.append(new_user)
    write_json_file(USERS_FILE, users)
    return {"message": "User  registered successfully"}

@app.post("/login")
async def login(data: LoginRequest):
    users = read_json_file(USERS_FILE)
    user = next((user for user in users if user["email"] == data.email), None)
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
        history = read_json_file(HISTORY_FILE)
        history.append(history_entry.dict())
        write_json_file(HISTORY_FILE, history)

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
        history = read_json_file(HISTORY_FILE)
        history.append(history_entry.dict())
        write_json_file(HISTORY_FILE, history)

        return {"response": reply, "file_location": str(file_location)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_user_history(user_id: str):
    history = read_json_file(HISTORY_FILE)
    user_history = [
        {
            "timestamp": h["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "source": h["source"],
            "user_input": h["user_input"],
            "bot_response": h["bot_response"]
        }
        for h in history if h["user_id"] == user_id
    ]
    return user_history
