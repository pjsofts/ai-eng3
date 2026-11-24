# Week 5 · Evals and discipline

Two parts, both plain Python with no framework, both with slides.

| Part | Folder | What you build |
|---|---|---|
| 1 | [`part1-diagram-agent/`](part1-diagram-agent) | A diagram agent that draws on an Excalidraw canvas, a golden dataset, scorers and the improvement loop, including the moment the eval turns out to be lying. Live visualizer on port 8769. |
| 2 | [`part2-intro-to-evals/`](part2-intro-to-evals) | Introduction to evals: pick the cheapest good-enough model, an LLM judge you calibrate, fixing the prompt before the model, then smoke evals, batch runs and drift in production. |

Each folder has its own README with run instructions. Both run offline in replay mode,
no API key needed.

Part 2 includes a GitHub Actions example in
[`part2-intro-to-evals/.github/workflows/smoke-eval.yml`](part2-intro-to-evals/.github/workflows/smoke-eval.yml).
GitHub only runs workflows from the repo root, so copy it there if you want it live.
