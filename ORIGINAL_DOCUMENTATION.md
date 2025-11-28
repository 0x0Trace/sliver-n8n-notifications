# Sliver C2 Implant Callback Integration with n8n

## Overview

This project integrates **Sliver C2** (Command & Control framework) with **n8n** (workflow automation) to provide **real-time notifications** when new implant connections are established. When a target machine connects to your Sliver server (via beacon or interactive session), you'll immediately receive alerts on Discord and Slack with detailed information about the compromised host.

**Use Case:** Red team operations, penetration testing engagements, security research, and authorized security assessments.

### How It Works

```
Sliver C2 Server
    ↓
Python Monitor (polls every 5 seconds)
    ↓
n8n Webhook
    ↓
Discord + Slack Notifications (parallel)
```

### What You'll Get

- Real-time alerts when beacons or sessions connect
- Color-coded notifications (Red for sessions, Green for beacons)
- Detailed target info: hostname, username, OS, IP address, architecture
- Persistent state tracking to prevent duplicate alerts on restart

---

## Prerequisites

Before starting, ensure you have:

1. **Sliver C2 Server** installed and running
2. **Sliver client config** file generated (`~/.sliver-client/configs/`)
3. **Python 3.7+** with pip
4. **Discord webhook URL** (create in Discord server settings)
5. **Slack workspace** with permissions to create apps (optional)
6. **Linux/WSL environment** (for systemd service)

---

## Step 1: Install n8n

n8n is the workflow automation platform that will receive webhooks and send notifications.

### 1.1 Install Node Version Manager (NVM)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
```

### 1.2 Load NVM into your shell

```bash
source ~/.zshrc  # or source ~/.bashrc if using bash
```

### 1.3 Install Node.js and n8n

```bash
# Install Node.js version 24
nvm install 24

# Install n8n globally
npm install n8n -g
```

### 1.4 Start n8n

```bash
n8n start
```

n8n will be accessible at `http://localhost:5678`

---

## Step 2: Install Python Dependencies

The monitoring script requires the Sliver Python client library.

```bash
pip install sliver-py requests
```

---

## Step 3: Create the Python Monitor Script

This script connects to your Sliver server and monitors for new beacon/session connections.

### 3.1 Create the script file

Save the following script as `sliver_beacon_monitor.py` in your working directory (e.g., `/home/kali/n8n/`):

### 3.2 Python Script Code

## python script

```python
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
```

### 3.3 Configuration Variables to Update

Before running, update these variables in the script:

- **`N8N_WEBHOOK_URL`**: Will be `http://localhost:5678/webhook/sliver-beacon` after you create the n8n workflow
- **`SLIVER_CONFIG_PATH`**: Path to your Sliver client config file (check `~/.sliver-client/configs/`)

### 3.4 Test the script manually

```bash
# Make it executable
chmod +x sliver_beacon_monitor.py

# Run it manually to test
python3 sliver_beacon_monitor.py
```

You should see:
```
[*] Loading config from: /home/kali/.sliver-client/configs/kali_localhost.cfg
[+] Connected to Sliver server
[*] Monitoring for new connections...
```

---

## Step 4: Create Systemd Service (Auto-Start)

To run the monitor automatically in the background, create a systemd service.

### 4.1 Find your Python path

```bash
which python3
```

Copy the output (e.g., `/home/kali/n8n/venv/bin/python` or `/usr/bin/python3`)

### 4.2 Create service file

Create `/etc/systemd/system/sliver-monitor.service` with the following content:

```bash
sudo nano /etc/systemd/system/sliver-monitor.service
```

### 4.3 Service Configuration

```ini
[Unit]
Description=Sliver Beacon Monitor
After=network.target sliver.service
Wants=sliver.service

[Service]
Type=simple
User=kali

# IMPORTANT: Replace the path below with the output of 'which python'
ExecStart=/home/kali/n8n/venv/bin/python  /home/kali/n8n/sliver_beacon_monitor.py

# Optional: Set the working directory to where your script is (helps with relative paths)
WorkingDirectory=/home/kali/n8n

Restart=always
RestartSec=5

[Install]
WantedBy=sliver.service
```

**Important:** Replace `/home/kali/n8n/venv/bin/python` with your actual Python path, and update the script path if different.

### 4.4 Enable and start the service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable sliver-monitor.service

# Start the service
sudo systemctl start sliver-monitor.service

# Check status
sudo systemctl status sliver-monitor.service
```

### 4.5 View logs

```bash
# Follow live logs
sudo journalctl -u sliver-monitor.service -f

# View recent logs
sudo journalctl -u sliver-monitor.service -n 50
```

---

## Step 5: Import n8n Workflow

Now we'll create the workflow in n8n that receives webhooks and sends notifications.

### 5.1 Copy the workflow JSON

The complete n8n workflow JSON is provided below. This workflow:
1. Receives webhook POST requests from the Python monitor
2. Formats the data for Discord and Slack
3. Sends color-coded notifications to both platforms simultaneously
4. Returns a success response to the monitor

### 5.2 n8n Workflow JSON

<img src="docs/images/image%201.png" alt="Discord Notification" width="500">

```json
{
  "name": "Sliver C2 Fixed Layout",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "sliver-beacon",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "1821514b-b15d-4d98-9608-2bfe6cef3052",
      "name": "Webhook - Sliver Beacon",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1.1,
      "position": [
        -240,
        192
      ],
      "webhookId": "sliver-beacon"
    },
    {
      "parameters": {
        "fields": {
          "values": [
            {
              "name": "discord_color",
              "type": "numberValue",
              "numberValue": "={{ $json.body.type == 'Session' ? 15158332 : 3066993 }}"
            },
            {
              "name": "slack_text",
              "stringValue": "=🚨 *NEW C2 CONNECTION*\n*Host:* {{ $json.body.hostname }}\n*User:* {{ $json.body.username }}\n*IP:* {{ $json.body.remote_address }}\n*Type:* {{ $json.body.type }}"
            }
          ]
        },
        "options": {}
      },
      "id": "1550cd22-ba27-4812-be7a-7d3771ef4478",
      "name": "Format Data",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.2,
      "position": [
        0,
        192
      ]
    },
    {
      "parameters": {
        "authentication": "webhook",
        "options": {},
        "embeds": {
          "values": [
            {
              "inputMethod": "json",
              "json": "={{\nJSON.stringify({\n  \"title\": \"🚨 New \" + $json.body.type + \" Connection\",\n  \"color\": parseInt($json.discord_color),\n  \"description\": \"**Target Acquired**\",\n  \"fields\": [\n    {\n      \"name\": \"Hostname\",\n      \"value\": $json.body.hostname,\n      \"inline\": true\n    },\n    {\n      \"name\": \"User\",\n      \"value\": $json.body.username,\n      \"inline\": true\n    },\n    {\n      \"name\": \"Remote IP\",\n      \"value\": $json.body.remote_address,\n      \"inline\": true\n    },\n    {\n      \"name\": \"OS / Arch\",\n      \"value\": $json.body.os + \" (\" + $json.body.arch + \")\",\n      \"inline\": true\n    }\n  ],\n  \"timestamp\": $json.body.timestamp\n})\n}}"
            }
          ]
        }
      },
      "id": "dd15b3f9-2dca-43ae-999e-fa9641675329",
      "name": "Discord Notification",
      "type": "n8n-nodes-base.discord",
      "typeVersion": 2,
      "position": [
        400,
        16
      ],
      "webhookId": "89bcf1ab-637c-4ff6-aad6-77b339b43459",
      "credentials": {
        "discordWebhookApi": {
          "id": "s2EfxTlE6XNXzEIA",
          "name": "Discord Webhook account"
        }
      }
    },
    {
      "parameters": {
        "select": "channel",
        "channelId": {
          "__rl": true,
          "value": "c2-server",
          "mode": "name"
        },
        "text": "={{ $json.slack_text }}",
        "otherOptions": {}
      },
      "id": "abcd260b-933a-49d9-b954-d80aee800571",
      "name": "Send a message",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.3,
      "position": [
        416,
        368
      ],
      "webhookId": "491fc4a8-1e3a-43d6-9620-6ba7c7dc7b73",
      "credentials": {
        "slackApi": {
          "id": "2V7dVbhWzytyBn8C",
          "name": "Slack account"
        }
      }
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "{\n  \"status\": \"success\"\n}",
        "options": {}
      },
      "id": "ae1c5c77-9d8f-4428-aabe-3d820da88fca",
      "name": "Webhook Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [
        864,
        192
      ]
    }
  ],
  "pinData": {},
  "connections": {
    "Webhook - Sliver Beacon": {
      "main": [
        [
          {
            "node": "Format Data",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Format Data": {
      "main": [
        [
          {
            "node": "Discord Notification",
            "type": "main",
            "index": 0
          },
          {
            "node": "Send a message",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Discord Notification": {
      "main": [
        [
          {
            "node": "Webhook Response",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Send a message": {
      "main": [
        [
          {
            "node": "Webhook Response",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": true,
  "settings": {
    "executionOrder": "v1"
  },
  "versionId": "ab7adcb6-32b6-4000-b084-989da2cc5359",
  "meta": {
    "templateCredsSetupCompleted": true,
    "instanceId": "3d65e600a9aeb19d6f05ce03e45f574014956a91db8dd7174a8b9335554e5aa3"
  },
  "id": "mC2tEf3azuitx6C9",
  "tags": []
}
```

### 5.3 Import into n8n

1. Open n8n at `http://localhost:5678`
2. Click **Workflows** in the left sidebar
3. Click **Add workflow** → **Import from File**
4. Paste the JSON above
5. Click **Import**

### 5.4 Workflow Visual Overview

![n8n Workflow Diagram](image.png)

The workflow consists of 5 nodes:
1. **Webhook - Sliver Beacon**: Entry point (receives POST requests)
2. **Format Data**: Transforms data for notifications
3. **Discord Notification**: Sends rich embed to Discord (runs in parallel)
4. **Send a message**: Posts to Slack channel (runs in parallel)
5. **Webhook Response**: Returns success to caller

---

## Step 6: Configure Discord Integration

### 6.1 Create Discord Webhook

1. Open your Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook**
4. Name it (e.g., "Sliver C2 Alerts")
5. Select the channel for notifications
6. Click **Copy Webhook URL**

### 6.2 Add to n8n

1. In the n8n workflow, click the **Discord Notification** node
2. Click **Create New Credential**
3. Select **Discord Webhook**
4. Paste your webhook URL
5. Click **Save**

---

## Step 7: Configure Slack Integration (Optional)

If you want Slack notifications in addition to Discord, follow these steps.

# How to Connect n8n to Slack

This guide outlines the steps to create a Slack Bot and connect it to n8n using an Access Token.

## Phase 1: Create the Slack App

1. Go to the [Slack API Console](https://api.slack.com/apps).
2. Click **Create New App** -> **From scratch**.
3. Name the app (e.g., `n8n Automation`) and select your target Workspace.

### Configure Permissions

1. On the left sidebar, go to **Features** -> **OAuth & Permissions**.
2. Scroll down to the **Scopes** section.
3. Under **Bot Token Scopes**, add the following:
    - `chat:write` (Required to send messages)
    - `chat:write.public` (Optional: Allows posting to public channels without being invited)
    - `files:write` (Optional: If you plan to upload files/images)

### Install & Get Token

1. Scroll to the top of the **OAuth & Permissions** page.
2. Click **Install to Workspace** and allow access.
3. Copy the **Bot User OAuth Token**.
    - *It starts with `xoxb-...`*

---

## Phase 2: Configure n8n Credentials

1. Open your n8n instance and click the slack block.
2. Navigate to **Credentials to connect with** 
3. Select for **Slack API**.
4. **Crucial Step:** In the "Authentication" dropdown, select **Access Token** (Do not use OAuth2).
5. Paste your `xoxb-...` token into the **Access Token** field.
6. Click **Save**.

> Note: If the connection test fails but the token is correct, n8n sometimes checks for the users:read scope. You can usually ignore this error if you only want to send messages, or add that scope in Slack to fix the test.
> 

---

## Phase 3: Setup the Workflow Node

1. Add a **Slack** node to your canvas.
2. Select the **Slack API** credential you created.
3. Set **Resource** to `Message`.
4. Set **Operation** to `Send`.
5. **Channel Selection:**
    - **Option A:** Select `By Name` and type the channel name (e.g., `#general` or `#alerts`).
    - **Option B:** Select `By ID` (more robust if channel names change).
6. Enter your text in the **Text** field.

---

## Step 8: Activate the Workflow

1. In n8n, ensure your workflow is saved
2. Toggle the **Active** switch in the top-right corner to ON
3. The webhook is now live at `http://localhost:5678/webhook/sliver-beacon`

---

## Step 9: Test the Integration

### 9.1 Test with curl

```bash
curl -X POST http://localhost:5678/webhook/sliver-beacon \
  -H "Content-Type: application/json" \
  -d '{
    "event": "new_connection",
    "type": "Beacon",
    "timestamp": "2025-01-15T10:30:00Z",
    "hostname": "test-machine",
    "username": "testuser",
    "os": "windows",
    "arch": "amd64",
    "remote_address": "192.168.1.100:8888"
  }'
```

You should receive a test notification on Discord and Slack.

### 9.2 Test with real implant

Deploy a Sliver implant to a test machine and wait for it to connect. You should see:

1. Terminal output from the monitor service
2. Discord notification (color-coded)
3. Slack message

---

## Example Notifications

### Discord Output (Beacon - Green)

![Discord Beacon Notification](image%201.png)

**Features:**
- Green color for beacons (color code: 3066993)
- Red color for sessions (color code: 15158332)
- Embedded fields showing hostname, user, IP, OS/Arch
- Timestamp of connection

### Slack Output

![Slack Notification](image%202.png)

**Features:**
- Simple text format with alert icon
- All critical info in one message
- Posted to `#c2-server` channel

---

## Troubleshooting

### Monitor service not starting

```bash
# Check if Sliver server is running
sudo systemctl status sliver.service

# Check Python dependencies
pip list | grep sliver

# Verify config file exists
ls -la ~/.sliver-client/configs/

# Check service logs for errors
sudo journalctl -u sliver-monitor.service -n 100
```

### Webhook not reaching n8n

```bash
# Verify n8n is running
curl http://localhost:5678

# Check if webhook is active in n8n UI
# Ensure workflow toggle is ON

# Test webhook directly
curl -X POST http://localhost:5678/webhook/sliver-beacon \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Notifications not appearing

**Discord:**
- Verify webhook URL is correct
- Check Discord server permissions
- Test webhook directly: `curl -X POST YOUR_DISCORD_WEBHOOK_URL -H "Content-Type: application/json" -d '{"content": "test"}'`

**Slack:**
- Ensure bot is invited to the channel
- Verify token starts with `xoxb-`
- Check bot has `chat:write` permission
- Try posting to a different channel

### Duplicate notifications

The monitor uses `beacon_state.json` to track known connections. If you're getting duplicates:

```bash
# Stop the service
sudo systemctl stop sliver-monitor.service

# Clear the state file
rm /path/to/beacon_state.json

# Restart the service
sudo systemctl start sliver-monitor.service
```

---

## Advanced Configuration

### Change polling interval

Edit `sliver_beacon_monitor.py` line 65:

```python
CHECK_INTERVAL = 10  # Change from 5 to 10 seconds
```

### Add email notifications

Add an email node to the n8n workflow parallel to Discord/Slack nodes.

### Filter by OS or hostname

Add an **IF** node in n8n after "Format Data" to filter based on conditions:

```javascript
{{ $json.body.os === "windows" }}  // Only notify for Windows targets
```

---

## Security Notes

- Keep your Discord webhook URL private (do not commit to Git)
- Restrict n8n to localhost or use authentication if exposing externally
- The `beacon_state.json` file contains connection IDs but no sensitive data
- Monitor logs may contain target information - secure log files appropriately
- This tool is for authorized penetration testing only

---

## Project Files Summary

- `sliver_beacon_monitor.py` - Python monitoring daemon
- `beacon_state.json` - Persistent state (auto-created)
- `/etc/systemd/system/sliver-monitor.service` - Systemd service unit
- n8n workflow (imported via JSON)

---

## References

- [Sliver C2 Documentation](https://github.com/BishopFox/sliver)
- [n8n Documentation](https://docs.n8n.io/)
- [Discord Webhooks Guide](https://discord.com/developers/docs/resources/webhook)
- [Slack API Documentation](https://api.slack.com/)