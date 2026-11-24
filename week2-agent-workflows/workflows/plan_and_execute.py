# Plan and execute: think first, then act.
# A planner writes the whole plan once; an executor (a ReAct agent) does each step.
#
# Who decides what happens next?  The model decides the plan up front,
# then the code follows it step by step.
from llm import ask, ask_json
from react import run as react_agent


def make_plan(goal):
    plan = ask_json(f"""Break this goal into 2-4 short, concrete steps.
Goal: {goal}

Reply as JSON: {{"steps": ["...", "..."]}}""")
    return plan["steps"]


def execute(step, notes):
    return react_agent(f"{step}\n\nWhat we already know:\n{notes or 'nothing yet'}")


def summarize(goal, notes):
    return ask(f"Goal: {goal}\n\nFindings:\n{notes}\n\nWrite the final answer in 2-3 sentences.")


def run(goal):
    steps = make_plan(goal)

    notes = ""
    for step in steps:
        result = execute(step, notes)
        notes += f"- {step}: {result}\n"

    return summarize(goal, notes)


if __name__ == "__main__":
    print(run("Compare Milad Tower and the Eiffel Tower: how much taller is one, and how many years apart did they open?"))
