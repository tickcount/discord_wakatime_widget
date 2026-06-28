import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request


WAKATIME_STATS_URL = "https://api.wakatime.com/api/v1/users/current/stats/last_7_days"
DISCORD_PROFILE_URL = (
    "https://discord.com/api/v9/applications/{application_id}"
    "/users/{user_id}/identities/0/profile"
)
REQUEST_TIMEOUT_SECONDS = 30


def log_step(message):
    print(f"[step] {message}")


def print_json(title, payload):
    print(f"[json] {title}:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def is_debug_wakatime_json_enabled():
    return os.environ.get("DEBUG_WAKATIME_JSON") == "1"


def require_env(name):
    log_step(f"Reading {name} from environment")
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def compact_number(value):
    value = int(value or 0)
    for suffix, threshold in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if value >= threshold:
            number = f"{value / threshold:.1f}".rstrip("0").rstrip(".")
            return f"{number}{suffix}"
    return str(value)


def compact_lower_number(value):
    return compact_number(value).lower()


def get_number(data, name):
    value = data.get(name, 0)
    return value if isinstance(value, (int, float)) else 0


def best_ai_agent_by_cost(stats):
    agents = stats.get("ai_agent_breakdown") or []
    if not agents:
        return "Unknown \u00b7 0 LOC"

    agent = max(agents, key=lambda item: get_number(item, "cost"))
    return f"{agent.get('name', 'Unknown')} \u00b7 {compact_lower_number(get_number(agent, 'lines'))} LOC"


def format_peak_hours(stats):
    best_day = stats.get("best_day") or {}
    total_seconds = get_number(best_day, "total_seconds")
    peak_hours = int((total_seconds + 3599) // 3600) if total_seconds else 0
    return f"{peak_hours}h+ peak"


def request_json(url, headers, method="GET", body=None):
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            text = response.read().decode("utf-8")
            if not text:
                return response.status, {}
            return response.status, json.loads(text)
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8")
        if not text:
            return error.code, {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"error": text}
        return error.code, payload


def fetch_wakatime_stats(api_key):
    log_step("Preparing WakaTime Basic Auth header")
    basic = base64.b64encode(api_key.encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {basic}",
        "Accept": "application/json",
        "User-Agent": "Discord WakaTime Widget",
    }

    for attempt in range(1, 6):
        log_step(f"Requesting WakaTime stats, attempt {attempt}/5")
        status, payload = request_json(WAKATIME_STATS_URL, headers)
        log_step(f"WakaTime response status: HTTP {status}")
        if is_debug_wakatime_json_enabled():
            print_json("WakaTime response", payload)

        data = payload.get("data") or {}

        if status == 200 and data.get("status") == "ok":
            log_step("WakaTime stats are ready")
            return data

        if status == 202 or data.get("status") == "pending_update":
            timeout = int(data.get("timeout") or 15)
            log_step(f"WakaTime stats are pending, waiting {min(timeout, 60)} seconds")
            time.sleep(min(timeout, 60))
            continue

        raise RuntimeError(f"WakaTime API error {status}: {json.dumps(payload)}")

    raise RuntimeError("WakaTime stats are still pending_update after retries")


def build_discord_payload(stats):
    log_step("Building Discord widget payload from WakaTime stats")

    return {
        "data": {
            "dynamic": [
                {"type": 1, "name": "stat_1_name", "value": "WakaTime"},
                {"type": 1, "name": "stat_1_value", "value": "Activity Overview"},
                {"type": 1, "name": "stat_2_name", "value": "7 Days"},
                {
                    "type": 1,
                    "name": "stat_2_value",
                    "value": stats.get("human_readable_total", ""),
                },
                {"type": 1, "name": "stat_3_name", "value": "Daily Average"},
                {
                    "type": 1,
                    "name": "stat_3_value",
                    "value": f"{stats.get('human_readable_daily_average', '')} \u00b7 {format_peak_hours(stats)}",
                },
                {"type": 1, "name": "stat_4_name", "value": "AI Coding"},
                {"type": 1, "name": "stat_4_value", "value": best_ai_agent_by_cost(stats)},
                {"type": 1, "name": "stat_5_name", "value": "Tokens"},
                {
                    "type": 1,
                    "name": "stat_5_value",
                    "value": (
                        f"{compact_number(get_number(stats, 'ai_input_tokens'))} in "
                        f"\u00b7 {compact_number(get_number(stats, 'ai_output_tokens'))} out"
                    ),
                },
                {"type": 1, "name": "stat_6_name", "value": "Cost"},
                {
                    "type": 1,
                    "name": "stat_6_value",
                    "value": f"${get_number(stats, 'ai_agent_total_cost'):,.0f} est.",
                },
            ]
        }
    }


def patch_discord_profile(application_id, user_id, bot_token, payload):
    log_step("Preparing Discord profile PATCH request")
    url = DISCORD_PROFILE_URL.format(application_id=application_id, user_id=user_id)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 1.0.0)",
    }

    log_step("Sending Discord profile PATCH request")
    status, response = request_json(url, headers, method="PATCH", body=body)
    log_step(f"Discord response status: HTTP {status}")
    print_json("Discord response", response)

    if status < 200 or status >= 300:
        raise RuntimeError(f"Discord API error {status}: {json.dumps(response)}")

    return status, response


def main():
    log_step("Starting Discord WakaTime widget sync")
    stats = fetch_wakatime_stats(require_env("WAKATIME_API_KEY"))
    payload = build_discord_payload(stats)

    print_json("Discord payload", payload)

    status, _ = patch_discord_profile(
        require_env("DISCORD_APPLICATION_ID"),
        require_env("DISCORD_USER_ID"),
        require_env("DISCORD_BOT_TOKEN"),
        payload,
    )
    log_step(f"Discord profile updated: HTTP {status}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
