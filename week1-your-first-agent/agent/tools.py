# tools.py — the agent's hands: plain Python functions.
#
# The model sees each function's name, parameters and docstring, nothing else.
# So the docstring is not a comment for humans: it is the instruction that
# tells the model WHEN to use the tool.
#
# Two rules for every tool:
#   1. Return a string. Errors too: never raise. The model reads the error and recovers.
#   2. Only touch files inside the workspace folder.
import datetime
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from llm import search_web

HERE = Path(__file__).parent
WORKSPACE = HERE / "workspace"          # the only folder the agent may touch
SAMPLE = HERE / "sample_workspace"      # a clean copy, to start again
MAX_LINES = 200                         # long files are cut, to save tokens
TIMEOUT = 30                            # seconds, for commands and code


def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")


# ---- files -----------------------------------------------------------------

def list_files(directory: str = ".") -> str:
    """List the files and folders in a directory of the workspace."""
    try:
        entries = sorted(inside_workspace(directory).iterdir())
    except FileNotFoundError:
        return f"Error: directory not found: {directory}"
    except Exception as error:
        return f"Error: {error}"
    lines = []
    for entry in entries:
        kind = "[dir]  " if entry.is_dir() else "[file] "
        lines.append(kind + entry.name)
    return "\n".join(lines) or f"{directory} is empty"


def read_file(path: str) -> str:
    """Read a text file from the workspace."""
    try:
        text = inside_workspace(path).read_text()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as error:
        return f"Error: {error}"
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        shown = "\n".join(lines[:MAX_LINES])
        return shown + f"\n... ({len(lines)} lines, showing the first {MAX_LINES})"
    return text


def write_file(path: str, content: str) -> str:
    """Write a text file in the workspace. Creates it, or replaces what was there."""
    try:
        file = inside_workspace(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
    except Exception as error:
        return f"Error: {error}"
    return f"Wrote {len(content)} characters to {path}"


def delete_file(path: str) -> str:
    """Delete a file from the workspace. This cannot be undone."""
    try:
        inside_workspace(path).unlink()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as error:
        return f"Error: {error}"
    return f"Deleted {path}"


def inside_workspace(path):
    """Turn a path from the model into a real path.
    Refuse anything outside the workspace."""
    full_path = (WORKSPACE / path).resolve()
    if not full_path.is_relative_to(WORKSPACE.resolve()):
        raise PermissionError(f"{path} is outside the workspace")
    return full_path


# ---- the web ---------------------------------------------------------------

def web_search(query: str) -> str:
    """Search the web. Use it ONLY for things that change or that you cannot know:
    news, weather, prices, latest versions, today's events.
    Do not search for things you already know, like the capital of France."""
    return search_web(query)


# ---- shell and code --------------------------------------------------------

def run_command(command: str) -> str:
    """Run a shell command in the workspace folder and return what it prints.
    Use it for things like counting lines, git, or checking installed versions."""
    try:
        result = subprocess.run(command, shell=True, cwd=WORKSPACE,
                                capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"Error: stopped after {TIMEOUT} seconds"
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return f"Command failed (exit code {result.returncode}):\n{output}"
    return output or "Done (no output)"


RUNNERS = {"python": (".py", sys.executable), "javascript": (".js", "node")}


def execute_code(code: str, language: str = "python") -> str:
    """Run a program and return what it prints. Use it for any calculation or data
    processing: never do maths in your head. Use print() to show the result.
    language is "python" or "javascript". Only the standard library is installed.
    The program runs in the workspace folder, so it can open files there."""
    if language not in RUNNERS:
        return f"Error: language must be one of {', '.join(RUNNERS)}"
    suffix, program = RUNNERS[language]
    file = Path(tempfile.gettempdir()) / f"agent_code{suffix}"
    file.write_text(code)                          # 1. write the code to a file
    try:                                           # 2. run it
        result = subprocess.run([program, str(file)], cwd=WORKSPACE,
                                capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"Error: stopped after {TIMEOUT} seconds"
    finally:
        file.unlink(missing_ok=True)               # 3. clean up
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return f"The code failed (exit code {result.returncode}):\n{output}"
    return output or "The program printed nothing. Use print() to see the result."


# ---- setup -----------------------------------------------------------------

def reset_workspace():
    """Start again from the clean sample files."""
    shutil.rmtree(WORKSPACE, ignore_errors=True)
    shutil.copytree(SAMPLE, WORKSPACE)


if not WORKSPACE.exists():
    reset_workspace()
