# Verification checklist

Manual tests for the IoT Deception Gateway. Start the server locally ([README](../README.md#quick-start)) or via Docker before running these steps.

**Note:** Ban lists, shadow state, and port-knock progress are **in-memory** and reset when the process restarts.

## Prerequisites

- Server listening on `http://127.0.0.1:8000`
- Optional header for scripted tests: `X-Gateway-Client-Id` (ban/whitelist uses **IP + client id**, not IP alone)

```bash
curl -H "X-Gateway-Client-Id: test-lab-client" http://127.0.0.1:8000/api/lights/living
```

The dashboard stores a client id in `localStorage` and sends it on API calls and on WebSocket `?client_id=`. A `curl` without the header is a **different** client than the browser on the same IP.

## Dashboard smoke test

1. Open `http://127.0.0.1:8000/`
2. In DevTools → Network, confirm `200` for `/static/css/style.css` and `/static/js/app.js`
3. Confirm the topology graph and live log connect (WebSocket `/ws/dashboard`; requires `uvicorn[standard]`)

## Legal vs sandboxed client

### Legal (clean) client

```bash
curl -H "X-Gateway-Client-Id: clean-client-1" http://127.0.0.1:8000/api/lights/living
```

- Response includes `source: REAL_API`, firmware such as `v2.1`
- `GET /api/states` → **3** entities: `light.living`, `light.kitchen`, `lock.main_door` (Home Assistant shape: `entity_id`, `state`, `attributes`). No `light.hall_dimmer_aux`

### Detection (honeypot)

```bash
curl http://127.0.0.1:8000/.env
```

That client (no `X-Gateway-Client-Id`) is banned. The dashboard browser on the same IP remains separate if it uses its own client id.

### Shadow twin

Repeat light/states requests with the **same** client id used for the ban (or any banned fingerprint):

- `GET /api/lights/living` → `SHADOW_TWIN`, legacy-style firmware (e.g. `1.49.195007`), response jitter
- `GET /api/states` → **4** entities (includes canary `light.hall_dimmer_aux`), ~0.15–0.35 s delay
- Server console: `[API] Client requested global states. Defending: True.`

### Canary (optional)

`hall_dimmer_aux` exists only in the shadow plane:

- Clean client: `GET /api/lights/hall_dimmer_aux` → 404
- Sandboxed client: same request → 200

## Rate limit (real trigger)

Send **11+ requests in one second** from the same IP (any path) without simulation env vars. Expect ratelimit detection and ban for that client fingerprint.

## Port knocking (sandbox exit)

While sandboxed, complete within **15 seconds** with a **fixed** `X-Gateway-Client-Id`:

**Sequence:** living light **ON** → `main_door` **unlock** → living light **OFF**

On the dashboard phone mock: toggle the living room light, tap unlock on the main door lock, toggle the living light off.

```bash
CID=11111111-1111-1111-1111-111111111111
H="X-Gateway-Client-Id: $CID"
# Ban this CID first (e.g. curl /.env with the same header), or use an already banned id.
# If living is ON, toggle once to OFF before starting the sequence.
curl -H "$H" -X POST http://127.0.0.1:8000/api/lights/living/toggle   # ON
curl -H "$H" -X POST http://127.0.0.1:8000/api/locks/main_door/unlock
curl -H "$H" -X POST http://127.0.0.1:8000/api/lights/living/toggle   # OFF
```

Expected:

- Server log: `[PORT KNOCKING] Sequence complete...`
- WebSocket `reauth_success`, gateway pulse on the graph, client moves toward the Real list
- Next `GET /api/lights/living` with the same header → `REAL_API`

**Negative tests:** three toggles without unlock does **not** whitelist; wrong order or timeout resets the FSM (`knock_reset` on the dashboard).

## Detector simulation (optional)

Set `ENABLE_DETECTOR_SIM=1`, restart the server, open the dashboard (WebSocket connected), then trigger a detector for your current browser client:

```bash
curl -X POST http://127.0.0.1:8000/api/dev/simulate-detection/honeypot \
  -H "X-Gateway-Client-Id: <your-dashboard-client-id>"
```

PowerShell:

```powershell
Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/dev/simulate-detection/honeypot"
Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/dev/simulate-detection/ratelimit"
```

Graph detector node ids: `honeypot`, `ratelimit`, `bruteforce`.

Expect: repeated red pulse on the matching detector node (10 pulses), an ALERT line in the terminal log, and the client on the Shadow (banned) list.

## Dashboard WebSocket (`/ws/dashboard`)

| `type` | Purpose |
|--------|---------|
| `log` | `{ level, message, timestamp }` |
| `ip_state` | `{ whitelist, blacklist }` — Real / Shadow labels (`IP · client id`) |
| `device_state` | `{ device_id, state, device_type? }` — topology graph + phone mock |
| `attack_alert` | `{ detector, message, client_ip, timestamp }` — terminal ALERT + detector pulse |
| `knock_progress` | `{ step: 1 \| 2 }` — port-knock step completed |
| `knock_reset` | Sequence timeout or wrong order; clear knock slots |
| `reauth_success` | `{ client, timestamp }` — port-knock exit; gateway pulse + Real list highlight |

## Shadow decoy paths (sandbox only)

For banned clients, exploit-shaped URLs return **static** bodies (no RCE), implemented in [`server/shadow_world/decoys.py`](../server/shadow_world/decoys.py).

| Request (banned client) | Typical response |
|-------------------------|------------------|
| `GET /api/tags` | 403 JSON |
| `GET /device.xml` | 500 XML |
| Unknown room `/api/lights/xyz` | 404 API JSON |
| Scanner `GET /.env` | honeypot + ban (response may be masked) |

Use a banned client header when testing decoys:

```bash
curl -H "X-Gateway-Client-Id: banned-test" http://127.0.0.1:8000/api/tags
```

## Masked errors (anti-fingerprinting)

Probe paths and API errors avoid exposing raw FastAPI `{"detail": ...}` JSON.

```bash
curl -i http://127.0.0.1:8000/wp-admin
curl -i http://127.0.0.1:8000/api/lights/unknown
```

OpenAPI UI: set `ENABLE_DOCS=1` and open `/docs` (see README Configuration table).
