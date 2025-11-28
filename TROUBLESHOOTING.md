# Troubleshooting Guide

This guide covers common issues and their solutions for the Sliver C2 + n8n integration.

---

## Table of Contents

1. [Monitor Service Issues](#monitor-service-issues)
2. [Webhook Connection Problems](#webhook-connection-problems)
3. [Notification Delivery Issues](#notification-delivery-issues)
4. [Duplicate Notifications](#duplicate-notifications)
5. [Configuration Issues](#configuration-issues)
6. [Performance Problems](#performance-problems)

---

## Monitor Service Issues

### Service Won't Start

**Symptoms:**
- Service status shows "failed" or "inactive"
- No logs appearing in journalctl

**Solutions:**

1. **Check if Sliver server is running:**
   ```bash
   sudo systemctl status sliver.service
   ```
   If Sliver is not running, start it:
   ```bash
   sudo systemctl start sliver.service
   ```

2. **Verify Python dependencies:**
   ```bash
   pip list | grep sliver
   pip list | grep requests
   ```
   If missing, install them:
   ```bash
   pip install sliver-py requests
   ```

3. **Verify config file exists:**
   ```bash
   ls -la ~/.sliver-client/configs/
   ```
   If no config exists, connect to Sliver server using the client to generate one.

4. **Check service logs for errors:**
   ```bash
   sudo journalctl -u sliver-monitor.service -n 100
   ```

5. **Verify Python path in service file:**
   ```bash
   which python3
   sudo nano /etc/systemd/system/sliver-monitor.service
   ```
   Ensure the `ExecStart` path matches your Python installation.

---

### Service Starts But Doesn't Connect to Sliver

**Symptoms:**
- Service status shows "active (running)"
- Logs show "Failed to connect to Sliver"

**Solutions:**

1. **Test Sliver connection manually:**
   ```bash
   cd /path/to/script
   python3 sliver_beacon_monitor.py
   ```

2. **Verify Sliver config path:**
   Edit the Python script and check line 18:
   ```python
   SLIVER_CONFIG_PATH = os.path.expanduser("~/.sliver-client/configs/kali_localhost.cfg")
   ```

3. **Check Sliver server is accepting connections:**
   ```bash
   # Connect with Sliver client
   sliver-client
   ```

4. **Verify file permissions:**
   ```bash
   ls -la ~/.sliver-client/configs/
   chmod 600 ~/.sliver-client/configs/*.cfg
   ```

---

### Service Crashes or Restarts Frequently

**Symptoms:**
- Service status shows constant restarts
- Logs show repeated connection attempts

**Solutions:**

1. **Check for network issues:**
   - Verify Sliver server is stable
   - Check network connectivity between monitor and Sliver server

2. **Increase restart delay in service file:**
   ```bash
   sudo nano /etc/systemd/system/sliver-monitor.service
   ```
   Change `RestartSec=5` to `RestartSec=30`

3. **Review error logs:**
   ```bash
   sudo journalctl -u sliver-monitor.service -p err -n 50
   ```

---

## Webhook Connection Problems

### Webhook Not Reaching n8n

**Symptoms:**
- Monitor shows "Webhook failed" errors
- No executions appearing in n8n

**Solutions:**

1. **Verify n8n is running:**
   ```bash
   curl http://localhost:5678
   ```
   If no response, start n8n:
   ```bash
   n8n start
   ```

2. **Check if workflow is active:**
   - Open n8n UI at `http://localhost:5678`
   - Ensure workflow toggle is **ON** (top-right corner)
   - Verify webhook path is `sliver-beacon`

3. **Test webhook directly:**
   ```bash
   curl -X POST http://localhost:5678/webhook/sliver-beacon \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

4. **Verify webhook URL in Python script:**
   Check line 17 of `sliver_beacon_monitor.py`:
   ```python
   N8N_WEBHOOK_URL = "http://localhost:5678/webhook/sliver-beacon"
   ```

5. **Check firewall rules:**
   ```bash
   sudo ufw status
   # If blocking, allow localhost traffic
   sudo ufw allow from 127.0.0.1
   ```

---

### Webhook Returns Error

**Symptoms:**
- Monitor logs show "Webhook failed: 400" or "Webhook failed: 500"

**Solutions:**

1. **Check n8n execution log:**
   - Open n8n UI
   - Click **Executions** in sidebar
   - Review failed executions for error details

2. **Verify JSON payload format:**
   The webhook expects this structure:
   ```json
   {
     "event": "new_connection",
     "type": "Session" | "Beacon",
     "timestamp": "ISO8601Z",
     "hostname": "string",
     "username": "string",
     "os": "string",
     "arch": "string",
     "remote_address": "string"
   }
   ```

3. **Test with minimal payload:**
   ```bash
   curl -X POST http://localhost:5678/webhook/sliver-beacon \
     -H "Content-Type: application/json" \
     -d '{"type": "Beacon", "hostname": "test"}'
   ```

---

## Notification Delivery Issues

### Discord Notifications Not Appearing

**Symptoms:**
- n8n execution succeeds but no Discord message

**Solutions:**

1. **Verify webhook URL is correct:**
   - Click Discord Notification node in n8n
   - Check credential configuration
   - Test webhook URL directly:
   ```bash
   curl -X POST YOUR_DISCORD_WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{"content": "test message"}'
   ```

2. **Check Discord server permissions:**
   - Ensure webhook is not deleted in Discord
   - Verify channel permissions allow webhooks

3. **Review Discord node configuration:**
   - Ensure "Embed" is properly configured
   - Check color values are valid integers
   - Verify JSON structure in embed configuration

4. **Test with simple message:**
   - Temporarily replace embed with simple content
   - If simple message works, issue is in embed formatting

---

### Slack Notifications Not Appearing

**Symptoms:**
- n8n execution succeeds but no Slack message

**Solutions:**

1. **Verify bot is invited to channel:**
   ```
   /invite @n8n-automation
   ```
   Or add the bot via channel settings

2. **Check token format:**
   - Token should start with `xoxb-`
   - Verify you're using Bot User OAuth Token (not User OAuth Token)

3. **Verify bot permissions:**
   - Go to [Slack API Console](https://api.slack.com/apps)
   - Select your app → **OAuth & Permissions**
   - Ensure `chat:write` scope is added
   - If missing, add it and reinstall the app

4. **Test with Slack API directly:**
   ```bash
   curl -X POST https://slack.com/api/chat.postMessage \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"channel": "#c2-server", "text": "test"}'
   ```

5. **Check channel name:**
   - Ensure channel exists and name is correct
   - Try using channel ID instead of name
   - Public channels don't need '#' prefix in n8n

6. **Review n8n credential:**
   - In Slack node, click credential
   - Ensure "Access Token" method is selected (not OAuth2)
   - Re-enter token and save

---

### Notifications Delayed

**Symptoms:**
- Notifications arrive several minutes late

**Solutions:**

1. **Check polling interval:**
   Edit `sliver_beacon_monitor.py` line 20:
   ```python
   CHECK_INTERVAL = 5  # Reduce if needed (minimum 1-2 seconds)
   ```

2. **Verify n8n is not overloaded:**
   - Check n8n execution queue
   - Reduce concurrent workflows if needed

3. **Check system resources:**
   ```bash
   top
   htop
   # Look for CPU/memory bottlenecks
   ```

---

## Duplicate Notifications

**Symptoms:**
- Same beacon/session triggers multiple notifications
- Notifications repeat after service restart

**Solutions:**

1. **Check state file:**
   ```bash
   ls -la beacon_state.json
   cat beacon_state.json
   ```

2. **Clear state file (fresh start):**
   ```bash
   # Stop the service
   sudo systemctl stop sliver-monitor.service

   # Clear the state file
   rm /path/to/beacon_state.json

   # Restart the service
   sudo systemctl start sliver-monitor.service
   ```

3. **Verify state file location:**
   - State file should be in the same directory as the script
   - Check `WorkingDirectory` in systemd service file

4. **Check for multiple monitor instances:**
   ```bash
   ps aux | grep sliver_beacon_monitor
   # Should only show one process + grep itself
   ```

5. **Ensure only one service is running:**
   ```bash
   # Stop all instances
   sudo systemctl stop sliver-monitor.service
   pkill -f sliver_beacon_monitor.py

   # Start service cleanly
   sudo systemctl start sliver-monitor.service
   ```

---

## Configuration Issues

### Wrong Connection Type Detected

**Symptoms:**
- Beacons shown as Sessions or vice versa
- Incorrect color coding

**Solutions:**

1. **Verify script version:**
   - Ensure you're using the latest version with explicit type tagging
   - Check lines 79-88 in `sliver_beacon_monitor.py`

2. **Review tagging logic:**
   ```python
   tagged_sessions = [(s, "Session") for s in current_sessions]
   tagged_beacons  = [(b, "Beacon") for b in current_beacons]
   ```

3. **Test with known beacon/session:**
   - Deploy test beacon
   - Deploy test session
   - Verify correct type appears in notification

---

### Missing Target Information

**Symptoms:**
- Notifications show "Unknown" for hostname, IP, etc.

**Solutions:**

1. **Check Sliver implant info:**
   ```bash
   # In Sliver client
   sessions
   beacons
   info [session_id]
   ```

2. **Verify attribute extraction:**
   - Script uses `getattr()` with defaults
   - If Sliver doesn't provide data, defaults to "Unknown"

3. **Update attribute mapping:**
   - Edit `sliver_beacon_monitor.py` lines 99-109
   - Add debug logging to see available attributes

---

## Performance Problems

### High CPU Usage

**Symptoms:**
- Python process consuming excessive CPU

**Solutions:**

1. **Increase polling interval:**
   ```python
   CHECK_INTERVAL = 10  # Increase from 5
   ```

2. **Check for excessive connections:**
   - Large number of beacons/sessions may slow processing
   - Consider filtering or batching notifications

3. **Review async operations:**
   - Ensure webhook calls are not blocking
   - Check for timeout issues

---

### High Memory Usage

**Symptoms:**
- Python process memory grows over time

**Solutions:**

1. **Check state file size:**
   ```bash
   ls -lh beacon_state.json
   ```

2. **Implement state cleanup:**
   - Remove old IDs from state periodically
   - Add max state size limit

3. **Restart service periodically:**
   - Add systemd timer to restart daily
   - Prevents long-running memory leaks

---

## Getting Help

If issues persist after trying these solutions:

1. **Collect debug information:**
   ```bash
   # Service status
   sudo systemctl status sliver-monitor.service

   # Recent logs
   sudo journalctl -u sliver-monitor.service -n 100

   # Python dependencies
   pip list | grep -E "sliver|requests"

   # n8n version
   n8n --version
   ```

2. **Test individual components:**
   - Run Python script manually
   - Test webhook with curl
   - Verify Discord/Slack independently

3. **Review documentation:**
   - [INSTALLATION.md](INSTALLATION.md) for setup steps
   - [README.md](README.md) for project overview
   - [QUICK_START.md](QUICK_START.md) for configuration reference

4. **Check upstream issues:**
   - [Sliver GitHub Issues](https://github.com/BishopFox/sliver/issues)
   - [n8n GitHub Issues](https://github.com/n8n-io/n8n/issues)
   - [sliver-py Issues](https://github.com/moloch--/sliver-py/issues)

---

## Common Error Messages

### "Failed to connect to Sliver: [SSL: CERTIFICATE_VERIFY_FAILED]"

**Cause:** SSL certificate issue with Sliver client config

**Solution:**
- Regenerate Sliver client config
- Verify certificate paths in config file
- Check system time is synchronized

---

### "Webhook failed: Connection refused"

**Cause:** n8n is not running or not accessible

**Solution:**
- Start n8n: `n8n start`
- Verify listening on port 5678: `netstat -tulpn | grep 5678`
- Check firewall rules

---

### "Error in loop: 'Session' object has no attribute 'Hostname'"

**Cause:** Sliver session missing expected attributes

**Solution:**
- Script uses `getattr()` with defaults, this should not happen
- Update script to latest version
- Report issue with debug details

---

### "Discord API error: Invalid Webhook Token"

**Cause:** Discord webhook URL is invalid or deleted

**Solution:**
- Recreate webhook in Discord server settings
- Update webhook URL in n8n credential
- Verify webhook wasn't deleted in Discord

---

## Debug Mode

To enable verbose logging:

1. **Edit Python script:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Restart service:**
   ```bash
   sudo systemctl restart sliver-monitor.service
   ```

3. **View detailed logs:**
   ```bash
   sudo journalctl -u sliver-monitor.service -f
   ```

---

**Still having issues?** Open an issue on GitHub with:
- Error messages from logs
- Steps to reproduce
- Environment details (OS, Python version, n8n version)
