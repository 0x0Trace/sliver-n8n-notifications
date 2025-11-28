# Security Considerations

## ⚠️ Authorized Use Only

This tool is designed exclusively for:
- **Authorized penetration testing** engagements with written permission
- **Red team operations** within your organization
- **Security research** in controlled environments
- **Educational purposes** in lab environments

**Unauthorized use against systems you don't own or have explicit permission to test is illegal and unethical.**

---

## Before Publishing to GitHub

### Pre-Commit Checklist

Before committing or pushing to GitHub, verify:

- [ ] **n8n_workflow.json is NOT committed** (use template instead)
- [ ] All credential IDs are removed from workflow files
- [ ] Instance ID and workflow ID are replaced with placeholders
- [ ] No Discord webhook URLs in any files
- [ ] No Slack OAuth tokens in any files
- [ ] No Sliver `.cfg` files committed
- [ ] `beacon_state.json` is not committed (may contain target IDs)
- [ ] No actual target hostnames or IP addresses in documentation examples

### Files That Should NEVER Be Committed

```
n8n_workflow.json              # Your personal workflow with real credentials
beacon_state.json              # Contains connection IDs from real targets
~/.sliver-client/configs/*.cfg # Sliver server certificates and keys
.env                           # Environment variables
*credentials*.json             # Any credential files
```

### Safe to Commit

```
n8n_workflow_template.json     # Sanitized template with placeholders
sliver_beacon_monitor.py       # Python script (no secrets)
sliver-monitor.service         # Systemd service (no secrets if paths are generic)
README.md, INSTALLATION.md     # Documentation
```

---

## When Deploying

### Network Security

- [ ] **Restrict n8n to localhost** - Only expose on `127.0.0.1:5678`
- [ ] **Use authentication** if exposing n8n externally (basic auth minimum)
- [ ] **Use HTTPS** for webhook endpoints if accessible over network
- [ ] **Firewall rules** - Block external access to n8n port
- [ ] **VPN access only** - If remote access needed, use VPN

### Example: Restrict n8n to Localhost

```bash
# When starting n8n, bind to localhost only
N8N_HOST=127.0.0.1 n8n start

# Or in environment file
echo "N8N_HOST=127.0.0.1" >> ~/.n8n/.env
```

### Webhook Security

```bash
# Generate random webhook path instead of predictable "sliver-beacon"
WEBHOOK_PATH=$(openssl rand -hex 16)
echo "Use webhook path: $WEBHOOK_PATH"

# Update Python script to use this path
# N8N_WEBHOOK_URL = "http://localhost:5678/webhook/$WEBHOOK_PATH"
```

---

## Credential Management

### Discord Webhooks

**Keep these private:**
- Never commit webhook URLs to Git
- Rotate webhook URLs if accidentally exposed
- Use webhook-specific channels (not general channels)

**If compromised:**
1. Delete the webhook in Discord server settings
2. Create a new webhook with different URL
3. Update n8n workflow credential
4. Check Discord audit log for unauthorized posts

### Slack Tokens

**Token security:**
- Slack tokens start with `xoxb-` (bot tokens) or `xoxp-` (user tokens)
- **Never** commit tokens to Git
- **Never** log tokens in debug output
- Store in n8n credentials only (encrypted at rest)

**If compromised:**
1. Revoke token in Slack API console
2. Generate new token
3. Update n8n credential
4. Review Slack audit logs for unauthorized activity

### Sliver Client Configs

**Critical files:**
```
~/.sliver-client/configs/*.cfg
```

These files contain:
- mTLS client certificates
- Server public keys
- Connection details

**If compromised:**
- Attacker can connect to your Sliver server
- Regenerate client configs immediately
- Rotate server certificates if needed

**Protection:**
```bash
# Restrict permissions
chmod 600 ~/.sliver-client/configs/*.cfg

# Never commit to Git (already in .gitignore)
```

---

## Logging and Monitoring

### Secure Log Files

Monitor logs may contain sensitive information:
- Target hostnames
- Internal IP addresses
- Usernames
- OS versions

**Best practices:**

```bash
# Restrict log file permissions
sudo chmod 640 /var/log/sliver-monitor.log
sudo chown root:adm /var/log/sliver-monitor.log

# Rotate logs regularly
# Add to /etc/logrotate.d/sliver-monitor
/var/log/sliver-monitor.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
}
```

### Monitor Service Logs

```bash
# View logs without saving to file
sudo journalctl -u sliver-monitor.service -f --no-pager

# Limit log retention
sudo journalctl --vacuum-time=7d
```

---

## State File Security

### beacon_state.json

**Contains:**
- Connection IDs from your Sliver server
- Timestamp of when connections were detected

**Security measures:**

```bash
# Restrict permissions
chmod 600 beacon_state.json

# Exclude from backups that go to untrusted locations
# Add to backup exclusion list
```

**If exposed:**
- Low risk: IDs are UUIDs, not directly exploitable
- Medium risk: Reveals you're using Sliver C2
- Consider: Rotate beacon IDs in Sliver if concerned

---

## Running with Least Privilege

### Service User

Instead of running as `root` or your main user:

```bash
# Create dedicated service user
sudo useradd -r -s /bin/false sliver-monitor

# Update service file
sudo nano /etc/systemd/system/sliver-monitor.service

# Change User line:
User=sliver-monitor

# Set file permissions
sudo chown sliver-monitor:sliver-monitor /path/to/sliver_beacon_monitor.py
sudo chown sliver-monitor:sliver-monitor /path/to/beacon_state.json
```

### Python Virtual Environment

```bash
# Create venv owned by service user
sudo -u sliver-monitor python3 -m venv /opt/sliver-monitor/venv

# Install dependencies
sudo -u sliver-monitor /opt/sliver-monitor/venv/bin/pip install sliver-py requests

# Update service ExecStart path
ExecStart=/opt/sliver-monitor/venv/bin/python /opt/sliver-monitor/sliver_beacon_monitor.py
```

---

## Discord/Slack Security

### Message Content

Notifications will contain:
- **Hostname** of compromised system
- **Username** of current user
- **IP address** of target
- **OS and architecture**

**Considerations:**
- Ensure Discord/Slack channels are private
- Limit channel membership to authorized personnel
- Enable 2FA on Discord/Slack accounts
- Use end-to-end encryption where available

### Notification Filtering

Filter sensitive notifications:

```javascript
// In n8n, add IF node after "Format Data"
// Only notify for specific conditions

// Example: Only notify for high-value targets
{{ $json.body.hostname.includes("prod") || $json.body.hostname.includes("server") }}

// Example: Exclude test lab
{{ !$json.body.remote_address.startsWith("192.168.1.") }}
```

---

## Incident Response

### If Credentials Are Compromised

**Immediate actions:**

1. **Revoke all exposed credentials**
   - Discord webhooks → Delete in server settings
   - Slack tokens → Revoke in API console
   - Sliver configs → Regenerate client certs

2. **Assess damage**
   - Check Discord channel history
   - Check Slack audit logs
   - Review Sliver server logs for unauthorized connections

3. **Rotate everything**
   - Generate new webhook URLs
   - Create new Slack app with new token
   - Update n8n workflow with new credentials
   - Consider rotating Sliver server certificates

4. **Review commit history**
   ```bash
   # Check if secrets were committed
   git log -p | grep -i "xoxb-\|discord.com/api/webhooks"

   # If found, use BFG Repo-Cleaner or git-filter-repo
   # to remove from history
   ```

### If n8n Instance Is Compromised

1. **Stop all workflows**
2. **Export critical workflows** (to encrypted backup)
3. **Wipe n8n database**
4. **Reinstall n8n**
5. **Restore workflows from backup**
6. **Regenerate all credentials**

---

## Best Practices Summary

### Development

- ✅ Use `n8n_workflow_template.json` for version control
- ✅ Keep `n8n_workflow.json` in `.gitignore`
- ✅ Never hardcode credentials in scripts
- ✅ Use environment variables for secrets
- ✅ Test in isolated lab environment first

### Production

- ✅ Run n8n on localhost only
- ✅ Use dedicated service user (not root)
- ✅ Restrict log file permissions
- ✅ Enable webhook path randomization
- ✅ Use private Discord/Slack channels
- ✅ Enable 2FA on all accounts
- ✅ Monitor for unauthorized access
- ✅ Regular credential rotation

### Version Control

- ✅ Review commits before pushing
- ✅ Use `.gitignore` properly
- ✅ Never commit `.env` files
- ✅ Never commit `.cfg` files
- ✅ Use sanitized templates for public repos
- ✅ Enable pre-commit hooks for secret scanning

---

## Recommended Tools

### Secret Scanning

```bash
# Install git-secrets
git clone https://github.com/awslabs/git-secrets
cd git-secrets
make install

# Configure for repository
cd /path/to/n8n_sliver_implant_callback
git secrets --install
git secrets --register-aws

# Add custom patterns
git secrets --add 'xoxb-[0-9A-Za-z\-]+'
git secrets --add 'discord\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+'
```

### TruffleHog (Deep History Scan)

```bash
# Install
pip install truffleHog

# Scan repository history
trufflehog --regex --entropy=True file:///path/to/repo
```

---

## Compliance and Legal

### Documentation Requirements

For authorized penetration tests:
- **Scope document** defining authorized targets
- **Rules of engagement** signed by client
- **Data handling procedures** for sensitive findings
- **Incident response plan** if credentials compromised

### Data Retention

- Logs containing target information: Follow engagement SOW
- Notification history: Review retention policies
- State files: Clear after engagement completion

### Reporting

When creating reports:
- **Redact** internal tool configurations
- **Sanitize** webhook URLs and credentials
- **Anonymize** client-specific information
- **Encrypt** reports containing sensitive data

---

## Questions or Concerns?

If you discover a security issue with this project:

1. **Do NOT** open a public GitHub issue
2. **Do NOT** post details in public forums
3. **Contact** the repository maintainer privately
4. **Provide** details of the vulnerability
5. **Allow** reasonable time for fix before disclosure

---

## Legal Disclaimer

This software is provided "as is" without warranty of any kind. Users are solely responsible for ensuring their use complies with all applicable laws and regulations. The authors assume no liability for misuse or unauthorized use of this software.
