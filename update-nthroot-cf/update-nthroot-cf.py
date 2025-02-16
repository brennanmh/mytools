import requests
import argparse
import os
import configparser

def get_wan_ip():
    # Get the current WAN IP address from ifconfig.me
    response = requests.get('https://ifconfig.me/ip')
    response.raise_for_status()
    return response.text.strip()

def update_dns_record(zone_id, record_id, ip, email, api_key, dry_run=False):
    # Update the DNS record with the new IP address
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key
    }
    data = {
        "type": "A",
        "name": "nthroot.org",
        "content": ip,
        "ttl": 120,
        "proxied": False
    }
    if dry_run:
        # If dry run, print the request details instead of sending it
        print(f"Dry run: would send PUT request to {url} with data {data} and headers {headers}")
        return {"success": True}
    response = requests.put(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def get_record_id(zone_id, email, api_key):
    # Retrieve the record ID for the A record of nthroot.org
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    records = response.json().get("result", [])
    for record in records:
        if record["name"] == "nthroot.org" and record["type"] == "A":
            print(f"Found record ID: {record['id']}")
            return record["id"]

    raise Exception("Record ID not found")

def get_zone_id(email, api_key):
    # Retrieve the zone ID for nthroot.org
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    zones = response.json().get("result", [])
    for zone in zones:
        if zone["name"] == "nthroot.org":
            print(f"Found zone ID: {zone['id']}")
            return zone["id"]
    raise Exception("Zone ID not found")

def has_record_changed(zone_id, record_id, ip, email, api_key):
    # Check if the current DNS record content matches the new IP address
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    record = response.json().get("result", {})
    return record.get("content") != ip

def get_credentials():
    # Retrieve email and API key from environment variables
    email = os.getenv("CLOUDFLARE_EMAIL")
    api_key = os.getenv("CLOUDFLARE_API_KEY")
    if not email or not api_key:
        raise Exception("CLOUDFLARE_EMAIL and CLOUDFLARE_API_KEY environment variables must be set")
    return email, api_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Cloudflare DNS record for nthroot.org")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without making any changes")
    args = parser.parse_args()

    # Retrieve email and API key from environment variables
    EMAIL, API_KEY = get_credentials()
    
    try:
        # Retrieve the zone ID and record ID
        ZONE_ID = get_zone_id(EMAIL, API_KEY)
        RECORD_ID = get_record_id(ZONE_ID, EMAIL, API_KEY)
        # Get the current WAN IP address
        wan_ip = get_wan_ip()
        print(f"Current WAN IP: {wan_ip}")
        
        # Check if the DNS record has changed
        if has_record_changed(ZONE_ID, RECORD_ID, wan_ip, EMAIL, API_KEY):
            # Update the DNS record if it has changed
            result = update_dns_record(ZONE_ID, RECORD_ID, wan_ip, EMAIL, API_KEY, dry_run=args.dry_run)
            if args.dry_run:
                print("Dry run completed successfully")
            else:
                print("DNS record updated successfully:", result)
        else:
            print("DNS record has not changed. No update needed.")
    except Exception as e:
        print(f"An error occurred: {e}")


