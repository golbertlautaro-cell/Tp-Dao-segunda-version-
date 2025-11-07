from app import create_app
import json

app = create_app()
with app.test_client() as c:
    payload = {
        'nombre': 'DeporteTestAPI',
        'duracion_minutos': 45,
        'servicios': [
            {'nombre': 'Arbitro', 'precio_adicional': '200,50'},
            {'nombre': 'Pelota', 'precio_adicional': '50'}
        ]
    }
    r = c.post('/api/deportes/', data=json.dumps(payload), content_type='application/json')
    print('POST status', r.status_code)
    print(r.get_data(as_text=True))
    # buscar el deporte creado
    r2 = c.get('/api/deportes/')
    print('LIST status', r2.status_code)
    print(r2.get_data(as_text=True))
    # si existe, pedir servicios
    try:
        arr = r2.get_json()
        created = next((x for x in arr if x['nombre'] == 'DeporteTestAPI'), None)
        if created:
            idd = created['id_deporte']
            r3 = c.get(f'/api/deportes/{idd}/servicios')
            print('SERV status', r3.status_code)
            print(r3.get_data(as_text=True))
    except Exception as e:
        print('error parsing json', e)
