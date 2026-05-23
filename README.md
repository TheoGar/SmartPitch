# SmartPitch — Simulated IoT Football Analytics Platform

> Projet IoT — Système de suivi tactique football basé sur simulation temps réel  

---

## Table des matières

- [Présentation du projet](#présentation-du-projet)
- [Objectif](#objectif)
- [Architecture du système](#architecture-du-système)
- [Architecture du dépôt](#architecture-du-dépôt)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Lancer le projet](#lancer-le-projet)
- [Docker](#docker)
- [Résultats attendus](#résultats-attendus)

---

## Présentation du projet

**SmartPitch** est une plateforme IoT simulée qui reproduit le comportement complet d'un système de suivi en temps réel de joueurs de football. En l'absence de capteurs physiques (GPS, IMU), toute la chaîne IoT est émulée par logiciel, tournant sur les PC des membres de l'équipe.

Le système génère des données de position et d'état physiologique synthétiques pour **8 à 10 joueurs**, les transmet via **MQTT**, les analyse en temps réel à l'aide de **règles simples basées sur des seuils**, et les affiche sur un **dashboard minimaliste** avec heatmaps, statistiques et alertes temps réel.

> Ce projet valide l'architecture, les flux de données et la faisabilité d'un système IoT football réel, dans un cadre académique, avant déploiement avec du matériel physique.

---

## Objectif

- Simuler des capteurs IoT (position X/Y, vitesse, fréquence cardiaque, fatigue) pour **8 à 10 joueurs**
- Reproduire la chaîne IoT complète : **Sensing → Communication → Computing → Visualization**
- Générer des **heatmaps**, détecter la fatigue et les joueurs inactifs via des règles à seuils
- Fournir un **dashboard temps réel** affichant positions, heatmaps, statistiques et alertes
- Démontrer la faisabilité du système sur données synthétiques avant industrialisation

---

## Architecture du système

### Vue d'ensemble — Pipeline IoT en 5 couches

```
┌─────────────────────────────────────────────────────────────────┐
│  COUCHE 1 — SIMULATION DES CAPTEURS (Sensing virtuel)          │
│  simulation/simulation_engine.py                                │
│  → 8 à 10 joueurs (positions x,y + vitesse + HR + fatigue)     │
│  → Déplacements simplifiés et contrôlés                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ JSON payloads
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 2 — COMMUNICATION (Transport MQTT)                      │
│  communication/mqtt_publisher.py                                │
│  → Eclipse Mosquitto (broker local, une seule machine)         │
│  → Plusieurs producteurs MQTT sur un seul PC                   │
│  → Topics : /match/{id}/player/{id}/position                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ subscribe / stream
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 3 — TRAITEMENT TEMPS RÉEL                               │
│  processing/data_pipeline.py                                    │
│  → Calcul vitesse, distance cumulée                            │
│  → Détection de fatigue et joueurs inactifs (règles à seuils)  │
│  → Identification des zones chaudes du terrain                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ données analysées
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 4 — ANALYTIQUE LÉGÈRE                                   │
│  analytics/                                                     │
│  → Heatmap (zones d'occupation du terrain)                     │
│  → Alertes : fatigue, inactivité, zones chaudes               │
│  → Stockage JSON, CSV ou SQLite                                │
└────────────────────────────┬────────────────────────────────────┘
                             │ données traitées
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 5 — VISUALISATION (Dashboard web minimaliste)           │
│  dashboard/index.html                                           │
│  → Positions des joueurs sur le terrain (Canvas)              │
│  → Heatmaps (individuelle + équipe)                           │
│  → Statistiques principales et alertes temps réel             │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture physique

> **Tous les modules tournent sur une seule machine** via **Docker Compose**, chaque service dans son propre conteneur isolé communiquant via un réseau interne Docker.

| Conteneur | Rôle | Module |
|---|---|---|
| `simulation` | Moteur de simulation + capteurs virtuels | `simulation/` |
| `mosquitto` | Broker MQTT | — |
| `processing` | Traitement temps réel (subscriber) | `communication/` + `processing/` |
| `analytics` | Analytique légère + stockage | `analytics/` + `database/` |
| `dashboard` | Dashboard de visualisation | `dashboard/` |

### Format JSON des données simulées

Chaque capteur virtuel publie des trames JSON :

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

---

## Architecture du dépôt

> ⚠️ Architecture potentielle, susceptible d'évoluer au fil du développement.

```
smartpitch/
│
├── README.md                        # Ce fichier
├── requirements.txt                 # Dépendances Python
├── docker-compose.yml               # Orchestration des conteneurs
├── .gitignore
│
├── simulation/                      # COUCHE 1 — Sensing virtuel
│   ├── Dockerfile
│   ├── simulation_engine.py         # Moteur principal : 8-10 joueurs, déplacements simplifiés
│   └── virtual_sensors.py           # Génération position, vitesse, HR, fatigue
│
├── communication/                   # COUCHE 2 — Transport MQTT
│   ├── mqtt_publisher.py            # Publie les trames JSON vers le broker
│   ├── mqtt_subscriber.py           # Reçoit et route les données
│   └── config_broker.py             # Configuration Eclipse Mosquitto
│
├── processing/                      # COUCHE 3 — Traitement temps réel
│   ├── Dockerfile
│   ├── feature_extractor.py         # Vitesse, distance, zones
│   └── data_pipeline.py             # Pipeline complet simulation → analyse
│
├── analytics/                       # COUCHE 4 — Analytique légère
│   ├── Dockerfile
│   ├── heatmap_generator.py         # Heatmaps individuelle + équipe
│   └── event_detector.py            # Détection fatigue, inactivité, zones chaudes (seuils)
│
├── database/                        # Persistance
│   └── db_handler.py                # Stockage JSON, CSV ou SQLite
│
├── dashboard/                       # COUCHE 5 — Visualisation web
│   ├── Dockerfile
│   ├── index.html                   # Dashboard principal
│   ├── style.css
│   ├── app.js                       # Logique WebSocket temps réel
│   └── charts/
│       ├── heatmap.js               # Rendu heatmap Canvas
│       └── stats_chart.js           # Graphes statistiques principales
│
└── tests/                           # Tests unitaires
    ├── test_simulation.py
    ├── test_processing.py
    └── test_analytics.py
```

---

## Stack technique

> ⚠️ Stack potentielle, susceptible d'évoluer au fil du développement.

| Couche | Technologie | Usage |
|---|---|---|
| Simulation | Python + NumPy | Génération trajectoires simplifiées |
| Communication | Eclipse Mosquitto + Paho-MQTT | Broker IoT local, publish/subscribe |
| Transport dashboard | `websockets` Python | Flux temps réel vers le navigateur |
| Traitement | Pandas | Manipulation et analyse des données |
| Analytique | Règles à seuils (Python) | Détection fatigue, inactivité, zones chaudes |
| Dashboard frontend | HTML5 + Chart.js + Canvas API | Interface temps réel sans framework lourd |
| Base de données | JSON / CSV / SQLite | Stockage léger, sans serveur, portable |
| Conteneurisation | Docker + Docker Compose | Isolation des services, déploiement en une commande |
| Versioning | Git + GitHub | Collaboration à 4, branches par module |

---

## Installation

> ⚠️ Instructions potentielles, susceptibles d'évoluer au fil du développement.

### Prérequis

- Docker + Docker Compose
- Git

### Cloner le dépôt

```bash
git clone https://github.com/TheoGar/SmartPitch.git
cd SmartPitch
```

---

## Lancer le projet

### Avec Docker Compose (recommandé)

Une seule commande lance l'ensemble des services :

```bash
docker-compose up --build
```

Les services démarrent dans l'ordre suivant :
1. `mosquitto` — broker MQTT
2. `processing` — subscriber + traitement temps réel
3. `analytics` — analytique + stockage
4. `simulation` — capteurs virtuels (publishers)
5. `dashboard` — interface web

Ouvrir le dashboard sur **http://localhost:8080**

Pour arrêter :
```bash
docker-compose down
```

### Sans Docker (terminaux séparés)

Si Docker n'est pas disponible, installer Python 3.10+ et Eclipse Mosquitto, puis :

```bash
pip install -r requirements.txt
```

Ouvrir **4 terminaux** sur la même machine et lancer dans l'ordre :

```bash
# Terminal 1 — Démarrer le broker MQTT
mosquitto -v

# Terminal 2 — Lancer le traitement temps réel (subscriber)
python communication/mqtt_subscriber.py

# Terminal 3 — Lancer la simulation (publisher)
python simulation/simulation_engine.py --players 10 --duration 90

# Terminal 4 — Lancer le serveur du dashboard
python dashboard/server.py
# Ouvrir http://localhost:8080 dans le navigateur
```

---

## Docker

### Structure des conteneurs

```yaml
# docker-compose.yml (aperçu)
services:
  mosquitto:
    image: eclipse-mosquitto
    ports: ["1883:1883"]

  simulation:
    build: ./simulation
    depends_on: [mosquitto]
    environment:
      - MQTT_BROKER=mosquitto
      - PLAYERS=10

  processing:
    build: ./processing
    depends_on: [mosquitto]
    environment:
      - MQTT_BROKER=mosquitto

  analytics:
    build: ./analytics
    depends_on: [processing]
    volumes: ["./data:/app/data"]

  dashboard:
    build: ./dashboard
    depends_on: [processing]
    ports: ["8080:8080"]
```

### Réseau interne

Tous les conteneurs communiquent via le réseau Docker interne. Le broker Mosquitto est accessible depuis les autres conteneurs via le hostname `mosquitto` (port 1883). Seul le dashboard est exposé à l'extérieur (port 8080).

---

## Répartition des tâches

| Membre | Rôle | Modules |
|---|---|---|
| **M1** — Chef de projet | Simulation Engine + coordination | `simulation/` |
| **M2** — IoT & Processing | Communication MQTT + traitement temps réel | `communication/` + `processing/` |
| **M3** — Data Science | Analytique légère + stockage | `analytics/` + `database/` |
| **M4** — Full Stack | Dashboard web | `dashboard/` |

### Branches Git

```bash
main                  # Branche stable, merge uniquement après validation
├── feature/simulation      # M1
├── feature/communication   # M2
├── feature/processing      # M2
├── feature/analytics       # M3
├── feature/dashboard       # M4
└── feature/database        # M4
```

---

## Résultats attendus

### Métriques de performance système

| Métrique | Valeur cible |
|---|---|
| Joueurs simulés en parallèle | 8 à 10 |
| Latence bout-en-bout | < 1 seconde |
| Durée de match simulée | 90 minutes |
| Taux de paquets reçus | Configurable : 90%, 95%, 100% |

### Analyses livrées

| Analyse | Méthode |
|---|---|
| Détection de fatigue | Règle à seuil sur vitesse + HR |
| Détection joueur inactif | Règle à seuil sur distance parcourue |
| Zones chaudes du terrain | Accumulation de positions sur grille |

### Visualisations livrées

- Positions des joueurs en temps réel sur le terrain
- Heatmap individuelle par joueur
- Heatmap collective de l'équipe
- Statistiques principales (vitesse, distance, fatigue)
- Alertes temps réel (fatigue, inactivité)

---

*SmartPitch — Projet IoT | Simulation de suivi tactique football*
