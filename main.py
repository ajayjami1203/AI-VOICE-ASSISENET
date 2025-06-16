from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.hash import bcrypt
from dotenv import load_dotenv
from datetime import datetime
from gtts import gTTS
from pathlib import Path
from starlette.responses import StreamingResponse
import os, json, io
from groq import Groq
from fastapi import UploadFile, File

# === CONFIG === #
app = FastAPI()
USERS_FILE = "users.json"
HISTORY_FILE = "history.json"

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fake user DB
fake_users_db = {
    "admin": "1234",
    "user": "password"
}

# Request body model
class LoginRequest(BaseModel):
    username: str
    password: str

class TextInput(BaseModel):
    text: str

# === HELPERS === #
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def save_to_history(user_input, ai_response):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_input,
        "bot": ai_response
    }
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            history = json.load(file)
    history.append(entry)
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)

#History #
@app.get("/history")
def get_history():
    history_file = Path("history.json")
    if history_file.exists():
        with open(history_file, "r") as f:
            return json.load(f)
    return []

# === ROUTES === #

@app.get("/")
def home():
    return {"message": "Welcome to the AI Voice Assistant API"}

@app.post("/register")
def register(data: LoginRequest):
    users = load_users()
    
    if data.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash the password before saving it
    hashed_password = bcrypt.hash(data.password)
    
    # Save user to the JSON file
    users[data.username] = {"password": hashed_password}
    save_users(users)
    return {"message": "Registered successfully"}

@app.post("/login")
def login(data: LoginRequest):
    users = load_users()
    
    if data.username not in users or not bcrypt.verify(data.password, users[data.username]["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful"}

# AI response endpoint
@app.post("/ai-response/")
async def ai_response(input_text: TextInput):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": input_text.text}]
        )
        if hasattr(response, 'choices') and response.choices:
            reply = response.choices[0].message.content
        else:
            raise HTTPException(status_code=500, detail="Unexpected response format")

        save_to_history(input_text.text, reply)
        return {"response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# File upload endpoint
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save the uploaded file with its original filename
        file_location = f"uploaded_files/{file.filename}"
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Here you could process the file content as text, depending on its type
        # If you want to extract text or process it, you can implement logic for that.
        contents = await file.read()
        input_text = contents.decode("utf-8", errors="ignore")  # Attempt to decode as text

        # AI response
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": input_text}]
        )

        if hasattr(response, 'choices') and response.choices:
            reply = response.choices[0].message.content
        else:
            raise HTTPException(status_code=500, detail="Unexpected response format")

        save_to_history(input_text, reply)
        return {"response": reply, "file_location": file_location}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
