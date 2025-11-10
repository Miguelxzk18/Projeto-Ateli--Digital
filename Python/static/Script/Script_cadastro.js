document.getElementById('cadastroForm').addEventListener('submit', function(e) {
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;

  if (password !== confirmPassword) {
    e.preventDefault();
    console.warn('As senhas não coincidem. Por favor, verifique novamente.');
    return;
  }

  if (password.length < 8) {
    e.preventDefault();
    console.warn('A senha deve ter pelo menos 8 caracteres.');
    return;
  }

  console.log('Enviando dados de cadastro...');
});