let cartCount = 0;
const cartCountElement = document.getElementById('cart-count');

function updateCartCount() {
  cartCountElement.textContent = cartCount;
  cartCountElement.style.transform = 'scale(1.2)';
  setTimeout(() => {
    cartCountElement.style.transform = 'scale(1)';
  }, 200);
}

document.addEventListener('click', function(e) {
  const btn = e.target.closest('.btn-add-to-cart');
  if (!btn) return;
  e.preventDefault();

  const card = btn.closest('.product-card');
  const name = card.querySelector('.product-details h4').innerText;
  const price = parseFloat(card.querySelector('.price-badge').innerText.match(/\d+[\.,]\d+/)[0].replace(',', '.'));
  const imgEl = card.querySelector('.product-image img');
  const image = imgEl ? imgEl.src : null;

  fetch('/cart/add', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name,
        price,
        qty: 1,
        image
      })
    })
    .then(async r => {
      if (r.status === 401) {
        // Usuário não está logado (entrou como convidado)
        let msg = 'Você precisa estar conectado a uma conta para adicionar itens ao carrinho.';
        try {
          const j = await r.json();
          if (j && j.erro === 'login_required') {
            msg = 'Você precisa estar conectado a uma conta para adicionar itens ao carrinho.';
          }
        } catch (e) {}
        alert(msg);
        return;
      }
      const j = await r.json();
      if (j.count !== undefined) {
        cartCount = j.count;
        updateCartCount();
        btn.innerHTML = '<i class="fas fa-check"></i> Adicionado!';
        btn.style.backgroundColor = '#4CAF50';
        setTimeout(() => {
          btn.innerHTML = '<i class="fas fa-shopping-cart"></i> Adicionar ao Carrinho';
          btn.style.backgroundColor = '#F99CA6';
        }, 1500);
      } else {
        console.warn(j.erro || 'Falha ao adicionar');
      }
    })
    .catch(err => {
      console.error('add cart', err);
      console.error('Erro de rede');
    });
});

document.addEventListener('DOMContentLoaded', async function() {
  fetch('/cart/items', {
      credentials: 'same-origin'
    })
    .then(async r => {
      if (r.status === 401) {
        // Visitante (convidado) não tem carrinho carregado da sessão
        cartCount = 0;
        updateCartCount();
        return [];
      }
      return r.json();
    })
    .then(items => {
      if (!Array.isArray(items)) return;
      cartCount = items.reduce((s, i) => s + i.qty, 0);
      updateCartCount();
    });

  const productGrid = document.querySelector('.product-grid');
  try {
    const respProd = await fetch('/api/produtos');
    const lista = await respProd.json();
    productGrid.innerHTML = '';
    lista.forEach(p => {
      const catSlug = (p.categoria || '').toLowerCase().replace(/\s+/g, '-') || 'all';
      const art = document.createElement('article');
      art.className = 'product-card';
      art.dataset.category = catSlug;
      const imgHtml = p.foto ? `<img src="${p.foto}" alt="${p.nome}">` : '';
      art.innerHTML = `
            <div class="product-image">
                ${imgHtml}
                <span class="price-badge">R$ ${parseFloat(p.valor).toFixed(2).replace('.', ',')}</span>
            </div>
            <div class="product-details">
                <h4>${p.nome}</h4>
                <p>${p.descricao}</p>
                <span class="category-tag">${p.categoria||''}</span>
                <a href="#" class="btn btn-primary btn-add-to-cart"><i class="fas fa-shopping-cart"></i> Adicionar ao Carrinho</a>
            </div>`;
      productGrid.appendChild(art);
    });
  } catch (e) {
    console.error('load produtos', e);
  }

  const filterButtons = document.querySelectorAll('.filter-link');
  const productCards = document.querySelectorAll('.product-card');

  function reorganizarItens() {
    productCards.forEach(card => card.classList.remove('hidden'));

    // Força um reflow para garantir que as animações/transições funcionem
    void productGrid.offsetHeight;

    const activeButton = document.querySelector('.filter-link.active');
    if (!activeButton) return;

    const selectedCategory = activeButton.getAttribute('data-category');

    productCards.forEach(card => {
      const cardCategory = card.getAttribute('data-category');
      const deveMostrar = selectedCategory === 'all' || cardCategory === selectedCategory;

      if (!deveMostrar) {
        card.classList.add('hidden');
      }
    });

    // Força um reflow/repintura para a transição
    productGrid.style.display = 'none';
    void productGrid.offsetHeight;
    productGrid.style.display = 'grid';
  }

  filterButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      filterButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');
      reorganizarItens();
      setTimeout(reorganizarItens, 50); // Garante a reorganização
    });
  });
  reorganizarItens();
});