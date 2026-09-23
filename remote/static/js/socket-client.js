// socket-client.js
window.remoteSocket = {
    socket: null,
    connected: false,
    
    init() {
        this.socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true
        });
        
        this.socket.on('connect', () => {
            this.connected = true;
            const statusEl = document.getElementById('connectionStatus');
            if (statusEl) {
                statusEl.textContent = '● Connected';
                statusEl.style.color = '#4CAF50';
            }
        });
        
        this.socket.on('disconnect', () => {
            this.connected = false;
            const statusEl = document.getElementById('connectionStatus');
            if (statusEl) {
                statusEl.textContent = '● Disconnected';
                statusEl.style.color = '#f44336';
            }
        });
        
        this.socket.on('command_ack', (data) => {
            console.log('Command acknowledged:', data);
        });
        
        // Initialize WebSocket for faster mouse movement
        this.initWebSocket();
    },
    
    initWebSocket() {
        const wsUrl = `ws://${window.REMOTE_CONFIG.hostname}:${window.REMOTE_CONFIG.wsPort}/ws`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected for mouse');
            this.wsReady = true;
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting...');
            this.wsReady = false;
            setTimeout(() => this.initWebSocket(), 1000);
        };
        
        this.ws.onerror = () => {
            this.wsReady = false;
        };
    },
    
    sendSocketCommand(category, action, data = {}) {
        if (this.connected) {
            this.socket.emit('remote_command', {
                category,
                action,
                ...data
            });
        }
    },
    
    sendTouchMove(dx, dy) {
        // Use WebSocket for faster mouse movement
        if (this.ws && this.wsReady && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'touchmove',
                dx: dx,
                dy: dy
            }));
        } else if (this.connected) {
            this.socket.emit('touchmove', { dx, dy });
        }
    }
};

// Initialize on load
window.remoteSocket.init();
