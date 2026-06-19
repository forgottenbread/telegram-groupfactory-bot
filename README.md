<!-- gitea-mirror-notice:start -->
> [!IMPORTANT]
> **This GitHub repository is a mirror.**  
> The canonical public repository is [https://git.mulas.me/corrado/telegram-groupfactory-bot](https://git.mulas.me/corrado/telegram-groupfactory-bot).
<!-- gitea-mirror-notice:end -->

# telegram-groupfactory-bot

Conventional Telegram Bot API client for `telegram-groupfactory`.

This service does not use Telethon and does not replace the userbot commands. It talks to the userbot REST API with `X-API-Key`, so the userbot remains the only service that owns Telegram user-session operations.

## Commands

```text
/newgrp                         - Guided group creation through the API
/get_group <group_id>            - Read group info
/group_add_users <group_id> <user_id> ...

/get_users                       - Show default group users
/set_users <id_or_username_or_id:username> ...
/add_users <id_or_username_or_id:username> ...
/remove_users <id_or_username_or_id:username> ...
/add_user <username_or_id:username>

/get_qr [qr_group]
/set_qr <payload>
/set_qr <qr_group> <payload>
/set_qr_group <qr_group>         - Forward a .importbackup QR image
/qr_groups [qr_group]
/qr_group_add <qr_group> <telegram_group_id> ...
/qr_group_remove <telegram_group_id> ...
/sync_qr [qr_group|all]

/users
/user <user_id>
/delete_user <user_id>
/ping
/cancel
```

`/newgrp` also accepts quick input:

```text
/newgrp Group name | Group description
```

## Configuration

```text
TELEGRAM_BOT_TOKEN       BotFather token for the conventional bot
GROUPFACTORY_API_BASE_URL Internal URL for the userbot REST API
GROUPFACTORY_API_KEY     Must match API_KEY on telegram-groupfactory
BOT_ALLOWED_CHAT_IDS     Comma-separated chat IDs allowed to use this bot
GROUPFACTORY_API_TIMEOUT API timeout in seconds, default 300
```

Inside the same Kubernetes namespace, `GROUPFACTORY_API_BASE_URL` can be:

```text
http://groupfactory:8000
```

## Local Run

```bash
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

## Kubernetes

Apply the example config and secret after replacing values:

```bash
kubectl apply -f examples/configmap.yaml
kubectl apply -f examples/secret.yaml
kubectl apply -f k8s/
```

The Deployment runs in namespace `groupfactory`, the same namespace as the userbot.
