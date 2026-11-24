# graders.py — turn one answer into a right / wrong per field.
#
# Pick the quickest grader you can trust, field by field:
#   code        service, severity: one right value, check it exactly
#   loose code  root_cause in step 1: enough of the expected words are there
#   LLM judge   root_cause from step 2: the same cause in any wording
#   a person    a sample, to check the judge (step 3)
import hashlib
import json
import re
from pathlib import Path

from llm import MODE, chat
from models import JUDGE
from prompts import JUDGE_SYSTEM, RUBRIC_V2

FIELDS = ("service", "severity", "root_cause")


# ---- code -------------------------------------------------------------------

def exact(expected, got):
    if expected is None or got is None:
        return expected is got
    return str(got).strip().lower() == expected.lower()


STOP = {"the", "that", "this", "with", "from", "after", "before", "into", "were", "was", "had", "its", "for", "and"}


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3 and w not in STOP}


def loose(expected, got):
    """At least half of the expected content words appear in the answer."""
    if expected is None or got is None:
        return expected is got
    wanted = words(expected)
    return len(wanted & words(got)) / len(wanted) >= 0.5


def by_code(case, answer):
    """Step 1: exact for the two enum fields, loose for the sentence."""
    if answer is None:
        return {field: False for field in FIELDS}
    expected = case["expected"]
    return {"service": exact(expected["service"], answer.get("service")),
            "severity": exact(expected["severity"], answer.get("severity")),
            "root_cause": loose(expected["root_cause"], answer.get("root_cause"))}


# ---- the LLM judge ----------------------------------------------------------

VERDICT = {"name": "verdict", "strict": True, "schema": {
    "type": "object",
    "properties": {
        "explanation": {"type": "string", "description": "One short sentence: why."},
        "verdict": {"type": "string", "enum": ["correct", "incorrect", "unknown"]},
    },
    "required": ["explanation", "verdict"],
    "additionalProperties": False,
}}


def judge(report, answer, rubric):
    """Grade an answer against the REPORT, not against our expected answer:
    a right answer in other words must not lose points. "unknown" is allowed,
    so the judge never has to guess."""
    user = f"<report>\n{report}</report>\n\n<answer>{json.dumps(answer)}</answer>\n\n<rubric>\n{rubric}\n</rubric>"
    key = hashlib.sha1(f"{MODE}\n{JUDGE}\n{user}".encode()).hexdigest()
    if key in CACHE:
        return CACHE[key]                              # never pay twice for the same grade
    reply = chat(JUDGE, JUDGE_SYSTEM, user, schema=VERDICT)
    result = json.loads(reply.text)
    CACHE[key] = result
    save_cache()
    return result


def with_judge(case, answer, rubric=RUBRIC_V2):
    """Steps 2+: code for the enum fields, the judge for the sentence."""
    grades = by_code(case, answer)
    if answer is None:
        return grades
    verdict = judge(case["report"], answer.get("root_cause"), rubric)
    grades["root_cause"] = verdict["verdict"] == "correct"     # unknown is not a pass
    grades["verdict"] = verdict
    return grades


CACHE_FILE = Path(__file__).parent / "runs" / "judge_cache.json"
CACHE = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}


def save_cache():
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(CACHE, indent=1))
