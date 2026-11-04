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

## 6. Tests, CI et déploiement

### Lancer les vérifications en local

Ce sont les mêmes commandes que la CI. Elles utilisent les données locales et n'ont besoin d'aucun secret.

```bash
uv run ruff check app tests     # lint : erreurs réelles (noms non définis, imports inutilisés…)
uv run pytest -q                # tests : données, graphiques, modèle, onglets Mission 1/2, démarrage de l'app
uv run pytest -q -k mission2    # un seul groupe de tests
```

### Intégration continue (GitHub Actions)

`.github/workflows/ci.yml` tourne à chaque push sur `main` et à chaque pull request. Il :
1. installe les versions exactes de `uv.lock` (`uv sync --locked`) ;
2. lance le lint (ruff) ;
3. vérifie que `app/requirements.txt` est synchronisé avec `uv.lock` ;
4. lance les tests (pytest) ;
5. démarre réellement l'app avec `shiny run` et vérifie qu'elle répond.

Le résultat apparaît dans l'onglet **Actions** du dépôt GitHub et sur chaque pull request.

### Ajouter ou mettre à jour une dépendance

Le serveur installe les dépendances listées dans `app/requirements.txt`. Ce fichier est généré à partir de `uv.lock` et doit être régénéré après chaque changement de dépendances, sinon la CI échoue :

```bash
uv add <paquet>                 # ou : uv add --dev <paquet> pour un outil de développement
uv export --no-dev --no-emit-project --no-hashes --no-header -o app/requirements.txt
```

### Déploiement continu (Posit Connect Cloud)

L'app est hébergée sur **[Posit Connect Cloud](https://connect.posit.cloud)**, l'hébergeur de Posit, l'éditeur de Shiny. Le plan gratuit accepte les dépôts GitHub publics.

**Comment ça marche :** après chaque push sur `main`, si le job `check` passe, le job **`deploy`** de la CI copie le contenu de `app/` seul sur la branche **`deploy`**. Connect Cloud publie cette branche, ce qui donne deux garanties :
- **une CI en échec bloque le déploiement** ;
- Connect Cloud ne voit que l'app (`app.py` et `requirements.txt` à la racine), sans les notebooks du dépôt, qui lui faisaient réclamer `jupyter`.

Ne modifie jamais la branche `deploy` à la main : elle est remplacée à chaque déploiement.

Configuration, à faire une seule fois :
1. Se connecter sur https://connect.posit.cloud avec son compte GitHub.
2. **Publish → Shiny** : choisir le dépôt **`Saar45/airport_data_project`**, la branche **`deploy`** et le fichier principal **`app.py`**.
   Publier depuis ce dépôt et non depuis un fork : un fork ne reçoit pas la branche `deploy`.
3. Dans **Advanced settings → Variables**, ajouter les variables du `.env`. Cocher **secret** pour le mot de passe :
   `DATA_SOURCE=supabase`, `SUPABASE_HOST`, `SUPABASE_PORT`, `SUPABASE_DB`, `SUPABASE_USER`, `SUPABASE_PASSWORD`, `SUPABASE_SCHEMA`.
4. Laisser **« Automatically publish on push »** activé, puis **Publish**.

À savoir :
- **Mise en veille :** sans visite, l'app se met en veille. Au réveil, elle relit Supabase et entraîne le modèle, ce qui prend environ 20 s. **Ouvrir l'app une minute avant une présentation.**
- **Changement dans la base :** cliquer sur **Republish** dans Connect Cloud. Une nouvelle publication part sans cache (`app/cache/` n'est pas dans le dépôt) et relit donc Supabase.
- **Republier sans changer le code :** GitHub → Actions → CI → **Run workflow** sur `main`. Ça relance les tests puis la publication de la branche `deploy`.

## 7. Dump SQL de la base (rendu Mission 2)

**`dumps/supabase_dump.sql`** est le dump complet de la base Supabase. Il contient :
- les 5 tables et toutes leurs données ;
- les clés primaires, UNIQUE et étrangères ;
- les séquences ;
- la Row Level Security et ses policies.

### Recharger le dump

Il faut **PostgreSQL 17 ou plus** et `psql`, idéalement en version 17.6 ou plus. Le chargement prend environ 2 s :

```bash
createdb airport
psql -d airport -v ON_ERROR_STOP=1 -f dumps/supabase_dump.sql
```

Pour vérifier le résultat :

```sql
select count(*) from flights;                                   -- 252 704
select count(*) from flights where dest in ('IAH', 'HOU');      -- 6 958 (Mission 1, Q4)
```

À savoir :
- Le fichier utilise le format `COPY … FROM stdin` de `pg_dump`. Il se recharge avec **`psql`**, pas en le collant dans un éditeur SQL (Supabase SQL Editor, DBeaver…).
- Les policies RLS visent le rôle de l'app, `shiny_reader`. Le dump crée ce rôle, sans droit de connexion, s'il n'existe pas.

### Regénérer le dump après un changement dans la base

```bash
uv run python scripts/dump_supabase.py
```

Il faut le `.env` rempli et `pg_dump` en version 17 ou plus (macOS : `brew install libpq`).

## 8. Contenu de l'application

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

## 9. Structure du projet

```
Airport_project/
├── README.md                     ← ce fichier
├── .env.example                  ← modèle de configuration (copier vers .env)
├── pyproject.toml / uv.lock      ← dépendances Python (gérées par uv)
├── Mission1_Exploration.ipynb    ← notebook Mission 1
├── Mission2_Import_Supabase.ipynb ← notebook Mission 2 (lecture des 5 fichiers, import dans Supabase)
├── EnoncéProjetTraficAérien-…pdf ← énoncé du projet
├── docs/                         ← documentation détaillée de l'app
├── tests/                        ← tests automatiques (pytest)
├── dumps/supabase_dump.sql       ← dump SQL complet de la base (rendu Mission 2)
├── scripts/dump_supabase.py      ← regénère ce dump
├── .github/workflows/ci.yml      ← intégration continue (GitHub Actions)
└── app/
    ├── app.py                    ← point d'entrée : mise en page, filtres, onglets
    ├── requirements.txt          ← dépendances pour Connect Cloud (généré depuis uv.lock)
    ├── data_source.py            ← lecture Supabase / locale, cache, métadonnées de la base
    ├── data_prep.py              ← nettoyage et jointures
    ├── model.py                  ← modèle de prédiction
    ├── utils.py                  ← formatage, agrégats partagés
    └── modules/                  ← un fichier par onglet
```

Le notebook de la Mission 2 est aussi disponible sur Colab :
https://colab.research.google.com/drive/1kFgVOSJJK44semax7cZEpBHEDENG4vWq?usp=sharing

## 10. Documentation

Le dossier [`docs/`](docs/README.md) explique l'app en détail, pour quelqu'un qui découvre Python :
- l'architecture ;
- la préparation des données ;
- le fonctionnement de Shiny ;
- le modèle de prédiction ;
- la connexion Supabase ;
- des recettes pour ajouter un graphique, un filtre ou un onglet.

## 11. Dépannage

| Message | Solution |
|---|---|
| `command not found: uv` | Installer uv (voir § 1). |
| `Variables d'environnement manquantes` | `.env` absent ou incomplet : voir § 3. |
| `password authentication failed for user "..."` | Le mot de passe ne correspond pas à l'utilisateur. Vérifier `SUPABASE_USER=shiny_reader.<project-ref>`. |
| `failed to resolve host 'db.xxx.supabase.co'` | Utiliser l'hôte du **Session pooler**, pas l'hôte direct. |
| `Tables vides côté supabase` | Tables non importées, ou RLS sans policy de lecture pour `shiny_reader`. |
| `Address already in use` | L'app tourne déjà : l'arrêter, ou ajouter `--port 8765`. |
| Chiffres pas à jour après un changement dans la base | Reconstruire le cache (§ 5). |
