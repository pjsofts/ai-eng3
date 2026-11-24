# Routing: one LLM call classifies the input,
# then the code sends it to the right specialist.
#
# Who decides what happens next?  The model picks the path,
# but only from the paths the code allows.
from llm import ask, ask_json

SPECIALISTS = {
    "billing": "You are a billing specialist. Be precise and brief.",
    "technical": "You are a senior support engineer. Give 3 short debugging steps.",
    "account": "You handle logins and account security. Be brief. Never ask for a password.",
}


def classify(ticket):
    return ask_json(f"""Classify this support ticket.
Categories: billing, technical, account, other

Ticket: {ticket}

Reply as JSON: {{"category": "...", "reason": "..."}}""")


def handle(category, ticket):
    return ask(ticket, system=SPECIALISTS[category])


def escalate_to_human(ticket):
    return "I've passed your message to a human colleague. They'll reply within a day."


def run(ticket):
    route = classify(ticket)
    category = route["category"]

    if category not in SPECIALISTS:  # always have a safe fallback
        return escalate_to_human(ticket)

    return handle(category, ticket)


if __name__ == "__main__":
    print(run("I was charged twice for my subscription this month."))
