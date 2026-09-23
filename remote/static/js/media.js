// media.js
(function() {
    // Media buttons
    document.querySelectorAll('[data-action="playpause"]').forEach(btn => {
        btn.addEventListener('click', () => {
            window.remoteSocket.sendSocketCommand('media', 'play_pause');
        });
    });
    
    document.querySelectorAll('[data-action="volumeup"]').forEach(btn => {
        btn.addEventListener('click', () => {
            window.remoteSocket.sendSocketCommand('media', 'volume_up');
        });
    });
    
    document.querySelectorAll('[data-action="volumedown"]').forEach(btn => {
        btn.addEventListener('click', () => {
            window.remoteSocket.sendSocketCommand('media', 'volume_down');
        });
    });
    
    document.querySelectorAll('[data-action="mute"]').forEach(btn => {
        btn.addEventListener('click', () => {
            window.remoteSocket.sendSocketCommand('media', 'mute');
        });
    });
    
    // System buttons
    document.querySelectorAll('[data-action="open"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = prompt('Enter app or file to open:');
            if (target) {
                window.remoteSocket.sendSocketCommand('system', 'open', { target });
            }
        });
    });
    
    document.querySelectorAll('[data-action="lock"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (confirm('Lock the computer?')) {
                window.remoteSocket.sendSocketCommand('system', 'lock');
            }
        });
    });
    
    document.querySelectorAll('[data-action="sleep"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (confirm('Put the computer to sleep?')) {
                window.remoteSocket.sendSocketCommand('system', 'sleep');
            }
        });
    });
    
    document.querySelectorAll('[data-action="restart"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (confirm('Restart the computer?')) {
                window.remoteSocket.sendSocketCommand('system', 'restart');
            }
        });
    });
    
    // Launcher buttons
    document.getElementById('launchChrome')?.addEventListener('click', () => {
        window.remoteSocket.sendSocketCommand('launcher', 'chrome');
    });
})();
