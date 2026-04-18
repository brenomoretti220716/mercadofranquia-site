# systemd units — Mercado Franquia (EC2)

Two units power the daily macro-data refresh:

| File | Role |
|---|---|
| `mf-macro-sync.service` | Oneshot job that runs `scripts/run_macro_sync.py`. |
| `mf-macro-sync.timer`   | Fires the service daily at 03:00 America/Sao_Paulo. |

The service has no `[Install]` section — it is never enabled directly.
Enable the **timer**; systemd activates the service each time the timer
fires.

---

## Install

From the repo on the EC2 box (`/home/ubuntu/mercadofranquia-api`):

```bash
sudo cp deploy/ec2/systemd/mf-macro-sync.service /etc/systemd/system/
sudo cp deploy/ec2/systemd/mf-macro-sync.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mf-macro-sync.timer
```

`--now` both enables on boot and starts the timer for the current session,
so the next 03:00 BRT will fire without a reboot.

## Verify

Next scheduled run and last result:

```bash
systemctl list-timers mf-macro-sync.timer
systemctl status mf-macro-sync.timer
```

Expected `list-timers` row shape:

```
NEXT                        LEFT     LAST PASSED UNIT                 ACTIVATES
Sat 2026-04-18 03:00:00 -03 7h left  n/a  n/a    mf-macro-sync.timer  mf-macro-sync.service
```

## Run manually (bypass the timer)

Useful for smoke-testing after a code deploy:

```bash
sudo systemctl start mf-macro-sync.service
# returns when the oneshot exits — blocks for the whole sync (~1-3 min)
systemctl status mf-macro-sync.service
```

## Logs

Tail the live run:

```bash
journalctl -u mf-macro-sync.service -f
```

Last run only:

```bash
journalctl -u mf-macro-sync.service -n 200 --no-pager
```

Last 7 days with timestamps:

```bash
journalctl -u mf-macro-sync.service --since '7 days ago' -o short-iso
```

## Disable temporarily

If you need to pause the timer (e.g. during BCB maintenance):

```bash
sudo systemctl disable --now mf-macro-sync.timer
# later:
sudo systemctl enable --now mf-macro-sync.timer
```

A one-off run remains available via `systemctl start mf-macro-sync.service`
even while the timer is disabled.
