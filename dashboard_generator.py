#!/usr/bin/env python3
import subprocess
import re
import requests
import yaml
import time
import os
import logging
import http.server
import socketserver
import threading
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)

CONFIG_FILE = "config.yaml"
OUTPUT_FILE = "index.html"

# HTML Template provided by user (Modified with Placeholders)
HTML_TEMPLATE = """<!DOCTYPE html>
<html class="dark" lang="pl"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            colors: {
              "primary": "#257bf4",
              "background-light": "#f5f7f8",
              "background-dark": "#0a0f18",
            },
            fontFamily: {
              "display": ["Space Grotesk", "sans-serif"]
            },
            borderRadius: {"DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px"},
          },
        },
      }
    </script>
<style>
        .glass-card {
            background: rgba(0, 20, 40, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 255, 0.3);
            position: relative;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .glass-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent, rgba(0, 255, 255, 0.1), transparent);
            transform: translateX(-100%);
            transition: 0.5s;
        }
        .glass-card:hover::before {
            transform: translateX(100%);
        }
        .glass-card:hover {
            border-color: #0ff;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.4), inset 0 0 10px rgba(0, 255, 255, 0.2);
            transform: scale(1.02) translateY(-5px);
        }
        .plasma-border-cyan { border: 1px solid #0ff; box-shadow: 0 0 10px #0ff, inset 0 0 5px #0ff; }
        .plasma-border-magenta { border: 1px solid #f0f; box-shadow: 0 0 10px #f0f, inset 0 0 5px #f0f; }
        .plasma-border-lime { border: 1px solid #0f0; box-shadow: 0 0 10px #0f0, inset 0 0 5px #0f0; }
        
        .neon-text-cyan { text-shadow: 0 0 10px #0ff, 0 0 20px #0ff; color: #0ff; }
        .neon-text-magenta { text-shadow: 0 0 10px #f0f, 0 0 20px #f0f; color: #f0f; }
        .neon-text-lime { text-shadow: 0 0 10px #0f0, 0 0 20px #0f0; color: #0f0; }

        .matrix-bg {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(rgba(0,0,0,0.9), rgba(0,0,0,0.9)), url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMDAzMzAwIiBzdHJva2Utd2lkdGg9IjEiPjxwYXRoIGQ9Ik0wIDQwTDQwIDAiLz48cGF0aCBkPSJNMCAwTDQwIDQwIi8+PC9nPjwvc3ZnPg==');
            z-index: -2;
        }
        .scanlines {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            background-size: 100% 4px, 3px 100%;
            pointer-events: none;
            z-index: -1;
        }
        @keyframes scan {
            from { top: -100%; } to { top: 100%; }
        }
        .scanline-move {
            position: fixed;
            width: 100%; height: 100px;
            background: linear-gradient(to bottom, transparent, rgba(0, 255, 255, 0.05), transparent);
            animation: scan 8s linear infinite;
            z-index: -1;
        }
    </style>
</head>
<body class="bg-black font-display text-white antialiased selection:bg-cyan-500/30 min-h-screen overflow-x-hidden">
<div class="matrix-bg"></div><div class="scanlines"></div><div class="scanline-move"></div>

<!-- Top Status Bar -->
<div class="w-full px-6 pt-8 pb-4 flex justify-between items-center max-w-5xl mx-auto">
<div class="flex items-center gap-3">
<div class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#0ff]"></div>
<span class="text-xs font-bold tracking-[0.3em] uppercase text-cyan-400 neon-text-cyan">Dashboard // System Active</span>
</div>
<div class="text-[10px] font-mono opacity-40 uppercase tracking-widest hidden sm:block">
            Last Scan: %%LAST_SCAN%%
        </div>
</div>

<main class="max-w-5xl mx-auto px-6 pb-20 space-y-10">

<!-- 1. AI Section -->
<section class="relative">
<div class="flex items-center gap-4 mb-6">
<h2 class="text-sm font-bold tracking-[0.3em] uppercase neon-text-cyan">[ 01 // CORE_AI_ENGINE ]</h2>
<div class="h-[2px] flex-1 bg-gradient-to-r from-[#0ff] to-transparent opacity-50"></div>
</div>
<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
%%AI_ITEMS%%
</div>
</section>

<!-- 2. Management Section (System) -->
<section>
<div class="flex items-center gap-4 mb-6">
<h2 class="text-sm font-bold tracking-[0.3em] uppercase neon-text-magenta">[ 02 // SYS_MANAGEMENT ]</h2>
<div class="h-[2px] flex-1 bg-gradient-to-r from-[#f0f] to-transparent opacity-50"></div>
</div>
<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
%%SYSTEM_ITEMS%%
</div>
</section>

<!-- 3. Storage Section (Pliki) -->
<section>
<div class="flex items-center gap-4 mb-6">
<h2 class="text-sm font-bold tracking-[0.3em] uppercase neon-text-lime">[ 03 // DATA_STORAGE ]</h2>
<div class="h-[2px] flex-1 bg-gradient-to-r from-[#0f0] to-transparent opacity-50"></div>
</div>
<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
%%STORAGE_ITEMS%%
</div>
</section>

</main>
</body></html>"""

ITEM_TEMPLATE_CYAN = """
<a class="glass-card plasma-border-cyan rounded-lg p-5 flex flex-col gap-3 group" href="{url}" target="_blank">
<span class="material-symbols-outlined text-[#0ff] group-hover:animate-pulse">{icon}</span>
<div class="space-y-1">
<p class="text-xs font-bold uppercase tracking-wider">{name}</p>
<p class="text-[9px] text-cyan-400/60 font-mono">{subtitle}</p>
</div>
</a>"""

ITEM_TEMPLATE_MAGENTA = """
<a class="glass-card plasma-border-magenta rounded-lg p-5 flex flex-col gap-3 group" href="{url}" target="_blank">
<span class="material-symbols-outlined text-[#f0f] group-hover:animate-pulse">{icon}</span>
<div class="space-y-1">
<p class="text-xs font-bold uppercase tracking-wider">{name}</p>
<p class="text-[9px] text-magenta-400/60 font-mono">{subtitle}</p>
</div>
</a>"""

ITEM_TEMPLATE_LIME = """
<a class="glass-card plasma-border-lime rounded-lg p-5 flex flex-col gap-3 group" href="{url}" target="_blank">
<span class="material-symbols-outlined text-[#0f0] group-hover:animate-pulse">{icon}</span>
<div class="space-y-1">
<p class="text-xs font-bold uppercase tracking-wider">{name}</p>
<p class="text-[9px] text-lime-400/60 font-mono">{subtitle}</p>
</div>
</a>"""

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

    # Flaga -p (procesy) może powodować błędy na systemach ze zdalnym użytkownikiem NIE-root.
    # Używamy jej tylko lokalnie lub gdy zdalny to root.
    use_process_flag = is_local or (ssh_user == 'root')

    if is_local:
        cmd = ["ss", "-t", "-l", "-n"] + (["-p"] if use_process_flag else [])
    else:
        cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", f"{ssh_user}@{host}", "ss", "-t", "-l", "-n"] + (["-p"] if use_process_flag else [])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            logging.error(f"Failed to run ss command on {host} (Code {res.returncode}): {res.stderr.strip()}")
            return []

        
        ports = []
        for line in res.stdout.splitlines():
            if "LISTEN" not in line: continue
            parts = line.split()
            if len(parts) < 4: continue
            
            local_addr = parts[3]
            if ':' not in local_addr: continue
            addr, port_str = local_addr.rsplit(':', 1)
            if addr in ['127.0.0.1', '::1', 'localhost']: continue
            
            # Extract process name if present
            process_name = "System"
            if len(parts) > 5:
                # e.g. users:(("nginx",pid=123,fd=6))
                match = re.search(r'users:\(\(\"([^\"]+)\"', line)
                if match:
                    process_name = match.group(1).capitalize()

            try:
                port = int(port_str)
                ports.append({'port': port, 'process': process_name})
            except ValueError:
                continue
        return ports
    except Exception as e:
        logging.error(f"Error scanning ports for {host}: {e}")
        return []


def get_page_title(host, port, fallback_name="Service"):
    url = f"http://{host}:{port}"
    try:
        res = requests.get(url, timeout=2)
        # Zezwalamy na każdy status code (nawet 4xx/5xx - jeśli jest odpowiedź, to strona istnieje)
        html = res.text
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            # Czyścimy z białych znaków
            return " ".join(title.split())
        return fallback_name if fallback_name else f"Port {port}"
    except Exception as e:
        logging.info(f"Skipped {url} due to error: {e}")
    return None


def categorize_service(name):
    name_lower = name.lower()
    
    # AI Keywords
    ai_keywords = ['webui', 'chat', 'ollama', 'ai', 'gpt', 'rag', 'crawler', 'psychology', 'llm']
    if any(k in name_lower for k in ai_keywords):
        return 'AI', 'psychology'
        
    # Storage/Pliki Keywords
    storage_keywords = ['cloud', 'sync', 'drive', 'storage', 'gokapi', 'backup', 'file', 'pliki', 'share', 'files']
    if any(k in name_lower for k in storage_keywords):
        return 'Storage', 'cloud_sync'
        
    # Default: System
    return 'System', 'terminal'

def generate_dashboard(services_by_category):
    ai_html = ""
    system_html = ""
    storage_html = ""

    for cat, items in services_by_category.items():
        for item in items:
            name = item['name']
            url = item['url']
            subtitle = item['subtitle']
            icon = item['icon']

            if cat == 'AI':
                ai_html += ITEM_TEMPLATE_CYAN.format(name=name, url=url, subtitle=subtitle, icon=icon)
            elif cat == 'Storage':
                storage_html += ITEM_TEMPLATE_LIME.format(name=name, url=url, subtitle=subtitle, icon=icon)
            else: # System
                system_html += ITEM_TEMPLATE_MAGENTA.format(name=name, url=url, subtitle=subtitle, icon=icon)

    # Fill sections if empty with placeholder/message
    if not ai_html: ai_html = "<div class='text-xs opacity-50'>Brak usług AI</div>"
    if not system_html: system_html = "<div class='text-xs opacity-50'>Brak usług Systemu</div>"
    if not storage_html: storage_html = "<div class='text-xs opacity-50'>Brak usług Storage</div>"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = HTML_TEMPLATE.replace("%%AI_ITEMS%%", ai_html)
    html = html.replace("%%SYSTEM_ITEMS%%", system_html)
    html = html.replace("%%STORAGE_ITEMS%%", storage_html)
    html = html.replace("%%LAST_SCAN%%", now_str)

    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    logging.info(f"Dashboard generated in {OUTPUT_FILE}")

def run_web_server(port):
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return # Silence logs

    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        logging.info(f"Dashboard HTTP Server running on port {port}")
        httpd.serve_forever()

def main():
    config = load_config()
    if not config: return

    port = config.get('server_port', 8080)
    scan_interval = config.get('scan_interval', 60)
    exclude_ports = config.get('exclude_ports', [])

    # Start Web Server in a background thread
    server_thread = threading.Thread(target=run_web_server, args=(port,), daemon=True)
    server_thread.start()

    while True:
        logging.info("Starting Scan Cycle...")
        services_by_cat = {'AI': [], 'System': [], 'Storage': []}

        for node in config.get('nodes', []):
            host = node['host']
            node_name = node['name']
            ports = get_open_ports(node)

            for port_data in ports:
                port_num = port_data['port']
                process_name = port_data['process']
                if port_num in exclude_ports: continue
                
                logging.info(f"Checking port {port_num} ({process_name}) on {host}...")
                title = get_page_title(host, port_num, fallback_name=process_name)
                if title:
                    cat, icon = categorize_service(title)
                    services_by_cat[cat].append({
                        'name': title,
                        'url': f"http://{host}:{port_num}",
                        'subtitle': f"{node_name} | Port: {port_num}",
                        'icon': icon
                    })

        generate_dashboard(services_by_cat)
        logging.info(f"Sleeping for {scan_interval} seconds.")
        time.sleep(scan_interval)

if __name__ == "__main__":
    main()

