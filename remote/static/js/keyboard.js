// keyboard.js
(function() {
    const keyboardInput = document.getElementById('keyboardInput');
    const sendTextBtn = document.getElementById('sendText');
    const enterKeyBtn = document.getElementById('enterKey');
    const backspaceKeyBtn = document.getElementById('backspaceKey');
    
    if (!keyboardInput) return;
    
    sendTextBtn?.addEventListener('click', () => {
        const text = keyboardInput.value.trim();
        if (text) {
            window.remoteSocket.sendSocketCommand('keyboard', 'type', { text });
            keyboardInput.value = '';
        }
    });
    
    enterKeyBtn?.addEventListener('click', () => {
        window.remoteSocket.sendSocketCommand('keyboard', 'press', { key: 'enter' });
    });
    
    backspaceKeyBtn?.addEventListener('click', () => {
        window.remoteSocket.sendSocketCommand('keyboard', 'press', { key: 'backspace' });
    });
    
    // Allow Enter key in textarea to send
    keyboardInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            const text = keyboardInput.value.trim();
            if (text) {
                window.remoteSocket.sendSocketCommand('keyboard', 'type', { text });
                keyboardInput.value = '';
            }
        }
    });
})();
