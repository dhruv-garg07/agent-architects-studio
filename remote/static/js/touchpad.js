// touchpad.js - Real laptop touchpad behavior with proper click prevention
(function() {
    const touchpad = document.getElementById("touchpad");
    if (!touchpad) return;
    
    let lastX = null;
    let lastY = null;
    let startX = null;
    let startY = null;
    let scrollMode = false;
    let dragMode = false;
    let pointerDown = false;
    let pointerMoved = false;
    let isDragging = false;
    let downTime = 0;
    let pendingDx = 0;
    let pendingDy = 0;
    let pendingFrame = false;
    let scrollAccumulator = 0;
    let sensitivity = 2.0;
    let dragTimer = null;
    
    // Movement thresholds
    const MOVE_THRESHOLD = 5; // Minimum pixels before cursor moves
    const CLICK_THRESHOLD = 8; // Maximum movement for a click (not a drag)
    const TAP_TIMEOUT = 200; // Maximum time for a tap (ms)
    const HOLD_DELAY = 400; // Time before hold becomes drag (ms)
    const SCROLL_STEP = 15; // Pixels to accumulate before scroll
    const BATCH_INTERVAL = 10; // ~100fps batching
    
    const sendScroll = (dy) => {
        window.remoteSocket.sendSocketCommand("mouse", "scroll", { clicks: -dy });
    };
    
    const flushMove = () => {
        if (pendingDx !== 0 || pendingDy !== 0) {
            const sendDx = Math.round(pendingDx * sensitivity);
            const sendDy = Math.round(pendingDy * sensitivity);
            if (sendDx !== 0 || sendDy !== 0) {
                window.remoteSocket.sendTouchMove(sendDx, sendDy);
            }
            pendingDx = 0;
            pendingDy = 0;
        }
        pendingFrame = false;
    };
    
    const scheduleFlush = () => {
        if (!pendingFrame) {
            pendingFrame = true;
            setTimeout(flushMove, BATCH_INTERVAL);
        }
    };
    
    const sendMove = (dx, dy) => {
        pendingDx += dx;
        pendingDy += dy;
        scheduleFlush();
    };
    
    const getPoint = (event) => {
        if (event.touches && event.touches.length > 0) {
            return { clientX: event.touches[0].clientX, clientY: event.touches[0].clientY };
        }
        if (event.changedTouches && event.changedTouches.length > 0) {
            return { clientX: event.changedTouches[0].clientX, clientY: event.changedTouches[0].clientY };
        }
        return { clientX: event.clientX, clientY: event.clientY };
    };
    
    const getDistance = (x1, y1, x2, y2) => {
        return Math.hypot(x2 - x1, y2 - y1);
    };
    
    const beginPointer = (point, event) => {
        if (event && typeof event.preventDefault === "function") {
            event.preventDefault();
        }
        lastX = point.clientX;
        lastY = point.clientY;
        startX = point.clientX;
        startY = point.clientY;
        pointerDown = true;
        pointerMoved = false;
        isDragging = false;
        downTime = Date.now();
        scrollAccumulator = 0;
        pendingDx = 0;
        pendingDy = 0;
        
        if (dragTimer) {
            clearTimeout(dragTimer);
            dragTimer = null;
        }
        
        if (!dragMode) {
            dragTimer = setTimeout(() => {
                if (pointerDown && !pointerMoved) {
                    isDragging = true;
                    window.remoteSocket.sendSocketCommand("mouse", "mousedown", { button: "left" });
                }
            }, HOLD_DELAY);
        } else {
            isDragging = true;
            window.remoteSocket.sendSocketCommand("mouse", "mousedown", { button: "left" });
        }
    };
    
    const movePointer = (point, event) => {
        if (lastX === null || lastY === null) return;
        if (event && typeof event.preventDefault === "function") {
            event.preventDefault();
        }
        
        const dx = point.clientX - lastX;
        const dy = point.clientY - lastY;
        const totalDistance = getDistance(startX, startY, point.clientX, point.clientY);
        
        lastX = point.clientX;
        lastY = point.clientY;
        
        if (scrollMode) {
            scrollAccumulator += dy;
            while (Math.abs(scrollAccumulator) >= SCROLL_STEP) {
                const step = Math.sign(scrollAccumulator);
                sendScroll(step);
                scrollAccumulator -= step * SCROLL_STEP;
            }
            return;
        }
        
        if (!pointerMoved && totalDistance < MOVE_THRESHOLD) {
            return;
        }
        
        if (!pointerMoved && totalDistance >= MOVE_THRESHOLD) {
            pointerMoved = true;
            if (dragTimer) {
                clearTimeout(dragTimer);
                dragTimer = null;
            }
        }
        
        sendMove(dx, dy);
    };
    
    const cleanupPointer = () => {
        if (dragTimer) {
            clearTimeout(dragTimer);
            dragTimer = null;
        }
        
        if (isDragging) {
            window.remoteSocket.sendSocketCommand("mouse", "mouseup", { button: "left" });
        }
        
        lastX = null;
        lastY = null;
        startX = null;
        startY = null;
        pointerDown = false;
        pointerMoved = false;
        isDragging = false;
        scrollAccumulator = 0;
    };
    
    const handleDown = (point, event) => {
        if (!point) return;
        beginPointer(point, event);
    };
    
    const handleMove = (point, event) => {
        if (!pointerDown || !point) return;
        movePointer(point, event);
    };
    
    const handleUp = () => {
        if (!pointerDown) return;
        
        flushMove();
        
        const elapsed = Date.now() - downTime;
        const totalDistance = getDistance(startX, startY, lastX, lastY);
        
        if (!isDragging && !pointerMoved && totalDistance < CLICK_THRESHOLD && elapsed < TAP_TIMEOUT) {
            window.remoteSocket.sendSocketCommand("mouse", "click", { button: "left" });
        }
        
        cleanupPointer();
    };
    
    touchpad.addEventListener('contextmenu', (event) => {
        event.preventDefault();
    });
    
    touchpad.style.userSelect = 'none';
    touchpad.style.webkitUserSelect = 'none';
    touchpad.style.touchAction = 'none';
    
    if (window.PointerEvent) {
        touchpad.addEventListener("pointerdown", (event) => {
            if (!event.isPrimary) return;
            if (typeof touchpad.setPointerCapture === "function") {
                try {
                    touchpad.setPointerCapture(event.pointerId);
                } catch (err) {}
            }
            handleDown(getPoint(event), event);
        });
        
        touchpad.addEventListener("pointermove", (event) => {
            if (!event.isPrimary) return;
            handleMove(getPoint(event), event);
        });
        
        touchpad.addEventListener("pointerup", (event) => {
            if (!event.isPrimary) return;
            if (
                typeof touchpad.hasPointerCapture === "function" &&
                touchpad.hasPointerCapture(event.pointerId) &&
                typeof touchpad.releasePointerCapture === "function"
            ) {
                try {
                    touchpad.releasePointerCapture(event.pointerId);
                } catch (err) {}
            }
            handleUp();
        });
        
        touchpad.addEventListener("pointercancel", () => {
            handleUp();
        });
        
        touchpad.addEventListener("lostpointercapture", () => {
            handleUp();
        });
    } else {
        touchpad.addEventListener("touchstart", (event) => {
            handleDown(getPoint(event), event);
        }, { passive: false });
        
        touchpad.addEventListener("touchmove", (event) => {
            handleMove(getPoint(event), event);
        }, { passive: false });
        
        touchpad.addEventListener("touchend", () => {
            handleUp();
        });
        
        touchpad.addEventListener("touchcancel", () => {
            handleUp();
        });
    }
    
    document.getElementById("leftClick")?.addEventListener("click", (e) => {
        e.preventDefault();
        window.remoteSocket.sendSocketCommand("mouse", "click", { button: "left" });
    });
    
    document.getElementById("okClick")?.addEventListener("click", (e) => {
        e.preventDefault();
        window.remoteSocket.sendSocketCommand("mouse", "click", { button: "left" });
    });
    
    document.getElementById("rightClick")?.addEventListener("click", (e) => {
        e.preventDefault();
        window.remoteSocket.sendSocketCommand("mouse", "click", { button: "right" });
    });
    
    document.getElementById("doubleClick")?.addEventListener("click", (e) => {
        e.preventDefault();
        window.remoteSocket.sendSocketCommand("mouse", "doubleclick");
    });
    
    document.getElementById("dragMode")?.addEventListener("click", (e) => {
        e.preventDefault();
        dragMode = !dragMode;
        touchpad.style.background = dragMode ? "rgba(255, 200, 90, 0.15)" : "rgba(255, 255, 255, 0.06)";
        document.getElementById("dragMode").textContent = dragMode ? "Drag Mode: ON" : "Drag Mode";
    });
    
    document.getElementById("scrollMode")?.addEventListener("click", (e) => {
        e.preventDefault();
        scrollMode = !scrollMode;
        touchpad.style.background = scrollMode ? "rgba(255, 255, 255, 0.1)" : "rgba(255, 255, 255, 0.06)";
        document.getElementById("scrollMode").textContent = scrollMode ? "Scroll Mode: ON" : "Scroll Mode";
    });
    
    document.getElementById("sensitivityRange")?.addEventListener("input", (event) => {
        sensitivity = parseFloat(event.target.value) || 2.0;
        document.getElementById("sensitivityValue").textContent = sensitivity.toFixed(1);
    });
})();