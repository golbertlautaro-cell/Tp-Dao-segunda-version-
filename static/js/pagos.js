// pagos.js
// Muestra lista de reservas y permite pagar o eliminar desde la UI de pagos
const API_RESERVAS = '/api/reservas';
const API_METODOS = '/api/metodos';

async function fetchJson(url, opts){
  try{ const r = await fetch(url, opts); if(!r.ok) return null; return await r.json(); }catch(e){ return null; }
}

async function renderPagosTable(){
  const placeholder = document.getElementById('pagos-table-placeholder');
  placeholder.innerHTML = '<div class="text-muted">Cargando...</div>';

  const reservas = await fetchJson(API_RESERVAS) || [];
  const metodos = await fetchJson(API_METODOS) || [];
  const metodoMap = {};
  metodos.forEach(m => metodoMap[m.id_metodo] = m.nombre);

  if(reservas.length === 0){
    placeholder.innerHTML = '<div class="alert alert-info">No hay reservas registradas</div>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'table table-striped';
  table.innerHTML = `
    <thead>
      <tr>
        <th>ID</th>
        <th>Cliente</th>
        <th>Cancha</th>
        <th>Fecha</th>
        <th>Horario</th>
        <th>Precio</th>
        <th>Pago</th>
        <th>Acciones</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector('tbody');

  reservas.forEach(r => {
    const tr = document.createElement('tr');
    const pagoInfo = r.pago && r.pago.metodo_nombre ? r.pago.metodo_nombre + ' $' + r.pago.monto : 'Pendiente';
    const cliente = (r.cliente_nombre || '') + ' ' + (r.cliente_apellido || '');
    tr.innerHTML = `
      <td>${r.id_reserva}</td>
      <td>${cliente}</td>
      <td>${r.id_cancha}</td>
      <td>${r.fecha_reserva}</td>
      <td>${r.hora_inicio} - ${r.hora_fin}</td>
      <td>$${r.precio_total}</td>
      <td>${pagoInfo}</td>
      <td></td>
    `;

    // acciones
    const actionsTd = tr.querySelector('td:last-child');

    // Pagar (si no está pagada)
    if(!r.pago || !r.pago.metodo_nombre){
      const payBtn = document.createElement('button');
      payBtn.className = 'btn btn-sm btn-success me-1';
      payBtn.textContent = 'Pagar';
      payBtn.addEventListener('click', () => showPayRow(tr, r, metodoMap));
      actionsTd.appendChild(payBtn);
    } else {
      const viewBadge = document.createElement('span');
      viewBadge.className = 'badge bg-info text-dark me-1';
      viewBadge.textContent = 'Pagada';
      actionsTd.appendChild(viewBadge);
    }

    // Eliminar
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-sm btn-outline-danger';
    delBtn.textContent = 'Eliminar';
    delBtn.addEventListener('click', async ()=>{
      if(!confirm('Eliminar reserva?')) return;
      const resp = await fetch(`${API_RESERVAS}/${r.id_reserva}`, {method:'DELETE'});
      if(resp.ok) renderPagosTable(); else alert('Error al eliminar');
    });
    actionsTd.appendChild(delBtn);

    tbody.appendChild(tr);
  });

  placeholder.innerHTML = '';
  placeholder.appendChild(table);
}

function showPayRow(tr, reserva, metodoMap){
  // si ya existe una fila de pago abierta, quitarla
  const existing = document.querySelector('#pagos-table-placeholder .pay-row');
  if(existing) existing.remove();

  const payTr = document.createElement('tr');
  payTr.className = 'pay-row';
  payTr.innerHTML = `
    <td colspan="8">
      <div class="d-flex gap-2 align-items-center">
        <div>
          <label class="form-label mb-0">Método:</label>
          <select id="pay-metodo" class="form-select form-select-sm">
            <option value="">Seleccionar método...</option>
          </select>
        </div>
        <div>
          <label class="form-label mb-0">Monto:</label>
          <input id="pay-monto" class="form-control form-control-sm" style="width:120px;" value="${reserva.precio_total}">
        </div>
        <div class="mt-2">
          <button id="pay-confirm" class="btn btn-sm btn-primary">Confirmar pago</button>
          <button id="pay-cancel" class="btn btn-sm btn-secondary">Cancelar</button>
        </div>
      </div>
    </td>
  `;

  // insertar después de la fila original
  tr.parentNode.insertBefore(payTr, tr.nextSibling);

  // poblar select de metodos
  (async ()=>{
    const metodos = await fetchJson(API_METODOS) || [];
    const sel = payTr.querySelector('#pay-metodo');
    metodos.forEach(m => {
      const opt = document.createElement('option'); opt.value = m.id_metodo; opt.textContent = m.nombre; sel.appendChild(opt);
    });
  })();

  payTr.querySelector('#pay-cancel').addEventListener('click', ()=> payTr.remove());
  payTr.querySelector('#pay-confirm').addEventListener('click', async ()=>{
    const idMetodo = parseInt(payTr.querySelector('#pay-metodo').value);
    const monto = parseFloat(payTr.querySelector('#pay-monto').value);
    if(!idMetodo){ alert('Seleccione método'); return; }
    try{
      const res = await fetch(`${API_RESERVAS}/${reserva.id_reserva}/pagar`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id_metodo: idMetodo, monto: monto})});
      if(res.status === 201){
        alert('Pago registrado');
        payTr.remove();
        renderPagosTable();
      } else {
        const err = await res.json();
        alert('Error: ' + (err.error || ''));
      }
    }catch(e){ alert('Error de red'); }
  });
}

// inicializar
document.addEventListener('DOMContentLoaded', ()=>{
  renderPagosTable();
});
