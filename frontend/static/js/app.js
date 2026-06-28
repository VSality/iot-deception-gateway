const GATEWAY_CLIENT_STORAGE_KEY = "gateway_client_id";
const CLIMATE_TOPOLOGY_ID = "dev_climate";

function generateClientUuid() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
        const bytes = new Uint8Array(16);
        crypto.getRandomValues(bytes);
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;
        const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

/** Map WS graph node ids → HA entity suffix for phone UI sync */
const WS_DEVICE_TO_HA = {
    dev_hue_living: { domain: "light", objectId: "living" },
    shadow_dev_hue_living: { domain: "light", objectId: "living" },
    dev_hue_kitchen: { domain: "light", objectId: "kitchen" },
    shadow_dev_hue_kitchen: { domain: "light", objectId: "kitchen" },
    shadow_canary_hall_dimmer_aux: { domain: "light", objectId: "hall_dimmer_aux" },
    dev_lock: { domain: "lock", objectId: "main_door" },
    shadow_dev_lock: { domain: "lock", objectId: "main_door" },
};

let haPhoneActionsBound = false;

function entityDomId(entityId) {
    return entityId.replace(/\./g, "-");
}

function parseEntityId(entityId) {
    const dot = entityId.indexOf(".");
    if (dot === -1) return { domain: "", objectId: entityId };
    return {
        domain: entityId.slice(0, dot),
        objectId: entityId.slice(dot + 1),
    };
}

function lightStatusLabel(on) {
    return on ? "Включено" : "Выключено";
}

function lockStatusLabel(unlocked) {
    return unlocked ? "Открыто" : "Заблокировано";
}

function lockIsUnlocked(haState) {
    return haState === "unlocked";
}

function lockRowDomIds(entityId) {
    const { objectId } = parseEntityId(entityId);
    const domId = entityDomId(entityId);
    return {
        objectId,
        domId,
        leftIconId: `icon-${domId}`,
        statusTextId: `lock-status-text-${objectId}`,
        actionIconId: `lock-action-icon-${objectId}`,
        btnId: `lock-btn-${objectId}`,
    };
}

/** @param {{ icon?, statusEl?, btn?, btnIcon?, row?, haState }} parts */
function paintLockRowUi(parts) {
    const { icon, statusEl, btn, btnIcon, row, haState } = parts;
    const unlocked = lockIsUnlocked(haState);
    if (row) row.dataset.lockState = haState;

    if (icon) {
        icon.className = unlocked ? "mdi mdi-lock-open-variant" : "mdi mdi-lock";
        if (unlocked) icon.classList.add("active");
        else icon.classList.remove("active");
    }
    if (statusEl) {
        statusEl.innerText = lockStatusLabel(unlocked);
        statusEl.style.color = unlocked ? "#fbbf24" : "#64748b";
    }
    if (btnIcon) {
        btnIcon.className = unlocked
            ? "mdi mdi-lock-open-variant"
            : "mdi mdi-lock";
        if (unlocked) btnIcon.classList.add("active");
        else btnIcon.classList.remove("active");
    }
    if (btn) {
        btn.title = unlocked
            ? "Заблокировать"
            : "Открыть замок (шаг knock)";
    }
}

function syncLockRowUi(entityId, state) {
    const ids = lockRowDomIds(entityId);
    paintLockRowUi({
        haState: state,
        row: document.querySelector(
            `.ha-device-row[data-entity-id="${entityId}"]`
        ),
        icon: document.getElementById(ids.leftIconId),
        statusEl: document.getElementById(ids.statusTextId),
        btn: document.getElementById(ids.btnId),
        btnIcon: document.getElementById(ids.actionIconId),
    });
}

function syncLightRowUi(entityId, state) {
    const domId = entityDomId(entityId);
    const toggle = document.getElementById(`toggle-${domId}`);
    const icon = document.getElementById(`icon-${domId}`);
    const status = document.getElementById(`status-${domId}`);
    const on = state === "on";
    if (toggle) toggle.checked = on;
    if (!icon || !status) return;
    if (on) {
        icon.className = "mdi mdi-lightbulb active";
        status.innerText = lightStatusLabel(true);
        status.style.color = "#fdd835";
    } else {
        icon.className = "mdi mdi-lightbulb";
        status.innerText = lightStatusLabel(false);
        status.style.color = "#64748b";
    }
}

function setClimateAlertUi(active) {
    const grid = document.getElementById("ha-climate-grid");
    const msg = document.getElementById("ha-climate-alert-msg");
    if (grid) grid.classList.toggle("ha-climate-alert", active);
    if (msg) msg.classList.toggle("visible", active);
}

function syncHaDeviceFromWs(payload) {
    if (payload.device_id === CLIMATE_TOPOLOGY_ID) {
        setClimateAlertUi(payload.state === "alert");
        return;
    }
    const mapping = WS_DEVICE_TO_HA[payload.device_id];
    if (!mapping) return;
    const entityId = `${mapping.domain}.${mapping.objectId}`;
    if (mapping.domain === "light") {
        syncLightRowUi(entityId, payload.state);
    } else if (mapping.domain === "lock") {
        syncLockRowUi(entityId, payload.state);
    }
}

function createHaCardHeader(iconClass, iconColorClass, title) {
    const header = document.createElement("div");
    header.className = "ha-card-header";
    const icon = document.createElement("i");
    icon.className = `mdi ${iconClass} ${iconColorClass}`;
    header.appendChild(icon);
    const span = document.createElement("span");
    span.textContent = title;
    header.appendChild(span);
    return header;
}

function createLightRow(entity) {
    const { objectId } = parseEntityId(entity.entity_id);
    const domId = entityDomId(entity.entity_id);
    const on = entity.state === "on";
    const friendlyName =
        entity.attributes?.friendly_name || objectId.replace(/_/g, " ");

    const row = document.createElement("div");
    row.className = "ha-device-row";
    row.dataset.entityId = entity.entity_id;

    const info = document.createElement("div");
    info.className = "ha-device-info";

    const icon = document.createElement("i");
    icon.className = "mdi mdi-lightbulb";
    icon.id = `icon-${domId}`;
    if (on) icon.classList.add("active");

    const textWrap = document.createElement("div");
    const nameEl = document.createElement("div");
    nameEl.className = "device-name";
    nameEl.textContent = friendlyName;
    const statusEl = document.createElement("div");
    statusEl.className = "device-status";
    statusEl.id = `status-${domId}`;
    statusEl.innerText = lightStatusLabel(on);
    statusEl.style.color = on ? "#fdd835" : "#64748b";
    textWrap.appendChild(nameEl);
    textWrap.appendChild(statusEl);

    info.appendChild(icon);
    info.appendChild(textWrap);

    const label = document.createElement("label");
    label.className = "switch";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = `toggle-${domId}`;
    input.dataset.entityId = entity.entity_id;
    input.dataset.roomId = objectId;
    input.checked = on;
    const slider = document.createElement("span");
    slider.className = "slider round";
    label.appendChild(input);
    label.appendChild(slider);

    row.appendChild(info);
    row.appendChild(label);
    return row;
}

function createLockRow(entity) {
    const { objectId } = parseEntityId(entity.entity_id);
    const ids = lockRowDomIds(entity.entity_id);
    const friendlyName =
        entity.attributes?.friendly_name || objectId.replace(/_/g, " ");

    const row = document.createElement("div");
    row.className = "ha-device-row";
    row.dataset.entityId = entity.entity_id;

    const info = document.createElement("div");
    info.className = "ha-device-info";

    const icon = document.createElement("i");
    icon.id = ids.leftIconId;

    const textWrap = document.createElement("div");
    const nameEl = document.createElement("div");
    nameEl.className = "device-name";
    nameEl.textContent = friendlyName;
    const statusEl = document.createElement("div");
    statusEl.className = "device-status";
    statusEl.id = ids.statusTextId;
    textWrap.appendChild(nameEl);
    textWrap.appendChild(statusEl);

    info.appendChild(icon);
    info.appendChild(textWrap);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-lock-unlock";
    btn.id = ids.btnId;
    btn.dataset.doorId = objectId;
    btn.dataset.entityId = entity.entity_id;
    const btnIcon = document.createElement("i");
    btnIcon.id = ids.actionIconId;
    btn.appendChild(btnIcon);

    row.appendChild(info);
    row.appendChild(btn);

    paintLockRowUi({
        row,
        icon,
        statusEl,
        btn,
        btnIcon,
        haState: entity.state,
    });

    return row;
}

function appendClimateCard(container) {
    const card = document.createElement("div");
    card.className = "ha-card";
    card.id = "ha-climate-card";
    card.appendChild(
        createHaCardHeader("mdi-thermometer", "ha-icon-green", "Климат")
    );

    const grid = document.createElement("div");
    grid.className = "ha-sensor-grid";
    grid.id = "ha-climate-grid";

    for (const [val, lbl] of [
        ["22.5 °C", "Температура"],
        ["48 %", "Влажность"],
    ]) {
        const item = document.createElement("div");
        item.className = "ha-sensor-item";
        const valEl = document.createElement("span");
        valEl.className = "sensor-val";
        valEl.textContent = val;
        const lblEl = document.createElement("span");
        lblEl.className = "sensor-lbl";
        lblEl.textContent = lbl;
        item.appendChild(valEl);
        item.appendChild(lblEl);
        grid.appendChild(item);
    }

    const alertMsg = document.createElement("div");
    alertMsg.className = "ha-climate-alert-msg";
    alertMsg.id = "ha-climate-alert-msg";
    alertMsg.textContent = "Тревога: аномалия климата";

    card.appendChild(grid);
    card.appendChild(alertMsg);
    container.appendChild(card);
}

function renderHomeAssistantUI(entities) {
    const root = document.getElementById("ha-dynamic-content");
    if (!root) return;

    const lights = entities
        .filter((e) => parseEntityId(e.entity_id).domain === "light")
        .sort((a, b) => a.entity_id.localeCompare(b.entity_id));
    const locks = entities
        .filter((e) => parseEntityId(e.entity_id).domain === "lock")
        .sort((a, b) => a.entity_id.localeCompare(b.entity_id));

    root.innerHTML = "";

    if (lights.length > 0) {
        const card = document.createElement("div");
        card.className = "ha-card";
        card.appendChild(
            createHaCardHeader("mdi-lightbulb-group", "ha-icon-blue", "Освещение")
        );
        for (const entity of lights) {
            card.appendChild(createLightRow(entity));
        }
        root.appendChild(card);
    }

    if (locks.length > 0) {
        const card = document.createElement("div");
        card.className = "ha-card";
        card.appendChild(
            createHaCardHeader("mdi-shield-home", "ha-icon-red", "Безопасность")
        );
        for (const entity of locks) {
            card.appendChild(createLockRow(entity));
        }
        root.appendChild(card);
    }

    appendClimateCard(root);
}

function bindHaPhoneActions(appendTerminalLog) {
    const root = document.getElementById("ha-dynamic-content");
    if (!root || haPhoneActionsBound) return;
    haPhoneActionsBound = true;

    root.addEventListener("change", async function (event) {
        const input = event.target.closest('input[type="checkbox"][data-room-id]');
        if (!input) return;
        const roomId = input.dataset.roomId;
        input.checked = !input.checked;
        try {
            const res = await gatewayFetch(`/api/lights/${roomId}/toggle`, {
                method: "POST",
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
        } catch (err) {
            appendTerminalLog({
                level: "ALERT",
                message: `Lamp toggle failed: ${err.message}`,
            });
        }
    });

    root.addEventListener("click", async function (event) {
        const btn = event.target.closest(".btn-lock-unlock");
        if (!btn) return;
        const doorId = btn.dataset.doorId;
        const row = btn.closest(".ha-device-row");
        const lockState = row?.dataset.lockState || "locked";
        const action = lockIsUnlocked(lockState) ? "lock" : "unlock";
        try {
            const res = await gatewayFetch(`/api/locks/${doorId}/${action}`, {
                method: "POST",
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            if (action === "unlock") {
                appendTerminalLog({
                    level: "INFO",
                    message: "Lock unlock sent (knock step 2)",
                });
            }
        } catch (err) {
            appendTerminalLog({
                level: "ALERT",
                message: `Lock ${action} failed: ${err.message}`,
            });
        }
    });
}

async function refreshHaPhone(appendTerminalLog) {
    try {
        const res = await gatewayFetch("/api/states");
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const entities = await res.json();
        renderHomeAssistantUI(entities);
    } catch (err) {
        if (appendTerminalLog) {
            appendTerminalLog({
                level: "ALERT",
                message: `Failed to refresh HA app: ${err.message}`,
            });
        }
        console.error(err);
    }
}

async function initHaPhone(appendTerminalLog) {
    bindHaPhoneActions(appendTerminalLog);
    try {
        const res = await gatewayFetch("/api/states");
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const entities = await res.json();
        renderHomeAssistantUI(entities);
        appendTerminalLog({
            level: "INFO",
            message: "Home Assistant mock loaded from /api/states",
        });
    } catch (err) {
        appendTerminalLog({
            level: "ALERT",
            message: `Failed to load HA app: ${err.message}`,
        });
        console.error(err);
    }
}

let haPhoneBootstrapped = false;

function showHaDashboardAfterLogin() {
    const login = document.getElementById("ha-login");
    const screen = document.getElementById("ha-screen");
    if (login) login.classList.add("ha-login--hidden");
    if (screen) screen.classList.remove("ha-screen--hidden");
}

function setupHaLogin(appendTerminalLog) {
    const container = document.getElementById("ha-login-form");
    const errorEl = document.getElementById("ha-login-error");
    const submitBtn = document.getElementById("ha-login-submit");
    const passwordEl = document.getElementById("ha-login-password");
    if (!container || !submitBtn) return;

    async function submitHaLogin() {
        const usernameEl = document.getElementById("ha-login-username");
        const username = usernameEl ? usernameEl.value.trim() : "";
        const password = passwordEl ? passwordEl.value : "";

        if (errorEl) errorEl.hidden = true;
        submitBtn.disabled = true;

        try {
            const res = await gatewayFetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            if (!res.ok) {
                if (errorEl) errorEl.hidden = false;
                return;
            }
            showHaDashboardAfterLogin();
            if (!haPhoneBootstrapped) {
                haPhoneBootstrapped = true;
                await initHaPhone(appendTerminalLog);
            } else {
                await refreshHaPhone(appendTerminalLog);
            }
        } catch (err) {
            if (errorEl) errorEl.hidden = false;
            appendTerminalLog({
                level: "ALERT",
                message: `HA login request failed: ${err.message}`,
            });
        } finally {
            submitBtn.disabled = false;
        }
    }

    submitBtn.addEventListener("click", function () {
        submitHaLogin();
    });

    if (passwordEl) {
        passwordEl.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                submitHaLogin();
            }
        });
    }
}

function isHaDashboardVisible() {
    const screen = document.getElementById("ha-screen");
    return screen && !screen.classList.contains("ha-screen--hidden");
}

async function refreshHaPhoneIfVisible(appendTerminalLog) {
    if (!haPhoneBootstrapped || !isHaDashboardVisible()) return;
    await refreshHaPhone(appendTerminalLog);
}

function isCurrentClientInBlacklist(blacklist) {
    if (!Array.isArray(blacklist) || blacklist.length === 0) return false;
    const cid = getOrCreateGatewayClientId();
    const short = cid.length > 8 ? cid.slice(0, 8) : cid;
    return blacklist.some((label) => label.includes(short));
}

function getOrCreateGatewayClientId() {
    let id = localStorage.getItem(GATEWAY_CLIENT_STORAGE_KEY);
    if (!id) {
        id = generateClientUuid();
        localStorage.setItem(GATEWAY_CLIENT_STORAGE_KEY, id);
    }
    return id;
}

function gatewayHeaders(extraHeaders = {}) {
    return {
        "X-Gateway-Client-Id": getOrCreateGatewayClientId(),
        ...extraHeaders,
    };
}

function gatewayFetch(url, options = {}) {
    const headers = gatewayHeaders(options.headers || {});
    return fetch(url, { ...options, headers });
}

const RED_TEAM_CLIENT_STORAGE_KEY = "red_team_client_id";
let kaliBusy = false;

const RED_TEAM_COMMANDS = {
    recon: "ffuf -w common_api.txt -u http://192.168.1.10/FUZZ",
    exploit:
        "python3 exploit_rce.py --target http://192.168.1.10/api/system/plugin_update",
};

const FFUF_RECON_DELAY_MS = 220;

const FFUF_FAKE_LINES = [
    { text: "[404] /api/v1/users", className: "kali-output-line--dim" },
    { text: "[404] /api/hassio/app", className: "kali-output-line--dim" },
    { text: "[403] /api/config", className: "kali-output-line--dim" },
    { text: "[404] /api/services", className: "kali-output-line--dim" },
    { text: "[404] /api/events", className: "kali-output-line--dim" },
    { text: "[404] /api/logbook", className: "kali-output-line--dim" },
    { text: "[404] /api/history/period", className: "kali-output-line--dim" },
    { text: "[403] /api/assist", className: "kali-output-line--dim" },
    { text: "[404] /api/stream", className: "kali-output-line--dim" },
    { text: "[404] /api/template", className: "kali-output-line--dim" },
    { text: "[403] /server-status", className: "kali-output-line--dim" },
    { text: "[404] /api/config/core", className: "kali-output-line--dim" },
    { text: "[403] /api/tags", className: "kali-output-line--dim" },
    { text: "[500] /device.xml", className: "kali-output-line--dim" },
    {
        text: "[404] /api/debug",
        className: "kali-output-line--dim",
        honeypot: "/api/debug",
    },
    { text: "[404] /.well-known/security.txt", className: "kali-output-line--dim" },
    { text: "[404] /auth/token", className: "kali-output-line--dim" },
    {
        text: "[404] /wp-admin",
        className: "kali-output-line--dim",
        honeypot: "/wp-admin",
    },
    { text: "[404] /api/websocket", className: "kali-output-line--dim" },
    { text: "[401] /api/auth/login", className: "kali-output-line--dim" },
    {
        text: "[200] /api/system/plugin_update",
        className: "kali-output-line--success",
    },
];

const PLUGIN_UPDATE_TOKEN = "admin_bypass_token_991";

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function getOrCreateRedTeamClientId() {
    let id = localStorage.getItem(RED_TEAM_CLIENT_STORAGE_KEY);
    if (!id) {
        id = generateClientUuid();
        localStorage.setItem(RED_TEAM_CLIENT_STORAGE_KEY, id);
    }
    return id;
}

function redTeamHeaders(extraHeaders = {}) {
    return {
        "X-Gateway-Client-Id": getOrCreateRedTeamClientId(),
        ...extraHeaders,
    };
}

function redTeamFetch(url, options = {}) {
    const headers = redTeamHeaders(options.headers || {});
    return fetch(url, { ...options, headers });
}

function appendKaliLine(text, className = "") {
    const out = document.getElementById("kali-output");
    if (!out) return;
    const line = document.createElement("div");
    line.className = className
        ? `kali-output-line ${className}`
        : "kali-output-line";
    line.textContent = text;
    out.appendChild(line);
    scrollKaliToBottom();
}

function scrollKaliToBottom() {
    const scroll = document.getElementById("kali-scroll");
    if (scroll) scroll.scrollTop = scroll.scrollHeight;
}

function setKaliPromptVisible(visible) {
    const line = document.querySelector(".kali-input-line");
    if (line) line.classList.toggle("kali-input-line--hidden", !visible);
}

async function typeKaliCommand(text) {
    const typed = document.getElementById("kali-typed");
    if (!typed) return;
    typed.textContent = "";
    for (const ch of text) {
        typed.textContent += ch;
        scrollKaliToBottom();
        await sleep(18 + Math.floor(Math.random() * 8));
    }
}

function commitKaliInputLine() {
    const typed = document.getElementById("kali-typed");
    const cmd = typed ? typed.textContent : "";
    appendKaliLine(`root@kali:~# ${cmd}`);
    if (typed) typed.textContent = "";
}

function setHackerScenarioButtonsDisabled(disabled) {
    document
        .querySelectorAll(".hacker-btn[data-action]")
        .forEach((btn) => {
            btn.disabled = disabled;
        });
}

async function runFfufReconLines() {
    for (const entry of FFUF_FAKE_LINES) {
        await sleep(FFUF_RECON_DELAY_MS);
        appendKaliLine(entry.text, entry.className);
        if (entry.honeypot) {
            await redTeamFetch(entry.honeypot);
        }
    }
}

async function runExploitPayload() {
    appendKaliLine("[*] Sending payload...", "kali-output-line--warn");
    await sleep(400);
    appendKaliLine("[*] Exploiting vulnerability...", "kali-output-line--warn");
    const res = await redTeamFetch("/api/system/plugin_update", {
        method: "POST",
    });
    let token = PLUGIN_UPDATE_TOKEN;
    if (res.ok) {
        try {
            const body = await res.json();
            if (body.token) token = body.token;
        } catch (_) {
            /* use default token label */
        }
    }
    appendKaliLine(
        `[*] Success! Acquired token: ${token}`,
        "kali-output-line--success"
    );
    appendKaliLine(`[*] HTTP Status: ${res.status}`, "kali-output-line--dim");
}

async function simulateHackerAction(actionType) {
    if (kaliBusy) return;
    const commandText = RED_TEAM_COMMANDS[actionType];
    if (!commandText) return;

    kaliBusy = true;
    setHackerScenarioButtonsDisabled(true);
    setKaliPromptVisible(true);
    try {
        await typeKaliCommand(commandText);
        commitKaliInputLine();
        setKaliPromptVisible(false);

        if (actionType === "recon") {
            appendKaliLine(
                ":: Progress: [################] 100%",
                "kali-output-line--dim"
            );
            await runFfufReconLines();
        } else if (actionType === "exploit") {
            await runExploitPayload();
        }
    } catch (err) {
        appendKaliLine(`[!] Error: ${err.message}`, "kali-output-line--hit");
    } finally {
        kaliBusy = false;
        setHackerScenarioButtonsDisabled(false);
        setKaliPromptVisible(true);
        scrollKaliToBottom();
    }
}

const HUE_FINGERPRINT_META = {
    living: {
        model_id: "LCT015",
        product: "Hue color ambiance E26/E27",
        zigbee_addr: "0x00178801083d5c2a",
    },
    kitchen: {
        model_id: "LWB014",
        product: "Hue white ambiance BR30",
        zigbee_addr: "0x0017880106a0e3de",
    },
};

function appendLightFingerprintBody(device) {
    const meta = HUE_FINGERPRINT_META[device.room] || {
        model_id: "LCT010",
        product: "Hue white and color ambiance",
        zigbee_addr: "0x0017880100000000",
    };
    const manufacturer =
        device.vendor === "Signify" || device.vendor === "Philips Hue"
            ? "Signify Netherlands B.V."
            : device.vendor;
    const lines = [
        `    entity_id: light.${device.room}`,
        `    state: ${device.status}  brightness: ${device.brightness}`,
        `    manufacturer: ${manufacturer}`,
        `    model_id: ${meta.model_id}`,
        `    product_name: ${meta.product}`,
        `    sw_version: ${device.firmware}`,
        `    protocol: zigbee`,
        `    ieee_address: ${meta.zigbee_addr}`,
        `    reachable: true`,
    ];
    for (const line of lines) {
        appendKaliLine(line, "kali-output-line--dim");
    }
}

async function redTeamProbeLightFingerprint(path, label) {
    appendKaliLine(
        `[*] curl -s ${window.location.origin}${path}`,
        "kali-output-line--dim"
    );
    const res = await redTeamFetch(path);
    appendKaliLine(`[*] HTTP ${res.status} — ${label}`, "kali-output-line--dim");
    if (!res.ok) {
        appendKaliLine("    (no body / access denied)", "kali-output-line--hit");
        return;
    }
    const device = await res.json();
    appendLightFingerprintBody(device);
}

async function redTeamDeviceFingerprint() {
    appendKaliLine(
        "[*] iot_fingerprint.py --vendor-probe hue,zigbee",
        "kali-output-line--warn"
    );
    appendKaliLine(
        "[*] Enumerating REST device descriptors (Home Assistant proxy)...",
        "kali-output-line--dim"
    );
    await redTeamProbeLightFingerprint("/api/lights/living", "Philips Hue — Living");
    await sleep(350);
    await redTeamProbeLightFingerprint("/api/lights/kitchen", "Philips Hue — Kitchen");
    appendKaliLine("[*] Fingerprint complete.", "kali-output-line--success");
}

async function redTeamIotCommand(iotAction) {
    if (kaliBusy) return;
    try {
        if (iotAction === "light") {
            appendKaliLine(
                "[*] iot_chaos.py --cmd toggle_light living",
                "kali-output-line--warn"
            );
            const res = await redTeamFetch("/api/lights/living/toggle", {
                method: "POST",
            });
            appendKaliLine(
                `[*] Injecting command: toggle_light... HTTP ${res.status}`,
                res.ok ? "kali-output-line--success" : "kali-output-line--hit"
            );
        } else if (iotAction === "unlock") {
            appendKaliLine(
                "[*] iot_chaos.py --cmd unlock_door main_door",
                "kali-output-line--warn"
            );
            const res = await redTeamFetch("/api/locks/main_door/unlock", {
                method: "POST",
            });
            appendKaliLine(
                `[*] Injecting command: unlock_door... HTTP ${res.status}`,
                res.ok ? "kali-output-line--success" : "kali-output-line--hit"
            );
        } else if (iotAction === "lock") {
            appendKaliLine(
                "[*] iot_chaos.py --cmd lock_door main_door",
                "kali-output-line--warn"
            );
            const res = await redTeamFetch("/api/locks/main_door/lock", {
                method: "POST",
            });
            appendKaliLine(
                `[*] Injecting command: lock_door... HTTP ${res.status}`,
                res.ok ? "kali-output-line--success" : "kali-output-line--hit"
            );
        } else if (iotAction === "fingerprint") {
            await redTeamDeviceFingerprint();
        }
    } catch (err) {
        appendKaliLine(`[!] IoT inject failed: ${err.message}`, "kali-output-line--hit");
    }
    scrollKaliToBottom();
}

function setupRedTeamPanel() {
    document.querySelectorAll(".hacker-btn[data-action]").forEach((btn) => {
        btn.addEventListener("click", function () {
            simulateHackerAction(btn.dataset.action);
        });
    });
    document.querySelectorAll(".hacker-btn[data-iot]").forEach((btn) => {
        btn.addEventListener("click", function () {
            redTeamIotCommand(btn.dataset.iot);
        });
    });
}

const BASE_NODE_BG = "#131a30";
const BORDER_REAL = "#3b82f6";
const BORDER_SHADOW = "#a855f7";
const BORDER_CANARY = "#ea580c";

/** Per-edge physics/style: `length` = spring length for this link only (vis-network). */
const GATEWAY_HUB_EDGES = {
    real: {
        length: 400,
        width: 5,
        color: { color: "#00ffcc" },
    },
    shadow: {
        length: 400,
        width: 3,
        dash: true,
        color: { color: "#ff3366" },
    },
};

const DEFAULT_EDGE_LENGTH = 120;

function deviceLabel(device) {
    const typeRu = device.type_label || device.device_type || "";
    return `${device.name}\n(${typeRu})`;
}

function nodeColorForState(deviceType, state, plane, isCanary = false) {
    const border = isCanary ? BORDER_CANARY : plane === "shadow" ? BORDER_SHADOW : BORDER_REAL;
    let background = BASE_NODE_BG;

    if (deviceType === "light" && state === "on") {
        background = "#fdd835";
    } else if (deviceType === "lock" && state === "unlocked") {
        background = "#fbbf24";
    } else if (deviceType === "sensor" && state === "alert") {
        background = "#ff3366";
    }

    return { background, border };
}

function buildGraphFromTopology(topo) {
    const nodes = [];
    const edges = [];
    const deviceMetaMap = new Map();

    function addDeviceNode(dev, plane) {
        const isCanary = dev.role === "canary";
        const group = isCanary ? "canary_dev" : `${dev.device_type}_${plane}`;
        deviceMetaMap.set(dev.id, {
            device_type: dev.device_type,
            plane,
            isCanary,
        });
        nodes.push({
            id: dev.id,
            label: deviceLabel(dev),
            group,
            color: nodeColorForState(dev.device_type, dev.state, plane, isCanary),
        });
    }

    const gw = topo.gateway;
    nodes.push({
        id: gw.id,
        label: gw.label,
        group: "gw",
        shape: "box",
        font: { color: "#fff", face: "monospace" },
    });

    for (const det of topo.detectors) {
        nodes.push({
            id: det.id,
            label: det.name,
            group: "detector",
        });
        edges.push({
            from: gw.id,
            to: det.id,
            length: DEFAULT_EDGE_LENGTH,
            color: { color: "#fbbf24" },
            width: 1,
        });
    }

    const realHub = topo.real.hub;
    nodes.push({
        id: realHub.id,
        label: `${realHub.name}\n${realHub.ip}`,
        group: "hub",
    });
    edges.push({
        from: gw.id,
        to: realHub.id,
        ...GATEWAY_HUB_EDGES.real,
    });

    for (const dev of topo.real.devices) {
        addDeviceNode(dev, "real");
        edges.push({
            from: realHub.id,
            to: dev.id,
            length: DEFAULT_EDGE_LENGTH,
            color: "#00ffcc",
        });
    }

    const shadowHub = topo.shadow.hub;
    nodes.push({
        id: shadowHub.id,
        label: `${shadowHub.name}\n${shadowHub.ip}`,
        group: "hub",
    });
    edges.push({
        from: gw.id,
        to: shadowHub.id,
        ...GATEWAY_HUB_EDGES.shadow,
    });

    for (const dev of topo.shadow.devices) {
        addDeviceNode(dev, "shadow");
        const isCanary = dev.role === "canary";
        edges.push({
            from: shadowHub.id,
            to: dev.id,
            length: DEFAULT_EDGE_LENGTH,
            color: isCanary ? "#ea580c" : "#ff3366",
            width: isCanary ? 2 : 1,
        });
    }

    return { nodes, edges, deviceMetaMap };
}

const graphOptions = {
    physics: {
        enabled: true,
        barnesHut: { gravitationalConstant: -10000, centralGravity: 0.3, springLength: DEFAULT_EDGE_LENGTH },
        solver: "barnesHut",
    },
    nodes: {
        shape: "dot",
        size: 15,
        font: { size: 12, color: "#94a3b8" },
        borderWidth: 2,
    },
    groups: {
        gw: { shape: "hexagon", color: { background: "#1e293b", border: "#00ffcc" }, size: 25 },
        hub: { shape: "database", color: { background: "#334155", border: "#94a3b8" }, size: 20 },
        detector: { shape: "diamond", color: { background: "#78350f", border: "#fbbf24" }, size: 18 },
        light_real: { shape: "dot", color: { background: BASE_NODE_BG, border: BORDER_REAL } },
        lock_real: { shape: "box", color: { background: BASE_NODE_BG, border: BORDER_REAL } },
        sensor_real: { shape: "triangle", color: { background: BASE_NODE_BG, border: BORDER_REAL } },
        light_shadow: { shape: "dot", color: { background: BASE_NODE_BG, border: BORDER_SHADOW } },
        lock_shadow: { shape: "box", color: { background: BASE_NODE_BG, border: BORDER_SHADOW } },
        sensor_shadow: { shape: "triangle", color: { background: BASE_NODE_BG, border: BORDER_SHADOW } },
        canary_dev: { color: { background: "#7c2d12", border: BORDER_CANARY }, shape: "star" },
    },
    edges: { smooth: { type: "continuous" } },
};

const DETECTOR_DEFAULT_SIZE = 18;
const DETECTOR_DEFAULT_COLOR = {
    background: "#78350f",
    border: "#fbbf24",
};
const ATTACK_PULSE_COLOR = { background: "#ff3366", border: "#ff3366" };
const ATTACK_PULSE_MS = 200;
const ATTACK_PULSE_COUNT = 10;
const GATEWAY_NODE_ID = "gateway";
const REAUTH_PULSE_COLOR = { background: "#00ffcc", border: "#00ffcc" };
const REAUTH_PULSE_MS = 250;
const REAUTH_PULSE_COUNT = 2;
const GATEWAY_DEFAULT_SIZE = 25;

function pulseGatewayNode(nodesDataSet) {
    if (!nodesDataSet) return;
    const node = nodesDataSet.get(GATEWAY_NODE_ID);
    if (!node) {
        console.warn("pulseGatewayNode: gateway node not found");
        return;
    }
    const baseSize = node.size ?? GATEWAY_DEFAULT_SIZE;
    const baseColor = node.color
        ? { background: node.color.background, border: node.color.border }
        : { background: "#1e293b", border: "#00ffcc" };

    function runPulse(index) {
        if (index >= REAUTH_PULSE_COUNT) return;
        nodesDataSet.update({
            id: GATEWAY_NODE_ID,
            size: baseSize * 1.5,
            color: { ...REAUTH_PULSE_COLOR },
        });
        setTimeout(() => {
            nodesDataSet.update({
                id: GATEWAY_NODE_ID,
                size: baseSize,
                color: { ...baseColor },
            });
            setTimeout(() => runPulse(index + 1), REAUTH_PULSE_MS);
        }, REAUTH_PULSE_MS);
    }
    runPulse(0);
}

function pulseNode(nodeId, nodesDataSet) {
    if (!nodesDataSet || !nodeId) return;
    const node = nodesDataSet.get(nodeId);
    if (!node) {
        console.warn("pulseNode: unknown node", nodeId);
        return;
    }
    const baseSize = node.size ?? DETECTOR_DEFAULT_SIZE;
    const baseColor = node.color
        ? { background: node.color.background, border: node.color.border }
        : { ...DETECTOR_DEFAULT_COLOR };

    function runPulse(index) {
        if (index >= ATTACK_PULSE_COUNT) return;
        nodesDataSet.update({
            id: nodeId,
            size: baseSize * 1.5,
            color: { ...ATTACK_PULSE_COLOR },
        });
        setTimeout(() => {
            nodesDataSet.update({
                id: nodeId,
                size: baseSize,
                color: { ...baseColor },
            });
            setTimeout(() => runPulse(index + 1), ATTACK_PULSE_MS);
        }, ATTACK_PULSE_MS);
    }
    runPulse(0);
}

function applyDeviceState(payload, nodesDataSet, deviceMetaMap) {
    if (!nodesDataSet || !payload.device_id) return;
    const meta = deviceMetaMap.get(payload.device_id) || {};
    const deviceType = payload.device_type || meta.device_type || "light";
    const plane =
        meta.plane ||
        (payload.device_id.startsWith("shadow_") || payload.device_id.includes("canary")
            ? "shadow"
            : "real");
    const color = nodeColorForState(
        deviceType,
        payload.state,
        plane,
        meta.isCanary || payload.device_id.includes("canary")
    );
    nodesDataSet.update({ id: payload.device_id, color });
    syncHaDeviceFromWs(payload);
}

function getDashboardWsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const clientId = encodeURIComponent(getOrCreateGatewayClientId());
    return `${proto}//${window.location.host}/ws/dashboard?client_id=${clientId}`;
}

function levelToCssClass(level) {
    const normalized = (level || "INFO").toUpperCase();
    if (normalized === "WARNING") return "log-line--warning";
    if (normalized === "ALERT") return "log-line--alert";
    return "log-line--info";
}

function formatLogTime(timestamp) {
    if (!timestamp) return "";
    const d = new Date(timestamp);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function renderIpState({ whitelist = [], blacklist = [], highlightClient = null } = {}) {
    const realList = document.getElementById("real-ip-list");
    const shadowList = document.getElementById("shadow-ip-list");
    const banCount = document.getElementById("ban-count");

    realList.innerHTML = "";
    if (whitelist.length === 0) {
        const empty = document.createElement("li");
        empty.className = "text-muted";
        empty.textContent = "Пусто";
        realList.appendChild(empty);
    } else {
        for (const entry of whitelist) {
            const li = document.createElement("li");
            if (highlightClient && entry === highlightClient) {
                li.classList.add("highlight-unlock");
                li.addEventListener(
                    "animationend",
                    () => li.classList.remove("highlight-unlock"),
                    { once: true }
                );
            }
            li.appendChild(document.createTextNode(`${entry} `));
            const badge = document.createElement("span");
            badge.className = "badge badge-user";
            badge.textContent = "User";
            li.appendChild(badge);
            realList.appendChild(li);
        }
    }

    shadowList.innerHTML = "";
    if (blacklist.length === 0) {
        const empty = document.createElement("li");
        empty.className = "text-muted";
        empty.textContent = "Пусто";
        shadowList.appendChild(empty);
    } else {
        for (const entry of blacklist) {
            const li = document.createElement("li");
            li.appendChild(document.createTextNode(`${entry} `));
            const badge = document.createElement("span");
            badge.className = "badge badge-banned";
            badge.textContent = "BANNED";
            li.appendChild(badge);
            shadowList.appendChild(li);
        }
    }

    if (banCount) {
        banCount.textContent = `${blacklist.length} client(s)`;
    }
}

function connectDashboardWebSocket(
    appendTerminalLog,
    renderIpStateFn,
    onDeviceState,
    onAttackAlert,
    onReauthSuccess
) {
    let reconnectDelayMs = 1000;
    const maxReconnectDelayMs = 30000;
    let socket = null;
    let reconnectTimer = null;

    function scheduleReconnect() {
        if (reconnectTimer) return;
        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            openSocket();
            reconnectDelayMs = Math.min(reconnectDelayMs * 2, maxReconnectDelayMs);
        }, reconnectDelayMs);
    }

    function openSocket() {
        socket = new WebSocket(getDashboardWsUrl());

        socket.onopen = function () {
            reconnectDelayMs = 1000;
            appendTerminalLog({
                level: "INFO",
                message: "Live log stream connected",
            });
        };

        socket.onmessage = function (event) {
            try {
                const payload = JSON.parse(event.data);
                if (payload.type === "log") {
                    appendTerminalLog(payload);
                } else if (payload.type === "ip_state") {
                    renderIpStateFn(payload);
                } else if (payload.type === "device_state") {
                    onDeviceState(payload);
                } else if (payload.type === "attack_alert") {
                    if (onAttackAlert) onAttackAlert(payload);
                } else if (payload.type === "knock_progress") {
                    setKnockProgress(payload.step);
                } else if (payload.type === "knock_reset") {
                    resetKnockUi();
                } else if (payload.type === "reauth_success") {
                    if (onReauthSuccess) onReauthSuccess(payload);
                }
            } catch (e) {
                console.warn("Invalid WS message", e);
            }
        };

        socket.onerror = function () {
            socket.close();
        };

        socket.onclose = function () {
            scheduleReconnect();
        };
    }

    openSocket();
}

const KNOCK_MSG_IDLE = "Ожидание последовательности...";
let knockUiResetTimer = null;

function setKnockProgress(step) {
    const n = Number(step);
    if (!n || n < 1) return;
    for (let i = 1; i <= 3; i++) {
        const slot = document.getElementById(`slot-${i}`);
        if (!slot) continue;
        if (i <= n) slot.classList.add("active");
        else slot.classList.remove("active");
    }
    const msg = document.getElementById("reauth-msg");
    if (msg) {
        msg.textContent = `Паттерн: шаг ${n}/3...`;
        msg.classList.remove("text-muted");
        msg.style.color = "#94a3b8";
    }
}

function resetKnockUi() {
    if (knockUiResetTimer) {
        clearTimeout(knockUiResetTimer);
        knockUiResetTimer = null;
    }
    for (let i = 1; i <= 3; i++) {
        const slot = document.getElementById(`slot-${i}`);
        if (slot) slot.classList.remove("active");
    }
    const msg = document.getElementById("reauth-msg");
    if (msg) {
        msg.textContent = KNOCK_MSG_IDLE;
        msg.classList.add("text-muted");
        msg.style.color = "";
    }
}

function showKnockSuccess() {
    for (let i = 1; i <= 3; i++) {
        const slot = document.getElementById(`slot-${i}`);
        if (!slot) continue;
        if (i === 3) slot.classList.add("active");
        else slot.classList.remove("active");
    }
    const msg = document.getElementById("reauth-msg");
    if (msg) {
        msg.textContent = "УСПЕХ!";
        msg.classList.remove("text-muted");
        msg.style.color = "#00ffcc";
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById("network-graph");
    const terminal = document.getElementById("terminal-log");

    const graphCtx = {
        nodesDataSet: null,
        deviceMetaMap: new Map(),
    };

    function appendTerminalLog({ level = "INFO", message, timestamp, cssClass } = {}) {
        const line = document.createElement("div");
        const cssLevel = cssClass || levelToCssClass(level);
        line.className = `log-line ${cssLevel}`;
        const timePrefix = formatLogTime(timestamp);
        const levelTag = (level || "INFO").toUpperCase();
        line.innerText = timePrefix
            ? `[${timePrefix}] [${levelTag}] ${message}`
            : `[${levelTag}] ${message}`;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    }

    async function initTopology() {
        try {
            const res = await gatewayFetch("/api/network-topology");
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const topo = await res.json();
            const { nodes, edges, deviceMetaMap } = buildGraphFromTopology(topo);
            graphCtx.deviceMetaMap = deviceMetaMap;
            graphCtx.nodesDataSet = new vis.DataSet(nodes);
            const edgesDataSet = new vis.DataSet(edges);
            const network = new vis.Network(
                container,
                { nodes: graphCtx.nodesDataSet, edges: edgesDataSet },
                graphOptions
            );
            appendTerminalLog({
                level: "INFO",
                message: "Network topology loaded from /api/network-topology",
            });
            return network;
        } catch (err) {
            appendTerminalLog({
                level: "ALERT",
                message: `Failed to load topology: ${err.message}`,
            });
            console.error(err);
            return null;
        }
    }

    let pendingHighlightClient = null;

    connectDashboardWebSocket(
        appendTerminalLog,
        (payload) => {
            renderIpState({
                ...payload,
                highlightClient: pendingHighlightClient,
            });
            pendingHighlightClient = null;
            if (isCurrentClientInBlacklist(payload.blacklist)) {
                refreshHaPhoneIfVisible(appendTerminalLog);
            }
        },
        (payload) => {
            applyDeviceState(payload, graphCtx.nodesDataSet, graphCtx.deviceMetaMap);
        },
        (payload) => {
            appendTerminalLog({
                level: "ALERT",
                message: payload.message,
                timestamp: payload.timestamp,
            });
            pulseNode(payload.detector, graphCtx.nodesDataSet);
            refreshHaPhoneIfVisible(appendTerminalLog);
        },
        (payload) => {
            pendingHighlightClient = payload.client || null;
            pulseGatewayNode(graphCtx.nodesDataSet);
            appendTerminalLog({
                level: "INFO",
                message:
                    ">>> RE-AUTH SUCCESS: FINGERPRINT VERIFIED. RESTORING ACCESS <<<",
                cssClass: "log-line--reauth",
            });
            showKnockSuccess();
            refreshHaPhoneIfVisible(appendTerminalLog);
            knockUiResetTimer = setTimeout(() => resetKnockUi(), 2500);
        }
    );
    initTopology();
    setupHaLogin(appendTerminalLog);
    setupRedTeamPanel();
});
