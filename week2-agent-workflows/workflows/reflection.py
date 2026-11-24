# Reflection: the model reviews its own work and improves it.
# Draft -> critique -> revise, until the critique finds nothing to fix.
#
# Who decides what happens next?  The model decides when it is done,
# and the code sets the maximum number of rounds.
from llm import ask

MAX_ROUNDS = 3


def draft(task):
    return ask(task)


def critique(task, text):
    return ask(f"""Task: {task}

Answer:
{text}

Critique this answer. List concrete problems.
If it is already excellent, reply with exactly: LGTM""")


def revise(task, text, feedback):
    return ask(f"Task: {task}\n\nAnswer:\n{text}\n\nFeedback:\n{feedback}\n\nRewrite the answer to fix every point.")


def run(task):
    text = draft(task)

    for round in range(MAX_ROUNDS):
        feedback = critique(task, text)
        if "LGTM" in feedback:
            break
        text = revise(task, text, feedback)

    return text


if __name__ == "__main__":
    print(run("Explain what an AI agent is to a high-school student, in 3 sentences."))
