document.querySelectorAll('.remove-item').forEach(button => {
  button.addEventListener('click', function() {
    this.closest('.cart-item').remove();
    updateOrderSummary();
  });
});

function updateOrderSummary() {
  let subtotal = 0;

  document.querySelectorAll('.cart-item').forEach(item => {
    const totalText = item.querySelector('.item-total').textContent;
    const totalValue = parseFloat(totalText.replace('R$', '').replace(',', '.'));
    subtotal += totalValue;
  });

  document.querySelector('.summary-row:first-child span:last-child').textContent =
    `R$ ${subtotal.toFixed(2).replace('.', ',')}`;

  document.querySelector('.summary-row.total span:last-child').textContent =
    `R$ ${subtotal.toFixed(2).replace('.', ',')}`;
}

const today = new Date().toISOString().split('T')[0];
document.getElementById('delivery-date').min = today;
updateOrderSummary();

const deliveryRadios = document.querySelectorAll('input[name="delivery-option"]');
deliveryRadios.forEach(radio => {
  radio.addEventListener('change', updateDeliveryVisibility);
});

function updateDeliveryVisibility() {
  const entregaChecked = deliveryRadios[0].checked;
  const addressSection = document.querySelector('.address-section');
  const scheduleSection = document.querySelector('.schedule-section');
  const deliveryFeeRow = document.querySelector('.delivery-fee');
  if (entregaChecked) {
    addressSection.style.display = '';
    scheduleSection.style.display = '';
  } else {
    addressSection.style.display = 'none';
    scheduleSection.style.display = 'none';
  }
  deliveryFeeRow.style.display = '';
}

updateDeliveryVisibility();
const badge = parent.document ? parent.document.getElementById('cart-count') : null;

function recalcTotals() {
  let subtotal = 0;
  document.querySelectorAll('.cart-item').forEach(it => {
    const price = parseFloat(it.querySelector('.item-price').dataset.price);
    const qty = parseInt(it.querySelector('.quantity').textContent);
    const total = price * qty;
    it.querySelector('.item-total').textContent = `R$ ${total.toFixed(2)}`;
    subtotal += total;
  });
  document.querySelectorAll('.summary-row.total span:last-child')[0].textContent = `R$ ${subtotal.toFixed(2)}`;
}

document.addEventListener('click', e => {
  const dec = e.target.closest('.btn-dec');
  const inc = e.target.closest('.btn-inc');
  const rem = e.target.closest('.remove-item');
  if (!dec && !inc && !rem) return;
  const itemEl = e.target.closest('.cart-item');
  const name = itemEl.dataset.name;
  let actionPromise;
  if (rem) {
    actionPromise = fetch('/cart/remove', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name
      })
    });
  } else {
    const delta = inc ? 1 : -1;
    actionPromise = fetch('/cart/update', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name,
        delta
      })
    });
  }
  actionPromise.then(r => r.json()).then(j => {
    if (j.count !== undefined && badge) {
      badge.textContent = j.count;
    }
    if (rem) {
      itemEl.remove();
    } else {
      const qEl = itemEl.querySelector('.quantity');
      let q = parseInt(qEl.textContent) + (inc ? 1 : -1);
      if (q <= 0) {
        itemEl.remove();
      } else {
        qEl.textContent = q;
      }
    }
    recalcTotals();
  });
});