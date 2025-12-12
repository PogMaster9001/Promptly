(function () {
    const shell = document.querySelector('.remote-shell');
    if (!shell) {
        return;
    }

    const token = shell.dataset.controlToken;
    if (!token) {
        console.error('No control token provided.');
        return;
    }

    const socket = window.io('/control', { transports: ['websocket', 'polling'] });
    socket.emit('join', { token });
    socket.on('error', (payload) => {
        console.error('Remote channel error:', payload?.message || payload);
    });

    const send = (action, value) => {
        socket.emit('control:update', { token, action, value });
    };

    shell.querySelectorAll('[data-action]').forEach((button) => {
        button.addEventListener('click', (event) => {
            const action = event.currentTarget.dataset.action;
            send(action, true);
        });
    });

    shell.querySelectorAll('[data-channel]').forEach((input) => {
        const action = input.dataset.channel;
        if (input.type === 'range') {
            input.addEventListener('input', (event) => {
                send(action, event.currentTarget.value);
            });
        } else if (input.type === 'checkbox') {
            input.addEventListener('change', (event) => {
                const target = event.currentTarget;
                let value = target.checked;
                if (action === 'theme') {
                    value = target.checked ? 'dark' : 'light';
                }
                send(action, value);
            });
        }
    });

    socket.on('teleprompter:update', ({ action, value }) => {
        const target = shell.querySelector(`[data-channel="${action}"]`);
        if (!target) {
            return;
        }
        if (target.type === 'range') {
            target.value = value;
        } else if (target.type === 'checkbox') {
            if (action === 'theme') {
                target.checked = value === 'dark';
            } else {
                target.checked = value === true || value === 'true';
            }
        }
    });

    socket.on('teleprompter:end', () => {
        console.info('Teleprompter session ended.');
    });
})();
