# AI Engineering · cohort 3

Code, slides and live visualizers for weeks 1–5 of the
[AI Engineering mentorship](https://pjsofts.github.io/curriculum): build a real AI agent
from scratch, with no framework, and learn to make it reliable.

Every week is a series of small, runnable steps. The visualizers let you pick a step,
run it and watch it work: the diagram lights up, the code view highlights the running
line, and a side panel shows what the model sees, tokens and costs.

## Weeks

| Week | Topic | Folder | Stack | Slides | Visualizer |
|---|---|---|---|---|---|
| 1 | Your first agent | [`week1-your-first-agent/`](week1-your-first-agent) | Python | ✓ | :8768 |
| 2 | Agent workflows | [`week2-agent-workflows/`](week2-agent-workflows) | Python | ✓ | :8765 |
| 3 | Harness engineering | [`week3-harness-engineering/`](week3-harness-engineering) | TypeScript, React | demo script | :3377 |
| 4 | Background agents | [`week4-background-agents/`](week4-background-agents) | Python, Inngest | ✓ | :8767 |
| 5 | Evals and discipline | [`week5-evals/`](week5-evals) | Python | ✓ (both parts) | :8769 (part 1) |

### Week 1 · Your first agent
An agent built from an empty file in ten steps: one LLM call, one tool call,
single-turn evals, the agent loop, multi-turn evals, file tools, web search,
context management, shell and code, and human approval.

### Week 2 · Agent workflows
When *not* to build an agent. Thirteen patterns side by side: prompt chaining, routing,
parallelization, ReAct, plan-and-execute, reflection, CodeAct and five multi-agent
patterns. The question behind all of them: who decides the next step, your code or the model?

### Week 3 · Harness engineering
The LLM decides the next step; the harness owns execution. Seven parts that each fix
one production failure: durable execution, sandboxing, memory, handoffs, supervision
and human-in-the-loop. A React GUI runs the real workshop code live.

### Week 4 · Background agents
An incident agent for a pretend checkout service, built on the Inngest SDK: durable
steps, waiting for events, human approval, safe retries and asking for help. You play
the world: kill the agent, approve, deny or fix the gateway.

### Week 5 · Evals and discipline
- **Part 1:** a diagram agent on an Excalidraw canvas, a golden dataset, scorers and the
  improvement loop, including the eval that lies.
- **Part 2:** introduction to evals: choose a model and a prompt from evidence, calibrate
  an LLM judge, then smoke evals, batch runs and drift in production.

## Run any week

Each folder is self-contained, with its own README.

```bash
# Python weeks (1, 2, 4, 5)
cd week1-your-first-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py                                    # visualizer; slides at /slides/

# Week 3 (Node 20+)
cd week3-harness-engineering/workshop && npm install && cp .env.example .env
cd ../gui && npm install && (cd client && npm install) && npm run gui
```

**Replay mode** is the default in the Python visualizers: recorded model answers, so it
runs offline with no API key. Switch to **Live** after copying `.env.example` to `.env`
and adding a key. Any OpenAI-compatible endpoint works.

Slides: `←` `→` to move, `F` fullscreen, `PDF` to print. Slides marked **▶ Demo** are
where you switch to the visualizer.

## Requirements

- Python 3.10+ (3.11+ for week 5)
- Node 20+ for week 3
- An API key only for Live mode
