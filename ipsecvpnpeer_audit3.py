import os
import meraki
from datetime import datetime

API_KEY = os.environ.get("MERAKI_DASHBOARD_API_KEY")
if not API_KEY:
    raise RuntimeError("MERAKI_DASHBOARD_API_KEY not set")

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"s2svpnconfig_{timestamp}.txt"

f = open(filename, "w")
def log(line=""):
    print(line)
    f.write(line + "\n")

def normalize(value):
    if not value:
        return []
    if isinstance(value, list):
        return [v.lower() for v in value if isinstance(v, str)]
    if isinstance(value, str):
        return [value.lower()]
    return []

def extract_group_number(group):
    try:
        return int(group.replace("group", ""))
    except:
        return None

def check_compliance(policies):
    issues = []
    enc = normalize(policies.get("ikeCipherAlgo"))
    auth = normalize(policies.get("ikeAuthAlgo"))
    child_enc = normalize(policies.get("childCipherAlgo"))
    child_auth = normalize(policies.get("childAuthAlgo"))
    dh = policies.get("ikeDiffieHellmanGroup")
    pfs = policies.get("childPfsGroup")

    if enc and not any("aes256" in e for e in enc):
        issues.append("Weak Phase1 encryption")
    if child_enc and not any("aes256" in e for e in child_enc):
        issues.append("Weak Phase2 encryption")
    if any(h in ["sha1", "md5"] for h in auth):
        issues.append("Weak Phase1 hash")
    if any(h in ["sha1", "md5"] for h in child_auth):
        issues.append("Weak Phase2 hash")

    dh_num = extract_group_number(dh) if dh else None
    if dh_num and dh_num < 14:
        issues.append("Weak DH group (Phase1)")
    pfs_num = extract_group_number(pfs) if pfs else None
    if pfs_num and pfs_num < 14:
        issues.append("Weak PFS group (Phase2)")
    if not pfs:
        issues.append("PFS disabled")

    return issues

dashboard = meraki.DashboardAPI(api_key=API_KEY, suppress_logging=True)

orgs = dashboard.organizations.getOrganizations()

for org in orgs:

    org_id = org["id"]
    org_name = org["name"]

    try:
        peers_resp = dashboard.appliance.getOrganizationApplianceVpnThirdPartyVPNPeers(org_id)
        statuses = dashboard.appliance.getOrganizationApplianceVpnStatuses(org_id, total_pages='all')
    except meraki.APIError:
        continue

    peers = peers_resp.get("peers", [])
    active_peers = [p for p in peers if p.get("ipsecPolicies")]
    if not active_peers:
        continue

    log("\n" + "="*70)
    log(f"Organization: {org_name}")
    log("="*70)

    # Build mapping of network VPN statuses
    vpn_status_map = {}
    for net_status in statuses:
        net_id = net_status.get("networkId")
        # For each third party peer record in this network, capture reachability
        third_peers = net_status.get("thirdPartyVpnPeers", [])
        vpn_status_map[net_id] = third_peers

    for peer in active_peers:

        policies = peer.get("ipsecPolicies", {}) or {}
        issues = check_compliance(policies)

        # Identify which networks list this third-party peer
        peer_ip = peer.get("publicIp")
        connected = []

        for net_id, third_peers in vpn_status_map.items():
            for tvp in third_peers:
                if tvp.get("publicIp") == peer_ip:
                    connected.append(f"{tvp.get('name')} ({tvp.get('reachability')})")

        net_display = ", ".join(connected) if connected else "No active VPN status found for this peer"

        log("\n" + "-"*50)
        log(f"Peer Name       : {peer.get('name')}")
        log(f"Public IP       : {peer_ip}")
        log(f"Private Subnets : {peer.get('privateSubnets')}")
        log(f"Peer active on  : {net_display}")

        # Phase 1
        log("\nPhase 1 (IKE):")
        log(f"  Encryption : {policies.get('ikeCipherAlgo')}")
        log(f"  Auth       : {policies.get('ikeAuthAlgo')}")
        log(f"  DH Group   : {policies.get('ikeDiffieHellmanGroup')}")
        log(f"  Lifetime   : {policies.get('ikeLifetime')}")

        # Phase 2
        log("\nPhase 2 (IPsec):")
        log(f"  Encryption : {policies.get('childCipherAlgo')}")
        log(f"  Auth       : {policies.get('childAuthAlgo')}")
        log(f"  PFS Group  : {policies.get('childPfsGroup')}")
        log(f"  Lifetime   : {policies.get('childLifetime')}")

        log("\nCompliance Check:")
        if not issues:
            log("  STATUS: OK")
        else:
            log("  STATUS: WEAK CONFIG")
            for issue in issues:
                log(f"   - {issue}")

        log("-"*50)

log("\nFinished.")
f.close()
print(f"\nOutput written to: {filename}")
