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
- [Répartition des tâches](#répartition-des-tâches)
- [Roadmap](#roadmap)
- [Résultats attendus](#résultats-attendus)

---

## Présentation du projet

**SmartPitch** est une plateforme IoT simulée qui reproduit le comportement complet d'un système de suivi en temps réel de joueurs de football. En l'absence de capteurs physiques (GPS, IMU), toute la chaîne IoT est émulée par logiciel, tournant sur les PC des membres de l'équipe.

Le système génère des données de position et d'état physiologique synthétiques pour **22 joueurs**, les transmet via **MQTT**, les traite en temps réel avec des algorithmes de **Machine Learning**, et les affiche sur un **dashboard interactif** avec heatmaps, statistiques et alertes tactiques.

> Ce projet valide l'architecture, les flux de données, les algorithmes d'analyse et la faisabilité d'un système IoT football réel, avant déploiement avec du matériel physique.

---

## Objectif

- Simuler des capteurs IoT (GPS, IMU, fréquence cardiaque) pour 22 joueurs à **10 Hz**
- Reproduire la chaîne IoT complète : **Sensing → Communication → Computing → Visualization**
- Générer des **heatmaps**, détecter des schémas tactiques et prédire la fatigue des joueurs
- Fournir un **dashboard temps réel** exploitable par coaches, analystes et joueurs
- Démontrer la faisabilité du système sur données synthétiques avant industrialisation

---

## Architecture du système

### Vue d'ensemble — Pipeline IoT en 5 couches

```
┌─────────────────────────────────────────────────────────────────┐
│  COUCHE 1 — SIMULATION DES CAPTEURS (Sensing virtuel)          │
│  simulation/simulation_engine.py                                │
│  → 22 agents joueurs (positions x,y + vitesse + HR simulés)    │
│  → Bruit gaussien, pertes de paquets, fréquence 10 Hz          │
└────────────────────────────┬────────────────────────────────────┘
                             │ JSON payloads
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 2 — COMMUNICATION (Transport MQTT)                      │
│  communication/mqtt_publisher.py                                │
│  → Eclipse Mosquitto (broker local)                             │
│  → Topics : /match/{id}/player/{id}/position                   │
│  → Simulation de latence et de pertes réseau                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ subscribe / stream
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 3 — TRAITEMENT TEMPS RÉEL (Edge + Cloud simulé)        │
│  processing/data_pipeline.py                                    │
│  → Filtre de Kalman (lissage des positions)                    │
│  → Calcul vitesse, accélération, distance cumulée              │
│  → Détection de sprints (seuil > 7 m/s)                       │
│  → Score de fatigue (vitesse + HR + charge cumulée)            │
└────────────────────────────┬────────────────────────────────────┘
                             │ features prêtes
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 4 — ANALYTIQUE & ML                                     │
│  analytics/                                                     │
│  → Heatmap (grille 50×34 sur terrain 105×68 m)                │
│  → K-Means clustering des zones occupées                       │
│  → Random Forest : classification du rôle joué                 │
│  → Régression : indice de fatigue                              │
│  → SQLite : stockage des données traitées                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ données traitées
┌────────────────────────────▼────────────────────────────────────┐
│  COUCHE 5 — VISUALISATION (Dashboard web)                       │
│  dashboard/index.html                                           │
│  → Terrain 2D avec trajectoires joueurs (Canvas)              │
│  → Heatmaps interactives (individuelle + équipe)              │
│  → Graphes : vitesse, fatigue, distance (Chart.js)            │
│  → Alertes tactiques en temps réel                            │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture physique (sur vos PC)

| Machine | Rôle | Module |
|---|---|---|
| **PC 1** | Moteur de simulation + capteurs virtuels | `simulation/` |
| **PC 2** | Broker MQTT + traitement temps réel | `communication/` + `processing/` |
| **PC 3** | Analytique ML + base de données | `analytics/` + `database/` |
| **PC 4** | Dashboard de visualisation | `dashboard/` |

> **En pratique pour la démo** : tous les modules peuvent tourner sur un seul PC via des terminaux séparés.

### Format JSON des données simulées

Chaque capteur virtuel publie des trames JSON à 10 Hz :

```json
{
  "player_id": 7,
  "match_id": "match_001",
  "timestamp": 1716156000.123,
  "x": 42.3,
  "y": 31.7,
  "speed": 5.2,
  "acceleration": 1.1,
  "heart_rate": 152,
  "zone": "central_midfield"
}
```

---
# <font color="red">Votre grand texte rouge</font>
## Architecture du dépôt

```
smartpitch/
│
├── README.md                        # Ce fichier
├── requirements.txt                 # Dépendances Python
├── .gitignore
│
├── simulation/                      # COUCHE 1 — Sensing virtuel
│   ├── simulation_engine.py         # Moteur principal : 22 joueurs, trajectoires
│   ├── virtual_sensors.py           # Ajout bruit gaussien + pertes de paquets
│   └── match_scenarios.py           # Scénarios : match complet, mi-temps, replay
│
├── communication/                   # COUCHE 2 — Transport MQTT
│   ├── mqtt_publisher.py            # Publie les trames JSON vers le broker
│   ├── mqtt_subscriber.py           # Reçoit et route les données
│   └── config_broker.py             # Configuration Eclipse Mosquitto
│
├── processing/                      # COUCHE 3 — Traitement temps réel
│   ├── kalman_filter.py             # Filtre de Kalman pour lissage positions
│   ├── feature_extractor.py         # Vitesse, accél, distance, zones
│   └── data_pipeline.py             # Pipeline complet simulation → features
│
├── analytics/                       # COUCHE 4 — ML & Analytics
│   ├── heatmap_generator.py         # Heatmaps individuelle + équipe (numpy)
│   ├── clustering.py                # K-Means + évaluation silhouette score
│   ├── fatigue_model.py             # Régression : score de fatigue
│   ├── role_classifier.py           # Random Forest : rôle du joueur
│   └── event_detector.py            # Détection sprints + alertes tactiques
│
├── database/                        # Persistance
│   ├── models.py                    # Schéma SQLite
│   └── db_handler.py                # CRUD : insert, query, export CSV
│
├── dashboard/                       # COUCHE 5 — Visualisation web
│   ├── index.html                   # Dashboard principal
│   ├── style.css
│   ├── app.js                       # Logique WebSocket temps réel
│   └── charts/
│       ├── heatmap.js               # Rendu heatmap Canvas
│       ├── speed_chart.js           # Graphe vitesse vs temps
│       └── fatigue_chart.js         # Graphe fatigue vs temps
│
└── tests/                           # Tests unitaires
    ├── test_simulation.py
    ├── test_processing.py
    └── test_analytics.py
```

---

## Stack technique

| Couche | Technologie | Usage |
|---|---|---|
| Simulation | Python + NumPy + SciPy | Génération trajectoires, bruit gaussien |
| Communication | Eclipse Mosquitto + Paho-MQTT | Broker IoT local, publish/subscribe |
| Transport dashboard | `websockets` Python | Flux temps réel vers le navigateur |
| Traitement | FilterPy + Pandas | Filtre de Kalman, manipulation données |
| Machine Learning | Scikit-learn | K-Means, Random Forest, régression |
| Visualisation backend | Matplotlib + Seaborn | Génération des heatmaps et plots |
| Dashboard frontend | HTML5 + Chart.js + Canvas API | Interface temps réel sans framework lourd |
| Base de données | SQLite | Stockage léger, sans serveur, portable |
| Versioning | Git + GitHub | Collaboration à 4, branches par module |

---

## Installation

### Prérequis

- Python 3.10+
- Eclipse Mosquitto installé ([mosquitto.org](https://mosquitto.org/download/))
- Git

### Cloner le dépôt

```bash
git clone https://github.com/<votre-org>/smartpitch.git
cd smartpitch
```

### Installer les dépendances Python

```bash
pip install -r requirements.txt
```

**Contenu de `requirements.txt` :**
```
numpy
scipy
pandas
matplotlib
seaborn
scikit-learn
filterpy
paho-mqtt
websockets
```

### Configurer le broker MQTT

```bash
# Démarrer Mosquitto en local (port 1883 par défaut)
mosquitto -v
```

---

## Lancer le projet

Ouvrir **4 terminaux** (ou 4 machines) et lancer dans l'ordre :

```bash
# Terminal 1 — Démarrer le broker MQTT
mosquitto -v

# Terminal 2 — Lancer le traitement temps réel (subscriber)
python communication/mqtt_subscriber.py

# Terminal 3 — Lancer la simulation (publisher)
python simulation/simulation_engine.py --players 22 --duration 90 --scenario full_match

# Terminal 4 — Lancer le serveur du dashboard
python dashboard/server.py
# Ouvrir http://localhost:8080 dans le navigateur
```

---

## Répartition des tâches

| Membre | Rôle | Modules |
|---|---|---|
| **M1** — Chef de projet | Simulation Engine + coordination | `simulation/` |
| **M2** — IoT & Processing | Communication MQTT + traitement temps réel | `communication/` + `processing/` |
| **M3** — Data Science | Machine Learning + analytics + plots | `analytics/` |
| **M4** — Full Stack | Dashboard web + base de données | `dashboard/` + `database/` |

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

**Convention de commits :**
```
[MODULE] Description courte de la modification

Exemples :
[SIM] Ajout du bruit gaussien sur les positions GPS
[MQTT] Configuration du broker avec QoS level 1
[ML] Implémentation K-Means + silhouette score
[DASH] Intégration heatmap temps réel via WebSocket
```

---

## Roadmap

| Phase | Semaine | Objectif | Responsable |
|---|---|---|---|
| **Phase 0** | S1 | Setup Git, MQTT local, format JSON commun | Tous |
| **Phase 1** | S2 | Simulation 22 joueurs + MQTT end-to-end fonctionnel | M1 + M2 |
| **Phase 2** | S3 | Filtre de Kalman + features extraites + BDD SQLite | M2 + M4 |
| **Phase 3** | S4 | Heatmaps + K-Means + Random Forest + fatigue model | M3 |
| **Phase 4** | S5 | Dashboard live intégrant toutes les visualisations | M4 + M3 |
| **Phase 5** | S6 | Tests, performance plots, rapport final, soutenance | Tous |

---

## Résultats attendus

### Métriques de performance système

| Métrique | Valeur cible |
|---|---|
| Fréquence de simulation | 10 Hz (200 msg/s pour 22 joueurs) |
| Latence bout-en-bout | < 1 seconde |
| Joueurs simulés en parallèle | 22 (11 par équipe) |
| Durée de match simulée | 90 minutes (avec replay possible) |
| Taux de paquets reçus | Configurable : 90%, 95%, 100% |

### Métriques ML

| Modèle | Métrique | Valeur attendue |
|---|---|---|
| K-Means (zones) | Silhouette Score | > 0.65 |
| Random Forest (rôle) | Accuracy | > 90% |
| Régression (fatigue) | RMSE | < 5 points |

### Visualisations livrées

- Heatmap individuelle par joueur (grille 50×34)
- Heatmap collective de l'équipe
- Graphe vitesse instantanée vs temps (avec détection de sprints)
- Graphe distance cumulée vs temps
- Courbe fatigue score vs temps de jeu
- Courbe MSE du modèle LSTM vs époques
- Matrice de confusion du classifieur de rôle

---

## Contributeurs

| Membre | Rôle |
|---|---|
| [Membre 1] | Chef de projet — Simulation Engine |
| [Membre 2] | Communication IoT — Traitement temps réel |
| [Membre 3] | Machine Learning — Analytics |
| [Membre 4] | Dashboard — Base de données |

---

*SmartPitch — Projet IoT | Simulation de suivi tactique football*
