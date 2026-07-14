import requests, json

api_key = '42d875c1b5e762735eaa8492981191bf78e10b4fa64193b4d8fbca9ac03f932d'

query = {
    'gpu_name': {'eq': 'RTX 4090'},
    'num_gpus': {'eq': 1},
    'rentable': {'eq': True},
    'order': [['dph_total', 'asc']],
    'limit': 10
}

r = requests.get(
    'https://console.vast.ai/api/v0/bundles',
    headers={'Authorization': f'Bearer {api_key}'},
    params={'q': json.dumps(query)},
    timeout=30
)

data = r.json()
offers = data.get('offers', [])
print(f'Total ofertas encontradas: {len(offers)}\n')
print('=' * 100)

for i, o in enumerate(offers):
    print(f"#{i+1} | ID: {o['id']} | ${o['dph_total']:.4f}/h")
    print(f"    GPU: {o.get('gpu_name', '?')}")
    print(f"    CPU: {o.get('cpu_name', '?')[:40]}")
    print(f"    RAM: {o.get('cpu_ram', '?')} MB | Disk: {o.get('disk_space', '?')} GB")
    print(f"    Score: {o.get('score', '?')} | Reliability: {o.get('reliability2', '?')}")
    print(f"    Location: {o.get('geolocation', '?')}")
    print(f"    Driver: {o.get('driver_version', '?')}")
    print('-' * 100)
