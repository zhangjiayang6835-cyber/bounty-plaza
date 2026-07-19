import requests

# Basescan API endpoint
url = "https://basescan.org/api/tx/0x1acda407abd7caf3052e654ffcae475a6e83b5bc284d6f1830b4b16a40cd6427"

# Fetch the transaction details
response = requests.get(url)

if response.status_code == 200:
    tx_data = response.json()
    if tx_data["isError"] == 0 and tx_data["value"] == "0.90":
        print("Funding confirmed: 0.90 USDC")
    else:
        print("Funding not confirmed. Check the transaction details.")
else:
    print("Failed to fetch transaction details:", response.status_code, response.text)
