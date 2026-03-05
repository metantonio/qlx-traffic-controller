# AI Kernel - AgentOS Dashboard and Control Tower

This repository contains the AI Command Kernel (Backend) and the Observability Dashboard (Frontend) for managing isolated, autonomous AI processes.

## Prerequisites

- **Node.js** (for the Next.js frontend)
- **Python 3.10+** (for the FastAPI backend)
- **Ollama** installed and running locally. (Make sure you have pulled models like `qwen2.5-coder:7b` or `llama3`)

---

## 1. Backend Setup (AI Command Kernel)

The backend is a robust Python architecture that manages agents as OS-like processes with capability-based security, isolated sandboxes, and an async task scheduler.

### Creating a Virtual Environment

It is highly recommended to run the backend inside a Python virtual environment to manage dependencies securely.

#### **On Windows:**
Open your terminal and run:
```bash
cd ../backend  # Assuming you are in the frontend folder, navigate to backend
python -m venv venv
venv\Scripts\activate
```

#### **On macOS / Linux:**
Open your terminal and run:
```bash
cd ../backend
python3 -m venv venv
source venv/bin/activate
```

### Installing Dependencies
With the virtual environment **activated**, install the required Python packages:
```bash
pip install -r requirements.txt
```

### Environment Configuration
Copy the template environment file to create your local config:
```bash
cp .env.example .env
```
*(Optionally edit the `.env` file to customize your LLM model or Telegram Token).*

### Starting the Server
Start the FastAPI server via Uvicorn:
```bash
uvicorn main:app --reload
```
The backend API and WebSocket server will now be listening on `http://127.0.0.1:8000`.

---

## 2. Frontend Setup (Observability Dashboard)

The frontend is a Next.js application styled with Tailwind CSS, offering live WebSocket-based `htop`-style process monitoring.

### Installation

Open a **new terminal window** (leave the backend running) and navigate to the frontend directory:

```bash
cd frontend
npm install
```

### Environment Configuration
Copy the template matching the backend's WebSocket location:
```bash
cp .env.example .env
```

### Starting the Application
Start the Next.js development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to view the AI Control Tower dashboard.

---

## 3. Usage & Examples

Once both servers are running:
1. The frontend Dashboard connects automatically to `ws://127.0.0.1:8000/ws`.
2. You can use the backend mockup to trigger a test simulation of processes and tool usage capabilities:
   ```bash
   # From the backend directory with venv activated:
   python example_workflow.py
   ```
3. Watch the Next.js Dashboard live-update as agent `PID`s spawn, shift priorities, and handle tool quotas securely!

---

## 4. Security Configuration (Localhost Only)

By default, the system is designed to act as a **local** kernel boundary that connects to your local machine exclusively. For safety, the AI agents are restricted to your local loopback architecture and are NOT exposed to the internet:
- **FastAPI / Uvicorn Server:** The backend binds strictly to `127.0.0.1`.
- **CORS Policies:** The backend API's Cross-Origin configurations (`CORS_ORIGINS` in `.env`) strictly reject connections from external domains, only permitting traffic from `http://localhost:3000` and `http://127.0.0.1:3000`.
- **Dashboard Next.js Server:** Starts locally rejecting remote connections unless explicitly modified.

*If you intend to expose the Control Tower externally (e.g., to integrate the Telegram webhook securely rather than polling), you must explicitly run the services on `0.0.0.0` or deploy behind a secure reverse proxy/tunnel while auditing your Agent Capabilities heavily.*
