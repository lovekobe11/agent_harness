# Agent Harness — Minimal Python Demo

A lightweight agent framework powered by **Qwen** (DashScope).  
Each feature is a separate Python file. Total: <=600 lines of readable code.

---

## Quick Start

```bash
cd agent_harness
pip install openai
python main.py
```

> Requires a DashScope API key in `.env`:  
> `DASHSCOPE_API_KEY=sk-your-key-here`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                    (Orchestrator + Demo CLI)                      │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  guard   │──▶│ prompts  │──▶│   LLM    │──▶│  tools   │    │
│  │ (input)  │   │ (system) │   │  (Qwen)  │   │(dispatch)│    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       │                              │               │           │
│       ▼                              ▼               ▼           │
│  ┌──────────┐                 ┌──────────┐   ┌──────────┐      │
│  │  guard   │                 │  memory  │   │  memory  │      │
│  │ (output) │                 │ (extract)│   │  (store) │      │
│  └──────────┘                 └──────────┘   └──────────┘      │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│  │ session  │   │  logger  │   │  config  │                    │
│  │ (history)│   │  (logs)  │   │ (env+cfg)│                    │
│  └──────────┘   └──────────┘   └──────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Breakdown

### Data Flow (per user turn)

```
User Input
    │
    ▼
① guard.is_safe()          ── Block harmful input (hack, SQL injection, etc.)
    │
    ▼
② prompts.build_system_prompt() ── Inject tool list + stored memories
    │
    ▼
③ call_llm()               ── Send to Qwen via DashScope API
    │
    ▼
④ Is reply a tool call?
    │ YES → tools.dispatch() → feed result back → loop to ③ (max 5x)
    │ NO  → continue
    ▼
⑤ extract_memories()       ── Auto-save facts from <!-- memories: {...} -->
    │
    ▼
⑥ guard.redact_pii()       ── Strip sensitive data (SSN, card numbers)
    │
    ▼
⑦ session.save()           ── Persist conversation to sessions/<id>.json
    │
    ▼
Agent Reply
```

---

## File Structure

```
agent_harness/
├── config.py            # ① Configuration — loads .env, central settings
├── logger.py            # ② Logging — console + file dual output
├── prompts.py           # ③ Prompts — system prompt, auto-memory instructions
├── guard.py             # ④ Safety — input filter + PII redaction
├── memory.py            # ⑤ Memory — JSON key-value store with auto-trim (1MB)
├── tools.py             # ⑥ Tools — registry + dispatch (calc, time, search)
├── session.py           # ⑦ Session — conversation history, save/load/resume
├── main.py              # ⑧ Orchestrator — agent loop + interactive demo
├── .env                 # API key (DASHSCOPE_API_KEY=sk-...)
├── memory_store.json    # Auto-generated — persistent memory
├── agent.log            # Auto-generated — full debug log
└── sessions/            # Auto-generated — one JSON per session
    ├── a1b2c3d4.json
    └── e5f6g7h8.json
```

---

## Module Details

| File | Lines | Responsibility |
|------|-------|---------------|
| `config.py` | 33 | Auto-loads `.env`, exposes `cfg` singleton with all settings |
| `logger.py` | 33 | Dual-output logger (console INFO+, file DEBUG+) |
| `prompts.py` | 42 | System prompt template with tool descriptions + auto-memory rule |
| `guard.py` | 32 | Input safety filter + output PII redaction |
| `memory.py` | 74 | Persistent JSON memory with timestamps + auto-trim at 1MB |
| `tools.py` | 164 | Tool registry, dispatch, and 3 built-in tools |
| `session.py` | 53 | Conversation history, save/load/list/resume sessions |
| `main.py` | 163 | Agent loop, LLM client, memory extraction, demo CLI |

---

## Configuration (`config.py`)

All settings in one place. Override via environment variables or edit directly:

| Setting | Default | Description |
|---------|---------|-------------|
| `API_KEY` | `DASHSCOPE_API_KEY` env | DashScope API key |
| `BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | DashScope endpoint |
| `MODEL` | `qwen3.6-flash-2026-04-16` | Qwen model name |
| `TEMPERATURE` | `0.7` | LLM creativity (0–1) |
| `MAX_TOKENS` | `1024` | Max response length |
| `MAX_LOOPS` | `5` | Max tool-call rounds per turn |
| `MEMORY_FILE` | `memory_store.json` | Persistent memory path |
| `LOG_FILE` | `agent.log` | Log file path |
| `SESSION_DIR` | `sessions/` | Session storage directory |

---

## Interactive Commands

| Command | Description |
|---------|-------------|
| `/remember key value` | Manually store a memory |
| `/recall` | Show all stored memories |
| `/sessions` | List all past sessions |
| `/resume <id>` | Resume a past session by ID |
| `quit` / `exit` | Exit the demo |

---

## Built-in Tools (`tools.py`)

| Tool | Args | Description |
|------|------|-------------|
| `calc` | `expression` | Evaluate math: `calc("123 * 456 + 789")` → `56877` |
| `get_time` | — | Current date and time |
| `web_search` | `query` | Placeholder (sandbox mode) |

**Adding a new tool:**
```python
def my_tool(arg1: str) -> str:
    """Description for the prompt."""
    return f"Result: {arg1}"

TOOL_REGISTRY["my_tool"] = {
    "fn": my_tool, "desc": "Does something cool", "args": "arg1"
}
```

---

## Auto-Memory System

The LLM is instructed (via `prompts.py`) to append `<!-- memories: {"key": "value"} -->`  
to its reply when it detects notable information. `main.py` parses and saves these  
automatically to `memory_store.json`.

**Storage format:**
```json
{
  "memories": {
    "name": "Gin",
    "topic_Eiffel_Tower": "discussed history and construction"
  },
  "_meta": {
    "name": 1717920000.0,
    "topic_Eiffel_Tower": 1717920100.0
  }
}
```

**Auto-trim:** When the file exceeds 1MB, the oldest 20% of memories are removed.

---

## Safety Guard (`guard.py`)

**Input filter** — blocks messages matching:
- `hack`, `exploit`, `malware`, `phishing`, `ddos`
- `DROP TABLE`, `DELETE FROM`, `rm -rf`

**Output filter** — redacts:
- US Social Security Numbers → `[SSN_REDACTED]`
- Credit card numbers (16–19 digits) → `[CARD_REDACTED]`

---

## Agent Loop Limit (`MAX_LOOPS`)

Prevents runaway tool chains. Each LLM call counts as one loop:

```
Loop 1/5 → LLM calls tool → dispatch → continue
Loop 2/5 → LLM calls tool → dispatch → continue
Loop 3/5 → LLM answers directly → break ✓
```

If all 5 loops produce tool calls without a final answer:
```
[Stopped: reached max 5 tool-call rounds. Please ask a follow-up if needed.]
```

---

## Example Session

```
==================================================
  Agent Harness Demo (Qwen)
==================================================

You: Hi, my name is Alice and I love tennis
Agent: Hi Alice! 🎾 Great to meet you...

You: What is 123 * 456 + 789?
Agent: The result is 56,877.

You: /recall
Agent: 📝 Memories:
- name: Alice
- interest: tennis
- topic_math: asked about 123 * 456 + 789

You: /sessions
Agent: 3 session(s):
  - a1b2c3d4  (12 msgs, created 2026-06-09T00:00:00)
  - e5f6g7h8  (6 msgs, created 2026-06-09T00:15:00)
  - f31e5307  (8 msgs, created 2026-06-09T00:30:00)

You: quit
Session 'f31e5307' saved. Bye!
```

---

## Requirements

- Python 3.9+
- `openai` package (`pip install openai`)
- DashScope API key (set in `.env` or environment variable)
