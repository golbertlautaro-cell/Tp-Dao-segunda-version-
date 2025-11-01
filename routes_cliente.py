from flask import Blueprint, request, jsonify
from models import Cliente
from app import db

bp = Blueprint('clientes', __name__)


def cliente_to_dict(c: Cliente):
    return {
        'id_cliente': c.id_cliente,
        'dni': c.dni,
        'nombre': c.nombre,
        'apellido': c.apellido,
        'telefono': c.telefono,
        'email': c.email,
        'activo': c.activo,
    }


@bp.route('/', methods=['GET'])
def get_clientes():
    clientes = Cliente.query.all()
    return jsonify([cliente_to_dict(c) for c in clientes])


@bp.route('/<int:id_cliente>', methods=['GET'])
def get_cliente(id_cliente):
    c = Cliente.query.get_or_404(id_cliente)
    return jsonify(cliente_to_dict(c))


@bp.route('/', methods=['POST'])
def create_cliente():
    data = request.get_json() or {}
    dni = data.get('dni')
    nombre = data.get('nombre')
    apellido = data.get('apellido')
    telefono = data.get('telefono')
    email = data.get('email')

    if not dni or not nombre or not apellido:
        return jsonify({'error': 'dni, nombre y apellido son obligatorios'}), 400

    # Validar unicidad de dni y email
    if Cliente.query.filter_by(dni=dni).first():
        return jsonify({'error': 'DNI ya registrado'}), 400
    if email and Cliente.query.filter_by(email=email).first():
        return jsonify({'error': 'Email ya registrado'}), 400

    cliente = Cliente(dni=dni, nombre=nombre, apellido=apellido, telefono=telefono, email=email)
    db.session.add(cliente)
    db.session.commit()

    return jsonify(cliente_to_dict(cliente)), 201


@bp.route('/<int:id_cliente>', methods=['PUT'])
def update_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    data = request.get_json() or {}

    dni = data.get('dni')
    email = data.get('email')

    # Si se intenta cambiar el DNI, verificar que no exista en otro registro
    if dni and dni != cliente.dni:
        if Cliente.query.filter(Cliente.dni == dni, Cliente.id_cliente != cliente.id_cliente).first():
            return jsonify({'error': 'DNI ya registrado por otro cliente'}), 400
        cliente.dni = dni

    if email and email != cliente.email:
        if Cliente.query.filter(Cliente.email == email, Cliente.id_cliente != cliente.id_cliente).first():
            return jsonify({'error': 'Email ya registrado por otro cliente'}), 400
        cliente.email = email

    # Campos opcionales
    for field in ('nombre', 'apellido', 'telefono'):
        if field in data:
            setattr(cliente, field, data.get(field))

    db.session.commit()
    return jsonify(cliente_to_dict(cliente))


@bp.route('/<int:id_cliente>', methods=['DELETE'])
def delete_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    cliente.activo = False
    db.session.commit()
    return jsonify({'message': 'Cliente desactivado'})
