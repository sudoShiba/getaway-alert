#!/usr/bin/env python3
import datetime as dt
import json
import os
import sqlite3
import subprocess
import urllib.error
import urllib.parse
import urllib.request

RYANAIR_OW = "https://www.ryanair.com/api/farfnd/v4/oneWayFares"
WIZZ_HOME = "https://www.wizzair.com/"
WIZZ_BASE = "https://be.wizzair.com/{version}/Api"

AIRPORTS = {
    "CRL": "Charleroi",
    "BRU": "Brussels",
    "EIN": "Eindhoven",
    "LIL": "Lille",
    "ANR": "Antwerp",
    "OST": "Ostend",
    "MST": "Maastricht",
}

MAX_PER_LEG = 30.0
LOOKAHEAD_DAYS = 35
TRIP_MIN = 0
TRIP_MAX = 2
DEAL_CAP = 10

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "deals_state.json")

PUSHOVER_TOKEN = os.environ.get("PUSHOVER_TOKEN", "")
PUSHOVER_USER = os.environ.get("PUSHOVER_USER", "")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/json"}

EXCLUDED_CALENDARS = {
    "Holidays in Belgium", "Feestdagen in België", "Birthdays",
    "Facebook Birthdays", "Siri Suggestions", "Scheduled Reminders",
    "Found in Mail", "Found in Natural Language",
    "Privé", "Gezin", "Werk", "Work", "Home", "Agenda", "iPhone",
    "Free time/travel", "KU Leuven Kalender", "Informatica KUL", "ULYSSIS",
}

CORE_DATA_EPOCH = 978307200
CALENDAR_DB = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.calendar/Calendar.sqlitedb"
)


def get_json(url, headers=None, data=None, timeout=60, opener=None):
    req = urllib.request.Request(url, headers=headers or HEADERS, data=data,
                                 method="POST" if data is not None else "GET")
    if opener is None:
        ctx = urllib.request.urlopen(req, timeout=timeout)
    else:
        ctx = opener.open(req, timeout=timeout)
    with ctx as response:
        return json.load(response)


def ryanair_one_way(origin, start, end):
    params = {
        "departureAirportIataCode": origin,
        "outboundDepartureDateFrom": start.isoformat(),
        "outboundDepartureDateTo": end.isoformat(),
        "currency": "EUR",
    }
    data = get_json(RYANAIR_OW + "?" + urllib.parse.urlencode(params))
    return data.get("fares", []) or []


def wizz_round_trips(start, end):
    results = []
    cj = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cj)

    home_req = urllib.request.Request(WIZZ_HOME, headers={"User-Agent": UA})
    try:
        with opener.open(home_req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return results

    ver_match = re.search(r'https://be\.wizzair\.com/([^/]+)/Api', html)
    token_match = re.search(r'RequestVerificationToken["\']\s*:\s*["\']([^"\']+)["\']', html)
    if not ver_match or not token_match:
        return results

    version = ver_match.group(1)
    token = token_match.group(1)

    map_url = WIZZ_BASE.format(version=version) + "/asset/map?languageCode=en-gb"
    try:
        map_data = get_json(map_url, headers={"User-Agent": UA, "Origin": WIZZ_HOME,
                                              "Referer": WIZZ_HOME}, opener=opener)
    except Exception:
        return results

    cities = {c.get("iata"): c for c in map_data.get("cities", [])}
    origin_cities = ["CRL", "EIN", "MST"]

    outbound_routes = []
    for origin in origin_cities:
        for conn in cities.get(origin, {}).get("connections", []) or []:
            dest = conn.get("iata")
            if dest:
                outbound_routes.append((origin, dest))

    for origin, dest in outbound_routes:
        for ret_origin in AIRPORTS.keys():
            dest_conns = [d.get("iata") for d in cities.get(dest, {}).get("connections", []) or []]
            if ret_origin not in dest_conns:
                continue

            payload = {
                "flightList": [
                    {"departureStation": origin, "arrivalStation": dest,
                     "from": start.isoformat(), "to": end.isoformat()},
                    {"departureStation": dest, "arrivalStation": ret_origin,
                     "from": start.isoformat(),
                     "to": (end + dt.timedelta(days=TRIP_MAX)).isoformat()},
                ],
                "priceType": "regular",
                "adultCount": 1,
                "childCount": 0,
                "infantCount": 0
            }
            headers = {
                "User-Agent": UA,
                "Origin": WIZZ_HOME,
                "Referer": WIZZ_HOME + "en-gb/flights/search",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json;charset=UTF-8",
                "x-requestverificationtoken": token
            }
            try:
                data = get_json(WIZZ_BASE.format(version=version) + "/search/timetable",
                                headers=headers, data=json.dumps(payload).encode(),
                                timeout=45, opener=opener)
                for out in data.get("outboundFlights", []) or []:
                    for ret in data.get("returnFlights", []) or []:
                        od = dt.date.fromisoformat(out["departureDate"][:10])
                        rd = dt.date.fromisoformat(ret["departureDate"][:10])
                        if not (TRIP_MIN <= (rd - od).days <= TRIP_MAX):
                            continue
                        po = float((out.get("price") or {}).get("amount", 0) or 0)
                        pi = float((ret.get("price") or {}).get("amount", 0) or 0)
                        if not (0 < po < MAX_PER_LEG and 0 < pi < MAX_PER_LEG):
                            continue
                        results.append(make_deal("Wizz Air", out, ret, po, pi, origin, dest))
            except Exception:
                continue
    return results


def make_deal(airline, out, ret, po, pi, origin=None, destination=None):
    out_air = out.get("departureAirport") or {"iataCode": origin, "name": origin}
    arr_air = out.get("arrivalAirport") or {"iataCode": destination, "name": destination}
    ret_dep = ret.get("departureAirport") or {"iataCode": destination, "name": destination}
    ret_arr = ret.get("arrivalAirport") or {"iataCode": origin, "name": origin}
    return {
        "airline": airline, "out": out, "ret": ret, "po": po, "pi": pi,
        "total": round(po + pi, 2), "out_air": out_air, "arr_air": arr_air,
        "ret_dep": ret_dep, "ret_arr": ret_arr,
        "dep_date": dt.date.fromisoformat(out["departureDate"][:10]),
        "ret_date": dt.date.fromisoformat(ret["departureDate"][:10])
    }


def route_key(deal):
    out, ret = deal["out"], deal["ret"]
    on = out.get("flightNumber") or (out.get("departureStation", "") + "-" + out.get("arrivalStation", ""))
    rn = ret.get("flightNumber") or (ret.get("departureStation", "") + "-" + ret.get("arrivalStation", ""))
    return "|".join([deal["airline"], on, rn, out.get("departureDate", ""), ret.get("departureDate", "")])


def _local_datetime(core_ts):
    return dt.datetime.fromtimestamp(core_ts + CORE_DATA_EPOCH).astimezone()


def _core_ts(local_dt):
    return local_dt.astimezone(dt.timezone.utc).timestamp() - CORE_DATA_EPOCH


def fetch_calendar_map(dates):
    if not dates:
        return {}, None
    wanted = set(dates)
    start_local = dt.datetime.fromisoformat(min(dates))
    end_local = dt.datetime.fromisoformat(max(dates)) + dt.timedelta(days=1)
    s, e = _core_ts(start_local), _core_ts(end_local)
    
    if not os.path.exists(CALENDAR_DB):
        return {}, None

    try:
        con = sqlite3.connect(f"file:{CALENDAR_DB}?mode=ro", uri=True, timeout=10)
    except Exception as exc:
        return None, str(exc)
    try:
        cur = con.cursor()
        rows = cur.execute("""
            SELECT i.summary, i.start_date, i.end_date, i.all_day, c.title
            FROM CalendarItem i
            JOIN Calendar c ON c.ROWID = i.calendar_id
            WHERE i.has_recurrences = 0
              AND i.start_date < ? AND i.end_date > ?
        """, (e, s)).fetchall()
        rows += cur.execute("""
            SELECT i.summary, oc.occurrence_start_date, oc.occurrence_end_date,
                   i.all_day, c.title
            FROM OccurrenceCache oc
            JOIN CalendarItem i ON i.ROWID = oc.event_id
            JOIN Calendar c ON c.ROWID = oc.calendar_id
            WHERE oc.occurrence_start_date < ? AND oc.occurrence_end_date > ?
        """, (e, s)).fetchall()

        mapping = {}
        for summary, start_ts, end_ts, all_day, cal_title in rows:
            if cal_title in EXCLUDED_CALENDARS:
                continue
            start_dt = _local_datetime(start_ts)
            end_dt = _local_datetime(end_ts)
            day = start_dt.date()
            last = end_dt.date()
            while day <= last:
                if day.isoformat() in wanted:
                    label = f"{cal_title} | {summary} | {start_dt.strftime('%a %-d %b %H:%M')} - {end_dt.strftime('%a %-d %b %H:%M')}"
                    mapping.setdefault(day.isoformat(), []).append(label)
                day += dt.timedelta(days=1)
        return mapping, None
    except Exception as exc:
        return None, str(exc)
    finally:
        con.close()


def clock(iso):
    return dt.datetime.fromisoformat(iso).strftime("%a %-d %b %H:%M")


def airport_name(airport, fallback="?"):
    return (airport or {}).get("name") or AIRPORTS.get((airport or {}).get("iataCode"), fallback)


def get_utility(deal):
    out_dep = dt.datetime.fromisoformat(deal["out"]["departureDate"][:19])
    ret_arr = dt.datetime.fromisoformat(deal["ret"].get("arrivalDate", deal["ret"]["departureDate"])[:19])
    stay_hours = (ret_arr - out_dep).total_seconds() / 3600

    if 10 <= stay_hours <= 20:
        return "☀️ Day Trip"
    elif stay_hours > 20:
        return "📅 Multi-day"
    else:
        return "⏱️ Short/Quick"


def format_deal(deal, cal_map, cal_error):
    out, ret = deal["out"], deal["ret"]
    busy_lines = []
    current = deal["dep_date"]
    while current <= deal["ret_date"]:
        if cal_map is not None:
            busy_lines.extend(cal_map.get(current.isoformat(), []))
        current += dt.timedelta(days=1)

    seen_busy = set()
    unique_busy = []
    for bl in busy_lines:
        norm = bl.split(" | ", 1)[-1]
        if norm not in seen_busy:
            seen_busy.add(norm)
            unique_busy.append(bl)
    busy_lines = unique_busy

    if cal_map is None:
        prefix = "✅ FREE?"
    elif busy_lines:
        prefix = "❌ busy"
    else:
        prefix = "✅ FREE"

    utility = get_utility(deal)

    oa = out.get("departureAirport") or deal["out_air"]
    aa = out.get("arrivalAirport") or deal["arr_air"]
    ra = ret.get("departureAirport") or deal["ret_dep"]
    za = ret.get("arrivalAirport") or deal["ret_arr"]
    route = f"{oa.get('iataCode', '?')} → {aa.get('iataCode', '?')} ({airport_name(aa)})"
    lines = [
        f"{prefix} | {route} | {utility}",
        f"🛫 Out: {clock(out['departureDate'])} {oa.get('iataCode', '?')} → {clock(out.get('arrivalDate', out['departureDate']))} {aa.get('iataCode', '?')}",
        f"🛬 Ret: {clock(ret['departureDate'])} {ra.get('iataCode', '?')} → {clock(ret.get('arrivalDate', ret['departureDate']))} {za.get('iataCode', '?')}",
        f"💰 €{deal['po']:.2f} + €{deal['pi']:.2f} = €{deal['total']:.2f}"
    ]
    if busy_lines:
        lines.append("❌ busy: " + " ; ".join(busy_lines[:2]))
    elif cal_error:
        lines.append("⚠️ calendar availability unknown: " + cal_error[:100])
    return "\n".join(lines)


def load_state():
    try:
        with open(STATE_FILE) as f:
            val = json.load(f)
        return val if isinstance(val, dict) else {}
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def pushover(title, message):
    if not PUSHOVER_TOKEN or not PUSHOVER_USER:
        print(f"[{title}]\n{message}")
        return
    cmd = ["curl", "-sS", "-F", f"token={PUSHOVER_TOKEN}", "-F", f"user={PUSHOVER_USER}",
           "-F", f"title={title}", "-F", f"message={message}",
           "https://api.pushover.net/1/messages.json"]
    subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def main():
    start = dt.date.today() + dt.timedelta(days=1)
    end = start + dt.timedelta(days=LOOKAHEAD_DAYS)
    deals, errors = [], []
    all_out = []
    all_in = []

    for origin in AIRPORTS.keys():
        try:
            outbound_fares = ryanair_one_way(origin, start, end)
            for fare in outbound_fares:
                if not fare.get("outbound"):
                    continue
                d = fare["outbound"]
                if d.get("departureDate", "")[11:19] == "00:00:00":
                    continue
                po = float(d["price"]["value"])
                if po >= MAX_PER_LEG:
                    continue
                arr_iata = d.get("arrivalAirport", {}).get("iataCode")
                if not arr_iata:
                    continue
                all_out.append({
                    "origin": origin,
                    "dest": arr_iata,
                    "date": dt.date.fromisoformat(d["departureDate"][:10]),
                    "fare_data": d,
                    "price": po
                })
        except Exception as exc:
            errors.append(f"Ryanair outbound ({origin}): {exc}")

    destinations_found = list(set([x["dest"] for x in all_out]))

    for dest in destinations_found:
        try:
            inbound_fares = ryanair_one_way(dest, start, end + dt.timedelta(days=TRIP_MAX))
            for fare in inbound_fares:
                if not fare.get("outbound"):
                    continue
                d = fare["outbound"]
                if d.get("departureDate", "")[11:19] == "00:00:00":
                    continue
                pi = float(d["price"]["value"])
                if pi >= MAX_PER_LEG:
                    continue
                arr_iata = d.get("arrivalAirport", {}).get("iataCode")
                if arr_iata not in AIRPORTS:
                    continue
                all_in.append({
                    "origin": dest,
                    "dest": arr_iata,
                    "date": dt.date.fromisoformat(d["departureDate"][:10]),
                    "fare_data": d,
                    "price": pi
                })
        except Exception as exc:
            errors.append(f"Ryanair inbound ({dest}): {exc}")

    for out in all_out:
        for inc in all_in:
            if out["dest"] != inc["origin"]:
                continue
            trip_days = (inc["date"] - out["date"]).days
            if not (TRIP_MIN <= trip_days <= TRIP_MAX):
                continue
            deal = make_deal("Ryanair", out["fare_data"], inc["fare_data"],
                             out["price"], inc["price"],
                             origin=out["origin"], destination=out["dest"])
            if deal:
                deals.append(deal)

    try:
        deals.extend(wizz_round_trips(start, end))
    except Exception as exc:
        errors.append("Wizz Air: " + str(exc))

    def looks_fake(deal):
        out, ret = deal["out"], deal["ret"]
        if out.get("departureDate", "")[11:19] == "00:00:00" or ret.get("departureDate", "")[11:19] == "00:00:00":
            return True
        if deal["dep_date"] == deal["ret_date"]:
            return True
        return False

    deals = [d for d in deals if not looks_fake(d)]

    state = load_state()
    unique = {}
    for deal in deals:
        r_key = route_key(deal)
        if r_key not in unique or deal["total"] < unique[r_key]["total"]:
            unique[r_key] = deal

    all_deals = list(unique.values())

    for deal in all_deals:
        r_key = route_key(deal)
        last_price = state.get(r_key, {}).get("price")
        diff = round(deal["total"] - last_price, 2) if last_price is not None else 0.0
        deal["diff"] = diff
        state[r_key] = {"price": deal["total"], "last_seen": dt.date.today().isoformat()}

    save_state(state)

    def sort_logic(d):
        if d['diff'] <= -5.0:
            return (0, -d['diff'], d['total'])
        if d['diff'] >= 5.0:
            return (2, d['diff'], d['total'])
        return (1, abs(d['diff']), d['total'])

    all_deals.sort(key=sort_logic)

    dates = set()
    for d in all_deals:
        cur = d["dep_date"]
        while cur <= d["ret_date"]:
            dates.add(cur.isoformat())
            cur += dt.timedelta(days=1)

    cal_map, cal_error = fetch_calendar_map(dates) if dates else (None, None)

    chunks = []
    for d in all_deals[:DEAL_CAP]:
        diff_info = ""
        if d['diff'] <= -5.0:
            diff_info = f"🚨 Price drop: {abs(d['diff']):.2f} "
        elif d['diff'] >= 5.0:
            diff_info = f"📈 Price hike: +{d['diff']:.2f} "
        elif d['diff'] != 0:
            diff_info = f"⚖️ Price change: {d['diff']:.2f} "

        line = f"{diff_info}{format_deal(d, cal_map, cal_error)}"
        chunks.append(line)

    if chunks:
        message = "\n\n".join(chunks)
        if errors:
            message += "\n\n⚠️ Source errors: " + " ; ".join(errors)[:350]
        pushover("✈️ Getaway Alert", message)
    elif errors:
        message = "⚠️ Getaway Alert source errors:\n" + "\n".join(errors)
        pushover("✈️ Getaway Alert", message)
    else:
        message = "🛫 No deals found today — the skies are quiet."
        pushover("✈️ Getaway Alert", message)


if __name__ == "__main__":
    main()
