/**
 * Chat Widget Flutuante - Agromercantil
 * Mantém conversa em localStorage
 */

(function() {
    // Estado do widget
    let isOpen = false;
    let chatHistory = JSON.parse(localStorage.getItem('agroChatHistory') || '[]');
    
    // Criar elemento do widget
    function createWidget() {
        const widget = document.createElement('div');
        widget.id = 'chat-widget';
        widget.innerHTML = `
            <style>
                #chat-widget-container {
                    position: fixed;
                    right: 0;
                    top: 50%;
                    transform: translateY(-50%);
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                }
                
                #chat-widget-button {
                    width: 60px;
                    height: 60px;
                    background: white;
                    border-radius: 16px 0 0 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    box-shadow: -4px 0 20px rgba(17, 40, 0, 0.25);
                    transition: all 0.3s ease;
                    border: none;
                    border-right: 4px solid #F58220;
                    padding: 8px;
                    overflow: hidden;
                }
                
                #chat-widget-button:hover {
                    width: 68px;
                    transform: translateX(-4px);
                    box-shadow: -6px 0 24px rgba(17, 40, 0, 0.35);
                }
                
                #chat-widget-button img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    border-radius: 10px;
                }
                
                #chat-widget-panel {
                    position: fixed;
                    right: -400px;
                    top: 0;
                    width: 400px;
                    height: 100vh;
                    background: #fafaf5;
                    box-shadow: -4px 0 24px rgba(0,0,0,0.15);
                    transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: flex;
                    flex-direction: column;
                    z-index: 10000;
                }
                
                #chat-widget-panel.open {
                    right: 0;
                }
                
                #chat-widget-header {
                    background: linear-gradient(135deg, #112800 0%, #253f0f 100%);
                    color: white;
                    padding: 16px 20px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                
                #chat-widget-header h3 {
                    margin: 0;
                    font-family: 'Manrope', sans-serif;
                    font-size: 16px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                #chat-widget-header img {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    object-fit: cover;
                    border: 2px solid rgba(255,255,255,0.3);
                }
                
                #chat-widget-close {
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                
                #chat-widget-close:hover {
                    background: rgba(255,255,255,0.1);
                }
                
                #chat-widget-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                
                .chat-message {
                    max-width: 80%;
                    padding: 12px 16px;
                    border-radius: 16px;
                    font-size: 14px;
                    line-height: 1.5;
                    animation: messageSlide 0.3s ease;
                }
                
                @keyframes messageSlide {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .chat-message.user {
                    align-self: flex-end;
                    background: #112800;
                    color: white;
                    border-bottom-right-radius: 4px;
                }
                
                .chat-message.bot {
                    align-self: flex-start;
                    background: #f4f4ef;
                    color: #1a1c19;
                    border-bottom-left-radius: 4px;
                }
                
                .chat-message.typing {
                    display: flex;
                    gap: 4px;
                    align-items: center;
                    padding: 16px;
                }
                
                .typing-dot {
                    width: 8px;
                    height: 8px;
                    background: #74796c;
                    border-radius: 50%;
                    animation: typingBounce 1.4s infinite ease-in-out;
                }
                
                .typing-dot:nth-child(1) { animation-delay: 0s; }
                .typing-dot:nth-child(2) { animation-delay: 0.2s; }
                .typing-dot:nth-child(3) { animation-delay: 0.4s; }
                
                @keyframes typingBounce {
                    0%, 80%, 100% { transform: scale(0.6); }
                    40% { transform: scale(1); }
                }
                
                #chat-widget-input-area {
                    padding: 16px 20px;
                    border-top: 1px solid #e4e2e1;
                    background: white;
                }
                
                #chat-widget-form {
                    display: flex;
                    gap: 8px;
                }
                
                #chat-widget-input {
                    flex: 1;
                    padding: 12px 16px;
                    border: 1px solid #c4c8ba;
                    border-radius: 24px;
                    font-size: 14px;
                    font-family: 'Inter', sans-serif;
                    outline: none;
                    transition: border-color 0.2s;
                }
                
                #chat-widget-input:focus {
                    border-color: #112800;
                }
                
                #chat-widget-send {
                    width: 44px;
                    height: 44px;
                    background: #112800;
                    border: none;
                    border-radius: 50%;
                    color: white;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s;
                }
                
                #chat-widget-send:hover {
                    background: #143d31;
                }
                
                #chat-widget-send:disabled {
                    background: #c4c8ba;
                    cursor: not-allowed;
                }
                
                .chat-suggestions {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin-top: 12px;
                }
                
                .chat-suggestion {
                    padding: 6px 12px;
                    background: #f4f4ef;
                    border: 1px solid #e4e2e1;
                    border-radius: 16px;
                    font-size: 12px;
                    color: #112800;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                
                .chat-suggestion:hover {
                    background: #112800;
                    color: white;
                    border-color: #112800;
                }
                
                #chat-widget-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0,0,0,0.3);
                    opacity: 0;
                    visibility: hidden;
                    transition: all 0.3s;
                    z-index: 9998;
                }
                
                #chat-widget-overlay.open {
                    opacity: 1;
                    visibility: visible;
                }
            </style>
            
            <div id="chat-widget-overlay"></div>
            
            <div id="chat-widget-container">
                <button id="chat-widget-button" title="Falar com AgroBot">
                    <img src="/static/images/agent.png" alt="AgroBot">
                </button>
            </div>
            
            <div id="chat-widget-panel">
                <div id="chat-widget-header">
                    <h3>
                        <img src="/static/images/agent.png" alt="AgroBot">
                        <div>
                            <div style="font-size: 16px; font-weight: 600;">AgroBot</div>
                            <div style="font-size: 11px; opacity: 0.8; font-weight: 400;">Analista de Commodities</div>
                        </div>
                    </h3>
                    <button id="chat-widget-close">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                
                <div id="chat-widget-messages"></div>
                
                <div id="chat-widget-input-area">
                    <form id="chat-widget-form">
                        <input 
                            type="text" 
                            id="chat-widget-input" 
                            placeholder="Digite sua pergunta..."
                            autocomplete="off"
                        />
                        <button type="submit" id="chat-widget-send">
                            <span class="material-symbols-outlined">send</span>
                        </button>
                    </form>
                    <div class="chat-suggestions">
                        <span class="chat-suggestion" data-msg="Qual o faturamento total?">Faturamento</span>
                        <span class="chat-suggestion" data-msg="Quantos clientes ativos?">Clientes</span>
                        <span class="chat-suggestion" data-msg="Top produtos vendidos">Produtos</span>
                        <span class="chat-suggestion" data-msg="Ajuda">Ajuda</span>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(widget);
        
        // Event listeners
        document.getElementById('chat-widget-button').addEventListener('click', toggleChat);
        document.getElementById('chat-widget-close').addEventListener('click', toggleChat);
        document.getElementById('chat-widget-overlay').addEventListener('click', toggleChat);
        document.getElementById('chat-widget-form').addEventListener('submit', sendMessage);
        
        // Suggestions
        document.querySelectorAll('.chat-suggestion').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const msg = e.target.dataset.msg;
                document.getElementById('chat-widget-input').value = msg;
                sendMessage(e);
            });
        });
        
        // Carregar histórico
        renderHistory();
    }
    
    // Toggle chat
    function toggleChat() {
        isOpen = !isOpen;
        document.getElementById('chat-widget-panel').classList.toggle('open', isOpen);
        document.getElementById('chat-widget-overlay').classList.toggle('open', isOpen);
        
        if (isOpen) {
            scrollToBottom();
        }
    }
    
    // Enviar mensagem
    async function sendMessage(e) {
        e.preventDefault();
        
        const input = document.getElementById('chat-widget-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Adicionar mensagem do usuário
        addMessage(message, 'user');
        input.value = '';
        
        // Mostrar typing
        showTyping();
        
        // Enviar para API
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            // Remover typing e adicionar resposta
            setTimeout(() => {
                removeTyping();
                addMessage(data.response, 'bot');
            }, 800);
            
        } catch (error) {
            removeTyping();
            addMessage('Desculpe, ocorreu um erro. Tente novamente.', 'bot');
        }
    }
    
    // Adicionar mensagem
    function addMessage(text, sender) {
        const messagesDiv = document.getElementById('chat-widget-messages');
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${sender}`;
        messageEl.textContent = text;
        messagesDiv.appendChild(messageEl);
        
        // Salvar no histórico
        chatHistory.push({ text, sender, timestamp: Date.now() });
        localStorage.setItem('agroChatHistory', JSON.stringify(chatHistory));
        
        scrollToBottom();
    }
    
    // Mostrar typing
    function showTyping() {
        const messagesDiv = document.getElementById('chat-widget-messages');
        const typingEl = document.createElement('div');
        typingEl.id = 'typing-indicator';
        typingEl.className = 'chat-message bot typing';
        typingEl.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        messagesDiv.appendChild(typingEl);
        scrollToBottom();
    }
    
    // Remover typing
    function removeTyping() {
        const typingEl = document.getElementById('typing-indicator');
        if (typingEl) typingEl.remove();
    }
    
    // Renderizar histórico
    function renderHistory() {
        const messagesDiv = document.getElementById('chat-widget-messages');
        messagesDiv.innerHTML = '';
        
        // Mensagem de boas-vindas se vazio
        if (chatHistory.length === 0) {
            const welcomeEl = document.createElement('div');
            welcomeEl.className = 'chat-message bot';
            welcomeEl.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <img src="/static/images/agent.png" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;">
                    <strong>AgroBot</strong>
                </div>
                Olá! 👋 Tudo bem? Sou seu assistente aqui na Agromercantil.<br><br>
                Posso te ajudar com números de vendas, informações de clientes, dados de commodities ou insights sobre o mercado agrícola.<br><br>
                <em>O que você gostaria de saber?</em>
            `;
            messagesDiv.appendChild(welcomeEl);
            
            // Adicionar sugestões iniciais
            const suggestionsEl = document.createElement('div');
            suggestionsEl.className = 'chat-suggestions';
            suggestionsEl.style.marginTop = '12px';
            suggestionsEl.innerHTML = `
                <span class="chat-suggestion" data-msg="Qual nosso faturamento?">💰 Faturamento</span>
                <span class="chat-suggestion" data-msg="Quantos clientes temos?">👥 Clientes</span>
                <span class="chat-suggestion" data-msg="Top produtos vendidos">🌾 Produtos</span>
                <span class="chat-suggestion" data-msg="Tem alguma dica?">💡 Dica do dia</span>
            `;
            messagesDiv.appendChild(suggestionsEl);
            
            // Re-attach event listeners
            suggestionsEl.querySelectorAll('.chat-suggestion').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const msg = e.target.dataset.msg;
                    document.getElementById('chat-widget-input').value = msg;
                    sendMessage(e);
                });
            });
        } else {
            chatHistory.forEach((msg, index) => {
                const msgEl = document.createElement('div');
                msgEl.className = `chat-message ${msg.sender}`;
                
                // Adicionar avatar para mensagens do bot
                if (msg.sender === 'bot' && index > 0) {
                    msgEl.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; opacity: 0.7;">
                            <img src="/static/images/agent.png" style="width: 20px; height: 20px; border-radius: 50%; object-fit: cover;">
                            <span style="font-size: 11px;">AgroBot</span>
                        </div>
                        ${formatMessage(msg.text)}
                    `;
                } else {
                    msgEl.innerHTML = formatMessage(msg.text);
                }
                
                messagesDiv.appendChild(msgEl);
            });
        }
        
        scrollToBottom();
    }
    
    // Formatar mensagem (converter quebras de linha)
    function formatMessage(text) {
        return text.replace(/\n/g, '<br>');
    }
    
    // Scroll para baixo
    function scrollToBottom() {
        const messagesDiv = document.getElementById('chat-widget-messages');
        if (messagesDiv) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }
    
    // Inicializar quando DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createWidget);
    } else {
        createWidget();
    }
})();
