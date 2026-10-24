#!/usr/bin/env python3
"""CLI utility to register or inspect the Telegram Bot webhook."""
import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.telegram import TelegramAdapter
from app.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Register or manage the Telegram Bot webhook for FunnelBot."
    )
    parser.add_argument(
        "--url",
        help="Public webhook URL (e.g., https://yourapp.onrender.com/webhooks/telegram or ngrok)",
    )
    parser.add_argument(
        "--secret",
        default=settings.TELEGRAM_WEBHOOK_SECRET,
        help="Secret token for verifying Telegram updates (defaults to TELEGRAM_WEBHOOK_SECRET)",
    )
    parser.add_argument(
        "--token",
        default=settings.TELEGRAM_BOT_TOKEN,
        help="Telegram Bot Token (defaults to TELEGRAM_BOT_TOKEN)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Unregister and delete the active Telegram webhook.",
    )

    args = parser.parse_args()

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN is not set in environment or --token argument.")
        sys.exit(1)

    adapter = TelegramAdapter(bot_token=token)

    if args.delete:
        print("🗑️ Deleting Telegram webhook...")
        success = adapter.delete_webhook()
        if success:
            print("✅ Telegram webhook successfully deleted!")
        else:
            print("❌ Failed to delete webhook.")
        return

    if not args.url:
        print("❌ Error: Missing --url. Example:")
        print("   python scripts/setup_telegram_webhook.py --url https://yourapp.onrender.com/webhooks/telegram")
        sys.exit(1)

    print(f"📡 Registering Telegram webhook: {args.url} ...")
    success = adapter.set_webhook(webhook_url=args.url, secret_token=args.secret)
    if success:
        print("🎉 Webhook registered successfully! Messages sent to your Telegram bot will now trigger FunnelBot.")
    else:
        print("❌ Failed to register webhook. Check your bot token and public URL.")
        sys.exit(1)


if __name__ == "__main__":
    main()
