# Discord WakaTime Widget

Discord profile widget that shows the [WakaTime](https://wakatime.com/) activity overview for the last 7 days.

The initial idea came from No Text To Speech's Discord widget video:

https://www.youtube.com/watch?v=gYv7D83u7yQ

That guide explains the Discord-side widget setup. This repository adds an automated updater that fetches WakaTime stats and patches the Discord application profile every 30 minutes through GitHub Actions.

After seeing the tutorial, I wanted to build the same kind of Discord widget for my WakaTime statistics: total coding time, daily average, AI coding share, AI spend, token usage, and AI session counts.

## What It Shows

The widget displays six compact stats on a Discord profile:

<img width="442" height="377" alt="image" src="https://github.com/user-attachments/assets/69f32291-29cf-401c-8e41-86f3ba8b05f0" />

## How It Works

`sync_widget.py` does three things:

1. Calls WakaTime:

```text
GET https://api.wakatime.com/api/v1/users/current/stats/last_7_days
```

2. Converts the response into Discord widget dynamic data.

3. Sends the payload to Discord:

```text
PATCH https://discord.com/api/v9/applications/{DISCORD_APPLICATION_ID}/users/{DISCORD_USER_ID}/identities/0/profile
```

The script uses only Python's standard library. There are no npm, pip, or .NET dependencies.

## Discord Setup

Follow Chloe Cinders' guide for the Discord widget/application setup:

https://chloecinders.com/blog/discord-widgets#setting-up-your-application-and-developer-portal

In the Discord widget editor, configure `Widget Bottom` as repeated stat rows. For each `Stat #x`, set both `Value` and `Label` to type `User Data`, then use these data fields:

| Widget Bottom item | Value data field | Label data field |
| --- | --- | --- |
| `Stat #1` | `stat_1_name` | `stat_1_value` |
| `Stat #2` | `stat_2_name` | `stat_2_value` |
| `Stat #3` | `stat_3_name` | `stat_3_value` |
| `Stat #4` | `stat_4_name` | `stat_4_value` |
| `Stat #5` | `stat_5_name` | `stat_5_value` |
| `Stat #6` | `stat_6_name` | `stat_6_value` |

The widget fields must use these data fields in the Sample Data json:

```text
stat_1_name
stat_1_value
stat_2_name
stat_2_value
stat_3_name
stat_3_value
stat_4_name
stat_4_value
stat_5_name
stat_5_value
stat_6_name
stat_6_value
```

Those names are what Discord matches when the script sends `data.dynamic`.

## WakaTime Setup

Create or copy your WakaTime API key from:

```text
https://wakatime.com/api-key
```

The script authenticates to WakaTime with HTTP Basic Auth using that API key.

## GitHub Actions Secrets

Open the repository on GitHub:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Create these repository secrets:

| Secret name | Value |
| --- | --- |
| `WAKATIME_API_KEY` | Your WakaTime API key |
| `DISCORD_APPLICATION_ID` | Discord application ID |
| `DISCORD_USER_ID` | Discord user ID whose profile widget is updated |
| `DISCORD_BOT_TOKEN` | Discord bot token |

The workflow reads them here:

```yaml
env:
  WAKATIME_API_KEY: ${{ secrets.WAKATIME_API_KEY }}
  DISCORD_APPLICATION_ID: ${{ secrets.DISCORD_APPLICATION_ID }}
  DISCORD_USER_ID: ${{ secrets.DISCORD_USER_ID }}
  DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_BOT_TOKEN }}
```

## Schedule

The workflow runs every 30 minutes:

```yaml
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:
```

GitHub Actions cron uses UTC. Scheduled workflows run from the repository's default branch. You can also start it manually from:

```text
Actions -> Sync Discord WakaTime Widget -> Run workflow
```

## Debug Logging

The workflow does not print the full WakaTime API response by default. That response can include project names, dependencies, machine names, editor usage, token counts, and AI cost details.

For temporary debugging, set this environment variable in the workflow:

```yaml
DEBUG_WAKATIME_JSON: "1"
```

Do not leave full WakaTime JSON logging enabled in a public repository.

## Deploy

Commit and push the repository:

```bash
git add .
git commit -m "Add WakaTime Discord widget sync"
git push -u origin main
```

After the push, add the GitHub Actions secrets, then run the workflow manually once to verify the setup.

## Troubleshooting

`Missing required environment variable`

One of the GitHub Actions secrets is missing or has a different name.

`WakaTime stats are still pending_update`

WakaTime sometimes returns `202 pending_update` while stats are recalculating. The script retries automatically, but a run can still fail if WakaTime takes too long.

`Discord API error 401`

The Discord bot token is invalid or expired.

`Discord API error 403`

The bot token or application/user combination does not have access to update that profile.

`actions/checkout` Node warning

The workflow uses `actions/checkout@v5`, which targets the newer GitHub Actions runtime.

## License

This project is licensed under the [MIT License](LICENSE).

## Security

Do not commit real tokens into the repository. Store them in GitHub Actions repository secrets instead.

If a WakaTime API key or Discord bot token is exposed, regenerate it before using this workflow again.
