---
name: webapp-testing
description: Run automated tests or interactions on a web application using Playwright.
---

# 🌐 Web App Testing Skill

This skill provides a structured way to perform automated testing and interaction on web applications using Playwright. It includes helpers for running tests with local development servers and common debugging patterns.

## 🛠 Features

- **Local Server Lifecycle**: Start and stop development servers (e.g., `npm run dev`) automatically during tests.
- **Port Management**: Ensure ports are available and wait for servers to be ready.
- **Reconnaissance**: Discover interactive elements and capture console logs/network requests.
- **Visual Validation**: Capture screenshots and compare UI states across different environments.

## 🚀 Usage

### 1. Basic Integration

Ensure `playwright` is installed in your environment:

```bash
pip install playwright
playwright install chromium
```

### 2. Running with a Development Server

Use the included `with_server.py` script to wrap your test execution. This ensures the server is running before the tests start and is cleaned up afterward.

```bash
python3 scripts/with_server.py --server "npm run dev" --port 5173 -- python3 tests/my_test.py
```

### 3. Debugging Patterns

- **Element Discovery**: Use the `element_discovery.py` example to map out clickable elements on a page.
- **Console Monitoring**: Capture and filter browser console logs for errors.

## 📂 Directory Structure

- `scripts/`: Utility scripts for environment management.
- `examples/`: Reference implementations for common testing tasks.
- `SKILL.md`: This documentation.

## ⚠️ Requirements

- Python 3.8+
- Playwright
- Chromium (or other supported browsers)
