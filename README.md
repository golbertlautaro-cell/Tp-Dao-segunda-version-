# Tp-Dao

Proyecto de gestión de reservas de canchas (Flask + SQLAlchemy).

Contenido principal:
- `app.py` - creación de la app Flask y registro de blueprints
- `models.py` - modelos SQLAlchemy
- `routes_*.py` - blueprints para clientes, canchas, reservas, pagos, reportes, campeonatos
- `templates/` - páginas HTML (clientes, canchas, reservar, reportes, dashboard)
- `seed.py` - script para insertar datos de ejemplo

Instrucciones rápidas:
1. Crear entorno virtual y activar
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Instalar dependencias
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Poblar la base de datos (opcional)
   ```powershell
   python seed.py
   ```
4. Ejecutar la app
   ```powershell
   python app.py
   ```

Luego abre http://127.0.0.1:5000/ui en el navegador.
