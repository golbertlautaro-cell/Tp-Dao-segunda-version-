from flask import Blueprint, request, jsonify
from app import db
from models import Campeonato, Equipo, Partido, Cancha, Reserva, HorarioDisponible
from datetime import datetime
from decimal import Decimal

bp = Blueprint('campeonatos', __name__, url_prefix='/api')


### Campeonatos CRUD
@bp.route('/campeonatos', methods=['GET'])
def list_campeonatos():
    items = Campeonato.query.all()
    return jsonify([{
        'id_campeonato': c.id_campeonato,
        'nombre': c.nombre,
        'fecha_inicio': c.fecha_inicio.isoformat() if c.fecha_inicio else None,
        'fecha_fin': c.fecha_fin.isoformat() if c.fecha_fin else None,
        'estado': c.estado,
    } for c in items])


@bp.route('/campeonatos/<int:id_campeonato>', methods=['GET'])
def get_campeonato(id_campeonato):
    c = Campeonato.query.get_or_404(id_campeonato)
    return jsonify({'id_campeonato': c.id_campeonato, 'nombre': c.nombre, 'fecha_inicio': c.fecha_inicio.isoformat() if c.fecha_inicio else None, 'fecha_fin': c.fecha_fin.isoformat() if c.fecha_fin else None, 'estado': c.estado})


@bp.route('/campeonatos', methods=['POST'])
def create_campeonato():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error':'nombre es obligatorio'}), 400
    c = Campeonato(nombre=nombre, fecha_inicio=data.get('fecha_inicio'), fecha_fin=data.get('fecha_fin'), estado=data.get('estado'))
    db.session.add(c)
    db.session.commit()
    return jsonify({'id_campeonato': c.id_campeonato}), 201


@bp.route('/campeonatos/<int:id_campeonato>', methods=['PUT'])
def update_campeonato(id_campeonato):
    c = Campeonato.query.get_or_404(id_campeonato)
    data = request.get_json() or {}
    for field in ('nombre','fecha_inicio','fecha_fin','estado'):
        if field in data:
            setattr(c, field, data.get(field))
    db.session.commit()
    return jsonify({'message':'ok'})


@bp.route('/campeonatos/<int:id_campeonato>', methods=['DELETE'])
def delete_campeonato(id_campeonato):
    c = Campeonato.query.get_or_404(id_campeonato)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message':'eliminado'})


### Equipos CRUD
@bp.route('/equipos', methods=['GET'])
def list_equipos():
    items = Equipo.query.all()
    return jsonify([{'id_equipo': e.id_equipo, 'nombre': e.nombre, 'id_campeonato': e.id_campeonato, 'representante': e.representante, 'telefono': e.telefono} for e in items])


@bp.route('/equipos/<int:id_equipo>', methods=['GET'])
def get_equipo(id_equipo):
    e = Equipo.query.get_or_404(id_equipo)
    return jsonify({'id_equipo': e.id_equipo, 'nombre': e.nombre, 'id_campeonato': e.id_campeonato, 'representante': e.representante, 'telefono': e.telefono})


@bp.route('/equipos', methods=['POST'])
def create_equipo():
    data = request.get_json() or {}
    id_campeonato = data.get('id_campeonato')
    nombre = data.get('nombre')
    if not id_campeonato or not nombre:
        return jsonify({'error':'id_campeonato y nombre son obligatorios'}), 400
    e = Equipo(id_campeonato=id_campeonato, nombre=nombre, representante=data.get('representante'), telefono=data.get('telefono'))
    db.session.add(e)
    db.session.commit()
    return jsonify({'id_equipo': e.id_equipo}), 201


@bp.route('/equipos/<int:id_equipo>', methods=['PUT'])
def update_equipo(id_equipo):
    e = Equipo.query.get_or_404(id_equipo)
    data = request.get_json() or {}
    for field in ('nombre','representante','telefono'):
        if field in data:
            setattr(e, field, data.get(field))
    db.session.commit()
    return jsonify({'message':'ok'})


@bp.route('/equipos/<int:id_equipo>', methods=['DELETE'])
def delete_equipo(id_equipo):
    e = Equipo.query.get_or_404(id_equipo)
    db.session.delete(e)
    db.session.commit()
    return jsonify({'message':'eliminado'})


### Partidos
def time_from_str(s: str):
    return datetime.strptime(s, '%H:%M').time()


def date_from_str(s: str):
    return datetime.strptime(s, '%Y-%m-%d').date()


@bp.route('/partidos', methods=['POST'])
def create_partido():
    data = request.get_json() or {}
    try:
        id_campeonato = int(data.get('id_campeonato'))
        id_cancha = int(data.get('id_cancha'))
        equipo_local = int(data.get('equipo_local'))
        equipo_visitante = int(data.get('equipo_visitante'))
        fecha_partido = date_from_str(data.get('fecha_partido'))
        hora_inicio = time_from_str(data.get('hora_inicio'))
        hora_fin = time_from_str(data.get('hora_fin'))
    except Exception:
        return jsonify({'error':'Campos inválidos o formato incorrecto'}), 400

    if hora_inicio >= hora_fin:
        return jsonify({'error':'hora_inicio debe ser anterior a hora_fin'}), 400

    # existencia
    if not Campeonato.query.get(id_campeonato):
        return jsonify({'error':'Campeonato no encontrado'}), 400
    if not Equipo.query.get(equipo_local) or not Equipo.query.get(equipo_visitante):
        return jsonify({'error':'Equipos no encontrados'}), 400
    cancha = Cancha.query.get(id_cancha)
    if not cancha or not cancha.activa:
        return jsonify({'error':'Cancha no existe o no está activa'}), 400

    # Validar horarios disponibles (HORARIO_DISPONIBLE)
    horarios = HorarioDisponible.query.filter_by(id_cancha=id_cancha).all()
    if horarios:
        weekday_es = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][fecha_partido.weekday()]
        ok = False
        for h in horarios:
            if h.dia_semana and h.dia_semana.lower() != weekday_es.lower():
                continue
            if (h.hora_inicio <= hora_inicio) and (h.hora_fin >= hora_fin) and h.disponible:
                ok = True
                break
        if not ok:
            return jsonify({'error':'HORARIO_DISPONIBLE: La cancha no tiene horario disponible para el rango solicitado'}), 409

    # Verificar conflictos con reservas
    overlapping_res = Reserva.query.filter(
        Reserva.id_cancha == id_cancha,
        Reserva.fecha_reserva == fecha_partido,
        Reserva.hora_fin > hora_inicio,
        Reserva.hora_inicio < hora_fin,
    ).first()
    if overlapping_res:
        return jsonify({'error':'RESERVAS: Existe una reserva superpuesta en la cancha'}), 409

    # Verificar conflictos con otros partidos
    overlapping_partido = Partido.query.filter(
        Partido.id_cancha == id_cancha,
        Partido.fecha_partido == fecha_partido,
        Partido.hora_fin > hora_inicio,
        Partido.hora_inicio < hora_fin,
    ).first()
    if overlapping_partido:
        return jsonify({'error':'PARTIDOS: Existe otro partido superpuesto en la cancha'}), 409

    partido = Partido(
        id_campeonato=id_campeonato,
        id_cancha=id_cancha,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        fecha_partido=fecha_partido,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        jugado=False,
    )
    db.session.add(partido)
    db.session.commit()
    return jsonify({'id_partido': partido.id_partido}), 201


@bp.route('/partidos/<int:id_partido>/resultado', methods=['PUT'])
def set_resultado(id_partido):
    data = request.get_json() or {}
    partido = Partido.query.get_or_404(id_partido)
    goles_local = data.get('goles_local')
    goles_visitante = data.get('goles_visitante')
    try:
        partido.goles_local = int(goles_local)
        partido.goles_visitante = int(goles_visitante)
    except Exception:
        return jsonify({'error':'goles_local y goles_visitante deben ser enteros'}), 400
    partido.jugado = True
    db.session.commit()
    return jsonify({'message':'resultado guardado'})
