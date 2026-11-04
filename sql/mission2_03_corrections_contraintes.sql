-- =============================================================================
-- Mission 2 · Étape 4 : corrections des données, clés primaires et étrangères
-- =============================================================================
-- Requêtes reconstituées : elles amènent la base de l'état « juste après l'import »
-- à l'état actuel de la base Supabase. Tout est dans une transaction : en cas
-- d'erreur, rien n'est modifié.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Valeurs manquantes déguisées en texte → vrais NULL
-- -----------------------------------------------------------------------------
UPDATE airports SET tzone = NULL WHERE tzone = '\N';                              -- 3 aéroports
UPDATE flights SET tailnum = NULL WHERE tailnum IS NOT NULL AND trim(tailnum) = '';  -- 1 973 vols

-- -----------------------------------------------------------------------------
-- 2. Les 4 destinations absentes de airports (énoncé : BQN, PSE, SJU, STT)
--    Territoires américains des Caraïbes : UTC−4, sans heure d'été.
-- -----------------------------------------------------------------------------
INSERT INTO airports (faa, name, lat, lon, tz, dst, tzone) VALUES
    ('BQN', 'Rafael Hernandez Airport', 18.4949, -67.1294, -4, 'N', 'America/Puerto_Rico'),
    ('PSE', 'Mercedita Airport',        18.0083, -66.5630, -4, 'N', 'America/Puerto_Rico'),
    ('SJU', 'San Juan Airport',         18.4394, -66.0018, -4, 'N', 'America/Puerto_Rico'),
    ('STT', 'Cyril E. King Airport',    18.3373, -64.9734, -4, 'N', 'America/St_Thomas')
ON CONFLICT (faa) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Avions de flights absents du registre FAA (énoncé : « des centaines d'avions »)
--    On ajoute leur immatriculation seule, sans inventer de caractéristiques : la clé
--    étrangère devient valide sans perdre l'information sur les 37 704 vols concernés.
-- -----------------------------------------------------------------------------
INSERT INTO planes (tailnum)
SELECT DISTINCT f.tailnum
FROM flights f
WHERE f.tailnum IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM planes p WHERE p.tailnum = f.tailnum);              -- 716 avions

-- -----------------------------------------------------------------------------
-- 4. Clés primaires composées (unicité vérifiée dans mission2_02_controles.sql)
-- -----------------------------------------------------------------------------
ALTER TABLE flights ADD CONSTRAINT flights_pkey PRIMARY KEY (flight, year, month, day, hour, carrier);
ALTER TABLE weather ADD CONSTRAINT weather_pkey PRIMARY KEY (year, month, day, hour, origin);
ALTER TABLE weather ADD CONSTRAINT weather_origin_time_unique UNIQUE (origin, time_hour);
-- Note : la base Supabase contient aussi flights_unique et weather_unique, qui reprennent
-- exactement les colonnes des clés primaires. Elles sont redondantes et ne sont pas reproduites.

-- -----------------------------------------------------------------------------
-- 5. Clés étrangères
--    Chaque vol a une compagnie, un aéroport de départ, une destination et un avion
--    (relations 1-N). Compagnies ↔ aéroports est une relation N-N, portée par flights.
--    Pas de clé étrangère flights → weather : la météo ne couvre qu'une partie des vols.
-- -----------------------------------------------------------------------------
ALTER TABLE flights ADD CONSTRAINT fk_flights_airlines FOREIGN KEY (carrier) REFERENCES airlines (carrier);
ALTER TABLE flights ADD CONSTRAINT fk_flights_origin   FOREIGN KEY (origin)  REFERENCES airports (faa);
ALTER TABLE flights ADD CONSTRAINT fk_flights_dest     FOREIGN KEY (dest)    REFERENCES airports (faa);
ALTER TABLE flights ADD CONSTRAINT fk_flights_tailnum  FOREIGN KEY (tailnum) REFERENCES planes (tailnum);
ALTER TABLE weather ADD CONSTRAINT fk_weather_origin   FOREIGN KEY (origin)  REFERENCES airports (faa);

COMMIT;
