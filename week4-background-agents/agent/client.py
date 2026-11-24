# client.py — the one Inngest client every step uses.
#
# is_production=False talks to the Inngest Dev Server on your machine
# (npx inngest-cli@latest dev). No account, no cloud.
import inngest

client = inngest.Inngest(app_id="incident-agent", is_production=False)
