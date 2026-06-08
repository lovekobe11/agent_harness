"""main.py — Agent loop & demo entry point.

Orchestrates all modules: config → guard → prompt → LLM → tools → memory.
Run:  cd agent_harness && python main.py
"""
from __future__ import annotations
import json, re
from openai import OpenAI

from config import cfg
from logger import logger
from prompts import build_system_prompt
from guard import is_safe, redact_pii
from memory import Memory
from tools import list_tool_descriptions, dispatch
from session import Session


# ---------- LLM client ----------
client = OpenAI(api_key=cfg.API_KEY, base_url=cfg.BASE_URL)


def call_llm(messages: list[dict]) -> str:
    """Send messages to Qwen and return the assistant reply."""
    resp = client.chat.completions.create(
        model=cfg.MODEL,
        messages=messages,
        temperature=cfg.TEMPERATURE,
        max_tokens=cfg.MAX_TOKENS,
    )
    return resp.choices[0].message.content

def extract_memories(reply: str, memory: Memory) -> str:
    """Parse <!-- memories: {...} --> from reply and save them. Returns cleaned reply."""
    match = re.search(r'<!-- memories: (\{.*?\}) -->', reply)
    if match:
        try:
            facts = json.loads(match.group(1))
            for k, v in facts.items():
                memory.remember(k, v)
                logger.info("Auto-remembered: %s = %s", k, v)
        except json.JSONDecodeError:
            pass
        reply = reply[:match.start()].rstrip()
    return reply

# ---------- core agent loop ----------
def agent_turn(user_input: str, session: Session, memory: Memory) -> str:
    """Process one user turn: guard → LLM → tool dispatch → respond."""

    # 1. Safety check
    safe, reason = is_safe(user_input)
    if not safe:
        return f"⛔ Blocked: {reason}"

    # 2. Memory commands (local, no LLM needed)
    if user_input.startswith("/remember "):
        parts = user_input.split(maxsplit=2)
        if len(parts) == 3:
            memory.remember(parts[1], parts[2])
            return f"✓ Remembered: {parts[1]}"
    if user_input == "/recall":
        return f"📝 Memories:\n{memory.summary()}"

    # 3. Build prompt with tools + memories
    system = build_system_prompt(list_tool_descriptions())
    if memory.summary() != "(no memories)":
        system += f"\n\nUser facts:\n{memory.summary()}"

    session.add("system", system)
    session.add("user", user_input)

    # 4. Agent loop: call LLM, dispatch tools, repeat (max cfg.MAX_LOOPS)
    reply = ""
    max_loops = cfg.MAX_LOOPS
    for loop in range(1, max_loops + 1):
        logger.info("Loop %d/%d — calling LLM", loop, max_loops)
        reply = call_llm(session.history())

        # Try to parse tool call
        try:
            data = json.loads(reply)
            if "tool" in data:
                tool_result = dispatch(data["tool"], data.get("args", {}))
                session.add("assistant", reply)
                session.add("user", f"Tool result: {tool_result}\nPlease continue.")
                logger.info("Tool dispatched, looping (%d/%d)", loop, max_loops)
                continue  # next loop iteration
        except (json.JSONDecodeError, TypeError):
            pass  # not a tool call

        break  # no tool call → final answer
    else:
        # Hit the loop limit without a final answer
        logger.warning("Agent hit max loop limit (%d)", max_loops)
        reply = (reply + f"\n\n[Stopped: reached max {max_loops} tool-call rounds. "
                          "Please ask a follow-up if needed.]")

    # 5. Auto-extract and save memories from the reply
    reply = extract_memories(reply, memory)

    # 6. Output guard
    reply = redact_pii(reply)
    session.add("assistant", reply)
    session.save()
    logger.info("Reply: %s", reply[:80])
    return reply

# ---------- demo ----------
def demo():
    """Interactive demo with guided examples."""
    print("=" * 50)
    print("  Agent Harness Demo (Qwen)")
    print("=" * 50)
    print("Try these examples:")
    print("  1. Hi, my name is Bob and I love pizza")
    print("  2. What is 123 * 456 + 789?")
    print("  3. What time is it now?")
    print("  4. /recall           — show stored memories")
    print("  5. /sessions         — list past sessions")
    print("  6. /resume <id>      — resume a past session")
    print("  7. What do you know about me?")
    print("Type 'quit' to exit.\n")

    session = Session()
    memory = Memory()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break
        # --- session commands ---
        if user_input == "/sessions":
            ids = Session.list_sessions()
            if not ids:
                print("\nAgent: No saved sessions.\n")
            else:
                lines = []
                for sid in ids:
                    s = Session.load(sid)
                    lines.append(f"  - {sid}  ({len(s.messages)} msgs, created {s.created_at[:19]})")
                print(f"\nAgent: {len(ids)} session(s):\n" + "\n".join(lines) + "\n")
            continue
        if user_input.startswith("/resume "):
            rid = user_input.split(maxsplit=1)[1].strip()
            try:
                session = Session.load(rid)
                print(f"\nAgent: Resumed session '{rid}' ({len(session.messages)} messages).\n")
            except FileNotFoundError:
                print(f"\nAgent: Session '{rid}' not found. Use /sessions to list.\n")
            continue
        # --- normal turn ---
        reply = agent_turn(user_input, session, memory)
        print(f"\nAgent: {reply}\n")

    print(f"\nSession '{session.id}' saved. Bye!")

if __name__ == "__main__":
    demo()
