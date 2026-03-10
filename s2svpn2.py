import os
import meraki

API_KEY = os.environ.get("MERAKI_DASHBOARD_API_KEY")

if not API_KEY:
    raise RuntimeError("MERAKI_DASHBOARD_API_KEY not set")

dashboard = meraki.DashboardAPI(
    api_key=API_KEY,
    suppress_logging=True
)

orgs = dashboard.organizations.getOrganizations()

for org in orgs:

    org_id = org["id"]
    org_name = org["name"]

    print("\n" + "="*70)
    print(f"Organization: {org_name}")
    print("="*70)

    networks = dashboard.organizations.getOrganizationNetworks(org_id)

    for net in networks:

        net_id = net["id"]
        net_name = net["name"]

        try:
            vpn = dashboard.appliance.getNetworkApplianceVpnSiteToSiteVpn(net_id)
        except meraki.APIError:
            continue  # skip networks without MX

        mode = vpn.get("mode", "disabled")

        print("\n" + "-"*50)
        print(f"Network : {net_name}")
        print(f"VPN Mode: {mode}")

        # Hubs (if spoke)
        if mode == "spoke":
            hubs = vpn.get("hubs", [])
            if hubs:
                print("Hub connections:")
                for hub in hubs:
                    print(f"  Hub ID: {hub['hubId']}")
                    print(f"  Default route: {hub['useDefaultRoute']}")

        # Advertised subnets
        subnets = vpn.get("subnets", [])
        if subnets:
            print("Advertised subnets:")
            for subnet in subnets:
                print(f"  {subnet['localSubnet']} (VPN: {subnet['useVpn']})")

print("\nFinished.")