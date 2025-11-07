from app import create_app

app = create_app()
with app.test_client() as c:
    r = c.get('/api/deportes/')
    print('status', r.status_code)
    print(r.get_data(as_text=True))
