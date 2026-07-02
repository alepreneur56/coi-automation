# COI Automation — Server Runbook

Plain-English operations guide for running the COI automation on a small
cloud server (Hetzner or DigitalOcean) instead of the Mac. No developer
knowledge assumed — every command here is copy-paste.

Throughout this doc, replace `SERVER_IP` with your server's IP address
(you get it when you create the server; write it down).

---

## Quick reference

| I want to... | Command (from the Mac) |
|---|---|
| Check it's alive | `ssh coi@SERVER_IP systemctl status coi-automation` |
| Watch it live | `ssh coi@SERVER_IP journalctl -u coi-automation -f` (Ctrl-C to stop) |
| Deploy a change | `cd ~/coi-automation && git push origin main && deploy/deploy.sh coi@SERVER_IP` |
| Undo the last deploy | `deploy/deploy.sh --rollback coi@SERVER_IP` |
| Stop the loop | `ssh coi@SERVER_IP sudo systemctl stop coi-automation` |
| Start the loop | `ssh coi@SERVER_IP sudo systemctl start coi-automation` |
| Restart (after .env edit) | `ssh coi@SERVER_IP sudo systemctl restart coi-automation` |

---

## The one rule: ONLY ONE POLLER, EVER

The Mac copy and the server copy watch the **same mailbox**
(admin@clientpolicyhelp.com). If both are running, every client email gets
processed twice — two replies, two PDFs, twice the confusion, twice the API
cost. The scripts check for this where they can (deploy.sh refuses to run if
the Mac poller is still loaded), but at cutover time the rule is on you:
**stop one before starting the other.** See "Cutover from the Mac" below.

---

## 1. Getting a server (from zero)

You need the smallest Linux server either provider sells. This app is tiny —
one Python process, no website, no database server.

**Before you start**, make sure your Mac has an SSH key. In Terminal:

```
cat ~/.ssh/id_ed25519.pub
```

If that prints a line starting with `ssh-ed25519`, copy it — that's your
public key. If it says "No such file", create one first:
`ssh-keygen -t ed25519` (press Enter through the prompts), then `cat` again.

**Hetzner** (cheapest, ~4-5 EUR/month):
1. console.hetzner.com -> sign up -> New Project -> Add Server
2. Location: any (Ashburn VA is closest to Miami; EU works fine too)
3. Image: **Ubuntu 24.04**
4. Type: shared vCPU — **CX22** (EU) or **CPX11** (US locations). Either is plenty.
5. SSH key: click Add SSH key, paste your public key from above
6. Everything else: defaults. Create & Buy Now. Note the IP address.

**DigitalOcean** (~6 USD/month):
1. digitalocean.com -> Create -> Droplets
2. Region: New York. Image: **Ubuntu 24.04**
3. Size: Basic -> Regular -> the cheapest (1 GB / 1 vCPU is enough)
4. Authentication: SSH key -> New SSH Key -> paste your public key
5. Create Droplet. Note the IP address.

No DNS, no domain, no load balancer — nothing connects TO this server. It
only makes outbound calls (Microsoft Graph + Anthropic). The only open port
you need is SSH, which is on by default.

---

## 2. First-time setup (provisioning)

From the Mac, copy the setup script to the server and run it:

```
scp ~/coi-automation/deploy/provision.sh root@SERVER_IP:/root/provision.sh
ssh root@SERVER_IP bash /root/provision.sh
```

(First connection asks "Are you sure you want to continue connecting?" —
type `yes`.)

**The script will stop partway and print a deploy key.** That's expected.
The server needs read-only access to the private GitHub repo:

1. Copy the `ssh-ed25519 ...` line it printed
2. In a browser: github.com/alepreneur56/coi-automation -> Settings ->
   Deploy keys -> Add deploy key
3. Title: `coi-server`. Paste the key. Leave **"Allow write access"
   UNCHECKED** (the server only ever pulls).
4. Add key, then run the same ssh command again:

```
ssh root@SERVER_IP bash /root/provision.sh
```

It picks up where it left off and ends with a checklist. The script is safe
to re-run any number of times.

---

## 3. Move the secrets (.env)

The `.env` file holds the Azure and Anthropic credentials. It is **never in
git** — it moves by hand, once:

```
scp ~/coi-automation/.env coi@SERVER_IP:/opt/coi-automation/.env
ssh coi@SERVER_IP chmod 600 /opt/coi-automation/.env
```

Also recommended — copy the COI history database (it powers the
address-autofill hints; without it the server starts with a blank memory):

```
scp ~/coi-automation/data/coi_history.db coi@SERVER_IP:/opt/coi-automation/data/
```

And set the server clock to Eastern time (the 8am daily digest and log
rotation run on server-local time):

```
ssh root@SERVER_IP timedatectl set-timezone America/New_York
```

---

## 4. First start

Verify everything before starting the loop:

```
ssh root@SERVER_IP "sudo -H -u coi /opt/coi-automation/.venv/bin/python /opt/coi-automation/main.py --check"
```

You want to see all six checks pass (config, prompt, templates, Graph token,
mailbox read, Anthropic API). If one fails, the message says which credential
is wrong — fix `.env` and re-run.

Then do the cutover (next section) before starting the service.

---

## 5. Cutover from the Mac (decommission the Mac copy)

Do these steps **in this order**, back to back — the whole thing takes two
minutes.

**Step 1 — stop the Mac poller** (on the Mac):

```
launchctl unload ~/Library/LaunchAgents/com.alepreneur.coi-automation.plist
rm ~/Library/LaunchAgents/com.alepreneur.coi-automation.plist
~/coi-automation/start.sh stop
pgrep -fl main.py
```

The last command must print **nothing**. Deleting the plist matters: without
it, the poller silently comes back the next time you log in to the Mac.

**Step 2 — carry the watermark over** (so no email falls in the gap and no
old email gets re-processed):

```
scp ~/coi-automation/state/runtime_state.json coi@SERVER_IP:/opt/coi-automation/state/
```

**Step 3 — start the server**:

```
ssh coi@SERVER_IP sudo systemctl start coi-automation
ssh coi@SERVER_IP journalctl -u coi-automation -f
```

You should see a `startup mailbox=admin@clientpolicyhelp.com ...` line within
a few seconds, then quiet 60-second polling.

**Step 4 — prove it works**: send a test COI request to the mailbox and
watch the journal process it. If `TEST_MODE=true` in the server's `.env`,
the reply comes to your Gmail instead of the client — a good way to run the
first day safely, then flip to `false` and
`sudo systemctl restart coi-automation`.

The Mac copy of the folder can stay as your working checkout for making
changes — just never run `main.py` or `start.sh` on it again.

---

## 6. Deploying a change

All changes flow Mac -> GitHub -> server. Edit on the Mac, then:

```
cd ~/coi-automation
git add -A && git commit -m "what changed"
git push origin main
deploy/deploy.sh coi@SERVER_IP
```

deploy.sh does the rest: pulls on the server, reinstalls packages only if
`requirements.txt` changed, runs `main.py --check`, restarts the service,
confirms a clean startup line in the log, and confirms the service is the
only poller running. If ANY step fails it stops and says so — the safest
response to a failed deploy is `deploy/deploy.sh --rollback coi@SERVER_IP`.

It also refuses to start if it detects the poller still running on your Mac.

---

## 7. Reading logs

Two places, same events:

**The journal** (managed by the OS; where crashes and restarts show up):

```
ssh coi@SERVER_IP journalctl -u coi-automation -f            # live tail
ssh coi@SERVER_IP journalctl -u coi-automation --since today # today's activity
ssh coi@SERVER_IP journalctl -u coi-automation -n 200        # last 200 lines
```

**The app's own JSONL logs** (one JSON object per event, one file per day,
auto-deleted after 60 days):

```
ssh coi@SERVER_IP "tail -50 /opt/coi-automation/logs/coi-$(date +%Y-%m-%d).jsonl"
ssh coi@SERVER_IP "grep processing_error /opt/coi-automation/logs/*.jsonl"
```

Useful event names to grep for: `processing_start`, `classified`,
`action_decided`, `send_result`, `processing_error`, `poll_error`.

You also still get the built-in email ops: the daily 8am digest and
immediate error alert emails keep working exactly as on the Mac.

---

## 8. Is it alive? Stop / start / restart

```
ssh coi@SERVER_IP systemctl status coi-automation    # "active (running)" = good
ssh coi@SERVER_IP sudo systemctl stop coi-automation
ssh coi@SERVER_IP sudo systemctl start coi-automation
ssh coi@SERVER_IP sudo systemctl restart coi-automation
```

The service restarts itself automatically if it crashes (backing off from 5
seconds up to 5 minutes between attempts, forever) and starts automatically
when the server reboots. Any change to `.env` needs a manual `restart` to
take effect.

Quick health test any time: send a COI request to the mailbox and watch the
journal.

---

## 9. Rolling back a bad deploy

```
deploy/deploy.sh --rollback coi@SERVER_IP
```

This resets the server's code to the commit it was on just before the last
deploy, reinstalls the packages for that commit, restarts, and verifies
startup. It goes one step back (the most recent deploy only). For anything
older, fix forward: on the Mac, `git revert` the bad commit, push, deploy.

---

## 10. When the Azure client secret expires

The Azure app secret was created **2026-07-02** and lives 24 months, so it
dies **around July 2, 2028**. Put a calendar reminder for **June 1, 2028**
right now.

**What expiry looks like:** error alert emails about "Graph token", the
journal fills with `poll_error` lines, and `main.py --check` fails at step 4.
The service keeps running but can't read or send mail.

**The fix (10 minutes):**

1. portal.azure.com -> Microsoft Entra ID -> App registrations -> the COI
   app -> Certificates & secrets -> **New client secret** (24 months)
2. Copy the **Value** column immediately — it's shown exactly once
3. Update the server:

```
ssh coi@SERVER_IP
nano /opt/coi-automation/.env        # replace the AZURE_CLIENT_SECRET line
exit
ssh coi@SERVER_IP sudo systemctl restart coi-automation
ssh root@SERVER_IP "sudo -H -u coi /opt/coi-automation/.venv/bin/python /opt/coi-automation/main.py --check"
```

4. Update the copy in 1Password (and the Mac's `~/coi-automation/.env` if
   you still keep one) so they don't drift.
5. Delete the old expired secret in the Azure portal.

---

## 11. Light server maintenance

Once a month or so:

```
ssh root@SERVER_IP "apt-get update && apt-get upgrade -y"
ssh root@SERVER_IP df -h        # disk usage — the app cleans up after itself
```

If an upgrade wants a reboot: `ssh root@SERVER_IP reboot` — the service is
enabled, so it comes back on its own. Give it two minutes, then check
`systemctl status`.

---

## Appendix: what's where on the server

| Thing | Location |
|---|---|
| App code (git checkout) | `/opt/coi-automation/` |
| Secrets | `/opt/coi-automation/.env` (mode 600, owner coi) |
| Python | `/opt/coi-automation/.venv/bin/python` |
| Daily JSONL logs | `/opt/coi-automation/logs/coi-YYYY-MM-DD.jsonl` |
| Generated PDFs | `/opt/coi-automation/output/` (auto-deleted after 180 days) |
| COI history DB | `/opt/coi-automation/data/coi_history.db` |
| Watermark / run state | `/opt/coi-automation/state/runtime_state.json` |
| Rollback ref | `/opt/coi-automation/state/last_deploy_prev_ref` |
| systemd unit | `/etc/systemd/system/coi-automation.service` |
| Runs as user | `coi` (non-root; sudo only for its own service) |
| GitHub deploy key | `/home/coi/.ssh/id_ed25519` (read-only key) |
