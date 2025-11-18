document.addEventListener("DOMContentLoaded", () => {
    
    // --- Lógica das Abas de Pagamento (pagamento.html) ---
    const paymentTabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    if (paymentTabs.length > 0) {
        // Define a primeira aba como ativa por padrão
        // (Baseado no 'Pagamento [crédito].pdf' que parece ser o padrão)
        const defaultTab = document.querySelector('.tab-link[data-tab="credito"]');
        const defaultContent = document.getElementById('credito');
        if (defaultTab && defaultContent) {
            defaultTab.classList.add('active');
            defaultContent.classList.add('active');
        }

        paymentTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.getAttribute('data-tab');

                // Remove 'active' de todas as abas e conteúdos
                paymentTabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                // Adiciona 'active' à aba clicada e ao conteúdo correspondente
                tab.classList.add('active');
                document.getElementById(targetTab).classList.add('active');
            });
        });
    }

});