(function () {
    const shell = document.querySelector('.prompter-shell');
    if (!shell) {
        return;
    }

    const stage = shell.querySelector('.prompter-stage');
    const content = shell.querySelector('.prompter-content');
    const overlay = shell.querySelector('.prompter-overlay');
    const controls = shell.querySelectorAll('[data-control]');
    const token = shell.dataset.controlToken;
    const controlsToggleBtn = shell.querySelector('[data-action="controls-toggle"]');

    let speed = parseFloat(shell.querySelector('[data-control="speed"]').value || '1');
    let fontSize = 54;
    let lineHeight = 140;
    let isPlaying = false;
    let lastTime = 0;
    let rafId;

    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    const setControlsVisibility = (visible) => {
        shell.classList.toggle('controls-hidden', !visible);
        if (controlsToggleBtn) {
            controlsToggleBtn.setAttribute('aria-expanded', visible ? 'true' : 'false');
            controlsToggleBtn.setAttribute('aria-label', visible ? 'Hide controls panel' : 'Show controls panel');
            controlsToggleBtn.classList.toggle('is-open', visible);
            const srText = controlsToggleBtn.querySelector('.sr-only');
            if (srText) {
                srText.textContent = visible ? 'Hide controls panel' : 'Show controls panel';
            }
        }
    };

    if (controlsToggleBtn) {
        controlsToggleBtn.addEventListener('click', () => {
            const shouldShow = shell.classList.contains('controls-hidden');
            setControlsVisibility(shouldShow);
        });
        controlsToggleBtn.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
                event.preventDefault();
                const shouldShow = shell.classList.contains('controls-hidden');
                setControlsVisibility(shouldShow);
            }
        });
    }

    const updateStyles = () => {
        content.style.fontSize = `${fontSize}px`;
        content.style.lineHeight = `${lineHeight / 100}`;
        stage.dataset.theme = shell.querySelector('[data-control="theme"]').value;
    };

    const toggleGuidelines = (active) => {
        if (active) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    };

    const tick = (timestamp) => {
        if (!isPlaying) {
            lastTime = timestamp;
            return;
        }
        const delta = (timestamp - lastTime) / 1000;
        const pixels = delta * speed * 120;
        content.scrollTop += pixels;
        lastTime = timestamp;
        rafId = window.requestAnimationFrame(tick);
    };

    const start = () => {
        if (isPlaying) {
            return;
        }
        isPlaying = true;
        lastTime = performance.now();
        rafId = window.requestAnimationFrame(tick);
    };

    const stop = () => {
        isPlaying = false;
        if (rafId) {
            window.cancelAnimationFrame(rafId);
        }
    };

    const rewind = () => {
        stop();
        content.scrollTop = 0;
    };

    shell.querySelector('[data-action="toggle"]').addEventListener('click', () => {
        if (isPlaying) {
            stop();
            shell.querySelector('[data-action="toggle"]').textContent = 'Start';
        } else {
            start();
            shell.querySelector('[data-action="toggle"]').textContent = 'Pause';
        }
    });

    shell.querySelector('[data-action="rewind"]').addEventListener('click', rewind);

    controls.forEach((control) => {
        control.addEventListener('input', (event) => {
            const target = event.currentTarget;
            const type = target.dataset.control;
            let resetScroll = false;

            switch (type) {
                case 'font-size':
                    fontSize = clamp(parseInt(target.value, 10), 24, 140);
                    resetScroll = true;
                    break;
                case 'line-height':
                    lineHeight = clamp(parseInt(target.value, 10), 100, 250);
                    resetScroll = true;
                    break;
                case 'speed':
                    speed = clamp(parseFloat(target.value), 0.2, 4);
                    break;
                case 'theme':
                    break;
                case 'mirror':
                    content.classList.toggle('mirrored', target.checked);
                    break;
                case 'uppercase':
                    content.classList.toggle('uppercase', target.checked);
                    break;
                case 'guidelines':
                    toggleGuidelines(target.checked);
                    break;
                default:
                    break;
            }

            updateStyles();
            if (resetScroll) {
                content.scrollTop = 0;
            }
        });
    });

    setControlsVisibility(false);
    updateStyles();

    const broadcastState = (action, value) => {
        if (!socket || !token) {
            return;
        }
        socket.emit('control:update', { token, action, value });
    };

    let socket;
    if (token) {
        socket = window.io('/control', { transports: ['websocket', 'polling'] });
        socket.emit('join', { token });
        socket.on('error', (payload) => {
            console.error('Remote channel error:', payload?.message || payload);
        });

        socket.on('teleprompter:update', ({ action, value }) => {
            switch (action) {
                case 'toggle':
                    shell.querySelector('[data-action="toggle"]').click();
                    break;
                case 'rewind':
                    rewind();
                    break;
                case 'speed':
                    shell.querySelector('[data-control="speed"]').value = value;
                    speed = parseFloat(value);
                    break;
                case 'font-size':
                    fontSize = parseInt(value, 10);
                    shell.querySelector('[data-control="font-size"]').value = value;
                    break;
                case 'line-height':
                    lineHeight = parseInt(value, 10);
                    shell.querySelector('[data-control="line-height"]').value = value;
                    break;
                case 'mirror':
                    const mirror = value === true || value === 'true';
                    shell.querySelector('[data-control="mirror"]').checked = mirror;
                    content.classList.toggle('mirrored', mirror);
                    break;
                case 'uppercase':
                    const uppercase = value === true || value === 'true';
                    shell.querySelector('[data-control="uppercase"]').checked = uppercase;
                    content.classList.toggle('uppercase', uppercase);
                    break;
                case 'guidelines':
                    const active = value === true || value === 'true';
                    shell.querySelector('[data-control="guidelines"]').checked = active;
                    toggleGuidelines(active);
                    break;
                case 'theme':
                    shell.querySelector('[data-control="theme"]').value = value;
                    break;
                default:
                    break;
            }
            updateStyles();
        });

        socket.on('teleprompter:end', () => {
            stop();
        });
    }

    // Broadcast local changes to remote controller when adjustments happen directly on the prompter.
    controls.forEach((control) => {
        control.addEventListener('change', (event) => {
            const target = event.currentTarget;
            const action = target.dataset.control;
            let value;
            if (target.type === 'checkbox') {
                value = target.checked;
            } else {
                value = target.value;
            }
            broadcastState(action, value);
        });
    });
})();
