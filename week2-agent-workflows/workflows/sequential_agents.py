# Sequential agents: an assembly line of agents.
# Each agent has its own role (and tools) and hands its work to the next.
# Like prompt chaining, except every stage is a full agent.
#
# Who decides what happens next?  The code decides the order;
# each agent decides how to do its own job.
from agent import Agent
from tools import search

researcher = Agent(
    "researcher",
    "Find the facts with the search tool. Reply with a short bullet list of facts only.",
    tools=[search],
)
writer = Agent(
    "writer",
    "Write a short, engaging paragraph (max 80 words) from these facts. Use no other facts.",
)
editor = Agent(
    "editor",
    "Fix any errors and tighten the prose. Reply with only the final text.",
)


def run(topic):
    facts = researcher.run(topic)
    draft = writer.run(facts)
    return editor.run(draft)


if __name__ == "__main__":
    print(run("Milad Tower vs the Eiffel Tower"))
