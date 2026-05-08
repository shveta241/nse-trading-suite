from app.data.yfinance_client import YFinanceClient

client = YFinanceClient()
quote = client.fetch_live_quote("^BSESN")
print("YFinance SENSEX Quote:", quote)
