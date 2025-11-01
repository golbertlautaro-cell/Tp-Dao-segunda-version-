from flask import Blueprint, request, jsonify
from app import db
from models import Reserva, Cliente, Cancha
from datetime import datetime, date
from sqlalchemy import func

bp = Blueprint('reportes', __name__)


def parse_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None


@bp.route('/reportes/reservas_por_cliente', methods=['GET'])
def reservas_por_cliente():
    id_cliente = request.args.get('id_cliente')
    if not id_cliente:
        return jsonify({'error':'id_cliente es obligatorio'}), 400
    try:
        id_cliente = int(id_cliente)
    except Exception:
        return jsonify({'error':'id_cliente inválido'}), 400

    cliente = Cliente.query.get(id_cliente)
    if not cliente:
        return jsonify({'error':'Cliente no encontrado'}), 404

    reservas = Reserva.query.filter_by(id_cliente=id_cliente).order_by(Reserva.fecha_reserva.desc(), Reserva.hora_inicio).all()
    result = []
    for r in reservas:
        result.append({
            'id_reserva': r.id_reserva,
            'id_cancha': r.id_cancha,
            'cancha_nombre': r.cancha.nombre if r.cancha else None,
            'fecha_reserva': r.fecha_reserva.isoformat() if r.fecha_reserva else None,
            'hora_inicio': r.hora_inicio.strftime('%H:%M') if r.hora_inicio else None,
            'hora_fin': r.hora_fin.strftime('%H:%M') if r.hora_fin else None,
            'precio_total': str(r.precio_total) if r.precio_total is not None else None,
            'estado': r.estado.nombre if r.estado else None,
            'usa_iluminacion': bool(r.usa_iluminacion),
        })

    return jsonify({'cliente': f"{cliente.nombre} {cliente.apellido}", 'reservas': result})


@bp.route('/reportes/reservas_por_cancha', methods=['GET'])
def reservas_por_cancha():
    id_cancha = request.args.get('id_cancha')
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')

    if not id_cancha:
        return jsonify({'error':'id_cancha es obligatorio'}), 400
    try:
        id_cancha = int(id_cancha)
    except Exception:
        return jsonify({'error':'id_cancha inválido'}), 400

    date_desde = parse_date(desde) if desde else None
    date_hasta = parse_date(hasta) if hasta else None
    if (desde and not date_desde) or (hasta and not date_hasta):
        return jsonify({'error':'Formato de fecha inválido. Use YYYY-MM-DD.'}), 400

    query = Reserva.query.filter_by(id_cancha=id_cancha)
    if date_desde:
        query = query.filter(Reserva.fecha_reserva >= date_desde)
    if date_hasta:
        query = query.filter(Reserva.fecha_reserva <= date_hasta)

    reservas = query.order_by(Reserva.fecha_reserva, Reserva.hora_inicio).all()

    cancha = Cancha.query.get(id_cancha)
    if not cancha:
        return jsonify({'error':'Cancha no encontrada'}), 404

    result = []
    for r in reservas:
        result.append({
            'id_reserva': r.id_reserva,
            'id_cliente': r.id_cliente,
            'cliente': f"{r.cliente.nombre} {r.cliente.apellido}" if r.cliente else None,
            'fecha_reserva': r.fecha_reserva.isoformat() if r.fecha_reserva else None,
            'hora_inicio': r.hora_inicio.strftime('%H:%M') if r.hora_inicio else None,
            'hora_fin': r.hora_fin.strftime('%H:%M') if r.hora_fin else None,
            'precio_total': str(r.precio_total) if r.precio_total is not None else None,
            'estado': r.estado.nombre if r.estado else None,
        })

    return jsonify({'cancha': cancha.nombre, 'desde': desde, 'hasta': hasta, 'reservas': result})


@bp.route('/reportes/ranking_canchas', methods=['GET'])
def ranking_canchas():
    """Devuelve las canchas ordenadas por número de reservas (desc)."""
    # Usamos join para obtener el nombre de la cancha y el conteo
    rows = db.session.query(
        Cancha.id_cancha,
        Cancha.nombre,
        func.count(Reserva.id_reserva).label('reservas_count')
    ).join(Reserva, Reserva.id_cancha == Cancha.id_cancha).group_by(Cancha.id_cancha).order_by(func.count(Reserva.id_reserva).desc()).all()

    result = []
    for id_cancha, nombre, cnt in rows:
        result.append({'id_cancha': id_cancha, 'nombre': nombre, 'reservas_count': int(cnt)})

    return jsonify({'ranking': result})


@bp.route('/reportes/uso_mensual', methods=['GET'])
def uso_mensual():
    """Devuelve el conteo de reservas agrupado por mes (YYYY-MM).

    Parámetros opcionales:
    - year: si se proporciona, filtra las reservas de ese año.
    """
    year = request.args.get('year')

    month_label = func.strftime('%Y-%m', Reserva.fecha_reserva)
    query = db.session.query(month_label.label('month'), func.count(Reserva.id_reserva).label('count'))

    if year:
        try:
            y = int(year)
        except Exception:
            return jsonify({'error':'year inválido'}), 400
        # filtrar entre el 1 de enero y 31 de diciembre del año
        start = date(y, 1, 1)
        end = date(y, 12, 31)
        query = query.filter(Reserva.fecha_reserva >= start, Reserva.fecha_reserva <= end)

    query = query.group_by('month').order_by('month')
    rows = query.all()

    result = [{'month': r[0], 'count': int(r[1])} for r in rows]
    return jsonify({'uso_mensual': result})
