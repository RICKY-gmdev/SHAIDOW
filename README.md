
<div align="center">

<!-- SCREENSHOT PLACEHOLDER: Add a banner/logo image here -->
<img width="300" height="300" alt="shaidow" src="https://github.com/user-attachments/assets/6352c507-6f27-4f04-8981-fcf9b965c0aa" />

### **SHAIDOW (v4.1)**
### *The AI That Thinks Twice Before It Answers*

**A cloud-native, multi-agent AI orchestrator with specialist routing, self-healing model fallbacks, and persistent memory**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen.svg)](https://orange-smoke-05f6fd200.7.azurestaticapps.net/)
[![.NET](https://img.shields.io/badge/.NET-10.0%20LTS-512BD4.svg)]()
[![Angular](https://img.shields.io/badge/Angular-18%2B-DD0031.svg)]()
[![LangGraph](https://img.shields.io/badge/powered%20by-LangGraph-orange.svg)]()
[![Neon DB](https://img.shields.io/badge/PostgreSQL-Neon%20Serverless-00E599.svg)]()
[![Azure](https://img.shields.io/badge/deployed%20on-Azure-0078D4.svg)]()

<br/>

**🔗 Live App: [SHAIDOW Web](https://orange-smoke-05f6fd200.7.azurestaticapps.net/)**

</div>

---

## 📌 What is SHAIDOW?

**SHAIDOW** is a cloud-native, three-tier full-stack AI platform powered by a **LangGraph multi-agent orchestrator**. Instead of sending every prompt to a single monolithic LLM, SHAIDOW's **Orchestrator Core** inspects user intent and dynamically dispatches tasks to **six specialized sub-engines**—covering software engineering, deep reasoning, factual synthesis, live web search, real-world photography, and AI artwork generation.

Built for resilience on cloud infrastructure, SHAIDOW features **cascading multi-model fallbacks** (automatically recovering from upstream API deprecations, 402 credit exhaustion, or 404 model retirements), **smart context-window trimming**, and a **Hybrid Fast-Path / Persona Synthesizer** that keeps single-tool latency low while seamlessly weaving multi-tool outputs into a unified voice.

---

## ✨ Key Features

- **🧠 6-Specialist LangGraph Orchestration** — Dynamically routes queries across Coding, Deep Reasoning, Factual Lookup, Live Web Search, Real Photo Search, and AI Image Generation—including parallel multi-tool execution.
- **🛡️ Self-Healing Model Fallbacks** — Never crashes when an upstream provider deprecates a model or exhausts credits:
  - *LLM Cascade:* `openai/gpt-oss-120b` $\rightarrow$ `openai/gpt-oss-20b` $\rightarrow$ `llama-3.1-8b-instant` $\rightarrow$ `mistral-large-latest`
  - *Image Gen Cascade:* `Stability AI (SD3.5 Flash)` $\rightarrow$ `Pollinations.ai (Flux Cloud)`
  - *Web Search Cascade:* `Tavily AI Search` $\rightarrow$ `DuckDuckGo Instant Answer + Wikipedia API`
- **⚡ Hybrid Fast-Path & Persona Synthesis** — Single-specialist calls take a zero-overhead Fast-Path straight to the user, while parallel multi-tool runs and upstream API errors are synthesized in real time by the `finalize` LLM node.
- **💻 Custom Dark Terminal Code Boxes** — Fenced code blocks render with language headers, neon syntax highlighting, and one-click copy-to-clipboard support.
- **🔐 JWT Auth & Neon PostgreSQL Persistence** — Full user authentication (JWT + BCrypt) with thread history and permanent cloud image URLs stored in **Neon Serverless PostgreSQL**.
- **🔥 Cold-Start Wakeup Optimization** — Background health-probe pings from the Angular client automatically warm up the Azure Linux containers the moment the app opens.

---

## 🏗️ Architecture Overview

### 1. System Infrastructure Diagram


```

┌────────────────────────────────────────────────────────────────────────┐
│                            Angular Frontend                            │
│        (Azure Static Web Apps · orange-smoke-05f6fd200...net)          │
│   Chat UI · Custom Code Boxes · Thread Sidebar · Gallery · Cold-Ping   │
└───────────────────────────────────┬────────────────────────────────────┘
│ HTTPS / JWT + SSE Stream
▼
┌────────────────────────────────────────────────────────────────────────┐
│                        SHAIDOW.Api (.NET 10 LTS)                       │
│                  (Azure App Service Linux · shaidow-api-n)             │
│       Auth (JWT + BCrypt) · Thread & Message Persistence · CORS        │
│             Real-Time SSE Streaming Proxy to Agent Backend             │
└──────────────────┬───────────────────────────────────┬─────────────────┘
│ ADO.NET / SSL Pooler              │ HTTP SSE (/chat)
▼                                   ▼
┌───────────────────────────────┐   ┌─────────────────────────────────┐
│   Neon Serverless PostgreSQL  │   │  SHAIDOW Agentic Core (v4.1.0)  │
│          (AWS Region)         │   │  (FastAPI + LangGraph · Python) │
│   Users · Threads · Messages  │   │  (Azure App Service · ml-n)     │
└───────────────────────────────┘   └───────────────┬─────────────────┘
│
▼
┌───────────────────────────────┐
│   LangGraph Orchestrator Core │
│  (Context Trimmer + Router)   │
└───────────────┬───────────────┘
│
┌───────────────┬───────────────┬───────────────┼───────────────┬───────────────┐
▼               ▼               ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ coding_tool │ │reasoning_tl │ │mistral_tool │ │web_search_tl│ │search_image │ │generate_img │
│  Groq LLM   │ │  Groq LLM   │ │Mistral Large│ │Tavily / DDG │ │ Pexels API  │ │Stability AI │
│  Cascade    │ │  Cascade    │ │   Latest    │ │ + Wikipedia │ │Real Photos  │ │+ Flux Cloud │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
└───────────────┴───────────────┴───────────────┼───────────────┴───────────────┘
▼
┌───────────────────────────────┐
│   Finalize / Synthesizer Node │
│  • Fast-Path (1 Text Tool)    │
│  • LLM Synthesis (Multi-Tool  │
│    / Web Search / Error Diag) │
└───────────────────────────────┘

```

### 2. LangGraph Orchestration & Fallback Flow


```

[User Message + Thread ID]
│
▼
┌────────────────────────────────────────────────────────┐
│ 1. Context Window Trimmer (_prepare_trimmed_messages)  │
│    Keeps System Prompt + Latest 12 Messages            │
└──────────────────────────┬─────────────────────────────┘
▼
┌────────────────────────────────────────────────────────┐
│ 2. Router Node (ChatGroq: openai/gpt-oss-20b)          │
└───────────┬──────────────────────────────┬─────────────┘
│ Casual / Greeting            │ Domain / Multi-Part Query
▼                              ▼
[Stream Direct Reply]        ┌────────────────────────┐
│                   │ 3. ToolNode Execution  │
│                   │ (Parallel Async Tools) │
│                   └──────────┬─────────────┘
│                              ▼
│                   ┌──────────────────────────────────────────┐
│                   │ 4. Finalize Node (Smart Routing)         │
│                   │  ├─ Image Only? ──► Confirm Visual       │
│                   │  ├─ 1 Specialist Succeeded? ──► Fast-Path│
│                   │  └─ Multi-Tool / Web / Error? ──►        │
│                   │     Synthesize via LLM (No Tools Bound)  │
│                   └──────────┬───────────────────────────────┘
▼                              ▼
[SSE Event Stream: tool_start ➔ tool_end ➔ text_chunk ➔ stream_end]

```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Angular (Standalone Components, Signals, Marked, SCSS) | Reactive chat UI, syntax-highlighted code boxes, gallery, cold-start ping |
| **API Layer** | ASP.NET Core (.NET 10 LTS), Entity Framework Core, Npgsql | JWT auth, user/thread persistence, real-time SSE streaming proxy |
| **Database** | Neon Serverless PostgreSQL (Connection Pooler) | Cloud persistence for users, threads, messages, and image URLs |
| **Agent Service** | Python 3.12, FastAPI, LangGraph 0.6, LangChain, HTTPX | Multi-agent state graph, context trimming, async tool execution |
| **LLM Cascade** | Groq (`gpt-oss-120b`, `gpt-oss-20b`, `llama-3.1-8b`) + Mistral (`mistral-large-latest`) | Orchestration routing, coding, deep reasoning, factual synthesis |
| **Search & Visuals** | Tavily / DuckDuckGo + Wikipedia, Pexels API, Stability AI + Pollinations Flux | Live web search, real photography lookup, permanent AI art generation |
| **Cloud & CI/CD** | Azure App Service (Linux ×2), Azure Static Web Apps, GitHub Actions | Independent per-service cloud hosting and automated CI/CD pipelines |

---

## 📂 Project Structure


```

SHAIDOW/
├── .github/
│   └── workflows/
│       ├── api.yml                                # CI/CD for .NET 10 API (shaidow-api-n)
│       ├── backend.yml                            # CI/CD for Python ML Core (shaidow-ml-n)
│       └── azure-static-web-apps-*.yml            # CI/CD for Angular Web App
├── App/
│   ├── SHAIDOW.Api/                               # .NET 10 LTS Web API
│   │   ├── Controllers/                           # Auth, Chat (SSE Proxy), Threads
│   │   ├── Data/                                  # EF Core AppDbContext & Entities
│   │   ├── Services/                              # JwtService & AgentBackendClient
│   │   └── Program.cs                             # DI, JWT, Npgsql & CORS configuration
│   └── shaidow-backend/                           # Python 3.12 FastAPI + LangGraph Service
│       ├── main.py                                # FastAPI lifespan, health & /chat SSE stream
│       ├── agent.py                               # LangGraph router, trimmer & finalize nodes
│       ├── tools.py                               # 6 specialist tools with cascading fallbacks
│       ├── system_prompt.txt                      # SHAIDOW core identity & persona rules
│       └── requirements.txt                       # Python dependencies
├── shaidow-web/                                   # Angular Frontend
│   └── src/app/
│       ├── chat/                                  # Chat UI, custom code-box renderer & styles
│       ├── sidebar/                               # Thread history drawer
│       ├── gallery/                               # Per-user visual gallery
│       ├── login/                                 # Authentication views
│       └── services/                              # SSE stream consumer & API services
└── .gitignore                                     # Root ignore rules for Python, .NET & Node

```

---

## 👥 Team

Built with dedication by a team of five:

| Role | Name |
|---|---|
| **Team Lead & Architect** | Md Ayman Iqbal (Ricky) |
| **Developer** | Ankit Sharma |
| **Developer** | Sk Wasef Mostafa |
| **Developer** | Vedant Jain |
| **Developer** | Atulya Raj Anand |

---

## 🔮 Roadmap

- [x] True token-by-token & synthesized streaming for tool-routed answers
- [x] Cascading multi-model & zero-cost image generation fallbacks
- [x] Live Web Search specialist (`web_search_tool`)
- [x] Dark-mode syntax-highlighted code boxes with one-click copy
- [ ] Persistent LangGraph Postgres checkpointer (`langgraph-checkpoint-postgres`)
- [ ] RAG / document upload knowledge layer
- [ ] Voice input and output support

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ by **Team SHAIDOW**

*"Strength born from struggle; light hidden within darkness."*

⭐ **Star this repo if SHAIDOW impressed you!** ⭐

</div>

```
