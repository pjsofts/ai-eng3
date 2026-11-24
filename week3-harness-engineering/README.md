# Week 3 · Harness engineering

> The LLM decides the next semantic step; **the harness owns execution**.

One incident/support agent, made production-grade one failure mode at a time.
Seven parts in TypeScript, plus a GUI that runs the same code live.

| Folder | What it is |
|---|---|
| [`workshop/`](workshop) | The seven parts as plain TypeScript, each runnable from the CLI. [`PRESENTATION.md`](workshop/PRESENTATION.md) is the live demo script. |
| [`gui/`](gui) | The visualizer: a React + Node app that imports the real `workshop/` modules and shows the chat, the event stream, crashes, handoffs and approvals live. |

| Part | Failure mode it fixes |
|---|---|
| 1 · Brittle agent | State lives in memory: a crash loses everything mid-task |
| 2 · Durable execution | Re-running after a crash double-bills and double-emails; save each step and resume (hand-rolled, DBOS and Jev variants) |
| 3 · Sandboxing & code mode | Model-written code can read your secrets or loop forever; run it isolated |
| 4 · Memory & context hydration | Long tasks overflow the context and cost grows quadratically |
| 5 · Routing & handoffs | One agent with every tool is over-privileged; triage hands off to specialists |
| 6 · Supervision | Serial sub-tasks are slow and one failure kills the job; plan, dispatch in parallel, fan in |
| 7 · Human-in-the-loop | Some actions need a human who may answer in three days; approvals as durable events |

## Run it

Requires Node 20+.

```bash
cd week3-harness-engineering/workshop
npm install
cp .env.example .env              # add your API key

cd ../gui
npm install && (cd client && npm install)
npm run gui                       # → http://127.0.0.1:3377
```

The GUI and the CLI share the same state (`wf/`, `events.jsonl`), so you can start
a workflow in the browser and resume it from the terminal. CLI commands for every
part are in [`workshop/PRESENTATION.md`](workshop/PRESENTATION.md#quick-reference--every-command).
