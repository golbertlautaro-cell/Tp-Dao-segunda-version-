from flask import Blueprint, request, jsonify
from models import Cancha
from app import db

bp = Blueprint('canchas', __name__)


def cancha_to_dict(c: Cancha):
    return {
        'id_cancha': c.id_cancha,
        'nombre': c.nombre,
        'tipo_deporte': c.tipo_deporte,
        'superficie': c.superficie,
        'precio_hora': str(c.precio_hora) if c.precio_hora is not None else None,
        'iluminacion': c.iluminacion,
        'activa': c.activa,
    }


@bp.route('/', methods=['GET'])
def get_canchas():
    canchas = Cancha.query.all()
    return jsonify([cancha_to_dict(c) for c in canchas])


@bp.route('/<int:id_cancha>', methods=['GET'])
def get_cancha(id_cancha):
    c = Cancha.query.get_or_404(id_cancha)
    return jsonify(cancha_to_dict(c))


@bp.route('/', methods=['POST'])
def create_cancha():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error': 'nombre es obligatorio'}), 400

    cancha = Cancha(
        nombre=nombre,
        tipo_deporte=data.get('tipo_deporte'),
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

    db.session.commit()
    return jsonify(cancha_to_dict(cancha))


@bp.route('/<int:id_cancha>', methods=['DELETE'])
def delete_cancha(id_cancha):
    cancha = Cancha.query.get_or_404(id_cancha)
    cancha.activa = False
    db.session.commit()
    return jsonify({'message': 'Cancha desactivada'})
