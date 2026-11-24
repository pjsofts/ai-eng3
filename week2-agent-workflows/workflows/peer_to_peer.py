# Peer-to-peer: agents hand the conversation directly to each other.
# There is no manager. Each agent decides whether to answer
# or pass the case to a peer, along with what it found.
#
# Who decides what happens next?  Whichever agent holds the case.
from agent import Agent
from tools import check_api_logs, lookup_invoice

HANDOFF_RULE = """If another teammate should take over, reply with exactly:
HANDOFF: <teammate> | <what you found>
Otherwise, answer the customer directly."""

agents = {
    "triage": Agent("triage", f"""You are the first contact. Teammates: billing, technical.
Do not solve problems yourself. {HANDOFF_RULE}"""),
    "technical": Agent("technical", f"""You are a support engineer. Teammates: billing.
{HANDOFF_RULE}""", tools=[check_api_logs]),
    "billing": Agent("billing", f"""You are a billing specialist. Teammates: technical.
{HANDOFF_RULE}""", tools=[lookup_invoice]),
}
MAX_HANDOFFS = 4


def run(message):
    current = "triage"
    case = f"Customer message: {message}"

    for hop in range(MAX_HANDOFFS):
        reply = agents[current].run(case)

        if not reply.startswith("HANDOFF:"):
            return reply  # this agent answered the customer

        target, found = reply.removeprefix("HANDOFF:").split("|", 1)
        case += f"\n{current} found: {found.strip()}"
        current = target.strip().lower()

    return "Sorry, we could not resolve this. A human will contact you."


if __name__ == "__main__":
    print(run("I'm customer 4521. Our API stopped working right after our subscription renewed."))
