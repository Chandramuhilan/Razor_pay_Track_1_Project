# Agentic Commerce Platform

This is my prototype for an AI buyer and a merchant agent working together. I started with a simple question: can a buyer agent find a product, negotiate an upsell, and complete a purchase without giving the agent unlimited control over money?

The answer needs more than a chat window. The merchant has to expose products in a way an agent can read, the buyer needs a clear spending limit, and every important decision needs to be visible after the transaction.

![Initial idea and product direction](Documents/Problem.jpg)

## What I Built

There are two agents in the project:

- The **Buyer Agent** understands the request, creates a bounded AP2 mandate, searches the merchant catalog, and evaluates an upsell.
- The **Merchant Agent** exposes the catalog through MCP and UCP, communicates through A2A, checks the mandate, creates a Razorpay test order, and records the result.

The original idea also included a campaign orchestrator. I kept the first working version focused on the part that is easiest to demonstrate honestly: agent-readable discovery, upselling, and a guarded checkout.

![The constraints and expected outcome](<Documents/Constraints%20and%20Needs.jpg>)

## How I Approached It

I broke the flow into small decisions instead of letting one model call do everything:

1. Discover a product from the buyer's request.
2. Recommend an add-on only when it fits the spending limit.
3. Sign and validate an AP2 mandate.
4. Check stock before sending anything to Razorpay.
5. Use Razorpay Standard Checkout for real test-mode authorization.
6. Confirm the order only after the payment is verified and captured.
7. Write the decisions and failures to a hash-chained SQLite ledger.

![Implementation plan](Documents/Plan.jpg)

## What I Fixed During Development

The first version looked good on the happy path, but testing exposed three problems:

- The audit record was changed after its hash was calculated.
- A stock failure could happen after payment.
- A Razorpay API error could look like a successful simulated payment.

I fixed those at the control points. The ledger now hashes the final event, inventory is checked before order creation, and live Razorpay errors fail closed. The checkout path uses Razorpay's supported browser flow, verifies the returned signature, checks the payment status, and only then updates stock and confirms the order.

![System architecture sketch](Documents/Architecture.jpg)

## Architecture After the Fix

```mermaid
flowchart LR
    U[Buyer request] --> B[Buyer Agent]
    B --> A[AP2 signed mandate]
    A --> M[Merchant Agent]
    M --> C[MCP/UCP catalog]
    C --> G[Upsell and cart]
    G --> V[Mandate validation]
    V --> I[Inventory check]
    I --> O[Razorpay test order]
    O --> R[Standard Checkout]
    R --> S[Signature and payment status]
    S --> P[Capture and order confirmation]
    P --> L[Hash-chained audit ledger]
    V -. reject .-> F[Audited failure]
    I -. unavailable .-> F
    R -. declined or cancelled .-> F
```

The important rule is simple: a failed check stops the flow. The system does not invent a payment, and it does not report an order as complete just because an order ID exists.

The test suite currently passes **28 tests**. With Razorpay test keys configured, the server creates real test orders and opens Standard Checkout; the final order is confirmed only when Razorpay reports a captured payment.

---

## ⚙️ Setup Guide

### Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Get API Keys (Free)

#### Gemini API Key (Required for real AI)

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key (starts with `AIzaSy...`)

#### Razorpay Test Keys (Required for real payments)

1. Go to **https://dashboard.razorpay.com**
2. Sign up free (no real money involved in test mode)
3. Go to **Settings → API Keys**
4. Click **"Generate Test Key"**
5. Copy **Key ID** (starts with `rzp_test_...`) and **Key Secret**

### Step 3 — Configure `.env`

Open `Razor_pay/.env` and fill in your keys:

```env
# Google AI — get from aistudio.google.com/app/apikey
GEMINI_API_KEY=AIzaSy_your_key_here

# Razorpay Test Mode — get from dashboard.razorpay.com → Settings → API Keys
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_here

# Agent URLs (leave as-is for local development)
MERCHANT_AGENT_URL=http://localhost:8000
BUYER_AGENT_URL=http://localhost:8001

# AP2 Mandate crypto secret (change this in production)
AP2_MANDATE_SECRET=AP2_MANDATE_SECRET_AUTHORIZATION_KEY_2026
```

> **Without keys**: Everything still runs in demo/simulated mode. The UI shows a warning banner explaining which keys are missing. All protocol structures (A2A, MCP, AP2) are real — only Razorpay API calls and Gemini AI reasoning are simulated.

---

## 🚀 Quick Start

### Terminal 1 — Merchant Agent (port 8000)

```bash
cd Razor_pay
python main.py
```

Open: http://localhost:8000 | Swagger: http://localhost:8000/docs

### Terminal 2 — Buyer Agent (port 8001)

```bash
cd Razor_pay
python buyer_agent/main.py
```

Open: **http://localhost:8001** ← The buyer UI with split-screen interface

### Terminal 3 — Standalone MCP Server (optional, for external LLM clients)

```bash
cd Razor_pay
python mcp_server.py
```

### Run Tests

```bash
python -m pytest tests/ -v
# Expected: 28/28 passed
```

---

## 🔌 Protocol Endpoints

### Merchant Agent (port 8000)

| Endpoint                    | Method | Protocol           | Description                                               |
| :-------------------------- | :----- | :----------------- | :-------------------------------------------------------- |
| `/.well-known/agent.json` | GET    | **A2A**      | Real`a2a.types.AgentCard` protobuf                      |
| `/api/a2a/message`        | POST   | **A2A**      | Real`SendMessageRequest → Task → SendMessageResponse` |
| `/mcp`                    | POST   | **MCP**      | JSON-RPC 2.0:`tools/list`, `tools/call`               |
| `/api/mcp/tools`          | GET    | **MCP**      | `mcp.types.Tool[]` manifest                             |
| `/api/catalog`            | GET    | **UCP**      | Schema.org JSON-LD agent-readable catalog                 |
| `/api/commerce/stream`    | POST   | **REST+SSE** | Full pipeline with live streaming                         |
| `/api/commerce/run-flow`  | POST   | **REST**     | Synchronous pipeline                                      |
| `/api/audit/ledger`       | GET    | **REST**     | SHA-256 hash-chained audit trail                          |

### Buyer Agent (port 8001)

| Endpoint                      | Method | Description                       |
| :---------------------------- | :----- | :-------------------------------- |
| `/`                         | GET    | Split-screen buyer UI             |
| `/api/buyer/health`         | GET    | Key status + configuration check  |
| `/api/buyer/merchant/card`  | GET    | Fetches merchant's A2A AgentCard  |
| `/api/buyer/merchant/tools` | GET    | Fetches merchant's MCP tools      |
| `/api/buyer/run`            | GET    | SSE pipeline stream (EventSource) |
| `/api/buyer/a2a/send`       | POST   | Direct A2A message to merchant    |
| `/api/buyer/mcp/call`       | POST   | Direct MCP tool call              |

---

## 📚 Real Protocol Libraries Used

| Protocol     | Library          | Version    | Types Used                                                                                                     |
| :----------- | :--------------- | :--------- | :------------------------------------------------------------------------------------------------------------- |
| Google A2A   | `a2a-sdk`      | `1.1.2`  | `AgentCard`, `Message`, `Part`, `Task`, `TaskStatus`, `TaskState`, `SendMessageRequest/Response` |
| MCP          | `mcp`          | `1.26.0` | `Tool`, `ToolAnnotations`, `TextContent`, `CallToolResult`, `ListToolsResult`                        |
| Razorpay     | `razorpay`     | `2.0.1`  | Test-mode order creation, payment execution, HMAC-SHA256 verification; live API errors fail closed             |
| Google AI    | `google-genai` | `2.19.0` | `Gemini 2.5 Flash`, `text-embedding-004`                                                                   |
| AP2 Mandates | stdlib`hmac`   | —         | HMAC-SHA256 signed bounded spending mandates                                                                   |

---

## 🏆 Track 01 Bar Compliance

| Requirement                              | Implementation                                                                                                                                                |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Grow merchant revenue**          | Dynamic upsell engine picks highest-margin add-on within AP2 mandate headroom                                                                                 |
| **Sellable to AI buyers**          | Real`AgentCard` + real MCP `Tool[]` + Schema.org UCP catalog                                                                                              |
| **Every money action explainable** | SHA-256 hash-chained SQLite audit ledger at`GET /api/audit/ledger`                                                                                          |
| **Bounded and gated**              | HMAC-SHA256 AP2 Mandate required for every payment — budget/merchant/expiry enforced                                                                         |
| **Audit trail shown**              | Full hash-chained event timeline with`integrity_verified: true`                                                                                             |
| **Failures handled gracefully**    | Tampered/expired/category-invalid mandate · Budget breach · Merchant offline · Out-of-stock checkout · Razorpay gateway failure · Missing keys/demo mode |
| **Razorpay test-mode APIs**        | `razorpay==2.0.1` SDK, real `client.order.create()`, HMAC verification                                                                                    |
| **Agent-to-agent commerce**        | Real A2A HTTP calls from buyer → merchant using`a2a-sdk` protobuf types                                                                                    |

---

## 📁 Project Structure

```
Razor_pay/
├── .env                          ← Your API keys (git-ignored)
├── .env.example                  ← Template — copy to .env
├── requirements.txt              ← Pinned production dependencies
├── main.py                       ← Merchant Agent (port 8000)
├── mcp_server.py                 ← Standalone FastMCP stdio server
├── buyer_agent/                  ← Buyer Agent (port 8001)
│   ├── main.py                   ← FastAPI entry point
│   ├── models.py                 ← BuyerIntent, PurchaseRequest
│   ├── static/index.html         ← Split-screen buyer UI
│   └── agent/
│       ├── buyer_core.py         ← Gemini-powered pipeline orchestrator
│       ├── a2a_client.py         ← Real A2A HTTP client (a2a-sdk)
│       ├── mcp_client.py         ← Real MCP HTTP client (mcp.types)
│       └── ap2_mandate.py        ← Standalone HMAC-SHA256 mandate creation
├── app/
│   ├── config.py                 ← Pydantic-settings (loads .env)
│   ├── models.py                 ← Core Pydantic data models
│   ├── protocols/
│   │   ├── a2a.py                ← Real a2a-sdk AgentCard + message handler
│   │   ├── mcp_ucp.py            ← Real mcp.types Tool + CallToolResult
│   │   └── ap2_mandate.py        ← HMAC-SHA256 mandate engine
│   ├── merchant/
│   │   ├── catalog.py            ← TF-IDF + Gemini embedding search
│   │   └── upsell_engine.py      ← Revenue maximizer
│   └── services/
│       ├── embedding_service.py  ← Gemini text-embedding-004 + JSON cache
│       ├── razorpay_service.py   ← Real Razorpay SDK integration
│       ├── audit_ledger.py       ← SHA-256 hash-chain ledger
│       └── database_ledger.py    ← SQLite persistence
└── tests/                        ← 22 automated tests
```
