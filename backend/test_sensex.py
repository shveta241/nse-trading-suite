import requests
import json

url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
res = requests.get(url)
data = res.json()

for item in data:
    if item.get('symbol') in ['RELIANCE-EQ', 'RELIANCE', 'TCS-EQ', 'NIFTY']:
        if item.get('exch_seg') == 'NSE':
            print(item)
