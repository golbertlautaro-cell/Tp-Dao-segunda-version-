from flask import Blueprint, request, jsonify
from app import db
from models import (
    Reserva,
    Cliente,
    Cancha,
    HorarioDisponible,
    EstadoReserva,
    ServicioAdicional,
    ReservaServicio,
    Partido,
)
from datetime import datetime, date as _date
from decimal import Decimal

bp = Blueprint('reservas', __name__)


def time_from_str(s: str):
    return datetime.strptime(s, '%H:%M').time()


def date_from_str(s: str):
    return datetime.strptime(s, '%Y-%m-%d').date()


@bp.route('/', methods=['POST'])
def create_reserva():
    data = request.get_json() or {}
    try:
        id_cliente = int(data.get('id_cliente'))
        id_cancha = int(data.get('id_cancha'))
        fecha_reserva = date_from_str(data.get('fecha_reserva'))
        hora_inicio = time_from_str(data.get('hora_inicio'))
        hora_fin = time_from_str(data.get('hora_fin'))
    except Exception:
        return jsonify({'error': 'Campos inválidos o formato incorrecto. fecha: YYYY-MM-DD, horas: HH:MM'}), 400

    if hora_inicio >= hora_fin:
        return jsonify({'error': 'hora_inicio debe ser anterior a hora_fin'}), 400

    # Verificar existencia de cliente y cancha
    cliente = Cliente.query.get(id_cliente)
    if not cliente or not cliente.activo:
        return jsonify({'error': 'Cliente no existe o no está activo'}), 400

    cancha = Cancha.query.get(id_cancha)
    if not cancha or not cancha.activa:
        return jsonify({'error': 'Cancha no existe o no está activa'}), 400

    # Validar que exista un estado por defecto (Pendiente) para asignar
    estado_default = EstadoReserva.query.filter_by(nombre='Pendiente').first() or EstadoReserva.query.first()
    if not estado_default:
        return jsonify({'error': 'No hay estados de reserva definidos. Cree al menos uno (ej: Pendiente)'}), 400

    # Si hay horarios definidos para la cancha, validar que el horario solicitado esté contenido
    horarios = HorarioDisponible.query.filter_by(id_cancha=id_cancha).all()
    if horarios:
        # Determinar nombre del día en español para comparar con dia_semana si así se usa
        weekday_es = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][fecha_reserva.weekday()]
        ok = False
        for h in horarios:
            if h.dia_semana and h.dia_semana.lower() != weekday_es.lower():
                continue
            # si el horario cubre el intervalo solicitado
            if (h.hora_inicio <= hora_inicio) and (h.hora_fin >= hora_fin) and h.disponible:
                ok = True
                break
        if not ok:
            return jsonify({'error': 'HORARIO_DISPONIBLE: La cancha no tiene un horario disponible que cubra el intervalo solicitado'}), 409

    # Verificar solapamientos con otras reservas en la misma cancha y fecha
    overlapping = Reserva.query.filter(
        Reserva.id_cancha == id_cancha,
        Reserva.fecha_reserva == fecha_reserva,
        # no (existing.hora_fin <= inicio or existing.hora_inicio >= fin)
        Reserva.hora_fin > hora_inicio,
        Reserva.hora_inicio < hora_fin,
    ).first()
    if overlapping:
        return jsonify({'error': 'RESERVAS: Ya existe una reserva en ese horario para la cancha seleccionada'}), 409

    # Verificar solapamientos con PARTIDOS en la misma cancha y fecha
    partido_overlap = Partido.query.filter(
        Partido.id_cancha == id_cancha,
        Partido.fecha_partido == fecha_reserva,
        Partido.hora_fin > hora_inicio,
        Partido.hora_inicio < hora_fin,
    ).first()
    if partido_overlap:
        return jsonify({'error': 'PARTIDOS: Ya existe un partido en ese horario para la cancha seleccionada'}), 409

    # Calcular precio: precio_hora * duración + servicios + iluminación si aplica
    # duración en horas (decimal)
    dt_start = datetime.combine(fecha_reserva, hora_inicio)
    dt_end = datetime.combine(fecha_reserva, hora_fin)
    duration_hours = Decimal((dt_end - dt_start).total_seconds() / 3600)
    precio_base = Decimal(cancha.precio_hora or Decimal('0'))
    total = (precio_base * duration_hours)

    # Iluminación: si el cliente solicita iluminación sumamos el recargo por hora
    usa_iluminacion = bool(data.get('usa_iluminacion', False))
    iluminacion_cost = Decimal('0')
    if usa_iluminacion:
        # usar precio_iluminacion definido en la cancha si existe, sino 0
        precio_ilum = Decimal(cancha.precio_iluminacion or Decimal('0'))
        iluminacion_cost = (precio_ilum * duration_hours)
        total += iluminacion_cost

    # Crear la reserva con estado por defecto
    reserva = Reserva(
        id_cliente=id_cliente,
        id_cancha=id_cancha,
        id_estado=estado_default.id_estado,
        fecha_reserva=fecha_reserva,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        precio_total=total.quantize(Decimal('0.01')),
        usa_iluminacion=usa_iluminacion,
    )
    db.session.add(reserva)
    db.session.flush()  # obtener id_reserva sin commit todavía

    # Procesar servicios adicionales (lista de objetos con id_servicio y cantidad opcional)
    servicios = data.get('servicios_adicionales') or []
    for s in servicios:
        sid = s.get('id_servicio') if isinstance(s, dict) else s
        cantidad = int(s.get('cantidad', 1)) if isinstance(s, dict) else 1
        svc = ServicioAdicional.query.get(sid)
        if not svc or not svc.activo:
            db.session.rollback()
            return jsonify({'error': f'Servicio adicional inválido: {sid}'}), 400
        rs = ReservaServicio(id_reserva=reserva.id_reserva, id_servicio=svc.id_servicio, cantidad=cantidad)
        db.session.add(rs)
        # sumar precio
        total += (Decimal(svc.precio_adicional) * Decimal(cantidad))

    reserva.precio_total = total.quantize(Decimal('0.01'))

    # Commit final
    db.session.commit()

    return jsonify({'id_reserva': reserva.id_reserva, 'precio_total': str(reserva.precio_total)}), 201
