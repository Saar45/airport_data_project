-- =============================================================================
-- Mission 2 · Étape 3 : contrôles demandés par l'énoncé (après l'import)
-- =============================================================================
-- Requêtes en lecture seule, reconstituées. Elles vérifient, avant d'ajouter les
-- contraintes, ce que l'énoncé demande de vérifier :
--   A. les clés primaires (unicité, aucune valeur manquante) ;
--   B. la nomenclature des codes, par expressions régulières ;
--   C. les valeurs manquantes déguisées en texte ;
--   D. les clés étrangères (codes présents dans une table et absents de l'autre).
--
-- « Avant correction » = résultat juste après l'import des fichiers fournis.
-- « Après correction » = résultat sur la base actuelle (étape 4 appliquée).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- A. Clés primaires : chaque clé doit être unique et sans valeur manquante.
-- -----------------------------------------------------------------------------

-- Clés des tables de référence. Résultat : 0 doublon, 0 valeur manquante partout.
SELECT 'airports.faa' AS cle, count(*) - count(DISTINCT faa) AS doublons, count(*) - count(faa) AS manquants FROM airports
UNION ALL
SELECT 'airlines.carrier', count(*) - count(DISTINCT carrier), count(*) - count(carrier) FROM airlines
UNION ALL
SELECT 'planes.tailnum', count(*) - count(DISTINCT tailnum), count(*) - count(tailnum) FROM planes;

-- weather : (year, month, day, hour, origin) est une clé composite valide.
-- Résultat : 0 combinaison en double
SELECT count(*) AS combinaisons_en_double
FROM (SELECT 1 FROM weather GROUP BY year, month, day, hour, origin HAVING count(*) > 1) d;

-- flights : le numéro de vol seul n'est PAS une clé…
-- Résultat : 3 652 numéros différents pour 252 704 vols
SELECT count(*) AS vols, count(DISTINCT flight) AS numeros_de_vol_differents,
       count(*) = count(DISTINCT flight) AS flight_seul_est_unique
FROM flights;

-- … mais (year, month, day, hour, carrier, flight) en est une.
-- Résultat : 0 combinaison en double
SELECT count(*) AS combinaisons_en_double
FROM (SELECT 1 FROM flights GROUP BY year, month, day, hour, carrier, flight HAVING count(*) > 1) d;


-- -----------------------------------------------------------------------------
-- B. Nomenclature des codes (expressions régulières).
--    Code FAA : 3 caractères · compagnie : 2 caractères · immatriculation : N + 1 à 5 caractères
-- -----------------------------------------------------------------------------

-- Résultat : 0 code aéroport ou compagnie non conforme
SELECT 'airports.faa' AS colonne, count(*) AS non_conformes FROM airports WHERE faa !~ '^[A-Z0-9]{3}$'
UNION ALL
SELECT 'flights.origin', count(*) FROM flights WHERE origin !~ '^[A-Z0-9]{3}$'
UNION ALL
SELECT 'flights.dest', count(*) FROM flights WHERE dest !~ '^[A-Z0-9]{3}$'
UNION ALL
SELECT 'weather.origin', count(*) FROM weather WHERE origin !~ '^[A-Z0-9]{3}$'
UNION ALL
SELECT 'airlines.carrier', count(*) FROM airlines WHERE carrier !~ '^[A-Z0-9]{2}$'
UNION ALL
SELECT 'flights.carrier', count(*) FROM flights WHERE carrier !~ '^[A-Z0-9]{2}$';

-- Immatriculations non conformes.
-- Résultat avant correction : « » (vide, 1 973 vols) et « D942DN » (3 vols, probable faute
-- de frappe pour N942DN) · après correction : seulement D942DN
SELECT tailnum, count(*) AS vols
FROM flights
WHERE tailnum !~ '^N[0-9A-Z]{1,5}$'
GROUP BY tailnum
ORDER BY vols DESC;


-- -----------------------------------------------------------------------------
-- C. Valeurs manquantes déguisées en texte (laissées par l'import des fichiers).
-- -----------------------------------------------------------------------------

-- Résultat avant correction : 3 fuseaux « \N » et 1 973 immatriculations vides · après : 0
SELECT 'airports.tzone = \N' AS anomalie, count(*) AS lignes FROM airports WHERE tzone = '\N'
UNION ALL
SELECT 'flights.tailnum vide', count(*) FROM flights WHERE tailnum IS NOT NULL AND trim(tailnum) = '';


-- -----------------------------------------------------------------------------
-- D. Clés étrangères : codes utilisés dans une table et absents de la table de référence.
-- -----------------------------------------------------------------------------

-- Destinations absentes de airports.
-- Résultat avant correction : BQN, PSE, SJU, STT (5 717 vols) · après : aucune
SELECT f.dest, count(*) AS vols
FROM flights f
WHERE NOT EXISTS (SELECT 1 FROM airports a WHERE a.faa = f.dest)
GROUP BY f.dest
ORDER BY vols DESC;

-- Origines, compagnies et stations météo absentes. Résultat : 0 partout
SELECT 'flights.origin → airports' AS relation, count(*) AS lignes_orphelines
FROM flights f WHERE NOT EXISTS (SELECT 1 FROM airports a WHERE a.faa = f.origin)
UNION ALL
SELECT 'flights.carrier → airlines', count(*)
FROM flights f WHERE NOT EXISTS (SELECT 1 FROM airlines al WHERE al.carrier = f.carrier)
UNION ALL
SELECT 'weather.origin → airports', count(*)
FROM weather w WHERE NOT EXISTS (SELECT 1 FROM airports a WHERE a.faa = w.origin);

-- Avions de flights absents du registre FAA (table planes), par compagnie.
-- Les lignes de planes sans aucune caractéristique (ajoutées à l'étape 4) ne comptent pas
-- comme des avions du registre : la requête donne le même résultat avant et après correction.
-- Résultat : 716 avions, 37 704 vols, dont 95 % chez MQ (Envoy) et AA (American), qui
--            déclarent des numéros de flotte et non des immatriculations
SELECT f.carrier, count(DISTINCT f.tailnum) AS avions_absents, count(*) AS vols
FROM flights f
LEFT JOIN planes p ON p.tailnum = f.tailnum
WHERE f.tailnum IS NOT NULL AND trim(f.tailnum) <> ''
  AND (p.tailnum IS NULL OR (p.year IS NULL AND p.type IS NULL AND p.manufacturer IS NULL AND p.model IS NULL
                             AND p.engines IS NULL AND p.seats IS NULL AND p.speed IS NULL AND p.engine IS NULL))
GROUP BY ROLLUP (f.carrier)
ORDER BY f.carrier IS NULL, vols DESC;

-- Vols sans observation météo correspondante (même aéroport, date et heure).
-- Résultat : 206 696 vols sur 252 704 (la table weather ne couvre qu'EWR, de janvier à mai)
SELECT count(*) AS vols_sans_meteo, (SELECT count(*) FROM flights) AS vols
FROM flights f
WHERE NOT EXISTS (SELECT 1 FROM weather w
                  WHERE (w.origin, w.year, w.month, w.day, w.hour) = (f.origin, f.year, f.month, f.day, f.hour));
