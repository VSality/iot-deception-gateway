# IoT Deception Gateway

Backend for an IoT cybersecurity gateway: one HTTP API, two data planes — **real devices** (`REAL_DEVICES`) and a **Shadow Digital Twin** for blacklisted attackers. Legitimate users (official smart-home app) can **exit the sandbox** via **In-Band IoT Port Knocking**.

## Project layout

```
frontend/
  templates/index.html    # Deception dashboard (served via FileResponse at GET /)
  static/css/style.css
  static/js/app.js
server/
  main.py                 # FastAPI app, static mount, dashboard, api router, honeypot catch-all
  decision_logic/         # client ban/whitelist (IP + X-Gateway-Client-Id), port_knock_config
  detection_module/       # Traffic analyzer + detectors
  shadow_world/           # REAL_DEVICES + ShadowWorld (canary light in shadow only)
  api/                    # lights, locks, GET /api/states (Home Assistant-style)
  error_masking.py        # Masked HTTP/validation errors (IoT JSON vs nginx HTML)
  schemas/                # JSON builders + ha_states
  requirements.txt
```

## Setup

From the project root or `server/`:

```bash
pip install -r server/requirements.txt
```

## Run

```bash
cd server
python main.py
```

Server listens on `http://0.0.0.0:8000`.

**Dashboard (browser):** open `http://127.0.0.1:8000/` — static assets at `/static/...` (no Jinja2). The lamp toggle on the phone mock is local UI for now; API integration uses room id `living` (see `PORT_KNOCK_ROOM_ID`).

## Manual verification

1. Install deps and start the server (see above).
2. **Dashboard:** `http://127.0.0.1:8000/` loads HTML; DevTools Network shows `200` for `/static/css/style.css` and `/static/js/app.js`.
3. **Legal user:** `GET http://127.0.0.1:8000/api/lights/living` → `source: REAL_API`, `firmware: v2.1`.
   - `GET http://127.0.0.1:8000/api/states` → JSON array of **3** entities (`light.living`, `light.kitchen`, `lock.main_door`), HA shape: `entity_id`, `state`, `attributes`. No `light.hall_dimmer_aux`.
4. **Detection:** `curl http://127.0.0.1:8000/.env` → that **client** (no `X-Gateway-Client-Id`) is banned; the dashboard browser (UUID in `localStorage`) on the same IP stays separate.
5. **Shadow twin:** `GET /api/lights/living` as banned client → `SHADOW_TWIN`, legacy-style firmware (e.g. `1.49.195007`), jitter.
   - `GET /api/states` → **4** entities (includes `light.hall_dimmer_aux` canary), ~0.15–0.35 s delay. Console: `[API] Client requested global states. Defending: True.`
6. **Canary (optional passive check):** `hall_dimmer_aux` exists only in shadow — `GET /api/lights/hall_dimmer_aux` → 404 when clean, 200 when sandboxed.
7. **Port knocking (FSM exit, 15 s window):** while sandboxed, run sequence **living ON → `main_door` unlock → living OFF** with the same fingerprint (`X-Gateway-Client-Id`). Dashboard phone mock: toggle **Гостиная Бра**, tap lock icon, toggle bra off.

```bash
CID=11111111-1111-1111-1111-111111111111
H="X-Gateway-Client-Id: $CID"
# If living was ON, toggle once to OFF before starting.
curl -H "$H" -X POST http://127.0.0.1:8000/api/lights/living/toggle   # ON
curl -H "$H" -X POST http://127.0.0.1:8000/api/locks/main_door/unlock
curl -H "$H" -X POST http://127.0.0.1:8000/api/lights/living/toggle   # OFF
```

Server log: `[PORT KNOCKING] Sequence complete...` — WebSocket `reauth_success` + gateway pulse on dashboard.

8. **Next request:** `GET /api/lights/living` → `REAL_API`.
9. **Wrong pattern:** 3× toggle without lock does **not** whitelist. Wrong order resets the FSM.

State is in-memory (resets on restart).

## Dashboard WebSocket (`/ws/dashboard`)

Requires `uvicorn[standard]` (WebSocket support). Message types:

| `type` | Purpose |
|--------|---------|
| `log` | `{ level, message, timestamp }` |
| `ip_state` | `{ whitelist, blacklist }` — Real / Shadow client labels (`IP · client id`) |
| `device_state` | `{ device_id, state, device_type? }` — graph + phone mock |
| `attack_alert` | `{ detector, message, client_ip, timestamp }` — terminal ALERT + detector node pulse |
| `knock_progress` | `{ step: 1 \| 2 }` — port-knock step done; lights slots 1..step on dashboard |
| `knock_reset` | — sequence timeout or wrong order; clear knock slots |
| `reauth_success` | `{ client, timestamp }` — port-knock exit; gateway pulse + highlight Real list |

Detector node IDs on the graph match `detector`: `honeypot`, `ratelimit`, `bruteforce`, `portscan`.

**Detector UI demo (optional):** set `ENABLE_DETECTOR_SIM=1`, open the dashboard (WebSocket connected), then:

```powershell
Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/dev/simulate-detection/honeypot"
Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/dev/simulate-detection/portscan"
```

Expect three red pulses on the matching diamond node, a red line in `#terminal-log`, and the client in the Shadow (banned) list.

**Real triggers (no sim):** `GET /.env` → honeypot; 11+ requests in one second from the same IP → ratelimit.

Demo log spam is off by default (`ENABLE_WS_DEMO_LOGS=0`).

## Client identity (`X-Gateway-Client-Id`)

Ban/whitelist/real-session use **`IP + X-Gateway-Client-Id`**, not IP alone (shared NAT / infected LAN device).

- Dashboard: UUID in `localStorage`, sent on every `gatewayFetch` and on WebSocket `?client_id=`.
- curl without header → `IP · no client id` (separate from the browser).

```bash
curl -H "X-Gateway-Client-Id: test-lab-client" http://127.0.0.1:8000/api/lights/living
```

## Shadow decoy paths (sandbox only)

Exploit-shaped URLs return **static** error bodies (no RCE), not a generic nginx 404 — e.g. `/api/tags`, `/clip/v2/resource`, `/device.xml`, `/ota/check`, `/api/legacy/auth`. Implemented in [`server/shadow_world/decoys.py`](server/shadow_world/decoys.py); only when `is_attacker` is true.

| Request (banned client) | Typical response |
|-------------------------|------------------|
| `GET /api/tags` | 403 JSON |
| `GET /device.xml` | 500 XML |
| Unknown room `/api/lights/xyz` | 404 API JSON (unchanged) |
| Scanner `GET /.env` | honeypot + ban (may still be masked 404 on non-API path) |

## Anti-fingerprinting (masked errors)

Probe paths and API errors do not expose FastAPI `{"detail": ...}` responses.

```bash
curl -i http://127.0.0.1:8000/wp-admin
curl -i http://127.0.0.1:8000/api/lights/unknown
```

OpenAPI UI is disabled by default. For local development: `set ENABLE_DOCS=1` (Windows) or `ENABLE_DOCS=1 python main.py`, then open `/docs`.
