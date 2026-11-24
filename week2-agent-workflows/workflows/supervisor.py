# Supervisor: one agent manages a team.
# Its "tools" are the other agents. It delegates, reads each result,
# and decides who works next, until the job is done.
#
# Who decides what happens next?  The supervisor model, after every result.
from agent import Agent
from tools import calculate, search

researcher = Agent("researcher", "Find facts with the search tool. Reply with facts only.", tools=[search])
analyst = Agent("analyst", "Do the math with the calculate tool. Show the result.", tools=[calculate])
writer = Agent("writer", "Write a clear, short answer for the user from the notes you get.")


def ask_researcher(task: str) -> str:
    """The researcher finds facts. Give it a specific question."""
    return researcher.run(task)


def ask_analyst(task: str) -> str:
    """The analyst does calculations. Include all the numbers it needs."""
    return analyst.run(task)


def ask_writer(notes: str) -> str:
    """The writer turns your notes into the final answer for the user."""
    return writer.run(notes)


supervisor = Agent(
    "supervisor",
    """You manage a team: a researcher, an analyst and a writer.
Delegate one task at a time and read each result before deciding the next step.
When the writer has produced the final answer, reply with it unchanged.""",
    tools=[ask_researcher, ask_analyst, ask_writer],
)


def run(request):
    return supervisor.run(request)


if __name__ == "__main__":
    print(run("How many times bigger is Istanbul than Tehran by population?"))
