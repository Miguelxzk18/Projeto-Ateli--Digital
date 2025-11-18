function toggleEditMode() {
  const viewMode = document.querySelector('.view-mode');
  const editMode = document.querySelector('.edit-mode');
  const isEditing = editMode.style.display === 'block';

  viewMode.style.display = isEditing ? 'block' : 'none';
  editMode.style.display = isEditing ? 'none' : 'block';

  const editButton = document.querySelector('.profile-edit-btn');
  editButton.querySelector('span').textContent = isEditing ? 'Editar perfil' : 'Cancelar';
}

function saveProfile() {
  const inputs = document.querySelectorAll('.edit-mode .form-control');
  const userData = {
    name: inputs[0].value,
    cpf: inputs[1].value,
    address: inputs[2].value,
    phone: inputs[3].value
  };

  fetch('/perfil/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    })
    .then(resp => resp.json())
    .then(json => {
      if (json.msg) {
        console.log(json.msg);
        const viewMode = document.querySelector('.view-mode');
        viewMode.innerHTML = `
              <h4>${userData.name}</h4>
              <p>Email: {{ user.email }}</p>
              <p style="margin-top: 10px; color: var(--text-light);">
                  CPF: ${userData.cpf || '(Não informado)'}<br>
                  Endereço: ${userData.address || '(Não informado)'}<br>
                  Celular: ${userData.phone || '(Não informado)'}
              </p>
              <small style="display:block; margin-top:15px; color: #999;">
                  Clique em "Editar perfil" para atualizar novamente.
              </small>
            `;
        toggleEditMode();
      } else {
        console.warn(json.erro || 'Falha ao atualizar.'); // Substituído alert por console.warn
      }
    })
    .catch(err => {
      console.error('Erro ao salvar perfil:', err);
      console.error('Erro de comunicação com o servidor.'); // Substituído alert por console.error
    });
}

document.addEventListener('DOMContentLoaded', function() {
  const cpfInput = document.querySelector('.cpf-mask');
  if (cpfInput) {
    cpfInput.addEventListener('input', function(e) {
      let value = e.target.value.replace(/\D/g, '');
      value = value.replace(/(\d{3})(\d)/, '$1.$2');
      value = value.replace(/(\d{3})(\d)/, '$1.$2');
      value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
      e.target.value = value;
    });
  }

  const phoneInput = document.querySelector('.phone-mask');
  if (phoneInput) {
    phoneInput.addEventListener('input', function(e) {
      let value = e.target.value.replace(/\D/g, '');
      if (value.length > 2) {
        value = `(${value.substring(0, 2)}) ${value.substring(2)}`;
      }
      if (value.length > 10) {
        value = `${value.substring(0, 10)}-${value.substring(10, 15)}`;
      }
      e.target.value = value;
    });
  }
});