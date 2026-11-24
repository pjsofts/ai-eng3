# Step 1 — Just an LLM
# One question in, one answer out. This is NOT an agent yet:
# no tools (it can't look at anything), no loop, no memory.
# Ask it something it can only know by looking, and watch it fail.
from llm import ask


def run(question):
    return ask(question)


if __name__ == "__main__":
    print(run("What time is it right now, and what files are in my folder?"))
