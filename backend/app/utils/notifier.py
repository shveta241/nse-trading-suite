import requests
import os
from app.utils.logger import get_logger

logger = get_logger("TelegramNotifier")

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)

    def send_message(self, message: str):
        if not self.enabled:
            logger.warning("Telegram Notifier not configured. Skipping message.")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_trade_alert(self, symbol, side, price, signal_type):
        emoji = "🚀" if side == "BUY" else "🔻"
        msg = (
            f"{emoji} <b>ALGO TRADE ALERT</b> {emoji}\n\n"
            f"<b>Symbol:</b> {symbol}\n"
            f"<b>Action:</b> {side}\n"
            f"<b>Price:</b> ₹{price}\n"
            f"<b>Strategy:</b> {signal_type}\n"
            f"<b>Time:</b> {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}"
        )
        return self.send_message(msg)

notifier = TelegramNotifier()
