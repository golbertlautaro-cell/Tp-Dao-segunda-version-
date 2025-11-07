from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    conn = db.session.connection()
    res = conn.execute(text("PRAGMA table_info('servicios_adicionales')")).fetchall()
    cols = [r[1] for r in res]
    if 'id_deporte' in cols:
        print("Columna 'id_deporte' ya existe en 'servicios_adicionales'.")
    else:
        print("Agregando columna 'id_deporte' a la tabla 'servicios_adicionales'...")
        conn.execute(text("ALTER TABLE servicios_adicionales ADD COLUMN id_deporte INTEGER"))
        print("Columna agregada.")
    db.session.commit()
