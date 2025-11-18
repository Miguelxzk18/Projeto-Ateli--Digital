const orderTbody = document.getElementById('ordersBody');

// Adiciona botão de visualização em cada linha que ainda não possua
orderTbody.querySelectorAll('tr').forEach(row => {
  if (!row.querySelector('.view-order')) {
    const td = document.createElement('td');
    td.innerHTML = '<a href="#" class="view-order"><i class="fas fa-chevron-right"></i></a>';
    row.appendChild(td);
  }
});

const orderModal = document.getElementById('orderModal');
// ---- Elementos de filtro ----
const filterDate = document.getElementById('filterDate');
const filterStatus = document.getElementById('filterStatus');
const priceMin = document.getElementById('priceMin');
const priceMax = document.getElementById('priceMax');
const filterClient = document.getElementById('filterClient');
const filterOrder = document.getElementById('filterOrder');
const clearFilter = document.getElementById('clearFilter');
// ---- Toggle Filtros ----
const filterBar = document.getElementById('filterBar');
const toggleFilterBtn = document.getElementById('toggleFilterBtn');
toggleFilterBtn.addEventListener('click', () => {
  filterBar.classList.toggle('open');
  toggleFilterBtn.textContent = filterBar.classList.contains('open') ? 'Ocultar filtros' : 'Mostrar filtros';
});
const orderInfo = document.getElementById('orderInfo');
const orderStatusSelect = document.getElementById('orderStatusSelect');
const closeOrderModalBtn = document.getElementById('closeOrderModal');
const saveOrderBtn = document.getElementById('saveOrderBtn');
let currentOrderRow = null;

// === Busca pedidos via API e preenche tabela ===
async function fetchOrders() {
  try {
    const resp = await fetch('/api/pedidos', {
      credentials: 'same-origin'
    });
    if (!resp.ok) {
      console.error('Falha API pedidos', resp.status);
      return;
    }
    const lista = await resp.json();
    renderOrders(lista);
  } catch (e) {
    console.error('Erro fetchOrders', e);
  }
}

function renderOrders(lista) {
  orderTbody.innerHTML = '';
  lista.forEach(r => {
    const tr = document.createElement('tr');
    tr.dataset.entrega = r.entrega || '';
    tr.dataset.phone = r.telefone || '';
    tr.dataset.pronto = (r.criado_em || '').split('T')[0];
    tr.dataset.pedido = (r.criado_em || '').split('T')[0];
    const partesDataHora = (r.criado_em || '').split('T');
    const hora = partesDataHora[1] ? partesDataHora[1].substring(0, 5) : '';
    tr.innerHTML = `
            <td>#${r.id}</td>
            <td>${r.cliente||'-'}</td>
            <td>${r.itens_str||''}</td>
            <td>R$ ${parseFloat(r.total||0).toFixed(2)}</td>
            <td class="status">${r.status || 'Pendente'}</td>
            <td>${hora}</td>
            <td><a href="#" class="view-order"><i class="fas fa-chevron-right"></i></a></td>`;
    orderTbody.appendChild(tr);
  });
  // Aplica cores aos status
  orderTbody.querySelectorAll('td.status').forEach(td => {
    applyStatusColor(td, td.textContent.trim());
  });
  filterOrders();
}
// Chamada inicial e polling a cada 15s
fetchOrders();
setInterval(fetchOrders, 15000);

// ----- Mapeamento de status para cores -----
const statusColors = {
  'Pendente': '#f1c40f', // amarelo
  'Confirmado': '#3498db', // azul
  'Preparando': '#555555', // cinza/preto
  'Pronto': '#3498db', // azul
  'Entregue': '#4CAF50', // verde
  'Cancelado': '#e74c3c' // vermelho
};

// Aplica a cor apropriada a um elemento conforme o status
function applyStatusColor(element, statusText) {
  const color = statusColors[statusText] || '#333333';
  // Evita colorir o <select> (lista); aplicamos cor só em células da tabela
  if (element.tagName !== 'SELECT') {
    element.style.color = color;
  } else {
    // remove qualquer cor inline caso tenha sido aplicada antes
    element.style.color = '';
  }
}

// Colore todos os status existentes na tabela ao carregar a página
orderTbody.querySelectorAll('td.status').forEach(td => {
  applyStatusColor(td, td.textContent.trim());
});

// Inicializa a cor do <select> de status
applyStatusColor(orderStatusSelect, orderStatusSelect.value);

// Atualiza a cor do <select> quando o usuário muda a opção
orderStatusSelect.addEventListener('change', () => {
  applyStatusColor(orderStatusSelect, orderStatusSelect.value);
});

orderTbody.addEventListener('click', function(e) {
  const view = e.target.closest('.view-order');
  if (view) {
    e.preventDefault();
    currentOrderRow = view.closest('tr');
    const cells = currentOrderRow.cells;
    orderInfo.innerHTML = `
            <strong>Nº:</strong> ${cells[0].textContent}<br>
            <strong>Cliente:</strong> ${cells[1].textContent}<br>
            <strong>Telefone:</strong> ${currentOrderRow.dataset.phone || '-'}<br>
            <strong>Itens:</strong> ${cells[2].textContent}<br>
            <strong>Total:</strong> ${cells[3].textContent}<br>
            <strong>Endereço:</strong> ${currentOrderRow.dataset.entrega}<br>
            <strong>Data de entrega:</strong> ${currentOrderRow.dataset.pronto}<br>
            <strong>Horário:</strong> ${cells[5].textContent}
        `;
    orderStatusSelect.value = cells[4].textContent.trim();
    orderModal.classList.add('open');
  }
});

closeOrderModalBtn.addEventListener('click', () => orderModal.classList.remove('open'));

// ---- Função de filtragem ----
function filterOrders() {
  const d = filterDate.value;
  const st = filterStatus.value.toLowerCase();
  const pMin = parseFloat(priceMin.value || '0');
  const pMax = parseFloat(priceMax.value || '0');
  const cli = filterClient.value.toLowerCase();
  const ord = filterOrder.value.replace('#', '').toLowerCase();

  orderTbody.querySelectorAll('tr').forEach(row => {
    const cells = row.cells;
    if (!cells.length) return;

    const rowDate = row.dataset.pedido || '';
    const rowStatus = cells[4].textContent.toLowerCase();
    const totalStr = cells[3].textContent.replace(/[R$\s.]/g, '').replace(',', '.');
    const totalVal = parseFloat(totalStr) || 0;
    const client = cells[1].textContent.toLowerCase();
    const orderNum = cells[0].textContent.replace('#', '').toLowerCase();

    let visible = true;
    if (d && rowDate !== d) visible = false;
    if (st && !rowStatus.includes(st)) visible = false;
    if (pMin && totalVal < pMin) visible = false;
    if (pMax && totalVal > pMax) visible = false;
    if (cli && !client.includes(cli)) visible = false;
    if (ord && !orderNum.includes(ord)) visible = false;

    row.style.display = visible ? '' : 'none';
  });
}

// Eventos de filtro
[filterDate, filterStatus, priceMin, priceMax, filterClient, filterOrder].forEach(el => {
  if (el) el.addEventListener('input', filterOrders);
});
if (clearFilter) {
  clearFilter.addEventListener('click', () => {
    filterDate.value = '';
    filterStatus.value = '';
    priceMin.value = '';
    priceMax.value = '';
    filterClient.value = '';
    filterOrder.value = '';
    filterOrders();
  });
}

// Executa filtro inicial
filterOrders();

saveOrderBtn.addEventListener('click', () => {
  if (currentOrderRow) {
    const newStatus = orderStatusSelect.value;
    const statusCell = currentOrderRow.cells[4];
    statusCell.textContent = newStatus;
    applyStatusColor(statusCell, newStatus);
    // persiste no servidor
    const id = currentOrderRow.cells[0].textContent.replace('#', '');
    fetch(`/api/pedido/${id}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          status: newStatus
        })
      })
      .then(res => {
        if (!res.ok) {
          console.warn('Falha ao salvar status'); // Substituído alert
        }
      });
  }
  orderModal.classList.remove('open');
});