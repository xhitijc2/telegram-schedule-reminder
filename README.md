# Telegram schedule reminder

Sends a Telegram message when an event in `schedule.csv` starts or ends. Runs
via GitHub Actions, triggered every minute by cron-job.org.

## How it works

1. **cron-job.org** hits GitHub's `workflow_dispatch` endpoint every minute.
2. **GitHub Actions** runs `reminder.py`.
3. `reminder.py` parses `schedule.csv`, checks IST clock, and sends a Telegram
   message if any event's start or end minute matches now.

## Update the schedule

Edit `schedule.csv`, commit, push. Next tick picks it up.

## Repo secrets (already set)

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
