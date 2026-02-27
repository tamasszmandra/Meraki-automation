import os
import meraki
import smtplib
from email.message import EmailMessage

# -------------------------
# Environment variables
# -------------------------

API_KEY = os.environ.get("MERAKI_DASHBOARD_API_KEY")
GMAIL_USERNAME = os.environ.get("GMAIL_USERNAME")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ALERT_RECIPIENT = os.environ.get("ALERT_RECIPIENT")

if not all([API_KEY, GMAIL_USERNAME, GMAIL_APP_PASSWORD, ALERT_RECIPIENT]):
    raise RuntimeError("Missing required environment variables")

dashboard = meraki.DashboardAPI(api_key=API_KEY, suppress_logging=True)

# -------------------------
# Build device inventory + status maps
# -------------------------

device_inventory = {}
device_status_map = {}

orgs = dashboard.organizations.getOrganizations()

for org in orgs:
    org_id = org["id"]

    # Inventory
    devices = dashboard.organizations.getOrganizationDevices(org_id)
    for d in devices:
        device_inventory[d["serial"]] = {
            "name": d.get("name", "N/A"),
            "model": d.get("model", "N/A"),
            "networkId": d.get("networkId")
        }

    # Status
    statuses = dashboard.organizations.getOrganizationDevicesStatuses(org_id)
    for s in statuses:
        device_status_map[s["serial"]] = s.get("status", "unknown")

# -------------------------
# Fetch current Assurance alerts
# -------------------------

active_alerts = []

for org in orgs:
    org_id = org["id"]
    org_name = org["name"]

    alerts = dashboard.organizations.getOrganizationAssuranceAlerts(org_id)

    for alert in alerts:

        network_name = alert.get("network", {}).get("name", "N/A")
        severity = alert.get("severity", "N/A")
        alert_type = alert.get("type", "N/A")
        first_occurred = alert.get("startedAt", "N/A")

        devices_in_scope = alert.get("scope", {}).get("devices", [])

        if not devices_in_scope:
            # No device listed → still report network-level alert
            active_alerts.append({
                "org": org_name,
                "network": network_name,
                "severity": severity,
                "type": alert_type,
                "serial": "N/A",
                "model": "N/A",
                "name": "Unknown Device",
                "device_state": "N/A",
                "firstOccurredAt": first_occurred
            })
        else:
            for d in devices_in_scope:
                serial = d.get("serial", "N/A")
                name = d.get("name", "N/A")
                model = d.get("productType", "N/A")
                device_state = device_status_map.get(serial, "unknown")

                active_alerts.append({
                    "org": org_name,
                    "network": network_name,
                    "severity": severity,
                    "type": alert_type,
                    "serial": serial,
                    "model": model,
                    "name": name,
                    "device_state": device_state,
                    "firstOccurredAt": first_occurred
                })

# -------------------------
# Exit if no alerts
# -------------------------

if not active_alerts:
    print("No active alerts.")
    exit()

# -------------------------
# Build email body
# -------------------------

lines = []
lines.append(f"CURRENT ACTIVE MERAKI ALERTS: {len(active_alerts)}\n")

for a in active_alerts:
    lines.append(f"Organization : {a['org']}")
    lines.append(f"Network      : {a['network']}")
    lines.append(f"Severity     : {a['severity']}")
    lines.append(f"Alert Type   : {a['type']}")
    lines.append(f"Device Name  : {a['name']}")
    lines.append(f"Model        : {a['model']}")
    lines.append(f"Serial       : {a['serial']}")
    lines.append(f"Device State : {a['device_state']}")
    lines.append(f"First Seen   : {a['firstOccurredAt']}")
    lines.append("-" * 60)

body = "\n".join(lines)
subject = f"[STATUS] Current Meraki Alerts ({len(active_alerts)})"

# -------------------------
# Send email
# -------------------------

msg = EmailMessage()
msg["From"] = GMAIL_USERNAME
msg["To"] = ALERT_RECIPIENT
msg["Subject"] = subject
msg.set_content(body)

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
    server.send_message(msg)

print(f"Email sent with {len(active_alerts)} active alerts.")