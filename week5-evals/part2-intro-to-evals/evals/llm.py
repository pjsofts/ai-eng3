# llm.py — the only code that talks to the model.
#
#   chat(model, system, user, schema=None) -> Reply   one call, with its token counts
#   submit_batch(requests) -> batch id                 many calls, half price, later (step 7)
#   collect_batch(batch_id) -> status, counts, replies
#
# EVAL_MODE=replay (the default) answers from replay.py: no key, no network.
# EVAL_MODE=live calls the OpenAI-compatible endpoint in .env.
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
MODE = os.environ.get("EVAL_MODE", "replay")


@dataclass
class Reply:
    text: str
    input_tokens: int     # what you pay for: read them from usage, never guess
    output_tokens: int


def chat(model, system, user, schema=None):
    """One request. With a schema the reply is JSON that matches it."""
    if MODE == "replay":
        import replay
        return replay.chat(model, system, user, schema)
    extra = {"response_format": {"type": "json_schema", "json_schema": schema}} if schema else {}
    response = client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **extra,
    )
    usage = response.usage
    return Reply(response.choices[0].message.content or "", usage.prompt_tokens, usage.completion_tokens)


# ---- batches (step 7) -------------------------------------------------------
# A batch is a file of requests, each with your own custom_id. The provider runs
# them within 24 hours at half price. Results come back in ANY order.

def submit_batch(requests):
    """requests: [{"custom_id", "model", "system", "user"}] -> a batch id."""
    if MODE == "replay":
        import replay
        return replay.submit_batch(requests)
    lines = [json.dumps({
        "custom_id": r["custom_id"], "method": "POST", "url": "/v1/chat/completions",
        "body": {"model": r["model"], "messages": [
            {"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}]},
    }) for r in requests]
    path = Path(__file__).parent / "runs" / "batch_input.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines))
    upload = client().files.create(file=path.open("rb"), purpose="batch")
    batch = client().batches.create(input_file_id=upload.id, endpoint="/v1/chat/completions",
                                    completion_window="24h")
    return batch.id


def collect_batch(batch_id):
    """-> (status, counts, {custom_id: Reply}). Replies only once status is "completed"."""
    if MODE == "replay":
        import replay
        return replay.collect_batch(batch_id)
    batch = client().batches.retrieve(batch_id)
    counts = batch.request_counts.model_dump() if batch.request_counts else {}
    if batch.status != "completed":
        return batch.status, counts, {}
    replies = {}
    for line in client().files.content(batch.output_file_id).text.splitlines():
        result = json.loads(line)
        if result.get("error") or result["response"]["status_code"] != 200:
            continue                                   # a failed request has no answer
        body = result["response"]["body"]
        replies[result["custom_id"]] = Reply(body["choices"][0]["message"]["content"] or "",
                                             body["usage"]["prompt_tokens"], body["usage"]["completion_tokens"])
    return batch.status, counts, replies


_client = None


def client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()        # reads OPENAI_API_KEY and OPENAI_BASE_URL
    return _client
