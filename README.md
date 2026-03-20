# Homer Auto Updater

Automatyczny aktualizator dashboardu Homer. Skanuje otwarte porty na zdefiniowanych węzłach Tailscale, weryfikuje dostępność HTTP, pobiera tytuły stron i dynamicznie aktualizuje plik `config.yml` Homera.

Zaprojektowany do działania jako usługa systemd na serwerze głównym.

---

## 🚀 Instalacja i Uruchomienie

Wykonaj poniższe kroki na serwerze z Homerem (`100.69.201.80`):

### 1. Sklonuj repozytorium
```bash
sudo git clone https://github.com/cenkierpiotr/aktualhomer /opt/homer-link-syncer
sudo chown -R $USER:$USER /opt/homer-link-syncer
cd /opt/homer-link-syncer
```

### 2. Zainstaluj Zależności
```bash
sudo apt update
sudo apt install -y python3-yaml python3-requests
```

### 3. Skonfiguruj
Edytuj `config.yaml` dostosowując ścieżkę do Twojego `config.yml` oraz listę serwerów:
```yaml
homer_config_path: "/opt/homer/assets/config.yml" # Ścieżka do Twojego Homera
scan_interval: 60                                 # Co ile sekund skanować

nodes:
  - name: "Serwer Główny"
    host: "100.69.201.80"
    is_local: true
  - name: "Zdalny VPS"
    host: "100.99.158.2"
    ssh_user: "root" # Użytkownik SSH

exclude_ports:
  - 22    # SSH
  - 8080  # Homer
```

> [!NOTE]
> **Autoryzacja SSH**:
> Aby skanować zdalne serwery (np. `100.99.158.2`), użytkownik uruchamiający skrypt musi mieć dostęp SSH bez hasła (klucze):
> `ssh-copy-id root@100.99.158.2`

---

### 4. Uruchom Serwis
```bash
sudo cp homer_updater.service /etc/systemd/system/homer_updater.service
sudo systemctl daemon-reload
sudo systemctl enable homer_updater
sudo systemctl start homer_updater
```

#### Monitorowanie Loganów
```bash
tail -f /opt/homer-link-syncer/homer_updater.log
```
