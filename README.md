# Trafic aérien NYC : WebApp (Mission 3)

Application web **Shiny for Python** du projet *Trafic Aérien* (Aéroports de Paris, données BTS). Elle analyse les vols partis de New York (EWR, JFK, LGA) pour aider le manager à **anticiper les retards, annulations et déroutements**.

Elle centralise aussi le travail de l'équipe :
- **Mission 1** : réponses aux 8 questions d'exploration ;
- **Mission 2** : base Supabase, avec son schéma, les contrôles qualité et la sécurité ;
- **Mission 3** : tableaux de bord d'analyse et modèle de prédiction.

Les données sont lues dans la base **Supabase (PostgreSQL)** de l'équipe.

---

## 1. Prérequis

- **macOS, Linux ou Windows**
- **[uv](https://docs.astral.sh/uv/)**, le gestionnaire Python du projet. Il installe aussi la bonne version de Python (3.12) :
  ```bash
  brew install uv                                     # macOS
  # ou : curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Le **mot de passe du rôle `shiny_reader`** (lecture seule), à demander à l'équipe. Il ne doit jamais être partagé dans un groupe ou commité.

Pas besoin d'installer Python soi-même ni de créer un environnement virtuel : `uv` s'en occupe.

## 2. Installation

```bash
git clone <url-du-dépôt> Airport_project     # ou récupérer le dossier
cd Airport_project
uv sync                                       # installe Python 3.12 + toutes les dépendances dans .venv/
```

## 3. Configuration

```bash
cp .env.example .env
```

Ouvrir `.env` et remplir `SUPABASE_PASSWORD`. Les autres valeurs sont déjà celles du projet :

| Variable | Valeur | Rôle |
|---|---|---|
| `DATA_SOURCE` | `supabase` | `local` pour travailler hors-ligne avec les données `nycflights13` |
| `SUPABASE_HOST` | `aws-0-eu-west-1.pooler.supabase.com` | Session pooler (compatible IPv4) |
| `SUPABASE_USER` | `shiny_reader.olqkxvifgalmtooaetwt` | rôle en lecture seule, au format `<rôle>.<project-ref>` |
| `SUPABASE_PASSWORD` | *à demander* | |
| `REFRESH_CACHE` | `false` | `true` pour relire la base (voir § 5) |

`.env` est ignoré par git.

## 4. Lancer l'application

```bash
uv run shiny run app/app.py --reload
```

Ouvrir **http://127.0.0.1:8000**. Le badge en haut à droite indique la source des données (`supabase` ou `local`).

- **Premier lancement :** l'app télécharge les 5 tables depuis Supabase, les prépare et entraîne le modèle (environ 20 s). Les lancements suivants prennent moins d'une seconde grâce au cache.
- **`--reload`** relance l'app à chaque modification d'un fichier `.py`, ce qui est pratique pendant le développement.
- **Arrêter :** `Ctrl + C` dans le terminal.
- **Autre port :** ajouter `--port 8765`.
- **Forcer une source pour un seul lancement**, sans modifier `.env` :
  ```bash
  DATA_SOURCE=local uv run shiny run app/app.py --reload
  ```

## 5. Le cache

Les données préparées et le modèle sont enregistrés dans `app/cache/<source>.pkl`.

**Il faut reconstruire le cache** après une modification de la base (nouvelles lignes, contraintes, droits) ou du code de préparation des données ou du modèle :

```bash
REFRESH_CACHE=true uv run shiny run app/app.py      # ou : supprimer le dossier app/cache/
```

Le cache se reconstruit aussi tout seul quand la structure des données de l'app change (`CACHE_VERSION` dans `app/data_source.py`).

## 6. Contenu de l'application

| Onglet | Contenu |
|---|---|
| **Vue d'ensemble** | Chiffres clés (vols, annulations, retards) et évolution mensuelle |
| **Mission 1** | Les 8 questions d'exploration (Q1 à Q8), recalculées sur la base |
| **Mission 2** | Pipeline d'import, schéma et relations, contrôles qualité, sécurité |
| **Quand ?** | Problèmes par jour de la semaine × heure, jours les plus critiques |
| **Compagnies & routes** | Taux de problèmes par compagnie, routes les plus touchées |
| **Météo** | Impact de la visibilité, du vent, de la pluie et de la température |
| **Avions** | Impact de l'âge et du constructeur de l'avion |
| **Carte** | Destinations : volume de vols et taux de problèmes |
| **Prédiction** | Probabilité de problème pour un scénario (régression logistique) |

Un **problème** = retard à l'arrivée de plus de 15 min, annulation ou déroutement.

Les **filtres de la barre latérale** (aéroport de départ, compagnies, destinations, mois) s'appliquent aux onglets d'analyse. Ils ne s'appliquent pas aux onglets Mission 1, Mission 2 et Prédiction.

## 7. Structure du projet

```
Airport_project/
├── README.md                     ← ce fichier
├── .env.example                  ← modèle de configuration (copier vers .env)
├── pyproject.toml / uv.lock      ← dépendances Python (gérées par uv)
├── Mission1_Exploration.ipynb    ← notebook Mission 1
├── EnoncéProjetTraficAérien-…pdf ← énoncé du projet
├── docs/                         ← documentation détaillée de l'app
└── app/
    ├── app.py                    ← point d'entrée : mise en page, filtres, onglets
    ├── data_source.py            ← lecture Supabase / locale, cache, métadonnées de la base
    ├── data_prep.py              ← nettoyage et jointures
    ├── model.py                  ← modèle de prédiction
    ├── utils.py                  ← formatage, agrégats partagés
    └── modules/                  ← un fichier par onglet
```

Le notebook de la Mission 2 (import dans Supabase) est sur Colab :
https://colab.research.google.com/drive/1kFgVOSJJK44semax7cZEpBHEDENG4vWq?usp=sharing

## 8. Documentation

Le dossier [`docs/`](docs/README.md) explique l'app en détail, pour quelqu'un qui découvre Python :
- l'architecture ;
- la préparation des données ;
- le fonctionnement de Shiny ;
- le modèle de prédiction ;
- la connexion Supabase ;
- des recettes pour ajouter un graphique, un filtre ou un onglet.

## 9. Dépannage

| Message | Solution |
|---|---|
| `command not found: uv` | Installer uv (voir § 1). |
| `Variables d'environnement manquantes` | `.env` absent ou incomplet : voir § 3. |
| `password authentication failed for user "..."` | Le mot de passe ne correspond pas à l'utilisateur. Vérifier `SUPABASE_USER=shiny_reader.<project-ref>`. |
| `failed to resolve host 'db.xxx.supabase.co'` | Utiliser l'hôte du **Session pooler**, pas l'hôte direct. |
| `Tables vides côté supabase` | Tables non importées, ou RLS sans policy de lecture pour `shiny_reader`. |
| `Address already in use` | L'app tourne déjà : l'arrêter, ou ajouter `--port 8765`. |
| Chiffres pas à jour après un changement dans la base | Reconstruire le cache (§ 5). |
