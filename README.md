<div align="center">

<!-- SCREENSHOT PLACEHOLDER: Add a banner/logo image here -->
<!-- Suggested: The SHAIDOW mascot on the dark cosmic gradient background -->
<!-- ![SHAIDOW Banner](assets/banner.png) -->
<img width="300" height="300" alt="shaidow" src="https://github.com/user-attachments/assets/6352c507-6f27-4f04-8981-fcf9b965c0aa" />

### **SHAIDOW**
### *The AI That Thinks Twice Before It Answers*

**A full-stack AI assistant with intelligent specialist routing, persistent memory, and cloud-native deployment**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-web.shaidow.me-brightgreen.svg)](https://web.shaidow.me)
[![.NET](https://img.shields.io/badge/.NET-9-512BD4.svg)]()
[![Angular](https://img.shields.io/badge/Angular-18%2B-DD0031.svg)]()
[![LangGraph](https://img.shields.io/badge/powered%20by-LangGraph-orange.svg)]()
[![Azure](https://img.shields.io/badge/deployed%20on-Azure-0078D4.svg)]()

<br/>

**🔗 Live: [web.shaidow.me](https://web.shaidow.me)**

<!-- SCREENSHOT PLACEHOLDER: Add a demo GIF or screenshot of the chat interface -->
<!-- ![SHAIDOW Demo](assets/demo.gif) -->

</div>

---

## 📌 What is SHAIDOW?

**SHAIDOW** is a full-stack AI assistant that doesn't just forward every message to one generic model. A lightweight router model looks at each query first and delegates it to whichever specialist is actually best suited to answer it — a fast factual model for quick lookups, a reasoning-tuned model for deep questions, a coding-tuned model for programming help, or an image search/generation tool when that's what's actually being asked for.

Unlike the single-service prototype this started as, SHAIDOW is now a genuine three-tier cloud application: a persistent Angular frontend, a .NET/C# API layer handling authentication and conversation history, and a Python agent service doing the actual LLM orchestration — all independently deployed on Azure behind a custom domain.

---

## ✨ Key Features

- **🔁 Specialist Routing** — A Groq-hosted router model classifies each query and delegates to the right specialist (information, reasoning, coding, image search, or image generation) rather than treating every prompt the same way
- **🔐 Real Authentication** — JWT-based auth with BCrypt password hashing; every conversation is scoped to the signed-in user
- **💾 Persistent Conversations** — Full thread history stored in PostgreSQL; pick up any past conversation with its complete context intact, not just a fresh session each time
- **⚡ Live Streaming Responses** — Direct answers stream token-by-token in real time; multi-tool answers append progressively as each specialist finishes, with a live status indicator while others are still working
- **🖼️ Multi-Model Image Pipeline** — Real photo search via Pexels, original image generation via Stable Diffusion, each user's gallery scoped privately to their own account
- **🛡️ Graceful Degradation** — If a specialist's tool-call generation fails or returns malformed output, SHAIDOW automatically falls back to a direct answer instead of surfacing a broken response
- **📱 Responsive UI** — Collapsible sidebar becomes a slide-in drawer on mobile; chat, gallery, and image viewer all adapt to small screens
- **☁️ Fully Cloud-Deployed** — Three independently deployed Azure services behind a custom domain, with CI/CD via GitHub Actions on every push

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                      Angular Frontend                    │
│         (Azure Static Web Apps · web.shaidow.me)         │
│   Chat UI · Thread Sidebar · Gallery · Auth Screens      │
└───────────────────────────┬──────────────────────────────┘
                            │ HTTPS / JWT
                            ▼
┌──────────────────────────────────────────────────────────┐
│                   SHAIDOW.Api (.NET 9)                   │
│                    (Azure App Service)                   │
│   Auth (JWT + BCrypt) · Thread/Message Persistence       │
│   Streaming Proxy to Agent Service                       │
└──────────────┬─────────────────────────────┬─────────────┘
               │                             │
               ▼                             ▼
   ┌───────────────────────┐     ┌─────────────────────────┐
   │  Azure PostgreSQL     │     │   Python Agent Service   │
   │  Flexible Server      │     │   (FastAPI + LangGraph)  │
   │  Users · Threads ·    │     │   (Azure App Service)    │
   │  Messages             │     └────────────┬─────────────┘
   └───────────────────────┘                  │
                                    Router decides, then:
                     ┌──────────────┬──────────┼──────────────┬─────────────────┐
                     ▼              ▼          ▼              ▼                 ▼
               ┌──────────┐  ┌──────────┐ ┌──────────┐  ┌──────────────┐ ┌──────────────┐
               │ Mistral  │  │  Groq    │ │  Groq    │  │   Pexels     │ │ Stability AI │
               │(Info)    │  │(Reason)  │ │(Coding)  │  │(Image Search)│ │(Image Gen)   │
               └──────────┘  └──────────┘ └──────────┘  └──────────────┘ └──────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Angular (standalone components, signals) | Chat UI, auth, thread sidebar, gallery |
| **API Layer** | ASP.NET Core (.NET 9), EF Core | Auth, JWT issuance, thread/message persistence, SSE proxy |
| **Database** | Azure Database for PostgreSQL (Flexible Server) | Users, threads, messages |
| **Agent Service** | Python, FastAPI, LangGraph, LangChain | Query routing, specialist orchestration, tool execution |
| **LLM Providers** | Groq (router, reasoning, coding), Mistral (information) | Specialist model inference |
| **Image Providers** | Pexels API, Stability AI | Real photo search, AI image generation |
| **Hosting** | Azure App Service ×2, Azure Static Web Apps | Independent deployment of each tier |
| **CI/CD** | GitHub Actions | Auto-deploy on push per service |

---

## 🧩 How Routing Works

Unlike a single always-on agent loop, SHAIDOW's router makes **one decision per turn**:

1. **Receive the message** along with conversation history
2. **Router model** (Groq) either answers directly for simple conversation, or selects exactly one specialist — sometimes more than one in parallel when the query calls for it (e.g. "tell me about X" → information summary *and* a real photo)
3. **Selected specialist(s) execute** — each one's result streams back to the user the moment *it* finishes, not after every parallel call completes
4. **No re-interpretation loop** — the specialist's result *is* the final answer; the router doesn't second-guess or rewrite it, which keeps latency low and avoids the compounding errors that come from chaining model calls unnecessarily
5. **Automatic fallback** — if the router's tool-call generation fails or comes back malformed, the same turn retries as a plain direct answer instead of surfacing an error to the user

---

## 📂 Project Structure

```
SHAIDOW/
├── .github/
│   └── workflows/          # Per-service GitHub Actions CI/CD pipelines
├── shaidow-web/             # Angular frontend
│   └── src/app/
│       ├── chat/            # Main chat interface
│       ├── sidebar/         # Thread history, collapsible/mobile drawer
│       ├── gallery/         # Per-user generated image gallery
│       ├── login/           # Auth screens
│       └── services/        # Auth + chat streaming services
├── SHAIDOW.Api/              # .NET 9 Web API
│   ├── Controllers/          # Auth, Chat (SSE proxy), Threads
│   ├── Data/                 # EF Core DbContext + entities
│   └── Services/             # JWT service, agent backend client
└── shaidow-backend/          # Python agent service
    ├── main.py               # FastAPI app, SSE streaming endpoint
    ├── agent.py               # LangGraph router + specialist graph
    └── tools.py               # Specialist tool implementations
```

---

## 👥 Team

Built with dedication by a team of five:

| Role | Name |
|---|---|
| **Team Lead** | Md Ayman Iqbal (Ricky) |
| **Developer** | Ankit Sharma |
| **Developer** | Sk Wasef Mostafa |
| **Developer** | Vedant Jain |
| **Developer** | Atulya Raj Anand |

---

## 🔮 Roadmap

- [ ] True token-by-token streaming for tool-routed answers (currently token-streamed only for direct/no-tool responses)
- [ ] Persistent LangGraph checkpointing so agent memory survives service restarts, not just conversation history
- [ ] RAG / document knowledge layer
- [ ] Voice input and output support
- [ ] Confidence scoring and telemetry on routing decisions
- [ ] Native mobile app

---


## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ by **Team SHAIDOW**

*"The right specialist for the right question."*

⭐ **Star this repo if SHAIDOW impressed you!** ⭐

</div>
