#!/usr/bin/env python3
import subprocess
import re
import requests
import yaml
import time
import os
import shutil
import logging
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("homer_updater.log"),
        logging.StreamHandler()
    ]
)

CONFIG_FILE = "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        logging.error(f"Configuration file {CONFIG_FILE} not found!")
        return None
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading config.yaml: {e}")
        return None

def get_open_ports(node):
    host = node['host']
    is_local = node.get('is_local', False)
    ssh_user = node.get('ssh_user', 'root')

    if is_local:
        logging.info(f"Scanning LOCAL node: {host}")
        cmd = ["ss", "-t", "-l", "-n"]
    else:
        logging.info(f"Scanning REMOTE node via SSH: {host} (User: {ssh_user})")
        # -o ConnectTimeout=5 to fail fast if SSH is down
        cmd = ["ssh", "-o", "ConnectTimeout=5", f"{ssh_user}@{host}", "ss", "-t", "-l", "-n"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            logging.error(f"Failed to run ss command on {host}: {res.stderr.strip()}")
            return []
        
        ports = set()
        logging.info(f"Raw output lines count from {host}: {len(res.stdout.splitlines())}")
        for line in res.stdout.splitlines():
            if "LISTEN" not in line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            local_addr = parts[3]
            if ':' not in local_addr:
                continue
            # rsplit from right once, to get addr and port
            addr, port_str = local_addr.rsplit(':', 1)
            # Filter out local loopbacks
            if addr in ['127.0.0.1', '::1', 'localhost']:
                continue
            try:
                port = int(port_str)
                ports.add(port)
            except ValueError:
                continue
        return list(ports)
    except subprocess.TimeoutExpired:
        logging.error(f"SSH Command Timeout for {host}")
        return []
    except Exception as e:
        logging.error(f"Error scanning ports for {host}: {e}")
        return []

def get_page_title(host, port):
    url = f"http://{host}:{port}"
    try:
        # Timeout 2 seconds to fail fast
        res = requests.get(url, timeout=2)
        if res.status_code >= 200 and res.status_code < 400:
            html = res.text
            # Use regex for title extraction
            match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Clean up title: remove newlines/tabs
                title = " ".join(title.split())
                if title:
                    return title
            # Fallback title if title empty or missing
            return f"App on Port {port}"
    except requests.exceptions.Timeout:
        logging.debug(f"Timeout checking {url}")
    except requests.exceptions.ConnectionError:
        logging.debug(f"Connection error checking {url}")
    except Exception as e:
        logging.debug(f"Error reading {url}: {e}")
    return None

def update_homer_config(homer_config_path, discovered_services):
    if not os.path.exists(homer_config_path):
        logging.error(f"Homer config file not found at {homer_config_path}")
        return False

    try:
        # Backup existing
        backup_path = f"{homer_config_path}.bak"
        shutil.copyfile(homer_config_path, backup_path)
        logging.info(f"Created backup of config.yml at {backup_path}")

        # Load existing
        with open(homer_config_path, 'r') as f:
            homer_config = yaml.safe_load(f) or {}

        # Prepare new services list
        existing_services = homer_config.get('services', [])
        new_services = []
        
        # Keep existing groups that are NOT managed by us (name doesn't match node name)
        managed_node_names = list(discovered_services.keys())
        for group in existing_services:
            if group.get('name') not in managed_node_names:
                new_services.append(group)

        # Add/Update managed groups
        for node_name, items in discovered_services.items():
            if not items:
                continue
            service_group = {
                "name": node_name,
                "icon": "fas fa-server",
                "items": []
            }
            for item in items:
                service_group["items"].append({
                    "name": item["name"],
                    "url": item["url"],
                    "subtitle": f"Port: {item['port']}",
                    "tag": "auto",
                    "target": "_blank"
                })
            new_services.append(service_group)

        # Update section
        homer_config['services'] = new_services


        # Save back
        with open(homer_config_path, 'w') as f:
            yaml.dump(homer_config, f, sort_keys=False, default_flow_style=False)
        
        logging.info(f"Successfully updated Homer config with {sum(len(items) for items in discovered_services.values())} items")
        return True

    except Exception as e:
        logging.error(f"Error updating Homer config: {e}")
        return False

def main():
    logging.info("Homer Auto Updater Started")
    config = load_config()
    if not config:
        return

    homer_config_path = config.get('homer_config_path', "/opt/homer/assets/config.yml")
    scan_interval = config.get('scan_interval', 60)
    exclude_ports = config.get('exclude_ports', [])

    while True:
        logging.info("Starting Scan Cycle...")
        discovered_services = {}

        for node in config.get('nodes', []):
            node_name = node['name']
            host = node['host']
            ports = get_open_ports(node)
            
            node_items = []
            for port in ports:
                if port in exclude_ports:
                    logging.debug(f"Skipping excluded port {port} on {host}")
                    continue
                
                logging.info(f"Checking port {port} on {host}...")
                title = get_page_title(host, port)
                if title:
                    logging.info(f"Discovered: {title} at {host}:{port}")
                    node_items.append({
                        "name": title,
                        "port": port,
                        "url": f"http://{host}:{port}"
                    })

            discovered_services[node_name] = node_items

        if any(discovered_services.values()):
            update_homer_config(homer_config_path, discovered_services)
        else:
            logging.warning("No services discovered in this cycle.")

        logging.info(f"Sleeping for {scan_interval} seconds.")
        time.sleep(scan_interval)

if __name__ == "__main__":
    main()
