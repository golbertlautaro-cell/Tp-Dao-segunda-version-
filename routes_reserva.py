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
    Pago,
    MetodoPago,
)
from datetime import datetime, date as _date, timedelta
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

    # Permitimos reservas que crucen medianoche. El intervalo válido es desde
    # fecha_reserva 10:00 (inclusive) hasta fecha_reserva+1 01:00 (inclusive).
    # Además la duración requerida depende del deporte de la cancha.
    # Permitimos slots cada 30 minutos (00 o 30). No forzamos minutos == 00.
    if hora_inicio.minute not in (0, 30) or hora_fin.minute not in (0, 30):
        return jsonify({'error': 'Las horas deben tener minutos 00 o 30 (ej. 07:00, 07:30).'}), 400

    dt_start = datetime.combine(fecha_reserva, hora_inicio)
    dt_end = datetime.combine(fecha_reserva, hora_fin)
    # si hora_fin es menor o igual a hora_inicio, asumir que terminó al día siguiente
    if dt_end <= dt_start:
        dt_end = dt_end + timedelta(days=1)

    # Rango global permitido: [fecha_reserva 10:00, fecha_reserva+1 01:00]
    window_start = datetime.combine(fecha_reserva, datetime.strptime('10:00', '%H:%M').time())
    window_end = datetime.combine(fecha_reserva + timedelta(days=1), datetime.strptime('01:00', '%H:%M').time())
    if dt_start < window_start or dt_end > window_end:
        return jsonify({'error': 'Horario fuera de rango. Las reservas sólo pueden realizarse entre 10:00 y 01:00 (incluye pasada de medianoche).'}), 400

    # Además limitar hora de inicio máxima a 23:00 (no permitimos iniciar después de las 23:00)
    if dt_start.time() > datetime.strptime('23:00', '%H:%M').time():
        return jsonify({'error': 'La hora de inicio no puede ser posterior a las 23:00.'}), 400

    # Verificar existencia de cliente y cancha
    cliente = Cliente.query.get(id_cliente)
    if not cliente or not cliente.activo:
        return jsonify({'error': 'Cliente no existe o no está activo'}), 400

    cancha = Cancha.query.get(id_cancha)
    if not cancha or not cancha.activa:
        return jsonify({'error': 'Cancha no existe o no está activa'}), 400

    # Determinar duración esperada por deporte: preferir catálogo `Deporte` si la cancha lo referencia
    if getattr(cancha, 'deporte', None):
        try:
            duracion_minutos = int(cancha.deporte.duracion_minutos or 60)
        except Exception:
            duracion_minutos = 60
    else:
        # Fallback a mapeo por texto para compatibilidad
        deporte = (cancha.tipo_deporte or '').strip().lower()
        DURACIONES_MIN = {
            'padel': 60,
            'pádel': 60,
            'tenis': 120,
            'futbol': 90,
            'fútbol': 90,
            'basket': 60,
            'basquet': 60,
            'baloncesto': 60,
        }
        duracion_minutos = DURACIONES_MIN.get(deporte, 60)

    # Validar que la duración solicitada coincida con la duración esperada para el deporte
    expected_end = dt_start + timedelta(minutes=duracion_minutos)
    if expected_end != dt_end:
        return jsonify({'error': f'La reserva para {cancha.tipo_deporte or "este deporte"} debe durar {duracion_minutos} minutos. Hora esperada de fin: {expected_end.time().strftime("%H:%M")}' }), 400

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
    # Verificar solapamientos con otras reservas: para soportar cruces de medianoche normalizamos intervalos
    candidate_dates = [fecha_reserva, fecha_reserva - timedelta(days=1)]
    existing_reservas = Reserva.query.filter(
        Reserva.id_cancha == id_cancha,
        Reserva.fecha_reserva.in_(candidate_dates)
    ).all()

    def to_datetime_interval(res):
        s = datetime.combine(res.fecha_reserva, res.hora_inicio)
        e = datetime.combine(res.fecha_reserva, res.hora_fin)
        if e <= s:
            e = e + timedelta(days=1)
        return s, e

    for ex in existing_reservas:
        s_ex, e_ex = to_datetime_interval(ex)
        if dt_start < e_ex and s_ex < dt_end:
            return jsonify({'error': 'RESERVAS: Ya existe una reserva en ese horario para la cancha seleccionada'}), 409

    # Verificar solapamientos con PARTIDOS en la misma cancha y fecha
    # Verificar solapamientos con PARTIDOS (incluir partido del día anterior que cruza medianoche)
    existing_partidos = Partido.query.filter(
        Partido.id_cancha == id_cancha,
        Partido.fecha_partido.in_(candidate_dates)
    ).all()
    def to_datetime_interval_part(p):
        s = datetime.combine(p.fecha_partido, p.hora_inicio)
        e = datetime.combine(p.fecha_partido, p.hora_fin)
        if e <= s:
            e = e + timedelta(days=1)
        return s, e

    for p in existing_partidos:
        s_p, e_p = to_datetime_interval_part(p)
        if dt_start < e_p and s_p < dt_end:
            return jsonify({'error': 'PARTIDOS: Ya existe un partido en ese horario para la cancha seleccionada'}), 409

    # Calcular precio: precio_hora * duración + servicios + iluminación si aplica
    # duración en horas (decimal)
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


@bp.route('/', methods=['GET'])
def list_reservas():
    """Listar reservas. Query params opcionales: id_cancha, fecha_reserva=YYYY-MM-DD"""
    try:
        id_cancha = request.args.get('id_cancha')
        fecha_str = request.args.get('fecha_reserva')
        q = Reserva.query
        if id_cancha:
            q = q.filter(Reserva.id_cancha == int(id_cancha))
        if fecha_str:
            fecha = date_from_str(fecha_str)
            q = q.filter(Reserva.fecha_reserva == fecha)
    except Exception:
        return jsonify({'error': 'Parámetros inválidos'}), 400

    reservas = q.all()
    out = []
    for r in reservas:
        # incluir información de pago si existe (último pago registrado)
        # obtener último pago registrado para esta reserva (si existe)
        last_pago = None
        pagos_res = Pago.query.filter_by(id_reserva=r.id_reserva).order_by(Pago.fecha_pago).all()
        if pagos_res and len(pagos_res) > 0:
            p = pagos_res[-1]
            metodo = MetodoPago.query.get(p.id_metodo)
            last_pago = {'id_pago': p.id_pago, 'id_metodo': p.id_metodo, 'metodo_nombre': metodo.nombre if metodo else None, 'monto': str(p.monto)}

        out.append({
            'id_reserva': r.id_reserva,
            'id_cliente': r.id_cliente,
            'cliente_nombre': getattr(r.cliente, 'nombre', None),
            'cliente_apellido': getattr(r.cliente, 'apellido', None),
            'id_cancha': r.id_cancha,
            'fecha_reserva': r.fecha_reserva.isoformat(),
            'hora_inicio': r.hora_inicio.strftime('%H:%M'),
            'hora_fin': r.hora_fin.strftime('%H:%M'),
            'precio_total': str(r.precio_total),
            'usa_iluminacion': bool(r.usa_iluminacion),
            'pago': last_pago,
        })
    return jsonify(out)


@bp.route('/<int:id_reserva>', methods=['DELETE'])
def delete_reserva(id_reserva):
    r = Reserva.query.get(id_reserva)
    if not r:
        return jsonify({'error': 'Reserva no encontrada'}), 404
    try:
        db.session.delete(r)
        db.session.commit()
        return jsonify({'ok': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al eliminar reserva'}), 500


@bp.route('/<int:id_reserva>', methods=['GET'])
def get_reserva(id_reserva):
    r = Reserva.query.get(id_reserva)
    if not r:
        return jsonify({'error': 'Reserva no encontrada'}), 404
    servicios = []
    for rs in r.reservas_servicios:
        servicios.append({'id_servicio': rs.id_servicio, 'cantidad': rs.cantidad})
    out = {
        'id_reserva': r.id_reserva,
        'id_cliente': r.id_cliente,
        'id_cancha': r.id_cancha,
        'fecha_reserva': r.fecha_reserva.isoformat(),
        'hora_inicio': r.hora_inicio.strftime('%H:%M'),
        'hora_fin': r.hora_fin.strftime('%H:%M'),
        'usa_iluminacion': bool(r.usa_iluminacion),
        'precio_total': str(r.precio_total),
        'servicios_adicionales': servicios,
        # incluir información de pago (último pago) para facilitar edición/pago desde el cliente
        'pago': None
    }
    # buscar último pago asociado
    pagos = Pago.query.filter_by(id_reserva=r.id_reserva).order_by(Pago.fecha_pago).all() if r else []
    if pagos and len(pagos) > 0:
        p = pagos[-1]
        metodo = MetodoPago.query.get(p.id_metodo)
        out['pago'] = {'id_pago': p.id_pago, 'id_metodo': p.id_metodo, 'metodo_nombre': metodo.nombre if metodo else None, 'monto': str(p.monto)}

    return jsonify(out)


@bp.route('/check', methods=['GET'])
def check_disponibilidad():
    """Verifica si un intervalo en una cancha y fecha está disponible.

    Query params esperados: id_cancha, fecha_reserva (YYYY-MM-DD), hora_inicio (HH:MM), hora_fin (HH:MM)
    Retorna JSON { available: True } o { available: False, reason: '...' }
    """
    try:
        id_cancha = int(request.args.get('id_cancha'))
        fecha_reserva = date_from_str(request.args.get('fecha_reserva'))
        hora_inicio = time_from_str(request.args.get('hora_inicio'))
        hora_fin = time_from_str(request.args.get('hora_fin'))
    except Exception:
        return jsonify({'error': 'Parámetros inválidos. id_cancha int, fecha: YYYY-MM-DD, horas: HH:MM'}), 400

    # Validar minutos en 00 o 30 y permitir cruce a día siguiente hasta 01:00
    if hora_inicio.minute not in (0, 30) or hora_fin.minute not in (0, 30):
        return jsonify({'available': False, 'reason': 'HORAS_DEBEN_TENER_00_O_30'}), 200

    dt_start = datetime.combine(fecha_reserva, hora_inicio)
    dt_end = datetime.combine(fecha_reserva, hora_fin)
    if dt_end <= dt_start:
        dt_end = dt_end + timedelta(days=1)

    window_start = datetime.combine(fecha_reserva, datetime.strptime('10:00', '%H:%M').time())
    window_end = datetime.combine(fecha_reserva + timedelta(days=1), datetime.strptime('01:00', '%H:%M').time())
    if dt_start < window_start or dt_end > window_end:
        return jsonify({'available': False, 'reason': 'HORARIO_FUERA_RANGO_10_01'}), 200

    cancha = Cancha.query.get(id_cancha)
    if not cancha or not cancha.activa:
        return jsonify({'available': False, 'reason': 'cancha_no_existente_o_inactiva'}), 200

    # Duraciones por deporte
    # determinar duración esperada por deporte
    if getattr(cancha, 'deporte', None):
        try:
            duracion_minutos = int(cancha.deporte.duracion_minutos or 60)
        except Exception:
            duracion_minutos = 60
    else:
        deporte = (cancha.tipo_deporte or '').strip().lower()
        DURACIONES_MIN = {
            'padel': 60,
            'pádel': 60,
            'tenis': 120,
            'futbol': 90,
            'fútbol': 90,
            'basket': 60,
            'basquet': 60,
            'baloncesto': 60,
        }
        duracion_minutos = DURACIONES_MIN.get(deporte, 60)
    expected_end = dt_start + timedelta(minutes=duracion_minutos)
    if expected_end != dt_end:
        return jsonify({'available': False, 'reason': f'DURACION_ESPERADA_{duracion_minutos}_MIN'}), 200

    # Si hay horarios definidos para la cancha, validar que el horario solicitado esté contenido
    horarios = HorarioDisponible.query.filter_by(id_cancha=id_cancha).all()
    if horarios:
        weekday_es = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][fecha_reserva.weekday()]
        ok = False
        for h in horarios:
            if h.dia_semana and h.dia_semana.lower() != weekday_es.lower():
                continue
            if (h.hora_inicio <= hora_inicio) and (h.hora_fin >= hora_fin) and h.disponible:
                ok = True
                break
        if not ok:
            return jsonify({'available': False, 'reason': 'HORARIO_DISPONIBLE: La cancha no tiene un horario que cubra el intervalo solicitado'}), 200

    # Verificar solapamientos con otras reservas y partidos (considerar día anterior para cruces de medianoche)
    candidate_dates = [fecha_reserva, fecha_reserva - timedelta(days=1)]
    existing_reservas = Reserva.query.filter(
        Reserva.id_cancha == id_cancha,
        Reserva.fecha_reserva.in_(candidate_dates)
    ).all()
    def to_dt_interval_res(res):
        s = datetime.combine(res.fecha_reserva, res.hora_inicio)
        e = datetime.combine(res.fecha_reserva, res.hora_fin)
        if e <= s:
            e = e + timedelta(days=1)
        return s, e
    for ex in existing_reservas:
        s_ex, e_ex = to_dt_interval_res(ex)
        if dt_start < e_ex and s_ex < dt_end:
            return jsonify({'available': False, 'reason': 'RESERVAS: Ya existe una reserva en ese horario para la cancha seleccionada'}), 200

    existing_partidos = Partido.query.filter(
        Partido.id_cancha == id_cancha,
        Partido.fecha_partido.in_(candidate_dates)
    ).all()
    def to_dt_interval_part(p):
        s = datetime.combine(p.fecha_partido, p.hora_inicio)
        e = datetime.combine(p.fecha_partido, p.hora_fin)
        if e <= s:
            e = e + timedelta(days=1)
        return s, e
    for p in existing_partidos:
        s_p, e_p = to_dt_interval_part(p)
        if dt_start < e_p and s_p < dt_end:
            return jsonify({'available': False, 'reason': 'PARTIDOS: Ya existe un partido en ese horario para la cancha seleccionada'}), 200

    return jsonify({'available': True}), 200
