# Getaway Alert ✈️🚆

A light, automated Python tool to scan budget flights (Ryanair, Wizz Air) and train options for quick getaway trips, cross-checking availability against local Apple Calendar database entries.

## Features

- **Multi-Source Scan:** Scans Ryanair, Wizz Air, and European rail connections (iRail / Eurostar) for quick getaways.
- **YAML Configuration & Environment Variables:** Fully configurable via `config.yaml` or environment variables for secret management.
- **Local Calendar Integration:** Queries macOS `Calendar.sqlitedb` directly (read-only SQLite query) to automatically flag busy days in alerts.
- **Price Trend Tracking:** Keeps track of previous deal prices in `deals_state.json` to highlight price drops (🚨) or increases (📈).
- **Push Notifications:** Sends daily summaries straight via Pushover.

## Setup & Usage

1. **Configuration File (`config.yaml`):**
   Copy `config.example.yaml` to `config.yaml`:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. **API Keys / Secrets:**
   Set API keys in your environment variables (recommended) or optionally inside `config.yaml`:
   ```bash
   export PUSHOVER_TOKEN="your_pushover_token_here"
   export PUSHOVER_USER="your_pushover_user_key_here"
   export KIWI_TEQUILA_API_KEY="your_kiwi_api_key_here"
   ```
   *Note: Environment variables automatically override values in `config.yaml` to prevent accidental credential commits.*

3. **Run the script:**
   ```bash
   python3 getaway.py
   ```

## Customizing Routes & Parameters

Customize travel settings, departure hubs, and destinations in `config.yaml`:

```yaml
max_flight_leg_price: 30.0
max_train_leg_price: 35.0

airports:
  CRL: "Charleroi"
  BRU: "Brussels"
  EIN: "Eindhoven"

train_stations:
  Brussels-Central: "Brussels"
  Antwerpen-Centraal: "Antwerp"

train_destinations:
  - "Amsterdam-Centraal"
  - "Paris-Nord"
  - "Rotterdam-Centraal"
```
