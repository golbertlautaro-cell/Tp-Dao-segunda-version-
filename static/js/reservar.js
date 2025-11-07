// API endpoints
const API_CLIENTES = '/api/clientes';
const API_CANCHAS = '/api/canchas';
const API_SERVICIOS = '/api/servicios';
const API_RESERVAS = '/api/reservas';
const API_METODOS = '/api/metodos';

// Duraciones por deporte (minutos). Deben coincidir con el backend.
const DURACIONES_MIN = {
  'padel': 60,
  'pádel': 60,
  'tenis': 120,
  'futbol': 90,
  'fútbol': 90,
  'basket': 60,
  'basquet': 60,
  'baloncesto': 60,
};
const canchasById = {};
const serviciosAll = {};
const serviciosById = {};
let metodosPago = [];
const deportesByName = {}; // map normalized-name -> id_deporte

function normalizeName(s){
  if(!s) return '';
  // eliminar diacríticos y normalizar espacios, pasar a minúsculas
  try{
    return s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
  }catch(e){
    // fallback más simple si normalize con \\p no está disponible
    return s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim() : String(s).toLowerCase().trim();
  }
}

// Manejo de selección de reserva: muestra acciones de pago según método o si está pagada
async function selectReserva(r){
  // precargar formulario con datos básicos
  document.getElementById('select-cliente').value = r.id_cliente;
  document.getElementById('select-cancha').value = r.id_cancha;
  document.getElementById('fecha').value = r.fecha_reserva;
  document.getElementById('hora_inicio').value = r.hora_inicio;
  document.getElementById('hora_fin').value = r.hora_fin;
  computeAndShowTotal();
  // almacenar selección global
  window.selectedReservaId = r.id_reserva;

  const resultDiv = document.getElementById('result');
  resultDiv.innerHTML = '';

  // Si ya tiene pago registrado
  if(r.pago && r.pago.metodo_nombre){
    const m = (r.pago.metodo_nombre || '').toLowerCase();
    if(m.includes('efect') ){
      resultDiv.innerHTML = `<div class="alert alert-info">Reserva seleccionada: ya fue pagada en efectivo (monto: $${r.pago.monto}).</div>`;
    } else if(m.includes('tarjeta') || m.includes('card')){
      resultDiv.innerHTML = `<div class="alert alert-info">Reserva seleccionada: ya fue pagada con tarjeta (monto: $${r.pago.monto}).</div>`;
    } else {
      resultDiv.innerHTML = `<div class="alert alert-info">Reserva seleccionada: pago registrado (${r.pago.metodo_nombre})</div>`;
    }
    // ocultar opciones de pago (ya está pagada)
    document.getElementById('pagar_ahora').checked = false;
    const pagoOpts = document.getElementById('pago-options'); if(pagoOpts) pagoOpts.style.display = 'none';
    // remover botón de pagar si existe
    const existing = document.getElementById('btn-pagar-reserva'); if(existing) existing.remove();
    return;
  }

  // Si no está pagada, mostrar controles para pagar la reserva seleccionada
  document.getElementById('pagar_ahora').checked = true;
  const pagoOpts = document.getElementById('pago-options'); if(pagoOpts) pagoOpts.style.display = 'block';
  // crear botón de pago específico para la reserva
  let btn = document.getElementById('btn-pagar-reserva');
  if(!btn){
    btn = document.createElement('button');
    btn.id = 'btn-pagar-reserva';
    btn.type = 'button';
    btn.className = 'btn btn-success btn-sm mt-2';
    btn.textContent = 'Pagar reserva seleccionada';
    const parent = document.getElementById('pago-options');
    if(parent) parent.appendChild(btn);
    btn.addEventListener('click', async ()=>{
      const metodoId = parseInt(document.getElementById('select-metodo').value);
      if(!metodoId){ alert('Seleccione un método de pago'); return; }
      const monto = r.precio_total || document.getElementById('precio-total').value;
      try{
        const resp = await fetch(`/api/reservas/${window.selectedReservaId}/pagar`, {method:'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id_metodo: metodoId, monto: monto})});
        if(resp.status === 201){
          const pd = await resp.json();
          resultDiv.innerHTML = `<div class="alert alert-success">Pago registrado (ID: ${pd.id_pago})</div>`;
          // refrescar lista y estado
          onCanchaFechaChange();
          // ocultar boton
          btn.remove();
        } else {
          const err = await resp.json();
          resultDiv.innerHTML = `<div class="alert alert-warning">Pago fallido: ${err.error || 'error'}</div>`;
        }
      }catch(e){ resultDiv.innerHTML = `<div class="alert alert-danger">Error de red al intentar pagar</div>`; }
    });
  }
}

async function fetchJson(url){
  try{
    const res = await fetch(url);
    if(!res.ok) return null;
    return await res.json();
  }catch(e){
    return null;
  }
}

// Helper utilities at module scope (used by slot rendering)
function pad(n){ return String(n).padStart(2,'0'); }
function timeStrToMin(t){ const p = String(t).split(':').map(x=>parseInt(x,10)); return (p[0]||0)*60 + (p[1]||0); }
function fmtMin(m){ let mm = m % 1440; return pad(Math.floor(mm/60)) + ':' + pad(mm%60); }
function intervalsOverlap(aS,aE,bS,bE){
  for(const offA of [0,1440]){
    const as = aS + offA, ae = aE + offA;
    for(const offB of [0,1440]){
      const bs = bS + offB, be = bE + offB;
      if(as < be && bs < ae) return true;
    }
  }
  return false;
}

async function loadSelects(){
  const clientes = await fetchJson(API_CLIENTES) || [];
  const canchas = await fetchJson(API_CANCHAS) || [];
  const servicios = await fetchJson(API_SERVICIOS) || [];

  const selCliente = document.getElementById('select-cliente');
  clientes.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id_cliente;
    opt.textContent = `${c.nombre} ${c.apellido} (${c.dni})`;
    selCliente.appendChild(opt);
  });

  const selCancha = document.getElementById('select-cancha');
  canchas.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id_cancha;
    opt.textContent = `${c.nombre} — ${c.tipo_deporte || ''} — $${c.precio_hora}`;
    selCancha.appendChild(opt);
    canchasById[c.id_cancha] = c;
  });

  // cargar deportes para poder inferir id_deporte cuando la cancha no tenga id_deporte pero tenga tipo_deporte
  try{
    const deps = await fetchJson('/api/deportes') || [];
    deps.forEach(d => {
      if(d && d.nombre){
        const key = normalizeName(d.nombre || '');
        deportesByName[key] = d.id_deporte;
      }
    });
  }catch(e){
    console.warn('No se pudieron cargar deportes para inferencia:', e);
  }

  // cuando cambia la cancha o la fecha, recargar reservas y slots
  document.getElementById('select-cancha').addEventListener('change', () => {
    // populateHoraOptions solo existe si el elemento #hora_inicio es un SELECT (compatibilidad con versiones antiguas)
    try{
      if(typeof populateHoraOptions === 'function') populateHoraOptions(23);
    }catch(e){}
    renderServiciosForCancha(); onCanchaFechaChange(); computeAndShowTotal();
  });
  document.getElementById('fecha').addEventListener('change', onCanchaFechaChange);

  // Ensure slots/reservas UI are hidden until a cancha+fecha are selected
  try{
    const slotsDivInit = document.getElementById('slots-list');
    const slotsContainerInit = document.getElementById('slots-container');
    const reservasListInit = document.getElementById('reservas-list');
    const slotsMsgInit = document.getElementById('slots-msg');
    if(slotsDivInit) slotsDivInit.style.display = 'none';
    if(slotsContainerInit) slotsContainerInit.style.display = 'none';
    if(reservasListInit) reservasListInit.innerHTML = '';
    if(slotsMsgInit) slotsMsgInit.style.display = 'block';
  }catch(e){/* ignore */}

  // poblar select de horas de inicio en pasos de 30 minutos (08:00 - 23:00).
    const selHora = document.getElementById('hora_inicio');
    function pad(n){ return String(n).padStart(2,'0'); }
    // si existe un select visible para hora_inicio (caso anterior), poblarlo; sino no hacemos nada
    if(selHora && selHora.tagName === 'SELECT'){
      function populateHoraOptions(maxStart=23){
        selHora.innerHTML = '<option value="">Seleccionar hora...</option>';
        const startMin = 8*60; // 08:00
        const endMin = maxStart*60; // 23:00
        for(let m = startMin; m <= endMin; m += 30){
          const hh = pad(Math.floor(m/60)) + ':' + pad(m%60);
          const opt = document.createElement('option');
          opt.value = hh;
          opt.textContent = hh;
          selHora.appendChild(opt);
        }
      }
      populateHoraOptions(23);
    }

    // utilidad: obtener duración de la cancha (priorizar objeto deporte si viene del API)
  function getCanchaDur(idCancha){
    const c = canchasById[idCancha];
    if(!c) return 60;
    if(c.deporte && c.deporte.duracion_minutos) return parseInt(c.deporte.duracion_minutos,10);
    const deporteText = (c.tipo_deporte || '').toLowerCase();
    return DURACIONES_MIN[deporteText] || 60;
  }

  // cuando cambia la hora de inicio, actualizar hora_fin automáticamente
  selHora.addEventListener('change', () => {
    const v = selHora.value;
    if(!v){ document.getElementById('hora_fin').value = '' ; return; }
    const canchaSel = document.getElementById('select-cancha').value;
    const parts = v.split(':').map(x=>parseInt(x,10));
    const startHour = parts[0];
    const startMin = parts[1];
    const dur = getCanchaDur(canchaSel) || 60;
    const endDate = new Date(0,0,0,startHour,startMin);
    endDate.setMinutes(endDate.getMinutes() + dur);
    const eh = pad(endDate.getHours()%24);
    const em = pad(endDate.getMinutes());
    document.getElementById('hora_fin').value = `${eh}:${em}`;
  });

  const serviciosDiv = document.getElementById('servicios-list');
  // almacenar servicios globalmente y renderizar según cancha seleccionada
  servicios.forEach(s => { serviciosAll[s.id_servicio] = s; serviciosById[s.id_servicio] = s; });
  renderServiciosForCancha();

  // cargar métodos de pago
  const metodos = await fetchJson(API_METODOS) || [];
  metodosPago = metodos;
  const selMet = document.getElementById('select-metodo');
  if(selMet){
    metodos.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id_metodo;
      opt.textContent = m.nombre;
      selMet.appendChild(opt);
    });
  }
}

async function renderServiciosForCancha(){
  const serviciosDiv = document.getElementById('servicios-list');
  const serviciosSection = document.getElementById('servicios-section');
  const serviciosDisabledMsg = document.getElementById('servicios-disabled-msg');
  serviciosDiv.innerHTML = '';
  const idCancha = document.getElementById('select-cancha').value;
  let canchaObj = canchasById[idCancha] || {};
  // intentar obtener la cancha fresca del servidor (incluye campo 'deporte' cuando está relacionado)
  if(idCancha){
    try{
      const resCan = await fetch(`${API_CANCHAS}/${idCancha}`);
      if(resCan && resCan.ok){
        const fresh = await resCan.json();
        canchaObj = fresh;
        canchasById[idCancha] = fresh;
      }
    }catch(e){
      // ignore
    }
  }
  // obtener id_deporte desde la relación 'deporte' o desde la columna id_deporte
  let idDeporte = canchaObj.deporte ? canchaObj.deporte.id_deporte : (canchaObj.id_deporte || null);
  // si no existe id_deporte, intentar inferirlo por el texto tipo_deporte (coincidencia por nombre)
  if(!idDeporte && canchaObj.tipo_deporte){
    const lookup = normalizeName(canchaObj.tipo_deporte || '');
    if(deportesByName[lookup]){
      idDeporte = deportesByName[lookup];
    } else {
      const alt = lookup.replace(/o$/,'ó');
      if(deportesByName[alt]){
        idDeporte = deportesByName[alt];
      }
    }
  }

  // Si no hay cancha seleccionada, mostrar mensaje y no activar opciones
  if(!idCancha){
    if(serviciosSection) serviciosSection.style.display = 'none';
    if(serviciosDisabledMsg) serviciosDisabledMsg.style.display = 'block';
    for(const k in serviciosById) delete serviciosById[k];
    computeAndShowTotal();
    return;
  }

  // si hay cancha, mostrar seccion y ocultar mensaje
  if(serviciosSection) serviciosSection.style.display = 'block';
  if(serviciosDisabledMsg) serviciosDisabledMsg.style.display = 'none';

  // Preferir pedir servicios específicos del deporte para asegurar datos actualizados
  let filtered = [];
  try{
    if(idDeporte){
      const url = `/api/deportes/${idDeporte}/servicios`;
      const res = await fetch(url);
      if(res.ok) {
        filtered = await res.json();
      } else {
        console.warn('/api/deportes/'+idDeporte+'/servicios returned', res.status);
      }
    }
  }catch(e){
    console.warn('Error fetching servicios por deporte', e);
    filtered = [];
  }

  // si no se obtuvieron, usar el endpoint global como fallback
  if(!filtered || filtered.length === 0){
    const list = Object.values(serviciosAll || {});
    filtered = list.filter(s => s.activo && (!s.id_deporte || String(s.id_deporte) === String(idDeporte)));
  }

  if(!filtered || filtered.length === 0){
    serviciosDiv.innerHTML = '<small class="text-muted">No hay servicios adicionales disponibles para este deporte</small>';
    for(const k in serviciosById) delete serviciosById[k];
    return;
  }

  // reconstruir mapping local de servicios por id para uso en cálculo
  for(const k in serviciosById) delete serviciosById[k];
  filtered.forEach(s => { serviciosById[parseInt(s.id_servicio)] = s; });

  filtered.forEach(s => {
    const id = `serv-${s.id_servicio}`;
    const wrapper = document.createElement('div');
    wrapper.className = 'd-flex align-items-center gap-2';
    wrapper.innerHTML = `
      <div class="form-check mb-1">
        <input class="form-check-input serv-chk" type="checkbox" value="${s.id_servicio}" id="${id}">
        <label class="form-check-label" for="${id}">${s.nombre} ($${s.precio_adicional})</label>
      </div>
      <div style="width:80px;">
        <input type="number" min="1" value="1" class="form-control form-control-sm serv-qty" data-serv="${s.id_servicio}">
      </div>
    `;
    serviciosDiv.appendChild(wrapper);
  });
  // asignar listeners para recalcular total
  document.querySelectorAll('.serv-chk, .serv-qty').forEach(el => el.addEventListener('change', () => computeAndShowTotal()));
  const ilum = document.getElementById('usa_iluminacion');
  if(ilum) ilum.addEventListener('change', () => computeAndShowTotal());
  const pagarNow = document.getElementById('pagar_ahora');
  if(pagarNow){
    pagarNow.addEventListener('change', ()=>{
      const opts = document.getElementById('pago-options');
      if(!opts) return;
      opts.style.display = pagarNow.checked ? 'block' : 'none';
    });
  }
  // Si estamos editando una reserva, precargar servicios y cantidades desde el backend
  if(window.editingReservaId){
    try{
      const res = await fetch(`/api/reservas/${window.editingReservaId}`);
      if(res.ok){
        const rd = await res.json();
        // marcar servicios
        (rd.servicios_adicionales || []).forEach(sv => {
          const cb = document.querySelector(`#serv-${sv.id_servicio}`);
          if(cb){ cb.checked = true; }
          const qty = document.querySelector(`.serv-qty[data-serv='${sv.id_servicio}']`);
          if(qty) qty.value = sv.cantidad || 1;
        });
        computeAndShowTotal();
      }
    }catch(e){ console.warn('No se pudieron precargar servicios de la reserva en edición', e); }
  }
}

// Calcula el total mostrado en la UI (mismo criterio que backend: horas * precio_hora + iluminación + servicios)
function computeAndShowTotal(){
  const idCancha = document.getElementById('select-cancha').value;
  const horaIni = document.getElementById('hora_inicio').value;
  const horaFin = document.getElementById('hora_fin').value;
  const precioInput = document.getElementById('precio-total');
  const btnConfirm = document.getElementById('btn-confirmar');
  if(!precioInput) return;
  if(!idCancha || !horaIni || !horaFin){
    precioInput.value = '0.00';
    if(btnConfirm) btnConfirm.disabled = true;
    return; }
  const cancha = canchasById[idCancha] || {};
  const precioHora = parseFloat(cancha.precio_hora || 0);
  const precioIlum = parseFloat(cancha.precio_iluminacion || 0);
  function timeToMin(t){ const p = t.split(':').map(x=>parseInt(x,10)); return p[0]*60 + p[1]; }
  let s = timeToMin(horaIni), e = timeToMin(horaFin);
  if(e <= s) e += 1440;
  const durHoras = (e - s) / 60.0;
  let total = (precioHora * durHoras) || 0;
  const ilumEl = document.getElementById('usa_iluminacion');
  if(ilumEl && ilumEl.checked) total += (precioIlum * durHoras);
  // servicios
  document.querySelectorAll('#servicios-list .serv-chk:checked').forEach(cb => {
    const sid = parseInt(cb.value);
    const svc = serviciosById[sid];
    if(!svc) return;
    const qtyEl = document.querySelector(`.serv-qty[data-serv="${sid}"]`);
    const qty = qtyEl ? Math.max(1, parseInt(qtyEl.value)||1) : 1;
    total += parseFloat(svc.precio_adicional || 0) * qty;
  });
  precioInput.value = total.toFixed(2);
  // habilitar botón de confirmar si hay datos mínimos (cancha + horas)
  if(btnConfirm) {
    btnConfirm.disabled = !(idCancha && horaIni && horaFin);
  }
}

document.getElementById('reserva-form').addEventListener('submit', async function(ev){
  ev.preventDefault();
  const payload = {
    id_cliente: parseInt(document.getElementById('select-cliente').value),
    id_cancha: parseInt(document.getElementById('select-cancha').value),
    fecha_reserva: document.getElementById('fecha').value,
    hora_inicio: document.getElementById('hora_inicio').value,
    hora_fin: document.getElementById('hora_fin').value,
    usa_iluminacion: document.getElementById('usa_iluminacion').checked,
    servicios_adicionales: []
  };

  // recoger servicios con cantidad
  document.querySelectorAll('#servicios-list .serv-chk:checked').forEach(cb => {
    const sid = parseInt(cb.value);
    const qtyEl = document.querySelector(`.serv-qty[data-serv="${sid}"]`);
    const qty = qtyEl ? Math.max(1, parseInt(qtyEl.value)||1) : 1;
    payload.servicios_adicionales.push({id_servicio: sid, cantidad: qty});
  });

  // antes de enviar, comprobar disponibilidad vía endpoint check
  const checkUrl = `/api/reservas/check?id_cancha=${payload.id_cancha}&fecha_reserva=${payload.fecha_reserva}&hora_inicio=${payload.hora_inicio}&hora_fin=${payload.hora_fin}`;
  const check = await fetchJson(checkUrl);
  const resultDiv = document.getElementById('result');
  if(!check || !check.available){
    resultDiv.innerHTML = `<div class="alert alert-warning">No disponible: ${check && check.reason ? check.reason : 'ocupado o error en la validación'}</div>`;
    return;
  }

  const res = await fetch(API_RESERVAS, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  
  if(res.status === 201){
    const data = await res.json();
    resultDiv.innerHTML = `<div class="alert alert-success">Reserva creada. ID: ${data.id_reserva} — Precio total: $${data.precio_total}</div>`;
    this.reset();
    // limpiar hora_fin y refrescar lista de reservas/slots
    document.getElementById('hora_fin').value = '';
    onCanchaFechaChange();
    // Si estábamos en modo edición, borrar la reserva original
    if(window.editingReservaId){
      try{
        const del = await fetch(`/api/reservas/${window.editingReservaId}`, {method: 'DELETE'});
        if(del.ok){
          resultDiv.innerHTML += `<div class="alert alert-info mt-2">Reserva original (ID: ${window.editingReservaId}) eliminada tras editar.</div>`;
        } else {
          resultDiv.innerHTML += `<div class="alert alert-warning mt-2">No se pudo eliminar la reserva original (ID: ${window.editingReservaId}).</div>`;
        }
      }catch(e){
        resultDiv.innerHTML += `<div class="alert alert-warning mt-2">Error al eliminar reserva original.</div>`;
      }
      window.editingReservaId = null;
    }
    // Si el usuario pidió pagar ahora, intentar pago automático
    const pagarAhora = document.getElementById('pagar_ahora').checked;
    if(pagarAhora){
      const metodoSel = document.getElementById('select-metodo').value;
      if(metodoSel){
        // llamar endpoint de pago
        const pagarRes = await fetch(`/api/reservas/${data.id_reserva}/pagar`, {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({id_metodo: parseInt(metodoSel), monto: data.precio_total})
        });
        if(pagarRes.status === 201){
          const pd = await pagarRes.json();
          resultDiv.innerHTML += `<div class="alert alert-info mt-2">Pago registrado (ID: ${pd.id_pago})</div>`;
        } else {
          const err = await pagarRes.json();
          resultDiv.innerHTML += `<div class="alert alert-warning mt-2">Pago fallido: ${err.error || 'error'}</div>`;
        }
      }
    }
  } else if(res.status === 409){
    const err = await res.json();
    resultDiv.innerHTML = `<div class="alert alert-warning">Conflicto: ${err.error}</div>`;
  } else {
    const err = await res.json();
    resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${err.error || 'Error al crear la reserva'}</div>`;
  }
});

if(document.getElementById('btn-reset')){
  document.getElementById('btn-reset').addEventListener('click', function(){
    document.getElementById('reserva-form').reset();
    document.getElementById('result').innerHTML = '';
  });
}

// Inicializar selects al cargar la página
loadSelects();

// --- Nuevas funciones para mostrar reservas y slots ---
async function onCanchaFechaChange(){
  const idCancha = document.getElementById('select-cancha').value;
  const fecha = document.getElementById('fecha').value;
  const listDiv = document.getElementById('reservas-list');
  const slotsDiv = document.getElementById('slots-list');
  const slotsContainer = document.getElementById('slots-container');
  if(listDiv) listDiv.innerHTML = '';
  if(slotsDiv) slotsDiv.innerHTML = '';
  // If no cancha selected or date, hide slots UI and return
  if(!idCancha || !fecha){
    if(slotsDiv) slotsDiv.style.display = 'none';
    if(slotsContainer) slotsContainer.style.display = 'none';
    const slotsMsg = document.getElementById('slots-msg');
    if(slotsMsg) slotsMsg.style.display = 'block';
    return;
  }

  // obtener reservas existentes
  const reservas = await fetchJson(`${API_RESERVAS}?id_cancha=${idCancha}&fecha_reserva=${fecha}`) || [];

  if(!listDiv) return;
  // Mostrar listado de reservas con acciones (editar / eliminar)
  if(reservas.length === 0){
    listDiv.innerHTML = '<div class="list-group-item text-muted">No hay reservas para la fecha seleccionada</div>';
  } else {
    reservas.forEach(r => {
      const item = document.createElement('div');
      item.className = 'list-group-item d-flex justify-content-between align-items-center';
      const left = document.createElement('div');
      left.innerHTML = `<strong>${r.hora_inicio} - ${r.hora_fin}</strong><br><small>${r.cliente_nombre || ''} ${r.cliente_apellido || ''}</small>`;
      const right = document.createElement('div');
      right.className = 'btn-group';
      // mostrar badge de pago si existe
      if(r.pago && r.pago.metodo_nombre){
        const pagoBadge = document.createElement('span');
        pagoBadge.className = 'badge bg-info text-dark me-2';
        pagoBadge.textContent = `Pagado: ${r.pago.metodo_nombre}`;
        left.appendChild(document.createElement('br'));
        left.appendChild(pagoBadge);
      }
      // Edit button: precarga la reserva en el formulario para editar (crear nueva luego borrar la antigua)
      const btnEdit = document.createElement('button');
      btnEdit.className = 'btn btn-sm btn-outline-primary';
      btnEdit.textContent = 'Editar';
      btnEdit.addEventListener('click', ()=>{
        // precargar formulario
        document.getElementById('select-cliente').value = r.id_cliente;
        document.getElementById('select-cancha').value = r.id_cancha;
        document.getElementById('fecha').value = r.fecha_reserva;
        document.getElementById('hora_inicio').value = r.hora_inicio;
        document.getElementById('hora_fin').value = r.hora_fin;
        document.getElementById('usa_iluminacion').checked = !!r.usa_iluminacion;
        // marcar modo edición
        window.editingReservaId = r.id_reserva;
        // scroll to form
        document.getElementById('reserva-form').scrollIntoView({behavior:'smooth'});
        // re-render servicios for cancha (will populate services)
        renderServiciosForCancha();
        computeAndShowTotal();
      });

      const btnDel = document.createElement('button');
      btnDel.className = 'btn btn-sm btn-outline-danger';
      btnDel.textContent = 'Eliminar';
      btnDel.addEventListener('click', async ()=>{
        if(!confirm('Eliminar reserva?')) return;
        const del = await fetch(`/api/reservas/${r.id_reserva}`, {method:'DELETE'});
        if(del.ok){
          // refrescar lista
          onCanchaFechaChange();
        } else {
          alert('Error al eliminar reserva');
        }
      });

      right.appendChild(btnEdit);
  // Seleccionar: cargar la reserva y mostrar acciones de pago según estado
  const btnSelect = document.createElement('button');
  btnSelect.className = 'btn btn-sm btn-outline-success';
  btnSelect.textContent = 'Seleccionar';
  btnSelect.addEventListener('click', ()=> selectReserva(r));
  right.appendChild(btnSelect);
      right.appendChild(btnDel);
      item.appendChild(left);
      item.appendChild(right);
      listDiv.appendChild(item);
    });
  }

  // obtener reservas existentes (ya realizado arriba) y generar franjas horarias
  // Generamos franjas por hora (60 minutos) desde 08:00 hasta 22:00 (terminan a las 23:00)
  // Nota: simplificamos y no dependemos de un endpoint de 'horarios' en el servidor
  const horarios = []; // no usamos horarios del servidor; generamos la franja por defecto
  const SLOT_START_MIN = 8 * 60; // 08:00
  const SLOT_END_LIMIT = 23 * 60; // 23:00 (hora límite de finalización)

  // helper (moved to module scope)

  // preparar reservas existentes en minutos
  const reservasIntervals = (reservas || []).map(r => {
    let rs = timeStrToMin(r.hora_inicio);
    let re = timeStrToMin(r.hora_fin);
    if(re <= rs) re += 1440; // cruza medianoche
    return {start: rs, end: re};
  });
  // show slots container
  if(slotsDiv) slotsDiv.style.display = 'flex';
  if(slotsContainer) slotsContainer.style.display = 'flex';
  const slotsMsg = document.getElementById('slots-msg');
  if(slotsMsg) slotsMsg.style.display = 'none';

  // Simpler slot strategy: create 1-hour slots every 60 minutes from 08:00 up to 22:00 (so they end by 23:00)
  const SLOT_DURATION = 60; // fixed duration in minutes for slots
  const STEP = 60; // one hour steps as requested
  const maxStartGlobal = SLOT_END_LIMIT - SLOT_DURATION; // latest allowed start so it finishes by 23:00

  if(horarios.length === 0){
    // si no hay horarios definidos, mostrar la franja completa 08:00-23:00 en pasos de 1h
    for(let m = SLOT_START_MIN; m <= maxStartGlobal; m += STEP){
      addSlotMinutes(m, reservasIntervals, slotsDiv, idCancha, SLOT_DURATION);
    }
  } else {
    for(const h of horarios){
      if(h.disponible_para_fecha === false) continue;
      const startMin = timeStrToMin(h.hora_inicio);
      let endMin = timeStrToMin(h.hora_fin);
      if(endMin <= startMin) endMin += 1440; // cruza medianoche
      // intersect horario with 08:00 - 23:00 window
      const windowStart = Math.max(SLOT_START_MIN, startMin);
      const windowEnd = Math.min(SLOT_END_LIMIT, endMin);
      const lastStart = windowEnd - SLOT_DURATION;
      for(let m = windowStart; m <= lastStart; m += STEP){
        if(m <= maxStartGlobal) addSlotMinutes(m, reservasIntervals, slotsDiv, idCancha, SLOT_DURATION);
      }
    }
  }
}

function addSlotMinutes(startMin, reservasIntervals, slotsDiv, idCancha, slotDuration = 60){
  // slotDuration default 60 minutes (fixed hourly slots)
  const dur = parseInt(slotDuration, 10) || 60;
  const slotStart = startMin;
  const slotEnd = slotStart + dur;
  const slotLabel = `${fmtMin(slotStart)} - ${fmtMin(slotEnd)}`;

  // contenedor del slot (botón + badge)
  const wrapper = document.createElement('div');
  wrapper.className = 'd-flex align-items-center gap-2 mb-1';

  const slotEl = document.createElement('button');
  slotEl.type = 'button';
  slotEl.className = 'btn btn-sm';
  slotEl.style.minWidth = '160px';
  slotEl.textContent = slotLabel;

  // badge que indica estado
  const badge = document.createElement('span');
  badge.className = 'badge align-self-start';
  badge.style.marginLeft = '6px';

  // determinar si está ocupado
  const ocupado = reservasIntervals.some(r => intervalsOverlap(slotStart, slotEnd, r.start, r.end));
  const maxSelectable = 23 * 60; // 23:00 end limit
  if(ocupado){
    slotEl.className += ' btn-outline-danger disabled';
    badge.className += ' bg-danger';
    badge.textContent = 'Ocupado';
  } else if(slotEnd > maxSelectable){
    // slot que finalizaría después de las 23:00 — no seleccionable
    slotEl.className += ' btn-outline-secondary disabled';
    badge.className += ' bg-secondary';
    badge.textContent = 'No seleccionable';
  } else {
    slotEl.className += ' btn-outline-success';
    badge.className += ' bg-success';
    badge.textContent = 'Disponible';
    slotEl.addEventListener('click', ()=>{
      // rellenar inputs ocultos (hora de inicio y fin). Si el start es >=1440, restar 1440 para el input del mismo día
      const displayStart = slotStart % 1440;
      const displayEnd = slotEnd % 1440;
      const hIni = fmtMin(displayStart);
      const hFin = fmtMin(displayEnd);
      const horaIniInput = document.getElementById('hora_inicio');
      const horaFinInput = document.getElementById('hora_fin');
      if(horaIniInput) horaIniInput.value = hIni;
      if(horaFinInput) horaFinInput.value = hFin;
      // marcar visualmente la selección
      document.querySelectorAll('#slots-list button').forEach(b => b.classList.remove('active'));
      slotEl.classList.add('active');
      // ocultar panel de selección (usamos el formulario principal para confirmar)
  // clear any legacy selected-slot element if present
  const selDiv = document.getElementById('selected-slot');
  if(selDiv) selDiv.innerHTML = '';
      // desplazar al formulario para que el usuario pueda completar datos y reservar
      const form = document.getElementById('reserva-form');
      if(form) form.scrollIntoView({behavior:'smooth'});
      // recalcular total ahora que se seleccionó un horario
      computeAndShowTotal();
    });
  }

  wrapper.appendChild(slotEl);
  wrapper.appendChild(badge);
  slotsDiv.appendChild(wrapper);
}
