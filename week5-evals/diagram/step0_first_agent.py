# Step 0 — The first diagram agent
# The week 1 loop, one big tool and a short, friendly prompt.
# Ask for a simple flow. The agent says "Done!". Then look at the canvas:
# draw() shows what Excalidraw really draws from the elements it sent.
from agent import run_agent
from canvas import draw, summarize
from prompts import FIRST
from tools import CANVAS, generate_diagram, modify_diagram, new_canvas

TOOLS = [generate_diagram, modify_diagram]


def run(task):
    new_canvas()
    messages = [
        {"role": "system", "content": FIRST},
        {"role": "user", "content": task},
    ]
    answer = run_agent(messages, TOOLS)

    seen = draw(CANVAS)    # what the user sees
    return f"The agent says: {answer}\n\nWhat the user sees:\n{summarize(seen)}"


if __name__ == "__main__":
    print(run("Draw a flow from User to API to Database"))
