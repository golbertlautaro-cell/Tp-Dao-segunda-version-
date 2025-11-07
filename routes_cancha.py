from flask import Blueprint, request, jsonify
from models import Cancha, HorarioDisponible, Reserva, Partido, ReservaServicio, Pago
from datetime import datetime
from app import db

bp = Blueprint('canchas', __name__)


def cancha_to_dict(c: Cancha):
    return {
        'id_cancha': c.id_cancha,
        'nombre': c.nombre,
        'tipo_deporte': c.tipo_deporte,
        'id_deporte': getattr(c, 'id_deporte', None),
        'deporte': {
            'id_deporte': c.deporte.id_deporte,
            'nombre': c.deporte.nombre,
            'duracion_minutos': c.deporte.duracion_minutos,
        } if getattr(c, 'deporte', None) else None,
        'superficie': c.superficie,
        'precio_hora': str(c.precio_hora) if c.precio_hora is not None else None,
        'iluminacion': c.iluminacion,
        'activa': c.activa,
    }


@bp.route('/', methods=['GET'])
def get_canchas():
    # Por defecto devolver solo canchas activas. Pasar ?all=true para incluir inactivas.
    include_all = request.args.get('all', 'false').lower() == 'true'
    if include_all:
        canchas = Cancha.query.order_by(Cancha.id_cancha).all()
    else:
        canchas = Cancha.query.filter_by(activa=True).order_by(Cancha.id_cancha).all()
    return jsonify([cancha_to_dict(c) for c in canchas])


@bp.route('/<int:id_cancha>', methods=['GET'])
def get_cancha(id_cancha):
    c = Cancha.query.get_or_404(id_cancha)
    return jsonify(cancha_to_dict(c))


def horario_to_dict(h: HorarioDisponible):
    return {
        'id_horario': h.id_horario,
        'id_cancha': h.id_cancha,
        'dia_semana': h.dia_semana,
        'hora_inicio': h.hora_inicio.strftime('%H:%M'),
        'hora_fin': h.hora_fin.strftime('%H:%M'),
        'disponible': h.disponible,
        'requiere_iluminacion': h.requiere_iluminacion,
    }


@bp.route('/<int:id_cancha>/horarios', methods=['GET'])
def get_horarios_cancha(id_cancha):
    """Listar horarios definidos para una cancha.

    Query params opcionales:
    - fecha=YYYY-MM-DD : si se provee, cada horario incluirá 'disponible_para_fecha' teniendo en cuenta reservas y partidos en esa fecha.
    """
    cancha = Cancha.query.get_or_404(id_cancha)
    fecha_str = request.args.get('fecha')
    fecha = None
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}), 400

    horarios = HorarioDisponible.query.filter_by(id_cancha=id_cancha).all()
    result = []
    for h in horarios:
        hd = horario_to_dict(h)
        if fecha:
            # comprobar que el dia coincida si dia_semana está definido
            weekday_es = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][fecha.weekday()]
            if h.dia_semana and h.dia_semana.lower() != weekday_es.lower():
                hd['disponible_para_fecha'] = False
                hd['motivo_no_disponible'] = 'DIA_NO_COINCIDE'
                result.append(hd)
                continue

            # comprobar solapamientos con reservas y partidos en esa fecha
            # si el horario no está marcado como disponible, no está disponible
            if not h.disponible:
                hd['disponible_para_fecha'] = False
                hd['motivo_no_disponible'] = 'HORARIO_NO_DISPONIBLE'
                result.append(hd)
                continue

            # buscar reservas que solapen
            reservas_ov = Reserva.query.filter(
                Reserva.id_cancha == id_cancha,
                Reserva.fecha_reserva == fecha,
                Reserva.hora_fin > h.hora_inicio,
                Reserva.hora_inicio < h.hora_fin,
            ).first()
            if reservas_ov:
                hd['disponible_para_fecha'] = False
                hd['motivo_no_disponible'] = 'RESERVA_EXISTENTE'
                result.append(hd)
                continue

            partidos_ov = Partido.query.filter(
                Partido.id_cancha == id_cancha,
                Partido.fecha_partido == fecha,
                Partido.hora_fin > h.hora_inicio,
                Partido.hora_inicio < h.hora_fin,
            ).first()
            if partidos_ov:
                hd['disponible_para_fecha'] = False
                hd['motivo_no_disponible'] = 'PARTIDO_EXISTENTE'
                result.append(hd)
                continue

            # si pasó todas las comprobaciones
            hd['disponible_para_fecha'] = True
        result.append(hd)

    return jsonify(result)


@bp.route('/', methods=['POST'])
def create_cancha():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error': 'nombre es obligatorio'}), 400

    cancha = Cancha(
        nombre=nombre,
        tipo_deporte=data.get('tipo_deporte'),
        id_deporte=data.get('id_deporte'),
        superficie=data.get('superficie'),
        precio_hora=data.get('precio_hora') or 0,
        iluminacion=data.get('iluminacion'),
    )
    db.session.add(cancha)
    db.session.commit()

    return jsonify(cancha_to_dict(cancha)), 201


@bp.route('/<int:id_cancha>', methods=['PUT'])
def update_cancha(id_cancha):
    cancha = Cancha.query.get_or_404(id_cancha)
    data = request.get_json() or {}

    for field in ('nombre', 'tipo_deporte', 'superficie', 'precio_hora', 'iluminacion', 'activa'):
        if field in data:
            setattr(cancha, field, data.get(field))
    # permitir actualizar id_deporte
    if 'id_deporte' in data:
        cancha.id_deporte = data.get('id_deporte')

    db.session.commit()
    return jsonify(cancha_to_dict(cancha))


@bp.route('/<int:id_cancha>', methods=['DELETE'])
def delete_cancha(id_cancha):
    cancha = Cancha.query.get_or_404(id_cancha)
    # por defecto hacemos hard delete (físico). Pasar ?hard=false para soft-delete
    hard = request.args.get('hard', 'true').lower() == 'true'
    if not hard:
        cancha.activa = False
        db.session.commit()
        return jsonify({'message': 'Cancha desactivada'})

    try:
        # eliminar servicios/pagos asociados a reservas de esta cancha
        reservas = Reserva.query.filter_by(id_cancha=id_cancha).all()
        for r in reservas:
            ReservaServicio.query.filter_by(id_reserva=r.id_reserva).delete()
            Pago.query.filter_by(id_reserva=r.id_reserva).delete()

        # eliminar reservas
        Reserva.query.filter_by(id_cancha=id_cancha).delete()

        # eliminar partidos en la cancha
        Partido.query.filter_by(id_cancha=id_cancha).delete()

        # eliminar horarios disponibles
        HorarioDisponible.query.filter_by(id_cancha=id_cancha).delete()

        # eliminar la cancha
        db.session.delete(cancha)
        db.session.commit()
        return jsonify({'message': 'Cancha eliminada definitivamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al eliminar cancha', 'details': str(e)}), 500
