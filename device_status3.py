import os
import meraki
from datetime import datetime, timezone

API_KEY = os.environ.get("MERAKI_DASHBOARD_API_KEY")
if not API_KEY:
    raise RuntimeError("MERAKI_DASHBOARD_API_KEY not set")

dashboard = meraki.DashboardAPI(api_key=API_KEY, suppress_logging=True)

def classify(status):
    if status == "online":
        return "ACTIVE"
    if status == "offline":
        return "FAILURE"
    if status == "dormant":
        return "INACTIVE"
    return "UNKNOWN"

orgs = dashboard.organizations.getOrganizations()

for org in orgs:
    print(f"\n=== Organization: {org['name']} ({org['id']}) ===")

    # Get networks once per org
    networks = dashboard.organizations.getOrganizationNetworks(org["id"])
    net_map = {n["id"]: n["name"] for n in networks}

    # Get all device statuses for the org
    devices = dashboard.organizations.getOrganizationDevicesStatuses(org["id"])

    # Group devices by network
    devices_by_network = {}
    for dev in devices:
        net_id = dev.get("networkId", "Unassigned")
        devices_by_network.setdefault(net_id, []).append(dev)

    # Print devices grouped by network
    for net_id, net_devices in devices_by_network.items():
        net_name = net_map.get(net_id, "Unassigned")
        print(f"\n--- Network: {net_name} ({net_id}) ---")
        print(f"{'Model':8} {'Serial':14} {'Name':20} {'Status':8} {'Last seen'}")
        print("-"*70)

        for dev in net_devices:
            state = classify(dev.get("status"))
            last_seen = dev.get("lastReportedAt")
            if last_seen:
                last_seen = datetime.fromisoformat(last_seen.replace("Z","+00:00")).astimezone(timezone.utc)
                last_seen = last_seen.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                last_seen = "Never"

            print(f"{dev['model']:8} {dev['serial']:14} {dev.get('name','-'):20} {state:8} {last_seen}")
