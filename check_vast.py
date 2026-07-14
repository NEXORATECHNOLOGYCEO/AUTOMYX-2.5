import requests, json, sys

api_key = '42d875c1b5e762735eaa8492981191bf78e10b4fa64193b4d8fbca9ac03f932d'

try:
    r = requests.get(
        'https://console.vast.ai/api/v0/instances/',
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=30
    )

    sys.stdout.write(f"STATUS: {r.status_code}\n")
    sys.stdout.flush()

    data = r.json()
    instances = data.get('instances', [])

    sys.stdout.write(f"INSTANCIAS ENCONTRADAS: {len(instances)}\n")
    sys.stdout.flush()

    if len(instances) == 0:
        sys.stdout.write("NO HAY INSTANCIAS ACTIVAS TODAVIA\n")
        sys.stdout.flush()
    else:
        for idx, inst in enumerate(instances):
            sys.stdout.write(f"\n--- Instancia {idx+1} ---\n")
            sys.stdout.write(f"ID: {inst.get('id')}\n")
            sys.stdout.write(f"Status: {inst.get('status')}\n")
            sys.stdout.write(f"GPU: {inst.get('gpu_name')}\n")
            sys.stdout.write(f"IP: {inst.get('ssh_host')}\n")
            sys.stdout.write(f"Puerto SSH: {inst.get('ssh_port')}\n")
            sys.stdout.flush()

except Exception as e:
    sys.stdout.write(f"ERROR: {str(e)}\n")
    sys.stdout.flush()
