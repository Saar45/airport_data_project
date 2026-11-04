-- =============================================================================
-- Mission 1 : se familiariser avec les données (les 8 questions de l'énoncé)
-- =============================================================================
-- Requêtes en lecture seule. On peut les lancer telles quelles dans le SQL Editor
-- de Supabase, ou avec psql : psql -d <base> -f sql/mission1_exploration.sql
--
-- Les résultats indiqués en commentaire ont été obtenus sur la base Supabase de
-- l'équipe. Ce sont les mêmes que dans l'onglet « Mission 1 » de l'application.
--
-- Rappel : en Mission 2, la base a été corrigée. 4 aéroports manquants ont été
-- ajoutés (BQN, PSE, SJU, STT), ainsi que 716 avions absents du registre FAA,
-- enregistrés sans caractéristiques. Quand ces ajouts changent la réponse, la
-- requête donne aussi la valeur du fichier fourni (celle qu'attend l'énoncé).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Q1. Combien y a-t-il d'aéroports (en tout, de départ, de destination),
--     d'aéroports sans heure d'été, de fuseaux horaires, de compagnies,
--     d'avions et de vols annulés ?
-- -----------------------------------------------------------------------------

-- Aéroports en tout, de départ et de destination.
-- Résultat : 1 462 en base (1 458 dans le fichier fourni) · 3 de départ · 103 de destination
SELECT
    (SELECT count(*) FROM airports)                                                AS aeroports_en_base,
    (SELECT count(*) FROM airports WHERE faa NOT IN ('BQN', 'PSE', 'SJU', 'STT'))  AS aeroports_fichier_fourni,
    (SELECT count(DISTINCT origin) FROM flights)                                   AS aeroports_de_depart,
    (SELECT count(DISTINCT dest) FROM flights)                                     AS aeroports_de_destination;

-- Aéroports où l'on ne passe pas à l'heure d'été (dst = 'N').
-- Résultat : 27 en base, 23 dans le fichier fourni (valeur de l'énoncé)
SELECT
    count(*) FILTER (WHERE dst = 'N')                                                 AS sans_heure_ete_en_base,
    count(*) FILTER (WHERE dst = 'N' AND faa NOT IN ('BQN', 'PSE', 'SJU', 'STT'))     AS sans_heure_ete_fichier_fourni
FROM airports;

-- Fuseaux horaires (tzone). Dans le fichier fourni, 3 aéroports avaient la valeur
-- « \N » (valeur manquante), désormais NULL. En la comptant comme une valeur, comme
-- l'énoncé, on retrouve 10 fuseaux.
-- Résultat : 11 en base · 3 aéroports sans fuseau · 10 dans le fichier fourni
SELECT
    count(DISTINCT tzone)                                                    AS fuseaux_en_base,
    count(*) FILTER (WHERE tzone IS NULL)                                    AS aeroports_sans_fuseau,
    (SELECT count(DISTINCT coalesce(tzone, '\N'))
       FROM airports WHERE faa NOT IN ('BQN', 'PSE', 'SJU', 'STT'))          AS fuseaux_fichier_fourni
FROM airports;

-- Détail des fuseaux horaires.
SELECT coalesce(tzone, '(manquant)') AS tzone, count(*) AS aeroports
FROM airports
GROUP BY tzone
ORDER BY aeroports DESC;

-- Compagnies, avions et vols annulés. Un vol annulé n'a pas d'heure de départ réelle.
-- Résultat : 16 compagnies · 4 038 avions en base (3 322 dans le fichier fourni + 716 ajoutés)
--            · 3 982 immatriculations dans flights · 6 481 vols annulés
SELECT
    (SELECT count(*) FROM airlines)                                AS compagnies,
    (SELECT count(*) FROM planes)                                  AS avions_en_base,
    (SELECT count(*) FROM planes
      WHERE year IS NULL AND type IS NULL AND manufacturer IS NULL AND model IS NULL
        AND engines IS NULL AND seats IS NULL AND speed IS NULL AND engine IS NULL) AS avions_ajoutes_sans_caracteristiques,
    (SELECT count(DISTINCT tailnum) FROM flights)                  AS immatriculations_dans_flights,
    (SELECT count(*) FROM flights WHERE dep_time IS NULL)          AS vols_annules;


-- -----------------------------------------------------------------------------
-- Q2. Aéroport de départ le plus emprunté ? 10 destinations les plus (moins)
--     prisées, avec le nom complet et le % ? 10 avions qui ont le plus (moins)
--     décollé ?
-- -----------------------------------------------------------------------------

-- Aéroports de départ. Résultat : EWR (Newark Liberty Intl) 91 241 vols, 36,11 %
SELECT f.origin, a.name AS aeroport, count(*) AS vols,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_vols
FROM flights f
JOIN airports a ON a.faa = f.origin
GROUP BY f.origin, a.name
ORDER BY vols DESC;

-- 10 destinations les plus prisées. Résultat : ATL 12 946 (5,12 %), ORD 12 654, LAX 11 895…
SELECT f.dest, a.name AS destination, count(*) AS vols,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_vols
FROM flights f
LEFT JOIN airports a ON a.faa = f.dest
GROUP BY f.dest, a.name
ORDER BY vols DESC, f.dest
LIMIT 10;

-- 10 destinations les moins prisées. Résultat : LEX 1 vol, SBN 4, HDN 15, MTJ 15…
SELECT f.dest, a.name AS destination, count(*) AS vols,
       round(100.0 * count(*) / sum(count(*)) OVER (), 4) AS pct_vols
FROM flights f
LEFT JOIN airports a ON a.faa = f.dest
GROUP BY f.dest, a.name
ORDER BY vols ASC, f.dest
LIMIT 10;

-- 10 avions qui ont le plus décollé (nombre de vols, comme dans le notebook et l'application).
-- Les avions d'Envoy Air (MQ) sont absents du registre FAA : constructeur inconnu.
SELECT f.tailnum, string_agg(DISTINCT al.name, ', ') AS compagnie, count(*) AS vols,
       coalesce(p.manufacturer, 'inconnu (absent du registre FAA)') AS constructeur, p.model
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
LEFT JOIN planes p ON p.tailnum = f.tailnum
WHERE f.tailnum IS NOT NULL
GROUP BY f.tailnum, p.manufacturer, p.model
ORDER BY vols DESC, f.tailnum
LIMIT 10;

-- 10 avions qui ont le moins décollé (beaucoup d'avions n'ont décollé qu'une fois :
-- en cas d'égalité, ordre alphabétique de l'immatriculation).
SELECT f.tailnum, string_agg(DISTINCT al.name, ', ') AS compagnie, count(*) AS vols,
       coalesce(p.manufacturer, 'inconnu (absent du registre FAA)') AS constructeur, p.model
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
LEFT JOIN planes p ON p.tailnum = f.tailnum
WHERE f.tailnum IS NOT NULL
GROUP BY f.tailnum, p.manufacturer, p.model
ORDER BY vols ASC, f.tailnum
LIMIT 10;


-- -----------------------------------------------------------------------------
-- Q3. Combien chaque compagnie a desservi de destinations ; et par aéroport
--     d'origine ? (Les graphiques sont dans l'application, onglet Mission 1.)
-- -----------------------------------------------------------------------------

-- Destinations par compagnie. Résultat : ExpressJet 61, Endeavor 47, United 45…
SELECT al.name AS compagnie, count(DISTINCT f.dest) AS destinations
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
GROUP BY al.name
ORDER BY destinations DESC, compagnie;

-- Destinations par compagnie et par aéroport d'origine (une colonne par aéroport).
SELECT al.name AS compagnie,
       count(DISTINCT f.dest) FILTER (WHERE f.origin = 'EWR') AS depuis_ewr,
       count(DISTINCT f.dest) FILTER (WHERE f.origin = 'JFK') AS depuis_jfk,
       count(DISTINCT f.dest) FILTER (WHERE f.origin = 'LGA') AS depuis_lga,
       count(DISTINCT f.dest)                                 AS total
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
GROUP BY al.name
ORDER BY total DESC, compagnie;


-- -----------------------------------------------------------------------------
-- Q4. Tous les vols ayant atterri à Houston (IAH ou HOU) ? Combien de vols de
--     NYC vers Seattle, combien de compagnies desservent cette destination et
--     combien d'avions « uniques » ?
-- -----------------------------------------------------------------------------

-- Résumé Houston. Résultat : 6 958 vols vers Houston (IAH 5 438, HOU 1 520), dont 6 846 ont
--   réellement atterri (heure d'arrivée connue) ; les autres ont été annulés ou déroutés.
SELECT count(*)                                     AS vols_vers_houston,
       count(*) FILTER (WHERE dest = 'IAH')         AS vers_iah,
       count(*) FILTER (WHERE dest = 'HOU')         AS vers_hou,
       count(*) FILTER (WHERE arr_time IS NOT NULL) AS ayant_atterri
FROM flights
WHERE dest IN ('IAH', 'HOU');

-- Liste des vols vers Houston.
SELECT f.year, f.month, f.day, f.sched_dep_time, al.name AS compagnie, f.flight,
       f.origin, f.dest, a.name AS aeroport_arrivee, f.tailnum, f.arr_time
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
JOIN airports a  ON a.faa = f.dest
WHERE f.dest IN ('IAH', 'HOU')
ORDER BY f.year, f.month, f.day, f.sched_dep_time, f.flight;

-- NYC → Seattle (SEA). Résultat : 2 736 vols · 5 compagnies · 856 avions uniques
SELECT count(*)                                            AS vols_vers_seattle,
       count(DISTINCT f.carrier)                           AS compagnies,
       string_agg(DISTINCT al.name, ', ')                  AS noms_compagnies,
       count(DISTINCT f.tailnum)                           AS avions_uniques
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
WHERE f.dest = 'SEA';


-- -----------------------------------------------------------------------------
-- Q5. Nombre de vols par destination ? Trier les vols suivant la destination,
--     l'aéroport d'origine, la compagnie (ordre alphabétique croissant, avec les
--     jointures nécessaires pour obtenir les noms explicites des aéroports).
-- -----------------------------------------------------------------------------

-- Vols par destination (103 lignes).
SELECT f.dest, a.name AS destination, count(*) AS vols,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_vols
FROM flights f
LEFT JOIN airports a ON a.faa = f.dest
GROUP BY f.dest, a.name
ORDER BY vols DESC, f.dest;

-- Vols triés par destination, origine et compagnie (noms explicites).
-- Retirer le LIMIT pour obtenir les 252 704 vols.
SELECT ad.name AS destination, f.dest, ao.name AS origine, f.origin, al.name AS compagnie,
       f.flight, f.year, f.month, f.day
FROM flights f
JOIN airports ao ON ao.faa = f.origin
JOIN airports ad ON ad.faa = f.dest
JOIN airlines al ON al.carrier = f.carrier
ORDER BY destination, origine, compagnie, f.year, f.month, f.day, f.sched_dep_time
LIMIT 100;


-- -----------------------------------------------------------------------------
-- Q6. Compagnies qui n'opèrent pas sur tous les aéroports d'origine ?
--     Compagnies qui desservent l'ensemble des destinations ? Tableau des
--     origines et destinations pour l'ensemble des compagnies.
-- -----------------------------------------------------------------------------

-- Compagnies absentes d'au moins un aéroport de départ.
-- Résultat : 8 compagnies (AirTran, Alaska, Frontier, Hawaiian, Mesa, SkyWest,
--            Southwest, Virgin America)
SELECT al.name AS compagnie,
       string_agg(DISTINCT f.origin, ', ' ORDER BY f.origin) AS aeroports_desservis
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
GROUP BY al.name
HAVING count(DISTINCT f.origin) < (SELECT count(DISTINCT origin) FROM flights)
ORDER BY compagnie;

-- Même question, sous forme de paires (compagnie, aéroport non desservi).
SELECT al.name AS compagnie, o.origin AS aeroport_non_desservi
FROM airlines al
CROSS JOIN (SELECT DISTINCT origin FROM flights) o
WHERE EXISTS (SELECT 1 FROM flights f WHERE f.carrier = al.carrier)
  AND NOT EXISTS (SELECT 1 FROM flights f WHERE f.carrier = al.carrier AND f.origin = o.origin)
ORDER BY compagnie, aeroport_non_desservi;

-- Compagnies qui desservent toutes les destinations. Résultat : aucune.
SELECT al.name AS compagnie, count(DISTINCT f.dest) AS destinations
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
GROUP BY al.name
HAVING count(DISTINCT f.dest) = (SELECT count(DISTINCT dest) FROM flights);

-- Celle qui en dessert le plus. Résultat : ExpressJet Airlines Inc., 61 destinations sur 103
SELECT al.name AS compagnie, count(DISTINCT f.dest) AS destinations,
       (SELECT count(DISTINCT dest) FROM flights) AS destinations_au_total
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
GROUP BY al.name
ORDER BY destinations DESC
LIMIT 1;

-- Tableau des origines et destinations de chaque compagnie (431 lignes).
SELECT f.origin, ao.name AS origine, f.dest, ad.name AS destination,
       f.carrier, al.name AS compagnie, count(*) AS vols
FROM flights f
JOIN airports ao ON ao.faa = f.origin
JOIN airports ad ON ad.faa = f.dest
JOIN airlines al ON al.carrier = f.carrier
GROUP BY f.origin, ao.name, f.dest, ad.name, f.carrier, al.name
ORDER BY f.origin, f.dest, compagnie;


-- -----------------------------------------------------------------------------
-- Q7. Quelles sont les destinations exclusives à certaines compagnies ?
-- -----------------------------------------------------------------------------

-- Destinations desservies par une seule compagnie. Résultat : 29 destinations
SELECT f.dest, a.name AS destination, min(al.name) AS compagnie_exclusive, count(*) AS vols
FROM flights f
JOIN airports a  ON a.faa = f.dest
JOIN airlines al ON al.carrier = f.carrier
GROUP BY f.dest, a.name
HAVING count(DISTINCT f.carrier) = 1
ORDER BY compagnie_exclusive, f.dest;


-- -----------------------------------------------------------------------------
-- Q8. Filtrer les vols exploités par United, American ou Delta.
-- -----------------------------------------------------------------------------

-- Nombre de vols par compagnie et total.
-- Résultat : United 44 165 · Delta 35 975 · American 24 602 · total 104 742 (41,4 % des vols)
SELECT coalesce(al.name, 'Total United + American + Delta') AS compagnie, count(*) AS vols,
       round(100.0 * count(*) / (SELECT count(*) FROM flights), 1) AS pct_des_vols
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
WHERE f.carrier IN ('UA', 'AA', 'DL')
GROUP BY ROLLUP (al.name)
ORDER BY al.name IS NULL, vols DESC;

-- Les vols filtrés. Retirer le LIMIT pour obtenir les 104 742 vols.
SELECT f.year, f.month, f.day, f.dep_time, al.name AS compagnie, f.flight, f.origin, f.dest
FROM flights f
JOIN airlines al ON al.carrier = f.carrier
WHERE f.carrier IN ('UA', 'AA', 'DL')
ORDER BY f.year, f.month, f.day, f.sched_dep_time, f.flight
LIMIT 100;
