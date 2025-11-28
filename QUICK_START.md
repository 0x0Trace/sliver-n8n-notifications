# Quick Start Guide

For experienced users who already have Sliver C2 and Python configured. This is a condensed reference - for detailed instructions, see [INSTALLATION.md](INSTALLATION.md).

---

## Prerequisites Check

- [ ] Sliver C2 server running
- [ ] Sliver client config exists (`~/.sliver-client/configs/`)
- [ ] Python 3.7+ installed
- [ ] Discord webhook URL ready
- [ ] Slack bot token (optional)

---

## 1. Install n8n

```bash
# Install NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.zshrc  # or ~/.bashrc

# Install Node.js and n8n
nvm install 24
npm install n8n -g

# Start n8n
n8n start  # Accessible at http://localhost:5678
```

---

## 2. Install Python Dependencies

```bash
pip install sliver-py requests
```

---

## 3. Deploy Monitor Script

```bash
# Download or copy the script
wget https://raw.githubusercontent.com/yourusername/repo/main/sliver_beacon_monitor.py
# OR
cp /path/to/repo/sliver_beacon_monitor.py .

# Make executable
chmod +x sliver_beacon_monitor.py

# Configure (edit these lines)
nano sliver_beacon_monitor.py
```

**Edit configuration (lines 17-18):**
```python
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/sliver-beacon"
SLIVER_CONFIG_PATH = os.path.expanduser("~/.sliver-client/configs/YOUR_CONFIG.cfg")
```

**Test run:**
```bash
python3 sliver_beacon_monitor.py
# Should show: [+] Connected to Sliver server
# Ctrl+C to stop
```

---

## 4. Setup Systemd Service

```bash
# Get Python path
which python3  # Copy the output

# Download service file
sudo wget -O /etc/systemd/system/sliver-monitor.service \
  https://raw.githubusercontent.com/yourusername/repo/main/sliver-monitor.service

# Edit service file
sudo nano /etc/systemd/system/sliver-monitor.service
```

**Update these values:**
- `User=` → Your username
- `ExecStart=` → Path from `which python3` + script location
- `WorkingDirectory=` → Directory containing script

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable sliver-monitor.service
sudo systemctl start sliver-monitor.service
sudo systemctl status sliver-monitor.service
```

---

## 5. Import n8n Workflow

1. Open n8n: `http://localhost:5678`
2. Workflows → Import from File
3. Select `n8n_workflow.json` from repository
4. Click Import

---

## 6. Configure Credentials

### Discord (Required)

1. Create webhook: Discord Server → Settings → Integrations → Webhooks → New Webhook
2. Copy webhook URL
3. In n8n: Click "Discord Notification" node → Create New Credential
4. Paste webhook URL → Save

### Slack (Optional)

1. Create app: [Slack API Console](https://api.slack.com/apps) → Create New App → From scratch
2. OAuth & Permissions → Add Bot Token Scopes: `chat:write`, `chat:write.public`
3. Install to Workspace → Copy Bot User OAuth Token (starts with `xoxb-`)
4. In n8n: Click "Send a message" node → Create New Credential
5. Select "Access Token" authentication → Paste token → Save
6. Set channel name (e.g., `c2-server`)

---

## 7. Activate Workflow

1. Click **Save** in n8n
2. Toggle **Active** switch to ON (top-right)
3. Verify webhook path: Should be `sliver-beacon`

---

## 8. Test

### Quick test with curl:
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

### Production test:
1. Deploy Sliver implant to test machine
2. Wait for connection
3. Check notifications on Discord/Slack

### Monitor logs:
```bash
# Follow service logs
sudo journalctl -u sliver-monitor.service -f

# Check recent logs
sudo journalctl -u sliver-monitor.service -n 50
```

---

## Configuration Reference

### Python Script Variables

| Variable | Location | Default Value | Description |
|----------|----------|---------------|-------------|
| `N8N_WEBHOOK_URL` | Line 17 | `http://localhost:5678/webhook/sliver-beacon` | n8n webhook endpoint |
| `SLIVER_CONFIG_PATH` | Line 18 | `~/.sliver-client/configs/kali_localhost.cfg` | Sliver client config |
| `STATE_FILE` | Line 19 | `beacon_state.json` | Persistent state storage |
| `CHECK_INTERVAL` | Line 20 | `5` | Polling interval (seconds) |

### Systemd Service Locations

| Item | Path |
|------|------|
| Service file | `/etc/systemd/system/sliver-monitor.service` |
| Log output | `journalctl -u sliver-monitor.service` |

### n8n Workflow Details

| Node | Purpose | Configuration |
|------|---------|---------------|
| Webhook - Sliver Beacon | Entry point | Path: `sliver-beacon`, Method: POST |
| Format Data | Data transformation | Sets Discord color and Slack text |
| Discord Notification | Discord alerts | Requires webhook credential |
| Send a message | Slack alerts | Requires bot token credential |
| Webhook Response | Success response | Returns JSON status |

---

## Notification Color Codes

| Type | Color | Discord Value |
|------|-------|---------------|
| Session | Red | 15158332 |
| Beacon | Green | 3066993 |

---

## Common Commands

```bash
# Service management
sudo systemctl start sliver-monitor.service
sudo systemctl stop sliver-monitor.service
sudo systemctl restart sliver-monitor.service
sudo systemctl status sliver-monitor.service

# View logs
sudo journalctl -u sliver-monitor.service -f       # Follow live
sudo journalctl -u sliver-monitor.service -n 50    # Last 50 lines

# Test webhook
curl -X POST http://localhost:5678/webhook/sliver-beacon \
  -H "Content-Type: application/json" \
  -d '{"type":"Beacon","hostname":"test"}'

# Check n8n
curl http://localhost:5678

# Find Python path
which python3

# List Sliver configs
ls ~/.sliver-client/configs/

# Clear state (reset notifications)
rm beacon_state.json
sudo systemctl restart sliver-monitor.service
```

---

## Troubleshooting Quick Checks

| Issue | Quick Fix |
|-------|-----------|
| Service won't start | `sudo systemctl status sliver.service` - Ensure Sliver is running |
| No webhooks received | `curl http://localhost:5678` - Verify n8n is running |
| No Discord messages | Test webhook URL directly with curl |
| No Slack messages | Ensure bot is invited to channel: `/invite @bot-name` |
| Duplicate notifications | `rm beacon_state.json && sudo systemctl restart sliver-monitor.service` |

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## File Checklist

After setup, you should have:

- [ ] `sliver_beacon_monitor.py` - Monitor script
- [ ] `/etc/systemd/system/sliver-monitor.service` - Systemd service
- [ ] `beacon_state.json` - Auto-created state file
- [ ] n8n workflow imported and active
- [ ] Discord webhook configured
- [ ] Slack bot configured (optional)

---

## Next Steps

- Review [INSTALLATION.md](INSTALLATION.md) for detailed explanations
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if issues arise
- See [README.md](README.md) for project overview
- Review [CLAUDE.md](CLAUDE.md) for technical architecture details

---

## Advanced Customization

### Change polling interval:
```python
# Edit sliver_beacon_monitor.py line 20
CHECK_INTERVAL = 10  # Increase to reduce load
```

### Filter notifications by OS:
Add IF node in n8n after "Format Data":
```javascript
{{ $json.body.os === "windows" }}
```

### Add email notifications:
Add email node in n8n parallel to Discord/Slack nodes

### Custom notification format:
Edit Discord/Slack node message templates in n8n workflow

---

**Ready to deploy?** Start at step 1 and work through sequentially. Each step should take 2-5 minutes for experienced users.
