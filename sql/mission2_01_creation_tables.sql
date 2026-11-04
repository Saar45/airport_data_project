-- =============================================================================
-- Mission 2 · Étape 1 : création des tables (avant l'import des données)
-- =============================================================================
-- Requêtes reconstituées. Elles reproduisent la structure de la base Supabase de
-- l'équipe (types identiques à ceux de dumps/supabase_dump.sql).
--
-- Ordre complet de la Mission 2 :
--   1. ce fichier : création des tables ;
--   2. import des 5 fichiers : notebook Mission2_Import_Supabase.ipynb ;
--   3. mission2_02_controles.sql : contrôles demandés par l'énoncé ;
--   4. mission2_03_corrections_contraintes.sql : corrections, clés primaires et étrangères ;
--   5. mission2_04_securite.sql : rôle de l'application en lecture seule et RLS.
--
-- Choix de conception :
-- - Les tables de référence ont tout de suite leur clé primaire naturelle :
--   faa (code FAA de l'aéroport), carrier (code de la compagnie), tailnum (immatriculation).
-- - flights et weather reçoivent un identifiant technique (id) pour l'import. Leur
--   clé primaire composée est ajoutée à l'étape 4, une fois son unicité vérifiée
--   (étape 3).
-- - Aucune clé étrangère à ce stade : les données fournies ne les respectent pas
--   toutes (problèmes signalés par l'énoncé, corrigés à l'étape 4).
-- =============================================================================

CREATE TABLE public.airlines (
    carrier character varying(10) PRIMARY KEY,      -- code à 2 caractères, ex. UA
    name    text
);

CREATE TABLE public.airports (
    faa   character varying(10) PRIMARY KEY,        -- code FAA à 3 caractères, ex. JFK
    name  text,
    lat   double precision,
    lon   double precision,
    alt   integer,                                  -- altitude en pieds
    tz    integer,                                  -- décalage horaire par rapport à GMT
    dst   character varying(5),                     -- heure d'été : A = oui, N = non, U = inconnu
    tzone text                                      -- fuseau IANA, ex. America/New_York
);

CREATE TABLE public.planes (
    tailnum      character varying(20) PRIMARY KEY, -- immatriculation, ex. N10156
    year         smallint,                          -- année de fabrication
    type         text,
    manufacturer text,
    model        text,
    engines      integer,
    seats        integer,
    speed        integer,
    engine       text
);

CREATE TABLE public.flights (
    id             bigint GENERATED ALWAYS AS IDENTITY,  -- identifiant technique pour l'import
    year           integer NOT NULL,
    month          integer NOT NULL,
    day            integer NOT NULL,
    dep_time       integer,              -- heure réelle de départ (HHMM) ; vide = vol annulé
    sched_dep_time integer,              -- heure prévue de départ (HHMM)
    dep_delay      double precision,     -- retard au départ, en minutes
    arr_time       integer,
    sched_arr_time integer,
    arr_delay      double precision,     -- retard à l'arrivée, en minutes
    carrier        character varying(10) NOT NULL,
    flight         integer NOT NULL,     -- numéro de vol (pas unique à lui seul)
    tailnum        character varying(20),
    origin         character varying(10),
    dest           character varying(10),
    air_time       double precision,
    distance       double precision,     -- en miles
    hour           integer NOT NULL,     -- heure prévue de départ
    minute         integer,
    time_hour      timestamp with time zone
);

CREATE TABLE public.weather (
    id         bigint GENERATED ALWAYS AS IDENTITY,      -- identifiant technique pour l'import
    origin     character varying(10) NOT NULL,           -- station météo = aéroport de départ
    year       integer NOT NULL,
    month      integer NOT NULL,
    day        integer NOT NULL,
    hour       integer NOT NULL,
    temp       double precision,     -- température (°F)
    dewp       double precision,     -- point de rosée (°F)
    humid      double precision,     -- humidité relative (%)
    wind_dir   double precision,     -- direction du vent (degrés)
    wind_speed double precision,     -- vitesse du vent (mph)
    wind_gust  double precision,     -- rafales (mph)
    precip     double precision,     -- précipitations (pouces)
    pressure   double precision,     -- pression au niveau de la mer (mbar)
    visib      double precision,     -- visibilité (miles)
    time_hour  timestamp with time zone
);
