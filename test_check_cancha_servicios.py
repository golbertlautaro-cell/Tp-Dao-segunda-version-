from app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/api/canchas/')
    print('Canchas status', r.status_code)
    print(r.get_data(as_text=True))
    arr = r.get_json() or []
    found = None
    for ch in arr:
        if ch.get('deporte'):
            found = ch
            break
    if not found and arr:
        found = arr[0]
    if not found:
        print('No canchas found')
    else:
        print('Selected cancha:', found.get('id_cancha'), found.get('nombre'))
        id_dep = found.get('deporte', {}).get('id_deporte') or found.get('id_deporte')
        print('id_deporte=', id_dep)
        if id_dep:
            r2 = c.get(f'/api/deportes/{id_dep}/servicios')
            print('Servicios for deporte status', r2.status_code)
            print(r2.get_data(as_text=True))
