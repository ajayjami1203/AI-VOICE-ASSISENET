Title: AI Voice Assistant - FastAPI Project (Internship)
🚀 This project is a voice-enabled AI assistant developed using FastAPI part of my 6-month internship. It combines speech-to-text interaction with AI-generated responses, allowing users to chat with the assistant, upload text files for analysis, and save chat history securely.

📌 Features
✅ User Authentication (Register/Login)
🗨️ Voice & Text Input AI interactions using Groq API
📁 File Upload Support (.txt files processed by AI)
📜 Chat History saved in json files (retrievable by user)
🔐 Environment Variables stored securely using .env
🌐 Cross-Origin Resource Sharing enabled for frontend use

🧰 Technologies Used
Backend: Python, FastAPI
Security: passlib for password hashing, .env for secrets
AI: Groq LLaMA 3 (via API)
Storage: File uploads handled via FastAPI and stored locally
Frontend (not in this repo): HTML interface with upload & voice input support

🏁 Endpoints
POST /register – User registration
POST /login – User login
POST /ai-response/ – Send a message and get AI reply
POST /upload/ – Upload a text file and receive AI response
GET /history.json= – Retrieve user's chat history

📂 Project Structure
main.py – All FastAPI routes and backend logic
.env – Stores GROQ_API_KEY securely
users.json – Simulated user data (for local/demo use)
history.json – Sample chat history (for testing/demo)
AI PPT.pptx – Presentation outlining project objectives, limitations, and future work
.gitignore – Keeps .env and Python cache files out of Git tracking

📚 Internship Details
This project was built during my 6-month internship, focusing on:
API development using FastAPI
Integration of AI APIs (Groq)
Handling user data and authentication securely
Working with async MongoDB and file handling
Presenting and documenting the project (see AI PPT.pptx)

🔮 Future Improvements
Real-time interaction with WebSockets
Support for PDFs and DOC files
Multi-language support and advanced TTS/STT integration
JWT-based session management
Deployment using Docker or cloud (e.g., Render/Heroku)
