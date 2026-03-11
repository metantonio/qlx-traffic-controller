<div align="center">

# 🌌 QLX Traffic Controller
### The Premier Neural Command Center for Autonomous Multi-Agent Orchestration

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](./LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js)](https://nextjs.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-blue.svg)](https://ollama.com/)

---

**QLX Traffic Controller** is a high-performance, OS-inspired kernel and dashboard designed to manage, monitor, and scale autonomous AI agents. Built for the era of local-first multimodal intelligence, but cloud LLM providers can be used as well.

[**Explore Features**](#-key-pillars) • [**Quick Start**](#-deployment-sequence) • [**Architecture**](#-neural-architecture)

</div>

---

## ✨ The Premium Neural interface
Experience an interface that feels alive. QLX features a high-fidelity **Dark Mode** dashboard with:
- 🚀 **Real-time Process Monitoring**: `htop`-inspired live telemetry of agent execution.
- ⚡ **Glassmorphism & Scanlines**: A sleek, futuristic aesthetic with smooth micro-animations.

---

## 🏗️ Key Pillars

### 🤖 Recursive Batch Terminal
Process entire directories of data with a single click. Launch **Neural Pipelines** that recursively iterate through files in isolated, capability-secured agent environments.
- **Repeat & Retry**: Intelligent state persistence allows you to re-run complex batches with one click.
- **Isolation Mode**: Prevent context drift by spawning fresh agent instances for every node.

### 👁️ Multimodal OCR Pipeline
Transform pixel-perfect images into production-ready code.
- **Image-to-TSX**: Automatically transcribe screenshots into React/TypeScript components.
- **Configurable Vision**: Hot-swap multimodal LLMs (Ollama/Google/Anthropic) from the settings UI.
- **Auto-Scrubbing**: Automated logic to remove lines numbers and noise from OCR results.

### 🔌 MCP & Skills Ecosystem
Infinite extensibility through the **Model Context Protocol (MCP)**.
- **Clawhub Integration**: Browse and install agent skills directly from the integrated **Skills Store**.
- **Unified Bridges**: Connect agents to Wikipedia, Playwright, Filesystem, and more with zero boilerplate.

---

## 🛠️ Tech Stack

- **Kernel**: FastAPI (Python 3.10+) with Asyncio orchestration.
- **Observability**: Next.js 14, Tailwind CSS, Lucide Icons.
- **Intelligence**: Native Ollama Support, LangChain Core, Multimodal Vision Models.
- **Real-time**: High-throughput WebSocket Memory Bus.

---

## 🚀 Deployment Sequence

### 1. The Kernel (Backend)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# From ROOT directory:
$env:PYTHONPATH=(Get-Location).Path # Windows
python backend\main.py
```

### 2. The Dashboard (Frontend)
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```
Navigate to `http://localhost:3000` to assume command.

---

## 🛡️ Capability-Based Security
Safety is baked into the kernel. Agents are restricted to a **local loopback architecture** by default:
- **Locked Scopes**: Agents only see the tools and directories you explicitly permit.
- **Local-First**: Your data stays on your machine via local LLM execution (Ollama).
- **Quota Management**: Real-time monitoring of tool usage and token budgets.

---

<div align="center">
  <sub>Built with ❤️ at Qualex Consulting Services, INC.</sub>
</div>