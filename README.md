# Getaway Alert ✈️🚆

A light, automated Python tool to scan budget flights (Ryanair, Wizz Air) and train options for quick getaway trips, cross-checking availability against local Apple Calendar database entries.

## Features

- **Multi-Source Scan:** Scans Ryanair, Wizz Air, and European rail connections (iRail / Eurostar) for quick getaways.
- **Configurable Hubs:** Easily configure home airports (`AIRPORTS`) and departure train stations (`TRAIN_STATIONS`) via top-level dictionary constants.
- **Local Calendar Integration:** Queries macOS `Calendar.sqlitedb` directly (read-only SQLite query) to automatically flag busy days in alerts.
- **Price Trend Tracking:** Keeps track of previous deal prices in `deals_state.json` to highlight price drops (🚨) or increases (📈).
- **Push Notifications:** Sends daily summaries straight via Pushover CLI / API.

## Requirements

- Python 3.10+ (Standard library only; no extra `pip` requirements needed).
- macOS (if you want the SQLite Apple Calendar availability check).
- Pushover account (optional, for notifications).

## Usage

1. Set your Pushover credentials in environment variables (optional):
   ```bash
   export PUSHOVER_TOKEN="your_pushover_app_token"
   export PUSHOVER_USER="your_user_key_here"
   ```

2. Run the script:
   ```bash
   python3 getaway.py
   ```

## Configuration

You can fully customize airport and station hubs at the top of `getaway.py`:
```python
AIRPORTS = {
    "CRL": "Charleroi",
    "BRU": "Brussels",
    "EIN": "Eindhoven",
    "LIL": "Lille",
    "ANR": "Antwerp",
}

TRAIN_STATIONS = {
    "Brussels-Central": "Brussels",
    "Antwerpen-Centraal": "Antwerp",
}

TRAIN_DESTINATIONS = [
    "Amsterdam-Centraal",
    "Paris-Nord",
    "Rotterdam-Centraal",
]
```
