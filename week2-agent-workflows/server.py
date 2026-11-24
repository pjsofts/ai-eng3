"""Runs a workflow and streams what it does to the browser.

The workflow files stay plain Python. This server watches them run with
sys.settrace: every function call, every line and every LLM call becomes an
event, sent to the page over Server-Sent Events. Nothing here is shown to the
audience; it is the projector, not the film.

    python server.py            # then open http://127.0.0.1:8765
"""
import importlib
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
WORKFLOWS = ROOT / "workflows"
UI = ROOT / "ui"
sys.path.insert(0, str(WORKFLOWS))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

try:
    import llm  # noqa: E402  (must be patched before any workflow imports it)
except Exception:  # no API key: replay mode still works
    os.environ["OPENAI_API_KEY"] = "missing"
    import llm  # noqa: E402
HAS_KEY = os.environ.get("OPENAI_API_KEY") != "missing"

import catalog  # noqa: E402
import mocks  # noqa: E402

PORT = int(os.environ.get("PORT", 8765))
SPEEDS = {  # seconds to pause per traced line, and per replayed LLM call
    "slow": (0.35, 1.8),
    "normal": (0.12, 1.0),
    "fast": (0.0, 0.3),
}
TEXT_LIMIT = 4000


class StopRun(Exception):
    pass


def short(value, limit=TEXT_LIMIT):
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[:limit] + " …"


def show_reply(reply):
    if isinstance(reply, llm.Reply):
        calls = [f"{call.name}({', '.join(f'{k}={v!r}' for k, v in call.args.items())})"
                 for call in reply.tool_calls]
        return {"text": reply.text, "tool_calls": calls}
    if isinstance(reply, dict):
        return {"text": json.dumps(reply, ensure_ascii=False, indent=2), "tool_calls": []}
    return {"text": str(reply), "tool_calls": []}


def show_messages(messages):
    shown = []
    for message in messages:
        message = message if isinstance(message, dict) else {"role": "?", "content": str(message)}
        item = {"role": message.get("role"), "content": short(message.get("content") or "")}
        if message.get("tool_calls"):
            item["tool_calls"] = [f"{c['function']['name']}({c['function']['arguments']})"
                                  for c in message["tool_calls"]]
        shown.append(item)
    return shown


class Run:
    def __init__(self, name, task, mode, step, speed):
        self.name = name
        self.task = task
        self.graph = catalog.WORKFLOWS[name]
        self.nodes = {node["id"]: node for node in self.graph["nodes"]}
        self.edges = {(a, b): by for a, b, by, _ in self.graph["edges"]}
        self.replay = mocks.Replay(name) if mode == "replay" else None
        self.step = step
        self.set_speed(speed)
        self.events = queue.Queue()
        self.gate = threading.Event()
        self.stopped = False
        self.lock = threading.RLock()
        self.local = threading.local()
        self.scope_ids = count(1)
        self.scopes = {"root": {"frontier": {"input"}, "wave": []}}
        self.threads = {}
        self.started = time.time()

    # ---- plumbing ------------------------------------------------------------

    def set_speed(self, speed):
        self.speed = speed if speed in SPEEDS else "normal"
        self.line_delay, self.llm_delay = SPEEDS[self.speed]

    def emit(self, event):
        event["t"] = round(time.time() - self.started, 3)
        self.events.put(event)

    def thread(self):
        ident = threading.get_ident()
        with self.lock:
            return self.threads.setdefault(ident, len(self.threads))

    def stack(self):
        if not hasattr(self.local, "stack"):
            self.local.stack = []
        return self.local.stack

    def check(self):
        if self.stopped:
            raise StopRun()

    # ---- graph bookkeeping ---------------------------------------------------

    def match(self, fn, args):
        for node in self.graph["nodes"]:
            rule = node.get("match")
            if rule and rule["fn"] == fn and all(
                    str(args.get(key)) == str(value) for key, value in rule.items() if key != "fn"):
                return node["id"]
        return None

    def parent(self, stack):
        for entry in reversed(stack):
            if entry["node"]:
                return entry
        return None

    def light(self, source, target):
        if (source, target) in self.edges:
            self.emit({"type": "edge", "from": source, "to": target, "by": self.edges[(source, target)]})

    def enter(self, fn, args, shown):
        self.check()
        stack = self.stack()
        node = self.match(fn, args)
        entry = {"fn": fn, "node": node, "scope": None}
        if node:
            with self.lock:
                # Which edge brought us here? A sibling that just finished, else
                # the same sources as the sibling that started alongside us
                # (parallel fan-out), else the parent node that called us.
                parent = self.parent(stack)
                scope = self.scopes[parent["scope"] if parent else "root"]
                sources = [s for s in scope["frontier"] if (s, node) in self.edges]
                if sources:
                    scope["frontier"] -= set(sources)
                    scope["wave"] = sources
                else:
                    sources = [s for s in scope["wave"] if (s, node) in self.edges]
                if not sources and parent and (parent["node"], node) in self.edges:
                    sources = [parent["node"]]
                for source in sources:
                    self.light(source, node)
                entry["scope"] = next(self.scope_ids)
                self.scopes[entry["scope"]] = {"frontier": set(), "wave": []}
            self.emit({"type": "enter", "node": node, "fn": fn, "args": shown, "thread": self.thread()})
        stack.append(entry)
        if node and self.step:
            self.emit({"type": "paused", "node": node})
            self.gate.clear()
            while not self.gate.wait(0.2):
                self.check()
            self.emit({"type": "resumed", "node": node})

    def exit(self, value, failed=False):
        stack = self.stack()
        if not stack:
            return
        entry = stack.pop()
        node = entry["node"]
        if node:
            with self.lock:
                own = self.scopes.pop(entry["scope"], {"frontier": set()})
                for child in own["frontier"]:  # an LLM step handing its result back up
                    if self.nodes[child]["kind"] == "llm":
                        self.light(child, node)
                parent = self.parent(stack)
                scope = self.scopes[parent["scope"] if parent else "root"]
                scope["frontier"].add(node)
                if parent and self.nodes[node]["kind"] != "llm":
                    self.light(node, parent["node"])
            if isinstance(value, llm.Reply):
                value = value.text or "→ " + ", ".join(call.name for call in value.tool_calls)
            self.emit({"type": "exit", "node": node, "value": short(value, 600),
                       "failed": failed, "thread": self.thread()})
        if not stack:
            self.emit({"type": "idle", "thread": self.thread()})

    def current_node(self):
        entry = self.parent(self.stack())
        return entry["node"] if entry else None

    # ---- sys.settrace hooks --------------------------------------------------

    def tracer(self, frame, event, arg):
        if event != "call":
            return None
        code = frame.f_code
        path = code.co_filename
        if not path.startswith(str(WORKFLOWS)) or path.endswith("llm.py"):
            return None
        if code.co_name == "<module>":
            return None
        if code.co_name.startswith("<"):  # generator expressions and lambdas: lines only
            return self.lines_only
        names = code.co_varnames[:code.co_argcount + code.co_kwonlyargcount]
        args, shown = {}, {}
        for name in names:
            value = frame.f_locals.get(name)
            if name == "self":
                if hasattr(value, "name"):
                    args["agent"] = value.name
                continue
            args[name] = value
            shown[name] = short(value, 300)
        self.enter(code.co_qualname, args, shown)
        return self.local_tracer

    def local_tracer(self, frame, event, arg):
        if event == "line":
            self.on_line(frame)
        elif event == "return":
            self.emit({"type": "ret", "file": Path(frame.f_code.co_filename).name, "thread": self.thread()})
            self.exit(arg)
        return self.local_tracer

    def lines_only(self, frame, event, arg):
        if event == "line":
            self.on_line(frame)
        return self.lines_only

    def on_line(self, frame):
        self.emit({"type": "line", "file": Path(frame.f_code.co_filename).name,
                   "line": frame.f_lineno, "thread": self.thread()})
        if self.line_delay:
            time.sleep(self.line_delay)
        self.check()

    # ---- the run itself ------------------------------------------------------

    def execute(self):
        self.emit({"type": "start", "workflow": self.name, "mode": "replay" if self.replay else "live"})
        self.emit({"type": "enter", "node": "input", "fn": "input", "args": {"task": short(self.task, 300)}, "thread": 0})
        self.emit({"type": "exit", "node": "input", "value": short(self.task, 600), "thread": 0})
        try:
            module = importlib.import_module(self.name)
            module = importlib.reload(module)  # pick up live edits to the file
            threading.settrace(self.tracer)
            sys.settrace(self.tracer)
            try:
                result = module.run(self.task)
            finally:
                sys.settrace(None)
                threading.settrace(None)
            for source in self.scopes["root"]["frontier"]:
                self.light(source, "output")
            self.emit({"type": "enter", "node": "output", "fn": "output", "args": {}, "thread": 0})
            self.emit({"type": "exit", "node": "output", "value": short(result, 600), "thread": 0})
            self.emit({"type": "done", "result": short(result)})
        except StopRun:
            self.emit({"type": "stopped"})
        except Exception as error:
            frames = [f for f in traceback.extract_tb(error.__traceback__)
                      if f.filename.startswith(str(WORKFLOWS))]
            where = frames[-1] if frames else None
            self.emit({"type": "error", "message": f"{type(error).__name__}: {error}",
                       "file": Path(where.filename).name if where else None,
                       "line": where.lineno if where else None,
                       "trace": traceback.format_exc()})
        self.emit({"type": "end"})


CURRENT = None
CURRENT_LOCK = threading.Lock()


def instrument(kind):
    """Wrap llm.ask / ask_json / chat so each call shows up in the UI,
    and is answered from the recording in replay mode."""
    real = getattr(llm, kind)

    def wrapper(*args, **kwargs):
        run = CURRENT
        if run is None:
            return real(*args, **kwargs)
        if kind == "chat":
            messages = args[0] if args else kwargs["messages"]
            tools = list(args[1] if len(args) > 1 else kwargs.get("tools", ()))
            request = {"messages": show_messages(messages), "tools": [t.__name__ for t in tools]}
            text = messages[0]["content"] if messages else ""
        else:
            prompt = args[0] if args else kwargs["prompt"]
            system = args[1] if len(args) > 1 else kwargs.get(
                "system", real.__defaults__[0] if real.__defaults__ else "")
            request = {"system": system, "prompt": short(prompt)}
            text = f"{system}\n{prompt}"

        run.enter(kind, {}, {})
        result, failed = None, False
        try:
            node = run.current_node()
            run.emit({"type": "llm_start", "kind": kind, "node": node, "request": request, "thread": run.thread()})
            began = time.time()
            if run.replay:
                waited = 0.0
                while waited < run.llm_delay:
                    time.sleep(0.05)
                    waited += 0.05
                    run.check()
                result = run.replay.respond(kind, text)
            else:
                result = real(*args, **kwargs)
            run.check()
            run.emit({"type": "llm_end", "kind": kind, "node": node, "reply": show_reply(result),
                      "seconds": round(time.time() - began, 2), "thread": run.thread()})
            return result
        except BaseException:
            failed = True
            raise
        finally:
            run.exit(result, failed)

    wrapper.__name__ = kind
    return wrapper


for _kind in ("ask", "ask_json", "chat"):
    setattr(llm, _kind, instrument(_kind))


def workflow_files(name):
    """The workflow file, the workflow files it imports, and llm.py."""
    main = (WORKFLOWS / f"{name}.py").read_text()
    files = {f"{name}.py": main}
    for module in re.findall(r"^from (\w+) import", main, re.MULTILINE):
        path = WORKFLOWS / f"{module}.py"
        if path.exists() and module != "llm":
            files[path.name] = path.read_text()
    files["llm.py"] = (WORKFLOWS / "llm.py").read_text()
    return files


def describe():
    workflows = []
    for module, names in catalog.MODULES:
        for name in names:
            meta = dict(catalog.WORKFLOWS[name])
            meta["edges"] = [{"from": a, "to": b, "by": by, "label": label} for a, b, by, label in meta["edges"]]
            workflows.append({"name": name, "module": module, **meta, "files": workflow_files(name)})
    return {"workflows": workflows, "has_key": HAS_KEY, "model": llm.MODEL,
            "base_url": os.environ.get("OPENAI_BASE_URL", "api.openai.com")}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        query = {key: values[-1] for key, values in parse_qs(url.query).items()}
        if url.path == "/api/workflows":
            return self.send(200, json.dumps(describe(), ensure_ascii=False))
        if url.path == "/api/run":
            return self.stream(query)
        if url.path == "/api/control":
            return self.control(query)
        if url.path == "/slides":
            self.send_response(301)
            self.send_header("Location", "/slides/")
            self.end_headers()
            return
        if url.path.startswith("/slides/"):
            return self.slides(url.path[len("/slides/"):] or "index.html")
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
        if url.path in files:
            path = UI / files[url.path]
            kind = {"html": "text/html", "js": "text/javascript", "css": "text/css"}[path.suffix[1:]]
            return self.send(200, path.read_bytes(), f"{kind}; charset=utf-8")
        self.send(404, "not found", "text/plain")

    def slides(self, name):
        folder = (ROOT / "slides").resolve()
        path = (folder / name).resolve()
        if folder not in path.parents or not path.is_file():
            return self.send(404, "not found", "text/plain")
        kinds = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".png": "image/png", ".woff2": "font/woff2"}
        self.send(200, path.read_bytes(), kinds.get(path.suffix, "application/octet-stream"))

    def control(self, query):
        run = CURRENT
        action = query.get("action")
        if run:
            if action == "next":
                run.gate.set()
            elif action == "stop":
                run.stopped = True
            elif action == "step":
                run.step = query.get("value") == "1"
                if not run.step:
                    run.gate.set()
            elif action == "speed":
                run.set_speed(query.get("value"))
        self.send(200, json.dumps({"ok": True, "running": run is not None}))

    def stream(self, query):
        global CURRENT
        name = query.get("workflow")
        if name not in catalog.WORKFLOWS:
            return self.send(400, "unknown workflow", "text/plain")
        run = Run(name, query.get("task") or catalog.WORKFLOWS[name]["example"],
                  query.get("mode", "replay"), query.get("step") == "1", query.get("speed", "normal"))
        with CURRENT_LOCK:
            if CURRENT:
                CURRENT.stopped = True
                time.sleep(0.3)
            CURRENT = run

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        def work():
            global CURRENT
            try:
                run.execute()
            finally:
                if CURRENT is run:
                    CURRENT = None

        threading.Thread(target=work, daemon=True).start()
        try:
            while True:
                try:
                    event = run.events.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
                if event["type"] == "end":
                    break
        except (BrokenPipeError, ConnectionResetError):
            run.stopped = True


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"Week 2 · AI Agent Workflows → http://127.0.0.1:{PORT}   (slides: /slides/)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
