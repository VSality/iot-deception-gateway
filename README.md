# IoT Deception Gateway

Backend for an IoT cybersecurity gateway: one HTTP API, two data planes — **real devices** (`REAL_DEVICES`) and a **Shadow Digital Twin** for blacklisted attackers. Legitimate users (official smart-home app) can **exit the sandbox** via **In-Band IoT Port Knocking**.

## Project layout

```
server/
  main.py                 # FastAPI app, monitor_traffic, api router, honeypot catch-all
  decision_logic/         # BLACKLIST_IPS, WHITELIST_IPS, port_knock_config
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

## Manual verification

1. Install deps and start the server (see above).
2. **Legal user:** `GET http://127.0.0.1:8000/api/lights/living` → `source: REAL_API`, `firmware: v2.1`.
   - `GET http://127.0.0.1:8000/api/states` → JSON array of **3** entities (`light.living`, `light.kitchen`, `lock.main_door`), HA shape: `entity_id`, `state`, `attributes`. No `light.hall_dimmer_aux`.
3. **Detection:** `curl http://127.0.0.1:8000/.env` → IP in `BLACKLIST_IPS`.
4. **Shadow twin:** `GET /api/lights/living` → `SHADOW_TWIN`, vulnerable firmware, jitter.
   - `GET /api/states` → **4** entities (includes `light.hall_dimmer_aux` canary), vulnerable firmware in attributes, ~0.15–0.35 s delay. Console: `[API] Client requested global states. Defending: True.`
5. **Canary (optional passive check):** `hall_dimmer_aux` exists only in shadow — `GET /api/lights/hall_dimmer_aux` → 404 when clean, 200 when sandboxed.
6. **Port knocking (in-band exit):** while sandboxed, toggle **`living`** **3 times within 3 seconds** using the official app or:

```bash
curl -X POST http://127.0.0.1:8000/api/lights/living/toggle
curl -X POST http://127.0.0.1:8000/api/lights/living/toggle
curl -X POST http://127.0.0.1:8000/api/lights/living/toggle
```

Server log: `[PORT KNOCKING] Secret pattern detected! IP ... released from sandbox.`

7. **Next request:** `GET /api/lights/living` → `REAL_API` (the 3rd toggle response may still be shadow JSON; the 4th call is real).
8. **Kitchen does not knock:** 3× toggle on `kitchen` does not whitelist (only `PORT_KNOCK_ROOM_ID`, default `living` — see [`decision_logic/port_knock_config.py`](server/decision_logic/port_knock_config.py)).

State is in-memory (resets on restart).

## Anti-fingerprinting (masked errors)

Probe paths and API errors do not expose FastAPI `{"detail": ...}` responses.

```bash
curl -i http://127.0.0.1:8000/wp-admin
curl -i http://127.0.0.1:8000/api/lights/unknown
```

OpenAPI UI is disabled by default. For local development: `set ENABLE_DOCS=1` (Windows) or `ENABLE_DOCS=1 python main.py`, then open `/docs`.
