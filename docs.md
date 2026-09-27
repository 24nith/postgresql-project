# Default agent instructions

Diagnose errors using the actual build, test, deployment, and user-provided output. Make at most one focused code repair, rerun available checks once, and report the final result. Never invent, hardcode, or hide missing API keys, database URLs, passwords, or other environment configuration; identify the exact variable and tell the user to set it in the target service's Render Environment.
