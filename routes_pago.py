from flask import Blueprint, request, jsonify
from app import db
from models import Reserva, MetodoPago, Pago, EstadoReserva
from decimal import Decimal

bp = Blueprint('pagos', __name__)


@bp.route('/api/reservas/<int:id_reserva>/pagar', methods=['POST'])
def pagar_reserva(id_reserva):
    data = request.get_json() or {}
    try:
        id_metodo = int(data.get('id_metodo'))
        monto = Decimal(str(data.get('monto')))
    except Exception:
        return jsonify({'error': 'id_metodo y monto son obligatorios y deben tener formato correcto'}), 400

    reserva = Reserva.query.get(id_reserva)
    if not reserva:
        return jsonify({'error': 'Reserva no encontrada'}), 404

    # Comparar monto con precio_total (usar Decimal para exactitud)
    precio_total = Decimal(str(reserva.precio_total or '0'))
    if monto != precio_total:
        return jsonify({'error': 'El monto no coincide con el precio_total de la reserva'}), 400

    metodo = MetodoPago.query.get(id_metodo)
    if not metodo:
        return jsonify({'error': 'Método de pago no encontrado'}), 400

    # Crear registro de pago
    pago = Pago(id_reserva=id_reserva, id_metodo=id_metodo, monto=monto, estado='Completado')
    db.session.add(pago)

    # Cambiar estado de la reserva a 'Confirmada'
    estado_confirmada = EstadoReserva.query.filter_by(nombre='Confirmada').first()
    if not estado_confirmada:
        # si no existe el estado, crear uno
        estado_confirmada = EstadoReserva(nombre='Confirmada')
        db.session.add(estado_confirmada)
        db.session.flush()

    reserva.id_estado = estado_confirmada.id_estado

    db.session.commit()

    return jsonify({'id_pago': pago.id_pago, 'id_reserva': id_reserva, 'monto': str(pago.monto)}), 201
