"""Herramienta mínima para ajustar el esquema de la BD local.

- Elimina la tabla `arbitros` si existe (ya que el modelo fue removido).
- Puede ejecutarse con: python db_migrate.py

Precaución: modifica la base local `reservas.db`.
"""
from app import create_app, db


def drop_arbitros_table():
    app = create_app()
    with app.app_context():
        try:
            # Ejecutar SQL directo para eliminar la tabla si existe
            from sqlalchemy import text
            sql = text("DROP TABLE IF EXISTS arbitros;")
            db.session.execute(sql)
            db.session.commit()
            print("Tabla 'arbitros' eliminada (si existía).")
        except Exception as e:
            print("Error al eliminar la tabla 'arbitros':", e)


if __name__ == '__main__':
    drop_arbitros_table()
