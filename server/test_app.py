"""Manual integration test: sandbox detection + IoT port knocking FSM exit."""

import requests

BASE_URL = "http://127.0.0.1:8000"
KNOCK_ROOM = "living"
LOCK_ID = "main_door"
TEST_CLIENT_ID = "11111111-1111-1111-1111-111111111111"
HEADERS = {"X-Gateway-Client-Id": TEST_CLIENT_ID}


def _toggle_living() -> dict:
    r = requests.post(
        f"{BASE_URL}/api/lights/{KNOCK_ROOM}/toggle",
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def test_port_knocking_fsm_exit():
    print("[Test] Honeypot block (fixed client id)...")
    requests.get(f"{BASE_URL}/.env", headers=HEADERS)

    print("[Test] Should be in shadow...")
    r = requests.get(f"{BASE_URL}/api/lights/{KNOCK_ROOM}", headers=HEADERS)
    body = r.json()
    print(f"  GET living: {r.status_code} source={body.get('source')} status={body.get('status')}")

    if body.get("status") == "on":
        print("[Test] Toggle living OFF first...")
        _toggle_living()

    print("[Test] Knock step 1: living ON...")
    t1 = _toggle_living()
    print(f"  -> {t1.get('new_state')}")

    print("[Test] Knock step 2: unlock lock...")
    ur = requests.post(
        f"{BASE_URL}/api/locks/{LOCK_ID}/unlock",
        headers=HEADERS,
    )
    print(f"  unlock: {ur.status_code}")

    print("[Test] Knock step 3: living OFF...")
    t2 = _toggle_living()
    print(f"  -> {t2.get('new_state')}")

    print("[Test] After knock — expect REAL_API on next GET...")
    r2 = requests.get(f"{BASE_URL}/api/lights/{KNOCK_ROOM}", headers=HEADERS)
    print(f"  GET living: {r2.status_code} source={r2.json().get('source')}")
    print(f"  firmware={r2.json().get('firmware')}")


if __name__ == "__main__":
    test_port_knocking_fsm_exit()
