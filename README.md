# Newtonite Operations Workboard

A lightweight web app for managing operational work items with team-based authorization, item history, and stale-update protection.

## Features

- create operational work items
- view items by team and assignee
- assign ownership and priority
- track status changes and history
- enforce server-side authorization checks
- reject stale updates with a version conflict
- keep work visible and easy to review

## Tech stack

- Python 3.11+
- Flask
- SQLite
- HTML/CSS/JS
- pytest

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:
   
   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:
   
   ```bash
   python app.py
   ```

4. Open http://localhost:5000 in a browser.

## Testing

```bash
pytest -q
```

## Notes

This solution keeps the app simple but deliberately focuses on the challenge's risk areas: authorization, concurrency, history, and operational usability.
