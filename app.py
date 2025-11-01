from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Extensión SQLAlchemy (instancia sin app para soportar app factory)
db = SQLAlchemy()


from models import *
def create_app(test_config=None):
    """Crea y configura la app Flask.

    Configura SQLAlchemy con una base de datos SQLite llamada 'reservas.db'
    ubicada en la misma carpeta que este archivo.
    """
    app = Flask(__name__, instance_relative_config=False)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'reservas.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'dev')

    # Inicializar extensiones
    db.init_app(app)

    # Registro de rutas simples
    @app.route('/')
    def index():
        return 'API de Reservas funcionando'

    # Importar modelos dentro del contexto de la app para que SQLAlchemy los
    # registre antes de crear las tablas. Importo explícitamente las clases
    # usadas en la aplicación para asegurar el registro de todos los metadatos.
    with app.app_context():
        try:
            # importar todos los modelos (si faltan, el import lanzará y lo ignoramos)
            from models import (
                Cliente,
                Cancha,
                HorarioDisponible,
                EstadoReserva,
                Reserva,
                ServicioAdicional,
                ReservaServicio,
                MetodoPago,
                Pago,
                Campeonato,
                Equipo,
                Partido,
            )  # noqa: F401
        except Exception:
            # si no existe models aún o hay un error, no rompemos la creación de la app
            pass

        # Crear todas las tablas declaradas por los modelos
        db.create_all()
        # Registrar Blueprints si existen
        try:
            from routes_cliente import bp as clientes_bp
            # Registrar bajo /api/clientes
            app.register_blueprint(clientes_bp, url_prefix='/api/clientes')
        except Exception:
            pass

        try:
            from routes_cancha import bp as canchas_bp
            # Registrar bajo /api/canchas
            app.register_blueprint(canchas_bp, url_prefix='/api/canchas')
        except Exception:
            pass

        try:
            from routes_reserva import bp as reservas_bp
            app.register_blueprint(reservas_bp, url_prefix='/api/reservas')
        except Exception:
            pass

        try:
            from routes_pago import bp as pagos_bp
            app.register_blueprint(pagos_bp)
        except Exception:
            pass

        try:
            from routes_servicio import bp as servicios_bp
            app.register_blueprint(servicios_bp, url_prefix='/api')
        except Exception:
            pass

        try:
            from routes_reportes import bp as reportes_bp
            app.register_blueprint(reportes_bp, url_prefix='/api')
        except Exception:
            pass

        # campeonato blueprint
        try:
            from routes_campeonato import bp as campeonatos_bp
            app.register_blueprint(campeonatos_bp)
        except Exception:
            # blueprint optional until routes_campeonato is available
            pass

        # Rutas para servir las plantillas (UI)
        try:
            from flask import render_template
            @app.route('/ui/clientes')
            def ui_clientes():
                return render_template('clientes.html')

            @app.route('/ui/canchas')
            def ui_canchas():
                return render_template('canchas.html')

            @app.route('/ui/reservar')
            def ui_reservar():
                return render_template('reservar.html')

            @app.route('/ui/reportes')
            def ui_reportes():
                return render_template('reportes.html')

            @app.route('/ui')
            def ui_index():
                return render_template('dashboard.html')
            
            @app.route('/ui/reservar')
            def ui_reservar():
                return render_template('reservar.html')

            @app.route('/ui/reportes')
            def ui_reportes():
                return render_template('reportes.html')
            
            @app.route('/ui/reservar')
            def ui_reservar():
                return render_template('reservar.html')

            @app.route('/ui/reportes')
            def ui_reportes():
                return render_template('reportes.html')
        except Exception:
            pass

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
