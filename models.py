from datetime import datetime
from app import db


class EstadoReserva(db.Model):
    """Lista de estados posibles para una reserva (ej: Pendiente, Confirmada, Cancelada)."""
    __tablename__ = 'estado_reserva'

    id_estado = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    # Relación 1:N a Reserva (un estado puede tener muchas reservas)
    reservas = db.relationship(
        'Reserva',
        backref='estado',
        cascade='all, delete-orphan',
        lazy=True
    )


class Reserva(db.Model):
    """Reserva detallada vinculada a cliente, cancha y estado."""
    __tablename__ = 'reservas'

    id_reserva = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    id_cancha = db.Column(db.Integer, db.ForeignKey('canchas.id_cancha'), nullable=False)
    id_estado = db.Column(db.Integer, db.ForeignKey('estado_reserva.id_estado'), nullable=False)
    fecha_reserva = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    precio_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    usa_iluminacion = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Reserva {self.id_reserva} cliente={self.id_cliente} cancha={self.id_cancha} {self.fecha_reserva} {self.hora_inicio}-{self.hora_fin}>"


class Cliente(db.Model):
    """Modelo para clientes.

    Campos:
    - id_cliente: PK autoincrement
    - dni: string (unique, not null)
    - nombre: string not null
    - apellido: string not null
    - telefono: string
    - email: string unique
    - activo: boolean (default True)
    """
    __tablename__ = 'clientes'

    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dni = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Cliente {self.id_cliente} {self.nombre} {self.apellido}>"

    # Relación 1:N a Reserva (un cliente puede tener muchas reservas)
    reservas = db.relationship(
        'Reserva',
        backref='cliente',
        cascade='all, delete-orphan',
        lazy=True
    )


class Cancha(db.Model):
    """Modelo para canchas.

    Campos:
    - id_cancha: PK autoincrement
    - nombre: string not null
    - tipo_deporte: string
    - superficie: string
    - precio_hora: decimal (10,2)
    - iluminacion: boolean
    - activa: boolean (default True)
    """
    __tablename__ = 'canchas'

    id_cancha = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_deporte = db.Column(db.String(50), nullable=True)
    superficie = db.Column(db.String(50), nullable=True)
    precio_hora = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    # Precio por hora adicional si se requiere iluminación (opcional)
    precio_iluminacion = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    iluminacion = db.Column(db.Boolean, nullable=True)
    activa = db.Column(db.Boolean, nullable=False, default=True)

    # Relación 1:N a HorarioDisponible (cada cancha puede tener muchos horarios)
    horarios_disponibles = db.relationship(
        'HorarioDisponible',
        backref='cancha',
        cascade='all, delete-orphan',
        lazy=True
    )

    # Relación 1:N a Reserva (una cancha puede tener muchas reservas)
    reservas = db.relationship(
        'Reserva',
        backref='cancha',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return f"<Cancha {self.id_cancha} {self.nombre}>"


class HorarioDisponible(db.Model):
    """Modelo para los horarios disponibles de una cancha.

    Campos:
    - id_horario: PK autoincrement
    - id_cancha: FK a canchas.id_cancha
    - dia_semana: String(20)
    - hora_inicio: Time
    - hora_fin: Time
    - disponible: Boolean default True
    - requiere_iluminacion: Boolean default False
    """
    __tablename__ = 'horarios_disponibles'

    id_horario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cancha = db.Column(db.Integer, db.ForeignKey('canchas.id_cancha'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    disponible = db.Column(db.Boolean, nullable=False, default=True)
    requiere_iluminacion = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<HorarioDisponible {self.id_horario} cancha={self.id_cancha} {self.dia_semana} {self.hora_inicio}-{self.hora_fin}>"


class ServicioAdicional(db.Model):
    """Servicios extra que se pueden agregar a una reserva (ej: alquiler de equipo)."""
    __tablename__ = 'servicios_adicionales'

    id_servicio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio_adicional = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    # Relación a la tabla pivot ReservaServicio
    reservas_servicios = db.relationship(
        'ReservaServicio',
        backref='servicio',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return f"<ServicioAdicional {self.id_servicio} {self.nombre}>"


class ReservaServicio(db.Model):
    """Tabla pivot que relaciona Reservas con ServiciosAdicionales (N:M)."""
    __tablename__ = 'reserva_servicio'

    id_reserva_servicio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_reserva = db.Column(db.Integer, db.ForeignKey('reservas.id_reserva'), nullable=False)
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios_adicionales.id_servicio'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f"<ReservaServicio {self.id_reserva_servicio} reserva={self.id_reserva} servicio={self.id_servicio} x{self.cantidad}>"


class MetodoPago(db.Model):
    """Métodos de pago disponibles (ej: Efectivo, Tarjeta, Transferencia)."""
    __tablename__ = 'metodos_pago'

    id_metodo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    # Relación 1:N con Pago
    pagos = db.relationship(
        'Pago',
        backref='metodo',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return f"<MetodoPago {self.id_metodo} {self.nombre}>"


class Pago(db.Model):
    """Registro de pagos realizados para reservas."""
    __tablename__ = 'pagos'

    id_pago = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_reserva = db.Column(db.Integer, db.ForeignKey('reservas.id_reserva'), nullable=False)
    id_metodo = db.Column(db.Integer, db.ForeignKey('metodos_pago.id_metodo'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_pago = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Pago {self.id_pago} reserva={self.id_reserva} {self.monto} {self.fecha_pago} [{self.estado}]>"


class Campeonato(db.Model):
    """Campeonatos que agrupan equipos y partidos."""
    __tablename__ = 'campeonatos'

    id_campeonato = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(200), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(50), nullable=True)

    # Relaciones: equipos y partidos pertenecientes al campeonato
    equipos = db.relationship(
        'Equipo',
        backref='campeonato',
        cascade='all, delete-orphan',
        lazy=True
    )
    partidos = db.relationship(
        'Partido',
        backref='campeonato',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return f"<Campeonato {self.id_campeonato} {self.nombre}>"


class Equipo(db.Model):
    """Equipos que participan en campeonatos."""
    __tablename__ = 'equipos'

    id_equipo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_campeonato = db.Column(db.Integer, db.ForeignKey('campeonatos.id_campeonato'), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    representante = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Equipo {self.id_equipo} {self.nombre}>"


class Partido(db.Model):
    """Partidos programados dentro de un campeonato."""
    __tablename__ = 'partidos'

    id_partido = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_campeonato = db.Column(db.Integer, db.ForeignKey('campeonatos.id_campeonato'), nullable=False)
    id_cancha = db.Column(db.Integer, db.ForeignKey('canchas.id_cancha'), nullable=False)
    equipo_local = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    equipo_visitante = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    fecha_partido = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    goles_local = db.Column(db.Integer, nullable=True)
    goles_visitante = db.Column(db.Integer, nullable=True)
    jugado = db.Column(db.Boolean, nullable=False, default=False)

    # Relaciones convenientes a equipos (no crean columnas adicionales)
    equipo_local_rel = db.relationship('Equipo', foreign_keys=[equipo_local], backref='partidos_local', lazy=True)
    equipo_visitante_rel = db.relationship('Equipo', foreign_keys=[equipo_visitante], backref='partidos_visitante', lazy=True)

    def __repr__(self):
        return f"<Partido {self.id_partido} {self.fecha_partido} {self.hora_inicio} {self.equipo_local} vs {self.equipo_visitante}>"
