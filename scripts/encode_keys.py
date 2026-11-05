import base64

with open('F:/SHIV/shivai/.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '_API_KEYS=' in line:
            parts = line.split('=', 1)
            k = parts[0].strip()
            v = parts[1].strip().strip('"').strip("'")
            if v:
                b64 = base64.b64encode(v.encode('utf-8')).decode('utf-8')
                print(f"{k} = '{b64}'")
