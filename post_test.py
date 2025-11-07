import urllib.request
import json

BASE = 'http://127.0.0.1:5000'

def get(path):
    url = BASE + path
    with urllib.request.urlopen(url) as resp:
        data = resp.read().decode('utf-8')
        try:
            return json.loads(data)
        except Exception:
            return data

def post(path, payload):
    url = BASE + path
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as resp:
        out = resp.read().decode('utf-8')
        try:
            return json.loads(out)
        except Exception:
            return out

if __name__ == '__main__':
    print('GET /api/canchas')
    print(get('/api/canchas/'))
    print('\nGET /api/clientes')
    print(get('/api/clientes/'))
    print('\nGET /api/reservas/check (18:00-19:00)')
    print(get('/api/reservas/check?id_cancha=1&fecha_reserva=2025-11-10&hora_inicio=18:00&hora_fin=19:00'))
    print('\nPOST /api/reservas (crear reserva ejemplo)')
    payload = {
        'id_cliente': 1,
        'id_cancha': 1,
        'fecha_reserva': '2025-11-10',
        'hora_inicio': '18:00',
        'hora_fin': '19:00',
        'usa_iluminacion': False,
        'servicios_adicionales': []
    }
    print(post('/api/reservas/', payload))
