# prompts.py — every prompt of the lesson, in order. Diff them.
#
#   EXTRACT_V1   steps 1-4   the prompt we start with
#   EXTRACT_V2   steps 5-8   the fix: when null applies, quote first, final severity
#   RUBRIC_V1    step 2      how the judge grades root_cause
#   RUBRIC_V2    step 3+     the same, plus the rule calibration found missing
#   RUBRIC_FULL  step 8      grades a whole answer, for live traffic with no expected answers

EXTRACT_V1 = """You read incident reports and extract three fields as JSON:

{"service": ..., "severity": ..., "root_cause": ...}

- service: the service where the incident happened
- severity: sev1, sev2 or sev3
- root_cause: one sentence, or null

Reply with the JSON only."""


EXTRACT_V2 = """You read incident reports and extract three fields as JSON:

{"service": ..., "severity": ..., "root_cause": ...}

- service: the service where the incident happened. Not the team that reported
  it, and not services that were only checked or affected downstream.
- severity: sev1, sev2 or sev3. If the severity changed, use the final one.
- root_cause: one sentence: the cause the report states.
  Use null when the report states no cause: the cause is still being
  investigated, only suspected, or not confirmed. A symptom, an action someone
  took, or a sentence saying something is NOT expected to be a problem is not
  a root cause.

Before the JSON, copy the one sentence from the report that states the root
cause, inside <source></source>. If there is no such sentence, write
<source>none</source> and use null.

Then reply with the JSON."""


JUDGE_SYSTEM = "You grade one field that a model extracted from an incident report. Follow the rubric exactly."

RUBRIC_V1 = """The answer is the root cause of the incident, taken from the report, or null.

correct: it names the cause the report states, in any wording.
         Or it is null, and the report states no cause.
incorrect: it names a cause the report does not state. This includes turning a
         symptom, an action someone took, or a reassurance into a cause.
         Or it is null, although the report states a cause.
unknown: you cannot decide from the report."""

RUBRIC_V2 = RUBRIC_V1 + """

A cause the report calls suspected, possible or not confirmed is NOT a stated
cause. The correct answer is then null."""

RUBRIC_FULL = """The answer has three fields, taken from the report.

correct: all three are right.
  service: the service where the incident happened.
  severity: sev1, sev2 or sev3, matching the report. Anything else is wrong.
  root_cause: the cause the report states, in any wording; null when it states none.
incorrect: any field is wrong, missing, or not one of the allowed values.
unknown: you cannot decide from the report."""
