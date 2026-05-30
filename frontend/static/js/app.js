// Инициализация Vis.js Графа Сети
document.addEventListener("DOMContentLoaded", function() {
    const container = document.getElementById('network-graph');
    
    // Описываем узлы (Nodes)
    const nodes = new vis.DataSet([
        // Центр управления
        { id: 'gateway', label: 'DECEPTION\nGATEWAY', group: 'gw', shape: 'box', font: { color: '#fff', face: 'monospace' } },
        
        // РЕАЛЬНЫЙ МИР (Сверху, координаты Y отрицательные)
        { id: 'real_subnet', label: 'Real Subnet\n(192.168.1.0/24)', group: 'real_group', x: 0, y: -100, fixed: true },
        { id: 'real_lamp', label: 'Бра Гостиная\n(Real)', group: 'real_dev', x: -150, y: -200, fixed: true },
        { id: 'real_lock', label: 'Замок Двери\n(Real)', group: 'real_dev', x: 0, y: -200, fixed: true },
        { id: 'real_sensors', label: 'Климат Сенсор\n(Real)', group: 'real_dev', x: 150, y: -200, fixed: true },

        // ТЕНЕВОЙ МИР (Снизу, координаты Y положительные)
        { id: 'shadow_subnet', label: 'SHADOW TWIN\n(Honeynet)', group: 'shadow_group', x: 0, y: 100, fixed: true },
        { id: 'shadow_lamp', label: 'Бра Гостиная\n(v1.0.4-vuln)', group: 'shadow_dev', x: -150, y: 200, fixed: true },
        { id: 'shadow_lock', label: 'Замок Двери\n(v2.1-exploit)', group: 'shadow_dev', x: 0, y: 200, fixed: true },
        { id: 'canary', label: 'sys_canary_99\n(MARKER)', group: 'canary_dev', x: 150, y: 200, fixed: true }
    ]);

    // Связи (Edges)
    const edges = new vis.DataSet([
        { from: 'gateway', to: 'real_subnet', color: { color: '#00ffcc' }, width: 3 },
        { from: 'real_subnet', to: 'real_lamp', color: '#00ffcc' },
        { from: 'real_subnet', to: 'real_lock', color: '#00ffcc' },
        { from: 'real_subnet', to: 'real_sensors', color: '#00ffcc' },

        { from: 'gateway', to: 'shadow_subnet', color: { color: '#ff3366', dash: true }, width: 2 },
        { from: 'shadow_subnet', to: 'shadow_lamp', color: '#ff3366' },
        { from: 'shadow_subnet', to: 'shadow_lock', color: '#ff3366' },
        { from: 'shadow_subnet', to: 'canary', color: '#ff3366', width: 2 }
    ]);

    const data = { nodes: nodes, edges: edges };

    // Стилизация групп узлов
    const options = {
        physics: false, // Отключаем динамику, так как задали фиксированные координаты для идеального split-экрана
        nodes: {
            shape: 'dot',
            size: 20,
            font: { size: 12, color: '#94a3b8' },
            borderWidth: 2
        },
        groups: {
            gw: { color: { background: '#1e293b', border: '#00ffcc' }, size: 30 },
            real_group: { color: { background: '#064e3b', border: '#00ffcc' }, shape: 'diamond' },
            real_dev: { color: { background: '#131a30', border: '#3b82f6' } },
            shadow_group: { color: { background: '#500724', border: '#ff3366' }, shape: 'triangle' },
            shadow_dev: { color: { background: '#131a30', border: '#a855f7' } },
            canary_dev: { color: { background: '#7c2d12', border: '#ea580c' }, shape: 'star' }
        }
    };

    const network = new vis.Network(container, data, options);

    // --- ИНТЕРАКТИВ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ ---
    const lampToggle = document.getElementById('lamp-toggle');
    const lampIcon = document.getElementById('lamp-icon');
    const lampStatus = document.getElementById('lamp-status');
    const terminal = document.getElementById('terminal-log');

    lampToggle.addEventListener('change', function() {
        if (this.checked) {
            lampIcon.classList.add('active');
            lampStatus.innerText = "Включено";
            lampStatus.style.color = "#fdd835";
            addLogLine("[INFO] User IP 192.168.1.15 -> POST /api/lights/living_room/toggle [STATUS: 200 OK]");
            
            // Подсветим реальную лампочку на графе
            nodes.update({id: 'real_lamp', color: {background: '#fdd835', border: '#03a9f4'}});
        } else {
            lampIcon.classList.remove('active');
            lampStatus.innerText = "Выключено";
            lampStatus.style.color = "#64748b";
            addLogLine("[INFO] User IP 192.168.1.15 -> POST /api/lights/living_room/toggle [STATUS: 200 OK]");
            
            nodes.update({id: 'real_lamp', color: {background: '#131a30', border: '#3b82f6'}});
        }
    });

    function addLogLine(text) {
        const line = document.createElement('div');
        line.className = 'log-line';
        line.innerText = text;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    }
});