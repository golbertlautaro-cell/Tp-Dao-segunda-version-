from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    conn = db.session.connection()
    res = conn.execute(text("PRAGMA table_info('deportes')")).fetchall()
    cols = [r[1] for r in res]
    if 'necesita_arbitros' not in cols:
        print("La columna 'necesita_arbitros' no existe en 'deportes' — nada que hacer.")
    else:
        print("Eliminando columna 'necesita_arbitros' de la tabla 'deportes' (re-creando la tabla)...")
        # SQLite no soporta DROP COLUMN; recreamos la tabla sin la columna
        try:
            conn.execute(text("PRAGMA foreign_keys=off;"))
            conn.execute(text("BEGIN TRANSACTION;"))

            # Crear nueva tabla sin la columna 'necesita_arbitros'
            conn.execute(text(
                """
                CREATE TABLE deportes_new (
                    id_deporte INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    duracion_minutos INTEGER NOT NULL DEFAULT 60
                )
                """
            ))

            # Copiar datos relevantes
            conn.execute(text(
                "INSERT INTO deportes_new (id_deporte, nombre, duracion_minutos) SELECT id_deporte, nombre, duracion_minutos FROM deportes;"
            ))

            # Reemplazar tabla antigua
            conn.execute(text("DROP TABLE deportes;"))
            conn.execute(text("ALTER TABLE deportes_new RENAME TO deportes;"))

            conn.execute(text("COMMIT;"))
            conn.execute(text("PRAGMA foreign_keys=on;"))
            print("Columna 'necesita_arbitros' eliminada correctamente.")
        except Exception as e:
            conn.execute(text("ROLLBACK;"))
            print("Error durante la migración:", e)
    db.session.commit()
