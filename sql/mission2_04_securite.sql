-- =============================================================================
-- Mission 2 · Étape 5 : sécurisation de l'accès à la base
-- =============================================================================
-- Requêtes reconstituées. L'application web (Mission 3) se connecte avec un rôle
-- dédié en lecture seule, shiny_reader, et jamais avec le compte administrateur.
-- Si l'application ou son fichier .env fuitait, personne ne pourrait modifier ni
-- supprimer les données.
-- Autres mesures, hors SQL :
-- - connexion chiffrée (sslmode=require) ;
-- - mots de passe dans les Secrets de Colab et dans .env (ignoré par git), jamais dans le code.
-- =============================================================================

-- 1. Rôle de l'application (créé sans droit de connexion s'il n'existe pas).
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'shiny_reader') THEN
        CREATE ROLE shiny_reader NOLOGIN;
    END IF;
END
$$;
-- Le droit de connexion et le mot de passe se donnent à part, avec un mot de passe fort
-- que l'on ne commite jamais :  ALTER ROLE shiny_reader WITH LOGIN PASSWORD '…';

-- 2. Droits : lecture seule.
GRANT USAGE ON SCHEMA public TO shiny_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO shiny_reader;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO shiny_reader;           -- nécessaire pour pg_dump
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO shiny_reader;  -- tables futures

-- 3. Row Level Security : chaque table n'est lisible que par les rôles qu'une policy
--    autorise. Sur Supabase, cela ferme aussi l'accès public par l'API (clé « anon »).
ALTER TABLE airlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE airports ENABLE ROW LEVEL SECURITY;
ALTER TABLE flights  ENABLE ROW LEVEL SECURITY;
ALTER TABLE planes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather  ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "app read" ON airlines;
DROP POLICY IF EXISTS "app read" ON airports;
DROP POLICY IF EXISTS "app read" ON flights;
DROP POLICY IF EXISTS "app read" ON planes;
DROP POLICY IF EXISTS "app read" ON weather;
CREATE POLICY "app read" ON airlines FOR SELECT TO shiny_reader USING (true);
CREATE POLICY "app read" ON airports FOR SELECT TO shiny_reader USING (true);
CREATE POLICY "app read" ON flights  FOR SELECT TO shiny_reader USING (true);
CREATE POLICY "app read" ON planes   FOR SELECT TO shiny_reader USING (true);
CREATE POLICY "app read" ON weather  FOR SELECT TO shiny_reader USING (true);

-- 4. Vérification : droits du rôle sur chaque table.
-- Résultat attendu : lecture = true, écriture = false, suppression = false pour les 5 tables
SELECT c.relname AS table_name,
       has_table_privilege('shiny_reader', c.oid, 'SELECT') AS lecture,
       has_table_privilege('shiny_reader', c.oid, 'INSERT') OR has_table_privilege('shiny_reader', c.oid, 'UPDATE') AS ecriture,
       has_table_privilege('shiny_reader', c.oid, 'DELETE') AS suppression,
       c.relrowsecurity AS rls
FROM pg_class c
WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r'
ORDER BY c.relname;
