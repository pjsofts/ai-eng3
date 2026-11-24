# Step 8 — Context management
# Every call sends the WHOLE conversation again. Long sessions get slow and
# expensive, and finally too big for the model's context window.
# Before each turn: estimate the tokens. Over 80% of the window? Replace the old
# messages with a short summary, then carry on.
from agent import run_agent
from llm import ask
from past_conversation import PAST_MESSAGES
from tools import list_files, read_file

CONTEXT_WINDOW = 1_000   # tokens. Tiny on purpose, to see it happen. gpt-4o-mini: 128,000
THRESHOLD = 0.8          # compact at 80%: leave room for the reply and tool results

TOOLS = [list_files, read_file]
SYSTEM = {"role": "system",
          "content": "You are a helpful assistant for a small software project. Be concise."}

SUMMARY_PROMPT = """Summarize this conversation so it can continue without it. Keep:
1. the decisions that were made
2. important facts, names and numbers
3. open tasks and questions
4. the overall goal
Be short.

The conversation:
"""


def run(question):
    history = list(PAST_MESSAGES)                       # earlier turns of this session
    new_message = {"role": "user", "content": question}

    tokens = estimate_tokens([SYSTEM] + history + [new_message])
    if tokens > CONTEXT_WINDOW * THRESHOLD:
        history = compact(history)

    messages = [SYSTEM] + history + [new_message]
    return run_agent(messages, TOOLS)


def estimate_tokens(messages):
    """About 4 characters per token. Close enough to decide when to compact."""
    characters = sum(len(message.get("content") or "") for message in messages)
    return characters // 4


def compact(history):
    """Replace the whole history with two messages: a summary, and an OK."""
    text = ""
    for message in history:
        text += f"{message['role'].upper()}: {message['content']}\n\n"

    summary = ask(SUMMARY_PROMPT + text)
    return [
        {"role": "user",
         "content": f"[Summary of our conversation so far]\n{summary}"},
        {"role": "assistant",
         "content": "Thanks, I have the summary. Let's continue."},
    ]


if __name__ == "__main__":
    print(run("Remind me: which database did we choose, "
              "and which port does the app use?"))
