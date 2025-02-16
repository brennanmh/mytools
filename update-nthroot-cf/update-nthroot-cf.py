import requests
import argparse
import os
import configparser
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_wan_ip():
    # Get the current WAN IP address from ifconfig.me
    logging.debug("Getting WAN IP address from ifconfig.me")
    response = requests.get('https://ifconfig.me/ip')
    response.raise_for_status()
    ip = response.text.strip()
    logging.debug(f"Retrieved WAN IP: {ip}")
    return ip

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
        logging.info(f"Dry run: would send PUT request to {url} with data {data} and headers {headers}")
        return {"success": True}
    logging.debug(f"Sending PUT request to {url} with data {data} and headers {headers}")
    response = requests.put(url, json=data, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTPError: {e.response.status_code} - {e.response.text}")
        raise
    logging.debug(f"DNS record updated successfully: {response.json()}")
    return response.json()

def get_record_id(zone_id, email, api_key):
    # Retrieve the record ID for the A record of nthroot.org
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key
    }
    logging.debug(f"Sending GET request to {url} with headers {headers}")
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTPError: {e.response.status_code} - {e.response.text}")
        raise
    records = response.json().get("result", [])
    for record in records:
        if record["name"] == "nthroot.org" and record["type"] == "A":
            logging.debug(f"Found record ID: {record['id']}")
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
    logging.debug(f"Sending GET request to {url} with headers {headers}")
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTPError: {e.response.status_code} - {e.response.text}")
        raise
    zones = response.json().get("result", [])
    for zone in zones:
        if zone["name"] == "nthroot.org":
            logging.debug(f"Found zone ID: {zone['id']}")
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
    logging.debug(f"Sending GET request to {url} with headers {headers}")
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTPError: {e.response.status_code} - {e.response.text}")
        raise
    record = response.json().get("result", {})
    logging.debug(f"Current DNS record content: {record.get('content')}, New IP: {ip}")
    return record.get("content") != ip

def get_credentials(config_file=None):
    # Retrieve email and API key from environment variables or config file
    def strip_quotes(value):
        return value.strip('"').strip("'")

    if config_file:
        logging.debug(f"Reading credentials from config file: {config_file}")
        config = configparser.ConfigParser()
        config.read(config_file)
        email = strip_quotes(config.get("cloudflare", "email"))
        api_key = strip_quotes(config.get("cloudflare", "api_key"))
        logging.debug(f"Retrieved email: {email}")
        logging.debug(f"Retrieved API key: {api_key}")
    else:
        logging.debug("Reading credentials from environment variables")
        email = strip_quotes(os.getenv("CLOUDFLARE_EMAIL", ""))
        api_key = strip_quotes(os.getenv("CLOUDFLARE_API_KEY", ""))
        if not email or not api_key:
            raise Exception("CLOUDFLARE_EMAIL and CLOUDFLARE_API_KEY environment variables must be set")
        logging.debug(f"Retrieved email: {email}")
        logging.debug(f"Retrieved API key: {api_key}")
    return email, api_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Cloudflare DNS record for nthroot.org")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without making any changes")
    parser.add_argument('--config', type=str, help="Path to the config file")
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Retrieve email and API key from environment variables or config file
    EMAIL, API_KEY = get_credentials(args.config)
    
    try:
        # Retrieve the zone ID and record ID
        ZONE_ID = get_zone_id(EMAIL, API_KEY)
        RECORD_ID = get_record_id(ZONE_ID, EMAIL, API_KEY)
        # Get the current WAN IP address
        wan_ip = get_wan_ip()
        logging.info(f"Current WAN IP: {wan_ip}")
        
        # Check if the DNS record has changed
        if has_record_changed(ZONE_ID, RECORD_ID, wan_ip, EMAIL, API_KEY):
            # Update the DNS record if it has changed
            result = update_dns_record(ZONE_ID, RECORD_ID, wan_ip, EMAIL, API_KEY, dry_run=args.dry_run)
            if args.dry_run:
                logging.info("Dry run completed successfully")
            else:
                logging.info("DNS record updated successfully")
        else:
            logging.info("DNS record has not changed. No update needed.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


