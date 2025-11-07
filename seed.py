"""Script para poblar la base de datos con datos de prueba.

Inserta:
- 3 clientes
- 2 canchas (fútbol y tenis)
- 2 estados de reserva ('Pendiente', 'Confirmada')
- 2 servicios adicionales ('Pelota', 'Chalecos')

Ejecutar::
    python seed.py
"""
from app import create_app, db
from models import Cliente, Cancha, EstadoReserva, ServicioAdicional, MetodoPago, Deporte
from datetime import date


def seed():
    app = create_app()

    with app.app_context():
        # Evitar insertar duplicados comprobando existencia mínima
        if Cliente.query.count() == 0:
            clientes = [
                Cliente(dni='12345678', nombre='Ana', apellido='Gomez', telefono='111-1111', email='ana@example.com'),
                Cliente(dni='23456789', nombre='Luis', apellido='Perez', telefono='222-2222', email='luis@example.com'),
                Cliente(dni='34567890', nombre='María', apellido='Lopez', telefono='333-3333', email='maria@example.com'),
            ]
            db.session.add_all(clientes)
            print('Añadidos 3 clientes')
        else:
            print('Clientes ya existentes, se omite inserción')

        if Cancha.query.count() == 0:
            # Crear deportes por defecto
            futbol = Deporte(nombre='Fútbol', duracion_minutos=90)
            tenis = Deporte(nombre='Tenis', duracion_minutos=120)
            padel = Deporte(nombre='Pádel', duracion_minutos=60)
            db.session.add_all([futbol, tenis, padel])
            db.session.flush()

            canchas = [
                Cancha(nombre='Cancha Central', tipo_deporte='Fútbol', id_deporte=futbol.id_deporte, superficie='Césped', precio_hora=200, iluminacion=True),
                Cancha(nombre='Cancha 2', tipo_deporte='Tenis', id_deporte=tenis.id_deporte, superficie='Cemento', precio_hora=100, iluminacion=False),
            ]
            db.session.add_all(canchas)
            print('Añadidas 2 canchas')
        else:
            print('Canchas ya existentes, se omite inserción')

        # Asegurarse de que existan deportes aunque ya haya canchas (caso de DB parcial)
        if Deporte.query.count() == 0:
            futbol = Deporte(nombre='Fútbol', duracion_minutos=90)
            tenis = Deporte(nombre='Tenis', duracion_minutos=120)
            padel = Deporte(nombre='Pádel', duracion_minutos=60)
            db.session.add_all([futbol, tenis, padel])
            print('Se añadieron deportes por defecto')

        if EstadoReserva.query.count() == 0:
            estados = [
                EstadoReserva(nombre='Pendiente'),
                EstadoReserva(nombre='Confirmada'),
            ]
            db.session.add_all(estados)
            print("Añadidos 2 estados de reserva")
        else:
            print('Estados de reserva ya existentes, se omite inserción')

        if ServicioAdicional.query.count() == 0:
            # Crear servicios generales y por deporte
            # Asegurar que los deportes referenciados existen y obtener sus ids
            futbol = Deporte.query.filter_by(nombre='Fútbol').first()
            tenis = Deporte.query.filter_by(nombre='Tenis').first()
            padel = Deporte.query.filter_by(nombre='Pádel').first()

            servicios = [
                # Servicios globales
                ServicioAdicional(nombre='Pelota', precio_adicional=50, id_deporte=None),
                ServicioAdicional(nombre='Chalecos', precio_adicional=30, id_deporte=None),
                # Tenis
                ServicioAdicional(nombre='Pelotas (set x3)', precio_adicional=150, id_deporte=(tenis.id_deporte if tenis else None)),
                ServicioAdicional(nombre='Máquina de pelotas (por hora)', precio_adicional=800, id_deporte=(tenis.id_deporte if tenis else None)),
                ServicioAdicional(nombre='Entrenador privado (por hora)', precio_adicional=1000, id_deporte=(tenis.id_deporte if tenis else None)),
                # Pádel
                ServicioAdicional(nombre='Paleta (alquiler)', precio_adicional=200, id_deporte=(padel.id_deporte if padel else None)),
                ServicioAdicional(nombre='Pelotas (set x3)', precio_adicional=150, id_deporte=(padel.id_deporte if padel else None)),
                ServicioAdicional(nombre='Entrenador privado (por hora)', precio_adicional=900, id_deporte=(padel.id_deporte if padel else None)),
                # Fútbol
                ServicioAdicional(nombre='Balón (alquiler)', precio_adicional=300, id_deporte=(futbol.id_deporte if futbol else None)),
                ServicioAdicional(nombre='Árbitro (por partido)', precio_adicional=1200, id_deporte=(futbol.id_deporte if futbol else None)),
                ServicioAdicional(nombre='Iluminación (por hora)', precio_adicional=400, id_deporte=(futbol.id_deporte if futbol else None)),
            ]
            db.session.add_all(servicios)
            print('Añadidos servicios adicionales por deporte y globales')
        else:
            print('Servicios adicionales ya existentes, se omite inserción')

        if MetodoPago.query.count() == 0:
            metodos = [
                MetodoPago(nombre='Efectivo'),
                MetodoPago(nombre='Tarjeta'),
            ]
            db.session.add_all(metodos)
            print('Añadidos métodos de pago')
        else:
            print('Métodos de pago ya existentes, se omite inserción')

        # Commit final
        db.session.commit()

        print('Seed finalizado')


if __name__ == '__main__':
    seed()
