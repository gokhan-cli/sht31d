#!/usr/bin/env python3
import sys
import json
import os

def main():
    if len(sys.argv) != 2:
        print("Kullanım: snmp_bridge.py <temp|humidity|heat_index|heater>")
        sys.exit(1)

    key_map = {
        "temp": "temperature",
        "humidity": "humidity",
        "heat_index": "heat_index",
        "heater": "heater_status"
    }

    req_key = sys.argv[1]
    if req_key not in key_map:
        print("Geçersiz parametre")
        sys.exit(1)

    state_file = "/dev/shm/sht31d_state.json"

    if not os.path.exists(state_file):
        print("U") # Bilinmeyen/Hazır Değil
        sys.exit(0)

    try:
        with open(state_file, "r") as f:
            data = json.load(f)
            print(data.get(key_map[req_key], "U"))
    except Exception:
        print("E") # Hata

if __name__ == "__main__":
    main()
