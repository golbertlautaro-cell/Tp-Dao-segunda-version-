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
from models import Cliente, Cancha, EstadoReserva, ServicioAdicional, MetodoPago
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
            canchas = [
                Cancha(nombre='Cancha Central', tipo_deporte='Fútbol', superficie='Césped', precio_hora=200, iluminacion=True),
                Cancha(nombre='Cancha 2', tipo_deporte='Tenis', superficie='Cemento', precio_hora=100, iluminacion=False),
            ]
            db.session.add_all(canchas)
            print('Añadidas 2 canchas')
        else:
            print('Canchas ya existentes, se omite inserción')

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
            servicios = [
                ServicioAdicional(nombre='Pelota', precio_adicional=50),
                ServicioAdicional(nombre='Chalecos', precio_adicional=30),
            ]
            db.session.add_all(servicios)
            print('Añadidos 2 servicios adicionales')
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
