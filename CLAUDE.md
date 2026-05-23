# CLAUDE.md — Instructions pour Claude Code

Ce fichier est lu automatiquement par Claude Code à chaque session.
Il décrit l'architecture, les conventions et les règles de développement du projet SmartPitch.

---

## Présentation du projet

**SmartPitch** est une plateforme IoT simulée de suivi tactique football en temps réel.
Elle émule par logiciel toute la chaîne IoT : capteurs → MQTT → traitement → analytics → dashboard.

- **8 à 10 joueurs** simulés (pas de capteurs physiques)
- Communication via **MQTT** (Eclipse Mosquitto)
- Analyse par **règles à seuils** (pas de ML complexe)
- Dashboard web **temps réel** via WebSockets
- Déploiement via **Docker Compose** (5 conteneurs)

---

## Architecture — 5 couches

```
simulation/ → communication/ → processing/ → analytics/ → dashboard/
```

### Couche 1 — simulation/
- `simulation_engine.py` : génère 8–10 joueurs avec des déplacements simplifiés (pas de physique avancée)
- `virtual_sensors.py` : produit les trames JSON à intervalle régulier

Chaque joueur publie un JSON toutes les 100ms :
```json
{
  "player_id": 7,
  "match_id": "match_001",
  "timestamp": 1716156000.123,
  "x": 42.3,
  "y": 31.7,
  "speed": 5.2,
  "heart_rate": 152,
  "fatigue": 0.74
}
```

Terrain : 105m × 68m. Coordonnées x ∈ [0, 105], y ∈ [0, 68].

### Couche 2 — communication/
- `mqtt_publisher.py` : publie les trames JSON sur le broker Mosquitto
- `mqtt_subscriber.py` : s'abonne aux topics et transmet au processing
- `config_broker.py` : paramètres de connexion (host, port, topics)

Topic pattern : `smartpitch/match/{match_id}/player/{player_id}`

Le broker Mosquitto est accessible :
- En local : `localhost:1883`
- En Docker : hostname `mosquitto`, port `1883`
- Lire `MQTT_BROKER` et `MQTT_PORT` depuis les variables d'environnement

### Couche 3 — processing/
- `feature_extractor.py` : calcule vitesse instantanée, distance cumulée, zone du terrain
- `data_pipeline.py` : reçoit les messages MQTT, applique les extractions, transmet à analytics

Zones du terrain (à calculer depuis x,y) :
```
defense       : x ∈ [0, 35]
milieu        : x ∈ [35, 70]
attaque       : x ∈ [70, 105]
```

### Couche 4 — analytics/ + database/
- `heatmap_generator.py` : grille d'occupation 21×14 (105/5 × 68/5), par joueur et collective
- `event_detector.py` : détection d'alertes par règles à seuils

Seuils de détection (modifiables via config) :
```python
FATIGUE_THRESHOLD = 0.80        # fatigue > 0.8 → alerte fatigue
INACTIVITY_DISTANCE = 5.0       # distance < 5m sur 30s → joueur inactif
SPRINT_SPEED = 7.0              # speed > 7 m/s → sprint détecté
HIGH_HR_THRESHOLD = 170         # heart_rate > 170 → alerte cardiaque
```

- `database/db_handler.py` : stockage SQLite (fichier `data/smartpitch.db`)

### Couche 5 — dashboard/
- `server.py` : serveur Python (websockets) qui pousse les données en temps réel
- `index.html` + `style.css` + `app.js` : interface web minimaliste
- `charts/heatmap.js` : rendu Canvas de la heatmap
- `charts/stats_chart.js` : graphes Chart.js (vitesse, fatigue, distance)

Le dashboard écoute sur le port **8080**.
WebSocket sur `ws://localhost:8765` (ou `ws://dashboard:8765` en Docker).

---

## Docker Compose

5 services, réseau interne `smartpitch-net` :

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports: ["1883:1883", "9001:9001"]

  processing:
    build: ./processing
    depends_on: [mosquitto]
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1883

  analytics:
    build: ./analytics
    depends_on: [processing]
    volumes: ["./data:/app/data"]
    environment:
      - MQTT_BROKER=mosquitto

  simulation:
    build: ./simulation
    depends_on: [mosquitto]
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1883
      - PLAYERS=10
      - MATCH_DURATION=90

  dashboard:
    build: ./dashboard
    depends_on: [processing]
    ports: ["8080:8080", "8765:8765"]
    environment:
      - MQTT_BROKER=mosquitto
```

Chaque service avec un `Dockerfile` a cette base :
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## Conventions de code

### Python
- Version : **Python 3.11**
- Style : **PEP 8**, fonctions documentées avec docstrings
- Logging : utiliser `logging` (pas `print`) avec niveau `INFO` par défaut
- Configuration : toujours lire depuis variables d'environnement avec valeur par défaut :
  ```python
  import os
  MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
  MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
  ```
- Gestion d'erreurs : `try/except` sur toutes les connexions réseau et I/O

### MQTT
- QoS = 1 pour tous les messages
- Reconnexion automatique si le broker est indisponible (retry avec backoff)
- Utiliser `paho-mqtt` version 2.x (API `mqtt.Client` avec `CallbackAPIVersion.VERSION2`)

### Structure des fichiers Python
Chaque module doit avoir un `if __name__ == "__main__":` pour pouvoir être lancé standalone.

### Tests
- Framework : `pytest`
- Chaque test mocke les connexions MQTT avec `unittest.mock`
- Pas de tests d'intégration Docker (tests unitaires seulement)

---

## Dépendances par service

### simulation/ et processing/
```
numpy==1.26.4
paho-mqtt==2.1.0
```

### analytics/
```
numpy==1.26.4
pandas==2.2.2
paho-mqtt==2.1.0
```

### dashboard/
```
websockets==12.0
paho-mqtt==2.1.0
```

### tests/
```
pytest==8.2.0
pytest-asyncio==0.23.6
```

---

## Points d'attention critiques

1. **Ordre de démarrage Docker** : Mosquitto doit être prêt avant que simulation et processing démarrent. Ajouter un healthcheck ou un `wait-for-it` script.

2. **Thread safety** : le dashboard server et le subscriber MQTT tournent dans des threads séparés. Utiliser `asyncio` ou des `queue.Queue` pour partager les données.

3. **Mosquitto config** : le fichier `mosquitto/mosquitto.conf` doit autoriser les connexions anonymes en local :
   ```
   listener 1883
   allow_anonymous true
   ```

4. **Heatmap** : la grille est mise à jour par accumulation. Ne pas recalculer depuis zéro à chaque frame, utiliser un numpy array persistant.

5. **WebSocket** : le serveur pousse un JSON global toutes les 500ms avec l'état complet de tous les joueurs (pas un message par joueur).

Format du payload WebSocket :
```json
{
  "timestamp": 1716156000.123,
  "players": [
    {
      "player_id": 7,
      "x": 42.3, "y": 31.7,
      "speed": 5.2,
      "heart_rate": 152,
      "fatigue": 0.74,
      "zone": "milieu",
      "alerts": ["fatigue"]
    }
  ],
  "heatmap": [[0, 1, 3, ...], ...],
  "match_time": 1234
}
```

---

## Ordre de développement recommandé

Générer tous les fichiers dans cet ordre, sans s'arrêter entre chaque étape.
Tester uniquement à la fin via `docker-compose up --build`.

### Phase 1 — Infrastructure
1. `mosquitto/mosquitto.conf`
2. `communication/config_broker.py`
3. `docker-compose.yml`
4. `Dockerfile` pour chaque service (simulation, processing, analytics, dashboard)
5. `requirements.txt` pour chaque service

### Phase 2 — Simulation (Couche 1 + 2)
6. `simulation/virtual_sensors.py`
7. `simulation/simulation_engine.py`
8. `communication/mqtt_publisher.py`

### Phase 3 — Traitement (Couche 2 + 3)
9. `communication/mqtt_subscriber.py`
10. `processing/feature_extractor.py`
11. `processing/data_pipeline.py`

### Phase 4 — Analytics + Database (Couche 4)
12. `analytics/heatmap_generator.py`
13. `analytics/event_detector.py`
14. `database/db_handler.py`

### Phase 5 — Dashboard (Couche 5)
15. `dashboard/server.py`
16. `dashboard/index.html`
17. `dashboard/style.css`
18. `dashboard/app.js`
19. `dashboard/charts/heatmap.js`
20. `dashboard/charts/stats_chart.js`

### Phase 6 — Tests
21. `tests/test_simulation.py`
22. `tests/test_processing.py`
23. `tests/test_analytics.py`

### Validation finale
```bash
docker-compose up --build
# Vérifier http://localhost:8080
```

---

## Ce que ce projet N'utilise PAS

Pour éviter toute dérive de scope :

- ❌ Pas de Machine Learning (pas de scikit-learn, pas de modèles)
- ❌ Pas de filtre de Kalman
- ❌ Pas de K-Means, Random Forest, régression
- ❌ Pas de Kafka, Redis, ou infrastructure Big Data
- ❌ Pas de framework frontend (pas de React, Vue, Angular)
- ❌ Pas de base de données distante (SQLite local uniquement)
- ❌ Pas de simulation physique avancée des mouvements
