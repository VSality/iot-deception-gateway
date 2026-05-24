"""Manual integration test: sandbox detection + IoT port knocking exit."""

import requests

BASE_URL = "http://127.0.0.1:8000"
KNOCK_ROOM = "living"


def test_port_knocking_exit():
    print("[Test] Simulate honeypot block...")
    requests.get(f"{BASE_URL}/.env")

    print("[Test] Should be in shadow...")
    r = requests.get(f"{BASE_URL}/api/lights/{KNOCK_ROOM}")
    print(f"  GET living: {r.status_code} source={r.json().get('source')}")

    print(f"[Test] Port knock: 3x POST toggle {KNOCK_ROOM}...")
    for i in range(3):
        tr = requests.post(f"{BASE_URL}/api/lights/{KNOCK_ROOM}/toggle")
        print(f"  toggle {i + 1}: {tr.status_code} new_state={tr.json().get('new_state')}")

    print("[Test] After knock — expect REAL_API on next GET...")
    r2 = requests.get(f"{BASE_URL}/api/lights/{KNOCK_ROOM}")
    print(f"  GET living: {r2.status_code} source={r2.json().get('source')}")
    print(f"  firmware={r2.json().get('firmware')}")


if __name__ == "__main__":
    test_port_knocking_exit()
