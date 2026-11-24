# Multi-agent parallelization: several agents work at the same time,
# each with its own tools, then a planner combines their results.
#
# Who decides what happens next?  The code runs every agent;
# each agent decides which of its tools to use.
from concurrent.futures import ThreadPoolExecutor

from agent import Agent
from llm import ask
from tools import find_restaurants, search_flights, search_hotels

agents = [
    Agent("transport", "Find the best way to get there. Be brief.", tools=[search_flights]),
    Agent("hotels", "Find a good place to stay on a budget. Be brief.", tools=[search_hotels]),
    Agent("food", "Find places to eat. Be brief.", tools=[find_restaurants]),
]


def combine(request, findings):
    notes = "\n\n".join(f"## {name}\n{text}" for name, text in findings.items())
    return ask(f"Request: {request}\n\nFindings:\n{notes}\n\nWrite a short weekend plan.")


def run(request):
    with ThreadPoolExecutor() as pool:
        futures = {agent.name: pool.submit(agent.run, request) for agent in agents}
        findings = {name: future.result() for name, future in futures.items()}

    return combine(request, findings)


if __name__ == "__main__":
    print(run("Plan a budget weekend in Isfahan for two people, leaving from Tehran."))
