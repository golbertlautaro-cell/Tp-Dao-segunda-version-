from flask import Blueprint, request, jsonify
from app import db
from models import Deporte, ServicioAdicional

bp = Blueprint('deportes', __name__)


def _parse_price(value):
    """Intentar parsear un precio tolerante a formatos (coma como separador, strings vacíos)."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    # aceptar coma como separador decimal
    s = s.replace(',', '.')
    try:
        return float(s)
    except Exception:
        return 0.0


def deporte_to_dict(d: Deporte):
    return {
        'id_deporte': d.id_deporte,
        'nombre': d.nombre,
        'duracion_minutos': d.duracion_minutos,
        # 'necesita_arbitros' removed from API (árbitros son ahora servicios)
        'servicios': [
            {'id_servicio': s.id_servicio, 'nombre': s.nombre, 'precio_adicional': str(s.precio_adicional), 'activo': bool(s.activo)}
            for s in getattr(d, 'servicios_adicionales', [])
        ]
    }


@bp.route('/', methods=['GET'])
def list_deportes():
    deps = Deporte.query.order_by(Deporte.nombre).all()
    return jsonify([deporte_to_dict(d) for d in deps])


@bp.route('/<int:id_deporte>', methods=['GET'])
def get_deporte(id_deporte):
    d = Deporte.query.get_or_404(id_deporte)
    return jsonify(deporte_to_dict(d))


@bp.route('/', methods=['POST'])
def create_deporte():
    data = request.get_json() or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'nombre es obligatorio'}), 400
    dur = int(data.get('duracion_minutos') or 60)
    d = Deporte(nombre=nombre, duracion_minutos=dur)
    db.session.add(d)
    db.session.commit()
    # si se enviaron servicios en el payload, créelos asociados al deporte
    servicios = data.get('servicios') or []
    created = []
    for s in servicios:
        nombre_s = (s.get('nombre') or '').strip()
        precio = _parse_price(s.get('precio_adicional'))
        if not nombre_s:
            continue
        svc = ServicioAdicional(nombre=nombre_s, precio_adicional=precio, id_deporte=d.id_deporte, activo=True)
        db.session.add(svc)
        created.append(svc)
    if created:
        db.session.commit()
    return jsonify(deporte_to_dict(d)), 201


@bp.route('/<int:id_deporte>', methods=['PUT'])
def update_deporte(id_deporte):
    d = Deporte.query.get_or_404(id_deporte)
    data = request.get_json() or {}
    if 'nombre' in data:
        d.nombre = data.get('nombre')
    if 'duracion_minutos' in data:
        d.duracion_minutos = int(data.get('duracion_minutos') or d.duracion_minutos)
    # permitir agregar servicios al actualizar si vienen en payload
    servicios = data.get('servicios') or []
    created = []
    for s in servicios:
        nombre_s = (s.get('nombre') or '').strip()
        precio = _parse_price(s.get('precio_adicional'))
        if not nombre_s:
            continue
        svc = ServicioAdicional(nombre=nombre_s, precio_adicional=precio, id_deporte=d.id_deporte, activo=True)
        db.session.add(svc)
        created.append(svc)
    db.session.commit()
    if created:
        db.session.commit()
    return jsonify(deporte_to_dict(d))


@bp.route('/<int:id_deporte>', methods=['DELETE'])
def delete_deporte(id_deporte):
    d = Deporte.query.get_or_404(id_deporte)
    try:
        db.session.delete(d)
        db.session.commit()
        return jsonify({'message': 'Deporte eliminado'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'No se pudo eliminar deporte', 'details': str(e)}), 500


# Endpoints para servicios por deporte (listado y creación individual)
@bp.route('/<int:id_deporte>/servicios', methods=['GET'])
def list_servicios(id_deporte):
    d = Deporte.query.get_or_404(id_deporte)
    servicios = getattr(d, 'servicios_adicionales', [])
    out = []
    for s in servicios:
        out.append({'id_servicio': s.id_servicio, 'nombre': s.nombre, 'precio_adicional': str(s.precio_adicional), 'activo': bool(s.activo)})
    return jsonify(out)


@bp.route('/<int:id_deporte>/servicios', methods=['POST'])
def add_servicio(id_deporte):
    d = Deporte.query.get_or_404(id_deporte)
    data = request.get_json() or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'nombre es obligatorio'}), 400
    precio = _parse_price(data.get('precio_adicional'))
    svc = ServicioAdicional(nombre=nombre, precio_adicional=precio, id_deporte=id_deporte, activo=bool(data.get('activo', True)))
    db.session.add(svc)
    db.session.commit()
    return jsonify({'id_servicio': svc.id_servicio, 'nombre': svc.nombre, 'precio_adicional': str(svc.precio_adicional), 'activo': bool(svc.activo)}), 201

