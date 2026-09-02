# 🚀 Revenue-Maximizing Merchant Agent & Safe Autonomous Commerce Protocol

> **Hackathon Track 01 — AI Growth & Agentic Commerce**: A focused Merchant Agent demonstrating revenue growth through dynamic value-add upsells, safe autonomous transactions using **AP2 Bounded Mandates**, real **Google A2A Protocol** (`a2a-sdk 1.1.2`), real **MCP** (`mcp 1.26.0`), **Razorpay Test Payment APIs**, and a **First-Class Immutable Cryptographic Audit Trail Ledger**.

---

## 🏛️ Real Protocol Libraries (No Custom Wrappers)

| Layer | Library | Version | What's Used |
|:---|:---|:---|:---|
| **Google A2A** | `a2a-sdk` | `1.1.2` | `AgentCard`, `AgentSkill`, `AgentCapabilities`, `AgentInterface`, `AgentProvider`, `Message`, `Part`, `Role`, `Task`, `TaskStatus`, `TaskState`, `SendMessageRequest`, `SendMessageResponse` — all real protobuf types |
| **MCP** | `mcp` | `1.26.0` | `Tool`, `ToolAnnotations`, `TextContent`, `CallToolResult`, `ListToolsResult` — real Pydantic types serialized via `.model_dump()` |
| **Razorpay** | `razorpay` | `2.0.1` | `razorpay.Client`, `.order.create()`, HMAC-SHA256 signature verification |
| **AP2 Mandates** | `hmac`, `hashlib` | stdlib | HMAC-SHA256 signed bounded spending mandates |
| **AI Buyer** | `google-genai` | `2.19.0` | `genai.Client`, `models.generate_content()` — Gemini 2.5 Flash for upsell reasoning |
| **FastAPI + MCP Server** | `fastapi` + `mcp.server.fastmcp` | Latest | HTTP server + standalone MCP stdio/SSE server |

---

## 🌟 Track 01 Hackathon Protocol Mapping

| Track 01 Requirement | Implementation | Protocol / Library |
|:---|:---|:---|
| **AI buyer ↔ merchant** | **Real A2A Protocol** | `a2a.types.SendMessageRequest/Response`, `AgentCard` at `/.well-known/agent.json` |
| **Agent-readable merchant** | **Real MCP tools** | `mcp.types.Tool`, `CallToolResult`, `ListToolsResult` at `/mcp` |
| **Checkout** | **UCP/ACP Transaction State Machine** | `CommerceStateMachine` with 10-state lifecycle |
| **Payment** | **Razorpay Test APIs** | `razorpay.Client.order.create()`, HMAC-SHA256 verification |
| **Agent authorization** | **AP2 Bounded Mandates** | HMAC-SHA256 signed mandates with budget + merchant + expiry bounds |
| **Explainability** | **Cryptographic Audit Ledger** | SHA-256 hash-chained, SQLite-persisted audit trail |
| **Failure handling** | **Graceful failure at 3 points** | Budget breach, tampered mandate, Razorpay error — all caught & logged |

---

## 🛠️ Complete End-to-End Autonomous Journey

```
AI Buyer: "I need a laptop for programming under ₹70,000."
              ↓
[1] Issue AP2 Bounded Mandate (HMAC-SHA256, Max: ₹70,000)
              ↓
[2] A2A Message → Merchant Agent (real a2a.types.SendMessageRequest)
              ↓
[3] MCP tools/call: merchant_search_catalog
    → TechPro DevBook 15 @ ₹65,000 (Vector Sim: 88.9%)
              ↓
[4] MCP tools/call: merchant_evaluate_upsell
    → 2-Year Warranty @ ₹2,999 (Headroom: ₹5,000)
              ↓
[5] AP2 Mandate Validation: ₹67,999 ≤ ₹70,000 ✓ (Headroom: ₹2,001)
              ↓
[6] razorpay.Client.order.create() → order_xxx created
              ↓
[7] HMAC-SHA256 Payment Signature Verified ✓
              ↓
[8] Audit Ledger SHA-256 Hash Chain Finalized → SQLite
```

---

## 💻 Quick Start

### 1. Install Dependencies
```bash
pip install fastapi uvicorn razorpay pydantic httpx pytest a2a-sdk mcp google-genai
```

### 2. Run the Web Dashboard
```bash
python main.py
```
Open: `http://localhost:8000` | Swagger: `http://localhost:8000/docs`

### 3. Run CLI Demo
```bash
python demo.py
```

### 4. Run Standalone MCP Server (stdio/SSE)
```bash
python mcp_server.py
```

### 5. Run Automated Tests
```bash
python -m pytest tests/ -v
```
**Expected: 22/22 tests passed** ✅

---

## 🔌 A2A Protocol Endpoints (real a2a-sdk protobuf types)

| Endpoint | Method | Description |
|:---|:---|:---|
| `/.well-known/agent.json` | GET | Real `a2a.types.AgentCard` protobuf → `MessageToDict` |
| `/api/a2a/message` | POST | Real `SendMessageRequest` → `Task` lifecycle → `SendMessageResponse` |

**Example A2A message:**
```json
POST /api/a2a/message
{
  "message": {
    "role": 2,
    "parts": [{"text": "I need a 65W GaN charger under ₹2500"}]
  }
}
```

---

## 🔌 MCP Endpoints (real mcp.types Pydantic objects)

| Endpoint | Method | Description |
|:---|:---|:---|
| `/mcp` | POST | JSON-RPC 2.0 dispatcher — `tools/list`, `tools/call` |
| `/api/mcp/tools` | GET | Returns `mcp.types.Tool[]` via `.model_dump()` |

---

## 🔑 Razorpay Test Mode

Set environment variables for your own Razorpay test keys:
```bash
set RAZORPAY_KEY_ID=rzp_test_YourKeyHere
set RAZORPAY_KEY_SECRET=YourSecretKeyHere
```
Without keys, the service uses a high-fidelity test mode with HMAC-verified simulated payments.

---

## 🏆 Track 01 Differentiators

1. **Real Protocol Libraries**: Uses `a2a-sdk 1.1.2` protobuf types and `mcp 1.26.0` Pydantic types — no custom wrapper classes.
2. **Revenue Maximisation**: Evaluates AP2 mandate headroom to recommend highest-margin upsells (e.g. warranty at 80% margin).
3. **Bounded & Gated**: Every money action requires a valid HMAC-SHA256 AP2 mandate — budget cap, merchant binding, category limits, expiry enforced.
4. **Full Explainability**: Every agent action (search, upsell, mandate check, payment) SHA-256 hash-chained in SQLite audit ledger.
5. **Three Graceful Failures**: Budget breach, tampered mandate signature, Razorpay gateway error — each caught, logged, and returned with structured error.
