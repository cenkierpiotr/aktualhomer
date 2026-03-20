# Custom Dynamic Dashboard (Substytut Homera)

Ten skrypt działa jako **samodzielny serwer dashboardu**. Automatycznie skanuje otwarte porty na zdefiniowanych węzłach Tailscale, weryfikuje dostępność HTTP, pobiera tytuły stron i kategoryzuje usługi w piękny, cybernetyczny layout (AI, System, Pliki).

Zaprojektowany do działania jako usługa systemd na serwerze głównym (`100.69.201.80`).

---

## 🚀 Instalacja i Uruchomienie

Wykonaj poniższe kroki na serwerze głównym (`Mikrus`):

### 1. Sklonuj projekt
Jeśli masz już pobrany `/opt/homer-link-syncer`, możesz go usunąć lub użyć nowej ścieżki:
```bash
sudo git clone https://github.com/cenkierpiotr/aktualhomer /opt/custom-dashboard
sudo chown -R $USER:$USER /opt/custom-dashboard
cd /opt/custom-dashboard
```

### 2. Zainstaluj Zależności
```bash
sudo apt update
sudo apt install -y python3-yaml python3-requests
```

### 3. Skonfiguruj `config.yaml`
Edytuj `config.yaml` za pomocą `nano config.yaml`, aby dopasować listę serwerów (node'ów):
```yaml
scan_interval: 60 # Skanowanie co 60 sekund
server_port: 8080 # Port, na którym będzie dostępny dashboard

nodes:
  - name: "Serwer Główny"   # Nazwa do wyświetlenia (np. Mikrus)
    host: "100.69.201.80"  # IP Tailscale
    is_local: true          # Skanowanie lokalne (nie wymaga SSH)
  - name: "Zdalny VPS"
    host: "100.99.158.2"
    ssh_user: "root"        # SSH do skanowania zdalnego

exclude_ports:
  - 22    # SSH
  - 53    # DNS
  - 8080  # Sam dashboard (zapobiega pętli)
```

> [!NOTE]
> **Autoryzacja SSH**:
> Aby skanować zdalne serwery (np. `100.99.158.2`), użytkownik uruchamiający skrypt musi mieć dostęp SSH bez hasła (klucze):
> `ssh-copy-id root@100.99.158.2`

---

### 4. Uruchom Serwis
Aby skrypt działał w tle i serwował stronę na porcie `8080`:

```bash
sudo cp dashboard.service /etc/systemd/system/dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable dashboard
sudo systemctl start dashboard
```

#### Monitorowanie Działania (Logi)
```bash
tail -f /opt/custom-dashboard/dashboard.log
```

---

## 🔒 Automatyczna Kategoryzacja:
Skrypt dopasowuje elementy na podstawie **Słów Kluczowych** w tytule strony:
- **AI** (Cyan): `webui`, `chat`, `ollama`, `ai`, `gpt`, `rag`, `crawler`, `psychology`.
- **System** (Magenta): `Wszystko inne` (np. Portainer, Netdata, Uptime).
- **Storage/Pliki** (Lime): `cloud`, `sync`, `drive`, `storage`, `gokapi`, `backup`, `file`, `pliki`.
