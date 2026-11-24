# Dispatcher: one agent reads the request, splits it into tasks,
# and sends each task to the right specialist. One pass, no loop.
# Unlike routing, the model can pick several specialists and write their tasks.
# Unlike a supervisor, it never reviews the results.
#
# Who decides what happens next?  The model, once, at the start.
from concurrent.futures import ThreadPoolExecutor

from agent import Agent
from llm import ask_json
from tools import check_api_logs, issue_refund, lookup_invoice

specialists = {
    "billing": Agent("billing", "You are a billing specialist. Use your tools.",
                     tools=[lookup_invoice, issue_refund]),
    "technical": Agent("technical", "You are a support engineer. Use your tools.",
                       tools=[check_api_logs]),
}


def dispatch(request):
    plan = ask_json(f"""Split this customer request into tasks for our specialists.
Specialists: billing, technical

Request: {request}

Reply as JSON: {{"tasks": [{{"specialist": "...", "task": "..."}}]}}""")
    return plan["tasks"]


def run(request):
    tasks = dispatch(request)

    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(specialists[t["specialist"]].run, t["task"]) for t in tasks]
        answers = [future.result() for future in futures]

    return "\n\n".join(answers)


if __name__ == "__main__":
    print(run("Customer 4521: I was charged twice in October, and our API has returned 403 since the 1st."))
