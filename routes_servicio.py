from flask import Blueprint, jsonify, request
from app import db
from models import ServicioAdicional

bp = Blueprint('servicios', __name__)


@bp.route('/servicios', methods=['GET'])
def list_servicios():
    items = ServicioAdicional.query.filter_by(activo=True).all()
    return jsonify([{
        'id_servicio': s.id_servicio,
        'nombre': s.nombre,
        'precio_adicional': str(s.precio_adicional),
        'activo': s.activo,
        'id_deporte': s.id_deporte,
    } for s in items])
