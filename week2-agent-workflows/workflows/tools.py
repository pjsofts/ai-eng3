# tools.py — pretend APIs the workflows call.
# They are plain Python functions. The docstring is what the model reads.

FACTS = {
    "eiffel tower": "The Eiffel Tower opened in 1889 in Paris. It is 330 m tall "
                    "and was built by the company of Gustave Eiffel.",
    "gustave eiffel": "Gustave Eiffel was a French engineer, born in 1832 in Dijon.",
    "milad tower": "Milad Tower in Tehran opened in 2007. It is 435 m tall.",
    "tehran": "Tehran is the capital of Iran, with about 9.5 million people.",
    "istanbul": "Istanbul is the largest city in Turkey, with about 15.7 million people.",
}


def search(query: str) -> str:
    """Search an encyclopedia. Use a short query such as 'Milad Tower'."""
    query = query.lower()
    hits = [fact for topic, fact in FACTS.items() if topic in query]
    if not hits:  # no exact topic: fall back to any matching word
        hits = [fact for topic, fact in FACTS.items()
                if any(word in query.split() for word in topic.split())]
    return "\n".join(hits) or "No results."


def calculate(expression: str) -> str:
    """Evaluate a math expression such as '435 - 330' or '15.7 / 9.5'."""
    return str(eval(expression, {"__builtins__": {}}))  # demo only, never eval untrusted input


def search_flights(destination: str) -> str:
    """Find flights from Tehran to a destination city."""
    return f"Tehran -> {destination}: Iran Air 08:00, 1h 05m, 2.1M toman. Bus: 6h, 0.6M toman."


def search_hotels(city: str) -> str:
    """Find hotels in a city, cheapest first."""
    return f"{city}: Saraye Ameri (traditional, 1.8M/night), Abbasi Hotel (historic, 6.5M/night)."


def find_restaurants(city: str) -> str:
    """Find well-known local restaurants in a city."""
    return f"{city}: Shahrzad (classic Persian), Azam Beryani (local beryani, cheap)."


def lookup_invoice(customer_id: str) -> str:
    """Look up the latest invoice for a customer."""
    return (f"Customer {customer_id}: Sep 1, Pro plan $49, charged TWICE (duplicate). "
            f"Oct 1 renewal FAILED (card expired), plan downgraded to Free.")


def check_api_logs(customer_id: str) -> str:
    """Check recent API errors for a customer."""
    return f"Customer {customer_id}: 403 'plan does not include API access' since Oct 1."


def issue_refund(customer_id: str, amount: str) -> str:
    """Refund an amount to a customer."""
    return f"Refunded {amount} to customer {customer_id}."
