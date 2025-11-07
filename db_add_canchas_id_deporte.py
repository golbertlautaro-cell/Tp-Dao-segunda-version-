from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    conn = db.session.connection()
    # check columns
    res = conn.execute(text("PRAGMA table_info('canchas')")).fetchall()
    cols = [r[1] for r in res]
    if 'id_deporte' in cols:
        print("Columna 'id_deporte' ya existe en 'canchas'.")
    else:
        print("Agregando columna 'id_deporte' a la tabla 'canchas'...")
        conn.execute(text("ALTER TABLE canchas ADD COLUMN id_deporte INTEGER"))
        print("Columna agregada. Nota: foreign key no aplicada en sqlite por compatibilidad.")
    db.session.commit()
