document.addEventListener("DOMContentLoaded", function() {
  const tabs = document.querySelectorAll('.tab');
  const tabContents = document.querySelectorAll('.tab-content');
  const paymentContainer = document.querySelector('.payment-methods');
  const successScreen = document.querySelector('.success-screen');
  const confirmButtons = document.querySelectorAll('[id^="confirm"]');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const tabId = tab.getAttribute('data-tab');

      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      tabContents.forEach(content => {
        content.classList.remove('active');
        if (content.id === tabId) {
          content.classList.add('active');
        }
      });
    });
  });

  async function handlePaymentConfirmation(method) {
    const total = parseFloat(document.querySelector('.order-total span:last-child').textContent.replace('R$', '').replace(',', '.'));
    const resp = await fetch('/pagamento/confirm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        method,
        total
      })
    });
    if (resp.ok) {
      window.location.href = '/perfil';
      return;
    }
    paymentContainer.style.display = 'none';
    successScreen.style.display = 'block';
    successScreen.scrollIntoView({
      behavior: 'smooth'
    });
  }

  document.getElementById('confirmPayment')?.addEventListener('click', () => handlePaymentConfirmation('credito'));
  document.getElementById('confirmDebitPayment')?.addEventListener('click', () => handlePaymentConfirmation('debito'));
  document.getElementById('confirmPixPayment')?.addEventListener('click', () => handlePaymentConfirmation('pix'));
  document.getElementById('confirmCashPayment')?.addEventListener('click', () => handlePaymentConfirmation('dinheiro'));

  const cardNumberInputs = document.querySelectorAll('input[placeholder*="0000 0000"]');
  cardNumberInputs.forEach(input => {
    input.addEventListener('input', function(e) {
      let value = e.target.value.replace(/\D/g, '');
      value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
      e.target.value = value.trim();
    });
  });

  const expiryInputs = document.querySelectorAll('input[placeholder="MM/AA"]');
  expiryInputs.forEach(input => {
    input.addEventListener('input', function(e) {
      let value = e.target.value.replace(/\D/g, '');
      if (value.length > 2) {
        value = value.substring(0, 2) + '/' + value.substring(2, 4);
      }
      e.target.value = value;
    });
  });

  const cvcInputs = document.querySelectorAll('input[placeholder="000"]');
  cvcInputs.forEach(input => {
    input.addEventListener('input', function(e) {
      e.target.value = e.target.value.replace(/\D/g, '').substring(0, 3);
    });
  });
});