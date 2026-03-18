import os
import meraki
from datetime import datetime

API_KEY = os.environ.get("MERAKI_DASHBOARD_API_KEY")

if not API_KEY:
    raise RuntimeError("MERAKI_DASHBOARD_API_KEY not set")

# Create timestamped filename
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"s2svpnconfig_{timestamp}.txt"

# Open file
f = open(filename, "w")

def log(line=""):
    print(line)
    f.write(line + "\n")

dashboard = meraki.DashboardAPI(
    api_key=API_KEY,
    suppress_logging=True
)

orgs = dashboard.organizations.getOrganizations()

for org in orgs:

    org_id = org["id"]
    org_name = org["name"]

    log("\n" + "="*70)
    log(f"Organization: {org_name}")
    log("="*70)

    networks = dashboard.organizations.getOrganizationNetworks(org_id)

    for net in networks:

        net_id = net["id"]
        net_name = net["name"]

        try:
            vpn = dashboard.appliance.getNetworkApplianceVpnSiteToSiteVpn(net_id)
        except meraki.APIError:
            continue  # skip networks without MX

        mode = vpn.get("mode", "disabled")

        log("\n" + "-"*50)
        log(f"Network : {net_name}")
        log(f"VPN Mode: {mode}")

        # Hubs (if spoke)
        if mode == "spoke":
            hubs = vpn.get("hubs", [])
            if hubs:
                log("Hub connections:")
                for hub in hubs:
                    log(f"  Hub ID: {hub['hubId']}")
                    log(f"  Default route: {hub['useDefaultRoute']}")

        # Advertised subnets
        subnets = vpn.get("subnets", [])
        if subnets:
            log("Advertised subnets:")
            for subnet in subnets:
                log(f"  {subnet['localSubnet']} (VPN: {subnet['useVpn']})")

log("\nFinished.")

f.close()

print(f"\nOutput written to: {filename}")