# Week 2 · AI Agent Workflows: live visualizer and slides

First given as the webinar on 29 October 2026. Pick a workflow, press **Enter**, and watch it run:
the diagram lights up each step and edge, the Python code highlights the line that is
executing, and the trace shows every prompt, reply and tool call.

The 13 workflows are plain Python in `workflows/`. Each one runs on its own
(`python workflows/routing.py`) and has no tracing code in it. The server watches them
run with `sys.settrace`.

## Run it

Requires Python 3.10+.

```bash
cd week2-agent-workflows
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt        # openai, python-dotenv
cp .env.example .env                   # only needed for Live mode
python server.py                       # → http://127.0.0.1:8765
```

Replay mode needs no API key, so you can try every workflow straight after cloning.

The slides are served by the same server at **http://127.0.0.1:8765/slides/**
(or open `slides/index.html` directly). `←` `→` to move, `F` fullscreen, `PDF` to print.

## Replay vs Live

- **Replay** (default) answers every LLM call from a recording in `mocks.py`. It works
  offline, and the same thing happens every time. Use it on stage.
- **Live** calls the model set in `.env`. It works with any OpenAI-compatible endpoint
  (OpenAI, Liara, OpenRouter). If the audience changes the input, use Live, because
  Replay only has recordings for the example inputs. Routing is the exception: in Replay
  it classifies any ticket by keyword.

## On stage

| Key | |
|---|---|
| `Enter` | run (Ctrl+Enter inside the input box) |
| `S` | step mode: pause before every step |
| `Space` / `→` / `PgDn` | next step while paused |
| `↑` `↓` / `PgUp` `PgDn` | previous / next workflow |
| `-` `=` | slower / faster |
| `1` `2` `3` | diagram + code / diagram only / code only |
| `[` `]` | switch code file (e.g. `agent.py`, where agents loop) |
| `B` / `L` / `T` | sidebar / trace / light theme |
| `Esc` | stop |

Click any node to see what it was last called with and what it returned. Use the
browser's Ctrl+/− to size everything for the projector.

**What to point at:** solid grey edges are paths the **code** chose, dashed amber edges
are paths the **model** chose. After a run, the paths that were not taken fade out
(this is clearest in Routing). Each node counts how many times it ran (×3), and the
status line shows the time, LLM calls and tool calls. That is the cost, latency and
predictability trade-off from the webinar's central question.

## Files

```
workflows/   what the audience sees
  llm.py       ask / ask_json / chat: the only LLM code
  agent.py     Agent class: the ReAct loop, packaged (used by multi-agent workflows)
  tools.py     fake APIs (search, calculate, invoices...)
  <13 workflows>.py
catalog.py   titles, example inputs, diagram layout for each workflow
mocks.py     recorded replies for Replay mode
server.py    runs a workflow under sys.settrace and streams events (SSE)
ui/          the page
```

To add a workflow, put `my_flow.py` (with a `run(task)` function) in `workflows/`, add
its diagram to `catalog.py` (nodes match function names), and optionally record replies
in `mocks.py`. You can edit workflow files while the server is running; each run reloads
the file.
