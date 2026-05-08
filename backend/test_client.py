from app.data.angel_client import AngelOneClient

client = AngelOneClient()
quote = client.fetch_live_quote("BSE:SENSEX")
print("SENSEX Quote:", quote)

df = client.fetch_historical_data("BSE:SENSEX", "5m", "2026-04-20")
print("SENSEX Historical Data:", df.tail() if not df.empty else "Empty")
