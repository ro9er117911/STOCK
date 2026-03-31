---
description: Run automated tests or interactions on a web application using Playwright.
---

1. Ensure `playwright` is installed:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. Use the `webapp-testing` skill to perform automation. You can reference the skill documentation in [.agent/skills/webapp-testing/SKILL.md](file:///Users/ro9air/STOCK/.agent/skills/webapp-testing/SKILL.md).

3. To run a test with a local development server:
// turbo
   ```bash
   python3 .agent/skills/webapp-testing/scripts/with_server.py --server "npm run dev" --port 5173 -- python3 path/to/your_test_script.py
   ```

4. For reconnaissance and element discovery, use the provided examples:
   - [.agent/skills/webapp-testing/examples/element_discovery.py](file:///Users/ro9air/STOCK/.agent/skills/webapp-testing/examples/element_discovery.py)
   - [.agent/skills/webapp-testing/examples/console_logging.py](file:///Users/ro9air/STOCK/.agent/skills/webapp-testing/examples/console_logging.py)