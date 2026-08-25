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

2. **API Keys / Secrets Setup:**
   An API key acts as a secure credential required to access external services (such as Pushover or Kiwi).

   - **Pushover Keys (`PUSHOVER_TOKEN` & `PUSHOVER_USER`):**
     1. Create a free account at [pushover.net](https://pushover.net) to find your **User Key**.
     2. Create a new Application on the dashboard to generate your **Application Token**.
   - **Kiwi Tequila API Key (`KIWI_TEQUILA_API_KEY`):**
     1. Register a free developer account at [tequila.kiwi.com](https://tequila.kiwi.com/).
     2. Navigate to **My Products** -> **Create Solution** (select Search API) to generate a free API key.

   Set these keys in your environment variables (recommended) or inside `config.yaml`:
   ```bash
   export PUSHOVER_TOKEN="your_pushover_app_token_here"
   export PUSHOVER_USER="your_pushover_user_key_here"
   export KIWI_TEQUILA_API_KEY="your_kiwi_tequila_api_key_here"
   ```
   *Note: Environment variables automatically override values in `config.yaml` to prevent accidental credential commits to public repositories.*

3. **Run the script:**
   ```bash
   python3 getaway.py
   ```

## Station & Airport Syntax Explained

Station dictionaries use a `Key: "Value"` structure:
```yaml
train_stations:
  Brussels-Central: "Brussels"
  Antwerpen-Centraal: "Antwerp"
```
- **Key (left, e.g. `Brussels-Central`):** The exact API query name recognized by railway APIs (e.g. iRail).
- **Value (right, e.g. `"Brussels"`):** The clean, human-readable label shown in your alert notifications.

### How to find official station query names:
The iRail API accepts standard station names as typed on the NMBS/SNCB website. You can inspect the complete list of supported European stations directly by visiting:
`https://api.irail.be/stations/?format=json`
