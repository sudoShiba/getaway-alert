# Getaway Alert ✈️🚆

A light, automated Python tool to scan budget flights (Ryanair, Wizz Air) and train options for quick getaway trips, cross-checking availability against local Apple Calendar database entries.

## Features

- **Multi-Airline Fare Finder:** Scans Ryanair and Wizz Air APIs for cheap round trips and open-jaw connections (sub-€30/leg).
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
   export PUSHOVER_TOKEN="your_token_here"
   export PUSHOVER_USER="your_user_key_here"
   ```

2. Run the script:
   ```bash
   python3 getaway.py
   ```

## Configuration

You can tweak top-level parameters in `getaway.py`:
- `MAX_PER_LEG`: Max price threshold per flight leg (default: €30.0)
- `LOOKAHEAD_DAYS`: Days ahead to check (default: 35)
- `AIRPORTS`: Dict of origin/destination airport IATA codes (CRL, BRU, EIN, etc.)
