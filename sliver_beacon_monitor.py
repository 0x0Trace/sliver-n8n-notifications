#!/usr/bin/env python3
"""
Sliver C2 Beacon Monitor (Fixed Session Detection)
Monitors Sliver for new beacons AND sessions, sending webhooks to n8n.
"""

import asyncio
import requests
import json
import os
from datetime import datetime
from sliver import SliverClientConfig, SliverClient

# --- Configuration ---
# MAKE SURE THIS IS YOUR PRODUCTION URL FROM WEBHOOK SLIVER BEACON
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/sliver-beacon"
SLIVER_CONFIG_PATH = os.path.expanduser("~/.sliver-client/configs/kali_localhost.cfg")
STATE_FILE = "beacon_state.json"
CHECK_INTERVAL = 5  # seconds

def load_state():
    """Load known IDs from disk to prevent alert floods on restart."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_state(known_ids):
    """Save known IDs to disk."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(list(known_ids), f)
    except Exception as e:
        print(f"[!] Error saving state: {e}")

def get_internal_ip(conn):
    """Attempt to extract an internal IP."""
    # Sessions often have different attributes than Beacons
    if hasattr(conn, "ActiveC2"):
        return str(conn.ActiveC2)
    return "Unknown"

def send_webhook(data):
    """Send data to n8n webhook."""
    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            print(f"✓ Webhook sent for: {data.get('hostname')} ({data['type']})")
        else:
            print(f"✗ Webhook failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error sending webhook: {e}")

async def monitor_beacons():
    known_ids = load_state()

    print(f"[*] Loading config from: {SLIVER_CONFIG_PATH}")
    try:
        config = SliverClientConfig.parse_config_file(SLIVER_CONFIG_PATH)
        client = SliverClient(config)
        await client.connect()
        print(f"[+] Connected to Sliver server")
    except Exception as e:
        print(f"[!] Failed to connect to Sliver: {e}")
        return

    print("[*] Monitoring for new connections...")

    while True:
        try:
            # 1. Fetch BOTH Lists separately
            current_sessions = await client.sessions()
            current_beacons = await client.beacons()

            # 2. Tag them EXPLICITLY before merging
            # We create a list of tuples: (connection_object, "Session") or (connection_object, "Beacon")
            tagged_sessions = [(s, "Session") for s in current_sessions]
            tagged_beacons  = [(b, "Beacon") for b in current_beacons]

            all_connections = tagged_sessions + tagged_beacons

            # 3. Check for NEW connections
            for conn, conn_type in all_connections:
                if conn.ID not in known_ids:

                    # Add to memory and Save
                    known_ids.add(conn.ID)
                    save_state(known_ids)

                    # Build Data Package
                    # We use 'conn_type' variable which we explicitly set above
                    data = {
                        "event": "new_connection",
                        "type": conn_type,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "id": conn.ID,
                        "name": getattr(conn, "Name", "Unknown"),
                        "hostname": getattr(conn, "Hostname", "Unknown"),
                        "username": getattr(conn, "Username", "Unknown"),
                        "os": getattr(conn, "OS", "Unknown"),
                        "arch": getattr(conn, "Arch", "Unknown"),
                        "remote_address": getattr(conn, "RemoteAddress", "Unknown"),
                        "internal_ip": get_internal_ip(conn),
                        "transport": getattr(conn, "Transport", "Unknown"),
                    }

                    # Color code output for the terminal
                    color = "\033[91m" if conn_type == "Session" else "\033[92m" # Red for Session, Green for Beacon
                    reset = "\033[0m"

                    print(f"\n[!] {color}NEW {conn_type.upper()} DETECTED{reset}: {data['hostname']} ({data['remote_address']})")

                    await asyncio.to_thread(send_webhook, data)

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"[!] Error in loop: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_beacons())
    except KeyboardInterrupt:
        print("\n[*] Stopping monitor")
