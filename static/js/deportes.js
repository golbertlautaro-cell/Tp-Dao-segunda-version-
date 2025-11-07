// JS para la gestión ABMC de Deportes y Servicios
const API_DEPORTES = '/api/deportes';

async function fetchJson(url, opts){
  try{ const r = await fetch(url, opts); if(!r.ok) throw r; return await r.json(); }catch(e){ return null; }
}

async function loadDeportes(){
  const res = await fetchJson(API_DEPORTES);
  const tbody = document.querySelector('#deportes-table tbody');
  tbody.innerHTML = '';
  if(!res || res.length === 0){
    tbody.innerHTML = '<tr><td colspan="5" class="text-muted">No hay deportes definidos</td></tr>';
    return;
  }
  res.forEach(d => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${d.id_deporte}</td>
      <td>
        ${d.nombre}
        <div class="small text-muted">Servicios: ${(d.servicios||[]).length}</div>
      </td>
  <td>${d.duracion_minutos}</td>
      <td>
        <div class="d-flex flex-column">
          <div class="d-flex gap-2">
            <input type="text" class="form-control form-control-sm svc-name" data-id="${d.id_deporte}" placeholder="Nombre servicio">
            <input type="text" class="form-control form-control-sm svc-price" data-id="${d.id_deporte}" placeholder="Precio">
            <button class="btn btn-sm btn-success btn-add-svc" data-id="${d.id_deporte}">Agregar</button>
          </div>
          <div class="mt-1 svc-list text-muted small" data-id="${d.id_deporte}"></div>
        </div>
      </td>
      <td>
        <button class="btn btn-sm btn-primary btn-edit" data-id="${d.id_deporte}">Editar</button>
        <button class="btn btn-sm btn-danger btn-delete" data-id="${d.id_deporte}">Eliminar</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  document.querySelectorAll('.btn-edit').forEach(b => b.addEventListener('click', onEdit));
  document.querySelectorAll('.btn-delete').forEach(b => b.addEventListener('click', onDelete));
  // agregar servicio inline
  document.querySelectorAll('.btn-add-svc').forEach(b => b.addEventListener('click', async (ev) => {
    const id = ev.currentTarget.dataset.id;
    const row = ev.currentTarget.closest('tr');
    const nameInput = row.querySelector('.svc-name[data-id="'+id+'"]');
    const priceInput = row.querySelector('.svc-price[data-id="'+id+'"]');
    const nombre = (nameInput && nameInput.value || '').trim();
    const precio = (priceInput && priceInput.value || '').trim();
    if(!nombre){ alert('Ingrese nombre del servicio'); return; }
    if(!precio){ alert('Ingrese precio del servicio'); return; }
    const body = { nombre, precio_adicional: precio };
    const res = await fetchJson(`${API_DEPORTES}/${id}/servicios`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if(res && res.id_servicio){
      // limpiar inputs y recargar lista parcial
      if(nameInput) nameInput.value = '';
      if(priceInput) priceInput.value = '';
      loadDeportes();
    } else {
      alert((res && res.error) ? res.error : 'Error creando servicio');
    }
  }));
  // poblar lista legible de servicios por deporte en cada fila
  document.querySelectorAll('.svc-list').forEach(async el => {
    const id = el.dataset.id;
    const svcs = await fetchJson(`${API_DEPORTES}/${id}/servicios`);
    if(svcs && svcs.length){
      el.textContent = svcs.map(s => `${s.nombre} $${s.precio_adicional}`).join(' • ');
    } else {
      el.textContent = 'Sin servicios';
    }
  });
}

async function onDelete(e){
  const id = e.target.dataset.id;
  if(!confirm('Eliminar deporte?')) return;
  const r = await fetchJson(`${API_DEPORTES}/${id}`, { method: 'DELETE' });
  if(r && !r.error) loadDeportes(); else alert(r && r.error ? r.error : 'Error eliminando');
}

async function onEdit(e){
  const id = e.target.dataset.id;
  const r = await fetchJson(`${API_DEPORTES}/${id}`);
  if(!r) return alert('No se pudo cargar deporte');
  document.getElementById('editingId').value = r.id_deporte;
  document.getElementById('nombre').value = r.nombre;
  document.getElementById('duracion_minutos').value = r.duracion_minutos;
  // cargar servicios existentes en el form de edición
  const svcArea = document.getElementById('new-services');
  svcArea.innerHTML = '';
  (r.servicios||[]).forEach(s => {
    const row = document.createElement('div');
    row.className = 'd-flex gap-2 mb-2 svc-row';
    row.innerHTML = `<input type="text" class="form-control form-control-sm new-svc-name" value="${s.nombre}">` +
                    `<input type="text" class="form-control form-control-sm new-svc-price" value="${s.precio_adicional}">` +
                    `<button type="button" class="btn btn-sm btn-remove-svc">X</button>`;
    svcArea.appendChild(row);
  });
  document.getElementById('btn-submit').textContent = 'Actualizar';
}

document.getElementById('deporte-form').addEventListener('submit', async function(ev){
  ev.preventDefault();
  const editingId = document.getElementById('editingId').value;
  const payload = {
    nombre: document.getElementById('nombre').value.trim(),
    duracion_minutos: parseInt(document.getElementById('duracion_minutos').value) || 60,
    // recoger servicios del form
    servicios: Array.from(document.querySelectorAll('#new-services .svc-row')).map(row => {
      const nombre = (row.querySelector('.new-svc-name') && row.querySelector('.new-svc-name').value || '').trim();
      const precio = (row.querySelector('.new-svc-price') && row.querySelector('.new-svc-price').value || '').trim();
      return nombre ? { nombre, precio_adicional: precio } : null;
    }).filter(x => x)
  };
  let res;
  if(editingId){
    // update deporte: first update basic fields, then sync services by simple approach: re-create sent services
    const patch = { nombre: payload.nombre, duracion_minutos: payload.duracion_minutos };
    res = await fetchJson(`${API_DEPORTES}/${editingId}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(patch) });
    if(res && !res.error){
      // create services sent in payload
      for(const s of payload.servicios || []){
        await fetchJson(`${API_DEPORTES}/${editingId}/servicios`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(s) });
      }
    }
  } else {
    res = await fetchJson(API_DEPORTES, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  }
  if(res && !res.error){ resetForm(); loadDeportes(); } else { alert(res && res.error ? res.error : 'Error guardando deporte'); }
});

function resetForm(){
  document.getElementById('editingId').value = '';
  document.getElementById('deporte-form').reset();
  document.getElementById('btn-submit').textContent = 'Guardar';
  // reset services area to a single empty row
  const svcArea = document.getElementById('new-services');
  svcArea.innerHTML = '';
  const row = document.createElement('div');
  row.className = 'd-flex gap-2 mb-2 svc-row';
  row.innerHTML = '<input type="text" class="form-control form-control-sm new-svc-name" placeholder="Nombre del servicio">' +
                  '<input type="text" class="form-control form-control-sm new-svc-price" placeholder="Precio (ej: 150.00)">' +
                  '<button type="button" class="btn btn-sm btn-remove-svc">X</button>';
  svcArea.appendChild(row);
}
document.getElementById('btn-reset').addEventListener('click', resetForm);

// Inicializar
loadDeportes();


async function onServicios(e){
  const id = e.target.dataset.id;
  // Obtener servicios existentes
  const svcList = await fetchJson(`${API_DEPORTES}/${id}/servicios`);
  let msg = `Servicios para deporte ${id}:\n`;
  (svcList||[]).forEach(s => msg += `${s.id_servicio}: ${s.nombre} — $${s.precio_adicional}\n`);
  msg += '\n¿Desea agregar un servicio nuevo? (OK = sí)';
  if(confirm(msg)){
    const nombre = prompt('Nombre del servicio');
    if(!nombre) return;
    const precio = prompt('Precio (ej: 150.00)');
    if(!precio) return;
    const body = { nombre, precio_adicional: precio };
    const res = await fetchJson(`${API_DEPORTES}/${id}/servicios`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if(res && res.id_servicio) alert('Servicio creado'); else alert((res && res.error) ? res.error : 'Error creando servicio');
    loadDeportes();
  }
}

// agregar nuevo row de servicio en el form principal
document.getElementById('btn-add-service').addEventListener('click', function(){
  const svcArea = document.getElementById('new-services');
  const row = document.createElement('div');
  row.className = 'd-flex gap-2 mb-2 svc-row';
  row.innerHTML = '<input type="text" class="form-control form-control-sm new-svc-name" placeholder="Nombre del servicio">' +
                  '<input type="text" class="form-control form-control-sm new-svc-price" placeholder="Precio (ej: 150.00)">' +
                  '<button type="button" class="btn btn-sm btn-remove-svc">X</button>';
  svcArea.appendChild(row);
});

// delegado para remover filas de servicio (tanto del form como en edición)
document.addEventListener('click', function(ev){
  if(ev.target && ev.target.classList && ev.target.classList.contains('btn-remove-svc')){
    const row = ev.target.closest('.svc-row');
    if(row) row.remove();
  }
});
