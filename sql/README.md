# Requêtes SQL des Missions 1 et 2

Ces requêtes ont été **reconstituées** à partir de l'état final de la base Supabase de l'équipe. Les requêtes d'origine, écrites dans le SQL Editor de Supabase, n'ont pas été conservées. Elles ont toutes été vérifiées :

- **Mission 1 :** exécutées sur la base Supabase. Les résultats sont identiques à ceux de l'onglet « Mission 1 » de l'application et du notebook `Mission1_Exploration.ipynb`, et ils sont indiqués en commentaire sous chaque question.
- **Mission 2 :** rejouées de bout en bout sur un PostgreSQL 17 vide, à partir des données dans leur état d'avant correction. La base obtenue est **identique** à la base Supabase : mêmes lignes, mêmes contraintes, mêmes policies et même empreinte MD5 des données.

## Fichiers et ordre d'exécution

| Ordre | Fichier | Contenu |
|---|---|---|
| 1 | `mission2_01_creation_tables.sql` | Création des 5 tables, avec les clés primaires des tables de référence |
| 2 | notebook `Mission2_Import_Supabase.ipynb` | Lecture des 5 fichiers fournis, nettoyage, import |
| 3 | `mission2_02_controles.sql` | Contrôles demandés par l'énoncé : clés primaires, regex, valeurs manquantes, clés étrangères (lecture seule) |
| 4 | `mission2_03_corrections_contraintes.sql` | Corrections, ajout des 4 aéroports et des 716 avions manquants, clés primaires composées, clés étrangères |
| 5 | `mission2_04_securite.sql` | Rôle de l'application en lecture seule, Row Level Security |
| – | `mission1_exploration.sql` | Les 8 questions de la Mission 1 (lecture seule, sur la base finale) |

## Exécution

Avec `psql`, sur une base PostgreSQL :

```bash
psql -d airport -v ON_ERROR_STOP=1 -f sql/mission1_exploration.sql
```

On peut aussi copier chaque requête dans le SQL Editor de Supabase.

Pour reproduire la base sans passer par l'import, le plus simple est de recharger `dumps/supabase_dump.sql` (voir le README principal, § 7).

## Résultats principaux

- **Clés :**
  - `flight` seul n'est pas une clé : 3 652 numéros pour 252 704 vols ;
  - `(year, month, day, hour, carrier, flight)` est une clé ;
  - `(year, month, day, hour, origin)` est une clé de `weather`.
- **Clés étrangères, avant correction :**
  - 4 destinations absentes de `airports` (BQN, PSE, SJU, STT : 5 717 vols) ;
  - 716 avions absents de `planes` (37 704 vols), dont 95 % chez MQ et AA, qui déclarent des numéros de flotte et non des immatriculations.
- **Valeurs déguisées :** 3 fuseaux `\N` et 1 973 immatriculations vides, remplacés par de vrais NULL.
- **Météo :** `weather` ne couvre qu'EWR, de janvier à mai. 206 696 vols n'ont pas d'observation, c'est pourquoi il n'y a pas de clé étrangère `flights → weather`.
