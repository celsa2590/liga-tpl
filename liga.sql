--
-- PostgreSQL database dump
--

\restrict E0TRUEX5mAHAARsTm4ZLuBwNXZSoJMJR8NPLM47R1QHXvVEn1cXui0lxM5kMtJf

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg13+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: clubs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clubs (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    commune character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: clubs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clubs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clubs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clubs_id_seq OWNED BY public.clubs.id;


--
-- Name: match_game_sets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_game_sets (
    id integer NOT NULL,
    match_game_id integer NOT NULL,
    set_number integer NOT NULL,
    home_games integer,
    away_games integer,
    CONSTRAINT match_game_sets_set_number_check CHECK ((set_number = ANY (ARRAY[1, 2, 3])))
);


--
-- Name: match_game_sets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.match_game_sets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: match_game_sets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_game_sets_id_seq OWNED BY public.match_game_sets.id;


--
-- Name: match_games; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_games (
    id integer NOT NULL,
    match_id integer NOT NULL,
    game_number integer NOT NULL,
    venue_club_id integer NOT NULL,
    scheduled_at timestamp without time zone NOT NULL,
    home_player_1_id integer,
    home_player_2_id integer,
    away_player_1_id integer,
    away_player_2_id integer,
    home_sets integer,
    away_sets integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT match_games_game_number_check CHECK ((game_number = ANY (ARRAY[1, 2, 3])))
);


--
-- Name: match_games_backup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_games_backup (
    id integer,
    match_id integer,
    game_number integer,
    venue_club_id integer,
    scheduled_at timestamp without time zone,
    home_player_1_id integer,
    home_player_2_id integer,
    away_player_1_id integer,
    away_player_2_id integer,
    home_sets integer,
    away_sets integer,
    created_at timestamp without time zone
);


--
-- Name: match_games_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.match_games_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: match_games_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_games_id_seq OWNED BY public.match_games.id;


--
-- Name: matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.matches (
    id integer NOT NULL,
    season_name character varying(100) NOT NULL,
    round_number integer NOT NULL,
    home_team_id integer NOT NULL,
    away_team_id integer NOT NULL,
    scheduled_date date NOT NULL,
    status character varying(20) DEFAULT 'scheduled'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT matches_check CHECK ((home_team_id <> away_team_id))
);


--
-- Name: players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.players (
    id integer NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    nickname character varying(100),
    category character varying(20),
    ranking_points integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    club_id integer NOT NULL,
    name character varying(100) NOT NULL,
    logo_url text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: match_schedule; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.match_schedule AS
 SELECT m.id AS match_id,
    m.season_name,
    m.round_number,
    th.id AS home_team_id,
    th.name AS home_team_name,
    ta.id AS away_team_id,
    ta.name AS away_team_name,
    mg.game_number,
    c.name AS venue_club,
    mg.scheduled_at,
    (((hp1.first_name)::text || ' '::text) || (hp1.last_name)::text) AS home_player_1,
    (((hp2.first_name)::text || ' '::text) || (hp2.last_name)::text) AS home_player_2,
    (((ap1.first_name)::text || ' '::text) || (ap1.last_name)::text) AS away_player_1,
    (((ap2.first_name)::text || ' '::text) || (ap2.last_name)::text) AS away_player_2,
    mg.home_sets,
    mg.away_sets,
        CASE
            WHEN ((mg.home_sets IS NULL) OR (mg.away_sets IS NULL)) THEN 'scheduled'::text
            WHEN (mg.home_sets > mg.away_sets) THEN 'home_win'::text
            WHEN (mg.away_sets > mg.home_sets) THEN 'away_win'::text
            ELSE 'draw'::text
        END AS result_status
   FROM ((((((((public.matches m
     JOIN public.teams th ON ((th.id = m.home_team_id)))
     JOIN public.teams ta ON ((ta.id = m.away_team_id)))
     JOIN public.match_games mg ON ((mg.match_id = m.id)))
     JOIN public.clubs c ON ((c.id = mg.venue_club_id)))
     LEFT JOIN public.players hp1 ON ((hp1.id = mg.home_player_1_id)))
     LEFT JOIN public.players hp2 ON ((hp2.id = mg.home_player_2_id)))
     LEFT JOIN public.players ap1 ON ((ap1.id = mg.away_player_1_id)))
     LEFT JOIN public.players ap2 ON ((ap2.id = mg.away_player_2_id)));


--
-- Name: matches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.matches_id_seq OWNED BY public.matches.id;


--
-- Name: players_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.players_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: players_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.players_id_seq OWNED BY public.players.id;


--
-- Name: standings; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.standings AS
 WITH team_stats AS (
         SELECT t.id AS team_id,
            t.name AS team_name,
            c.name AS club_name,
            count(mg.id) FILTER (WHERE ((mg.home_sets IS NOT NULL) AND (mg.away_sets IS NOT NULL))) AS played_games,
            count(*) FILTER (WHERE ((mg.home_sets IS NOT NULL) AND (mg.away_sets IS NOT NULL) AND (((mg.home_sets > mg.away_sets) AND (m.home_team_id = t.id)) OR ((mg.away_sets > mg.home_sets) AND (m.away_team_id = t.id))))) AS won_games,
            count(*) FILTER (WHERE ((mg.home_sets IS NOT NULL) AND (mg.away_sets IS NOT NULL) AND (((mg.home_sets > mg.away_sets) AND (m.away_team_id = t.id)) OR ((mg.away_sets > mg.home_sets) AND (m.home_team_id = t.id))))) AS lost_games,
            COALESCE(sum(
                CASE
                    WHEN (m.home_team_id = t.id) THEN COALESCE(mg.home_sets, 0)
                    WHEN (m.away_team_id = t.id) THEN COALESCE(mg.away_sets, 0)
                    ELSE 0
                END), (0)::bigint) AS sets_for,
            COALESCE(sum(
                CASE
                    WHEN (m.home_team_id = t.id) THEN COALESCE(mg.away_sets, 0)
                    WHEN (m.away_team_id = t.id) THEN COALESCE(mg.home_sets, 0)
                    ELSE 0
                END), (0)::bigint) AS sets_against
           FROM (((public.teams t
             JOIN public.clubs c ON ((c.id = t.club_id)))
             LEFT JOIN public.matches m ON (((m.home_team_id = t.id) OR (m.away_team_id = t.id))))
             LEFT JOIN public.match_games mg ON ((mg.match_id = m.id)))
          GROUP BY t.id, t.name, c.name
        ), match_results AS (
         SELECT m.id AS match_id,
            m.home_team_id,
            m.away_team_id,
            count(*) FILTER (WHERE ((mg.home_sets IS NOT NULL) AND (mg.away_sets IS NOT NULL) AND (mg.home_sets > mg.away_sets))) AS home_game_wins,
            count(*) FILTER (WHERE ((mg.home_sets IS NOT NULL) AND (mg.away_sets IS NOT NULL) AND (mg.away_sets > mg.home_sets))) AS away_game_wins
           FROM (public.matches m
             JOIN public.match_games mg ON ((mg.match_id = m.id)))
          GROUP BY m.id, m.home_team_id, m.away_team_id
        ), team_match_points AS (
         SELECT mr.home_team_id AS team_id,
            sum(
                CASE
                    WHEN ((mr.home_game_wins > mr.away_game_wins) AND (mr.home_game_wins = 2) AND (mr.away_game_wins = 0)) THEN 3
                    WHEN ((mr.home_game_wins > mr.away_game_wins) AND (mr.home_game_wins = 2) AND (mr.away_game_wins = 1)) THEN 2
                    ELSE 0
                END) AS points_from_home,
            (0)::bigint AS points_from_away
           FROM match_results mr
          GROUP BY mr.home_team_id
        UNION ALL
         SELECT mr.away_team_id AS team_id,
            (0)::bigint AS points_from_home,
            sum(
                CASE
                    WHEN ((mr.away_game_wins > mr.home_game_wins) AND (mr.away_game_wins = 2) AND (mr.home_game_wins = 0)) THEN 3
                    WHEN ((mr.away_game_wins > mr.home_game_wins) AND (mr.away_game_wins = 2) AND (mr.home_game_wins = 1)) THEN 2
                    ELSE 0
                END) AS points_from_away
           FROM match_results mr
          GROUP BY mr.away_team_id
        ), points_summary AS (
         SELECT team_match_points.team_id,
            COALESCE(sum((team_match_points.points_from_home + team_match_points.points_from_away)), ((0)::bigint)::numeric) AS total_points
           FROM team_match_points
          GROUP BY team_match_points.team_id
        ), bonus_summary AS (
         SELECT mr.home_team_id AS team_id,
            count(*) FILTER (WHERE ((mr.home_game_wins = 2) AND (mr.away_game_wins = 0))) AS bonus_points
           FROM match_results mr
          GROUP BY mr.home_team_id
        UNION ALL
         SELECT mr.away_team_id AS team_id,
            count(*) FILTER (WHERE ((mr.away_game_wins = 2) AND (mr.home_game_wins = 0))) AS bonus_points
           FROM match_results mr
          GROUP BY mr.away_team_id
        ), bonus_total AS (
         SELECT bonus_summary.team_id,
            COALESCE(sum(bonus_summary.bonus_points), ((0)::bigint)::numeric) AS bonus_points
           FROM bonus_summary
          GROUP BY bonus_summary.team_id
        )
 SELECT 'Liga San Miguel 2026'::character varying(100) AS season_name,
    ts.team_id,
    ts.team_name,
    ts.club_name,
    ts.played_games,
    ts.won_games,
    ts.lost_games,
    ts.sets_for,
    ts.sets_against,
    (ts.sets_for - ts.sets_against) AS sets_diff,
    (COALESCE(ps.total_points, ((0)::bigint)::numeric) - COALESCE(bt.bonus_points, ((0)::bigint)::numeric)) AS base_points,
    COALESCE(bt.bonus_points, ((0)::bigint)::numeric) AS bonus_points,
    COALESCE(ps.total_points, ((0)::bigint)::numeric) AS total_points
   FROM ((team_stats ts
     LEFT JOIN points_summary ps ON ((ps.team_id = ts.team_id)))
     LEFT JOIN bonus_total bt ON ((bt.team_id = ts.team_id)));


--
-- Name: team_players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_players (
    id integer NOT NULL,
    team_id integer NOT NULL,
    player_id integer NOT NULL,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    active boolean DEFAULT true
);


--
-- Name: team_players_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.team_players_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: team_players_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.team_players_id_seq OWNED BY public.team_players.id;


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: clubs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs ALTER COLUMN id SET DEFAULT nextval('public.clubs_id_seq'::regclass);


--
-- Name: match_game_sets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_game_sets ALTER COLUMN id SET DEFAULT nextval('public.match_game_sets_id_seq'::regclass);


--
-- Name: match_games id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games ALTER COLUMN id SET DEFAULT nextval('public.match_games_id_seq'::regclass);


--
-- Name: matches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches ALTER COLUMN id SET DEFAULT nextval('public.matches_id_seq'::regclass);


--
-- Name: players id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players ALTER COLUMN id SET DEFAULT nextval('public.players_id_seq'::regclass);


--
-- Name: team_players id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_players ALTER COLUMN id SET DEFAULT nextval('public.team_players_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Data for Name: clubs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clubs (id, name, commune, created_at) FROM stdin;
2	Propadel	San Miguel	2026-03-06 01:30:09.157668
1	Espacio Active	San Miguel	2026-03-06 01:30:09.157668
3	Arena	San Miguel	2026-03-06 01:30:09.157668
4	Maiclub	San Miguel	2026-03-06 01:30:09.157668
\.


--
-- Data for Name: match_game_sets; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.match_game_sets (id, match_game_id, set_number, home_games, away_games) FROM stdin;
\.


--
-- Data for Name: match_games; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.match_games (id, match_id, game_number, venue_club_id, scheduled_at, home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, home_sets, away_sets, created_at) FROM stdin;
1	1	1	2	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
2	1	2	2	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
3	2	1	4	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
4	2	2	4	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
5	3	1	3	2026-05-30 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
6	3	2	3	2026-05-30 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
7	4	1	4	2026-05-30 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
8	4	2	4	2026-05-30 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
9	5	1	1	2026-06-13 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
10	5	2	1	2026-06-13 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
11	6	1	2	2026-06-13 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
12	6	2	2	2026-06-13 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
13	7	1	1	2026-07-04 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
14	7	2	1	2026-07-04 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
15	8	1	3	2026-07-04 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
16	8	2	3	2026-07-04 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
17	9	1	1	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
18	9	2	1	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
19	10	1	2	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
20	10	2	2	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
21	11	1	4	2026-07-26 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
22	11	2	4	2026-07-26 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
25	13	1	1	2026-08-01 20:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
26	13	2	1	2026-08-01 20:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
38	13	3	1	2026-08-01 20:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
39	1	3	2	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
27	2	3	4	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
28	3	3	3	2026-05-30 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
29	4	3	4	2026-05-30 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
30	5	3	1	2026-06-13 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
31	6	3	2	2026-06-13 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
32	7	3	1	2026-07-04 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
33	8	3	3	2026-07-04 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
34	9	3	1	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
35	10	3	2	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
36	11	3	4	2026-07-26 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
23	12	1	3	2026-07-26 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
24	12	2	3	2026-07-26 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
37	12	3	3	2026-07-26 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-27 16:15:51.383748
\.


--
-- Data for Name: match_games_backup; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.match_games_backup (id, match_id, game_number, venue_club_id, scheduled_at, home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, home_sets, away_sets, created_at) FROM stdin;
7	4	1	4	2026-05-23 14:30:00	13	14	9	10	\N	\N	2026-03-13 21:12:19.92258
8	4	2	4	2026-05-23 14:30:00	15	16	11	12	\N	\N	2026-03-13 21:12:19.92258
9	5	1	2	2026-06-21 14:30:00	9	10	5	6	\N	\N	2026-03-13 21:12:19.92258
10	5	2	2	2026-06-21 14:30:00	11	12	7	8	\N	\N	2026-03-13 21:12:19.92258
11	6	1	4	2026-06-21 14:30:00	13	14	1	2	\N	\N	2026-03-13 21:12:19.92258
12	6	2	4	2026-06-21 14:30:00	15	16	3	4	\N	\N	2026-03-13 21:12:19.92258
13	7	1	2	2026-07-11 14:30:00	9	10	1	2	\N	\N	2026-03-13 21:12:19.92258
14	7	2	2	2026-07-11 14:30:00	11	12	3	4	\N	\N	2026-03-13 21:12:19.92258
15	8	1	3	2026-07-11 14:30:00	5	6	13	14	\N	\N	2026-03-13 21:12:19.92258
16	8	2	3	2026-07-11 14:30:00	7	8	15	16	\N	\N	2026-03-13 21:12:19.92258
17	9	1	1	2026-07-18 14:30:00	1	2	5	6	\N	\N	2026-03-13 21:12:19.92258
18	9	2	1	2026-07-18 14:30:00	3	4	7	8	\N	\N	2026-03-13 21:12:19.92258
19	10	1	2	2026-07-18 14:30:00	13	14	9	10	\N	\N	2026-03-13 21:12:19.92258
20	10	2	2	2026-07-18 14:30:00	15	16	11	12	\N	\N	2026-03-13 21:12:19.92258
21	11	1	3	2026-07-25 14:30:00	9	10	5	6	\N	\N	2026-03-13 21:12:19.92258
22	11	2	3	2026-07-25 14:30:00	11	12	7	8	\N	\N	2026-03-13 21:12:19.92258
23	12	1	1	2026-07-25 14:30:00	13	14	1	2	\N	\N	2026-03-13 21:12:19.92258
24	12	2	1	2026-07-25 14:30:00	15	16	3	4	\N	\N	2026-03-13 21:12:19.92258
25	13	1	1	2026-08-01 20:30:00	1	2	9	10	\N	\N	2026-03-13 21:12:19.92258
26	13	2	1	2026-08-01 20:30:00	3	4	11	12	\N	\N	2026-03-13 21:12:19.92258
29	4	3	4	2026-05-23 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
30	5	3	2	2026-06-21 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
31	6	3	4	2026-06-21 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
32	7	3	2	2026-07-11 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
33	8	3	3	2026-07-11 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
34	9	3	1	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
35	10	3	2	2026-07-18 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
36	11	3	3	2026-07-25 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
37	12	3	1	2026-07-25 14:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
38	13	3	1	2026-08-01 20:30:00	\N	\N	\N	\N	\N	\N	2026-03-20 19:12:28.291273
6	3	2	1	2026-05-23 14:30:00	3	4	7	8	2	0	2026-03-13 21:12:19.92258
28	3	3	1	2026-05-23 14:30:00	\N	\N	\N	\N	1	2	2026-03-20 19:12:28.291273
3	2	1	3	2026-05-20 14:30:00	5	6	13	14	2	0	2026-03-13 21:12:19.92258
4	2	2	3	2026-05-20 14:30:00	7	8	15	16	0	2	2026-03-13 21:12:19.92258
27	2	3	3	2026-05-20 14:30:00	\N	\N	\N	\N	0	3	2026-03-20 19:12:28.291273
1	1	1	2	2026-05-20 14:30:00	9	10	1	2	2	1	2026-03-13 21:12:19.92258
2	1	2	2	2026-05-20 14:30:00	11	12	3	4	2	0	2026-03-13 21:12:19.92258
39	1	3	2	2026-05-20 14:30:00	\N	\N	\N	\N	0	0	2026-03-20 19:12:28.291273
5	3	1	1	2026-05-23 14:30:00	1	2	5	6	1	2	2026-03-13 21:12:19.92258
\.


--
-- Data for Name: matches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.matches (id, season_name, round_number, home_team_id, away_team_id, scheduled_date, status, created_at) FROM stdin;
1	Liga San Miguel 2026	1	1	2	2026-05-20	scheduled	2026-03-13 21:09:51.612082
2	Liga San Miguel 2026	1	3	4	2026-05-20	scheduled	2026-03-13 21:09:51.612082
3	Liga San Miguel 2026	2	1	4	2026-05-23	scheduled	2026-03-13 21:09:51.612082
4	Liga San Miguel 2026	2	2	3	2026-05-23	scheduled	2026-03-13 21:09:51.612082
5	Liga San Miguel 2026	3	1	3	2026-06-21	scheduled	2026-03-13 21:09:51.612082
6	Liga San Miguel 2026	3	2	4	2026-06-21	scheduled	2026-03-13 21:09:51.612082
7	Liga San Miguel 2026	4	1	2	2026-07-11	scheduled	2026-03-13 21:09:51.612082
8	Liga San Miguel 2026	4	3	4	2026-07-11	scheduled	2026-03-13 21:09:51.612082
9	Liga San Miguel 2026	5	1	4	2026-07-18	scheduled	2026-03-13 21:09:51.612082
10	Liga San Miguel 2026	5	2	3	2026-07-18	scheduled	2026-03-13 21:09:51.612082
11	Liga San Miguel 2026	6	1	3	2026-07-25	scheduled	2026-03-13 21:09:51.612082
12	Liga San Miguel 2026	6	2	4	2026-07-25	scheduled	2026-03-13 21:09:51.612082
13	Liga San Miguel 2026	7	1	2	2026-08-01	scheduled	2026-03-13 21:09:51.612082
\.


--
-- Data for Name: players; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.players (id, first_name, last_name, nickname, category, ranking_points, created_at) FROM stdin;
1	Celsa		Celsa	C	100	2026-03-13 21:11:21.295579
2	Dave		Dave	C	100	2026-03-13 21:11:21.295579
3	Joseph		Joseph	C	100	2026-03-13 21:11:21.295579
4	Camilo		Camilo EA	C	100	2026-03-13 21:11:21.295579
5	Miraida		Miraida	C	100	2026-03-13 21:11:21.295579
6	Eli		Eli	C	100	2026-03-13 21:11:21.295579
7	Paolo		Paolo Arena	C	100	2026-03-13 21:11:21.295579
8	Jose		Jose	C	100	2026-03-13 21:11:21.295579
9	Sybell		Sybell	C	100	2026-03-13 21:11:21.295579
10	Belen		Belen	C	100	2026-03-13 21:11:21.295579
11	Jorge		Jorge	C	100	2026-03-13 21:11:21.295579
12	Sebas		Sebas	C	100	2026-03-13 21:11:21.295579
13	Cami		Cami	C	100	2026-03-13 21:11:21.295579
14	Cony		Cony	C	100	2026-03-13 21:11:21.295579
15	Carlos		Carlos	C	100	2026-03-13 21:11:21.295579
16	Juan		Juan	C	100	2026-03-13 21:11:21.295579
\.


--
-- Data for Name: team_players; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.team_players (id, team_id, player_id, joined_at, active) FROM stdin;
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teams (id, club_id, name, logo_url, created_at) FROM stdin;
1	1	Espacio Active	\N	2026-03-06 01:30:09.170322
2	2	Propadel	\N	2026-03-06 01:30:09.170322
3	3	Arena	\N	2026-03-06 01:30:09.170322
4	4	Revueltas	\N	2026-03-06 01:30:09.170322
\.


--
-- Name: clubs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.clubs_id_seq', 4, true);


--
-- Name: match_game_sets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.match_game_sets_id_seq', 25, true);


--
-- Name: match_games_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.match_games_id_seq', 39, true);


--
-- Name: matches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.matches_id_seq', 13, true);


--
-- Name: players_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.players_id_seq', 16, true);


--
-- Name: team_players_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.team_players_id_seq', 1, false);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teams_id_seq', 4, true);


--
-- Name: clubs clubs_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_name_key UNIQUE (name);


--
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- Name: match_game_sets match_game_sets_match_game_id_set_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_game_sets
    ADD CONSTRAINT match_game_sets_match_game_id_set_number_key UNIQUE (match_game_id, set_number);


--
-- Name: match_game_sets match_game_sets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_game_sets
    ADD CONSTRAINT match_game_sets_pkey PRIMARY KEY (id);


--
-- Name: match_games match_games_match_id_game_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_match_id_game_number_key UNIQUE (match_id, game_number);


--
-- Name: match_games match_games_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_pkey PRIMARY KEY (id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);


--
-- Name: players players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_pkey PRIMARY KEY (id);


--
-- Name: team_players team_players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_players
    ADD CONSTRAINT team_players_pkey PRIMARY KEY (id);


--
-- Name: team_players team_players_team_id_player_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_players
    ADD CONSTRAINT team_players_team_id_player_id_key UNIQUE (team_id, player_id);


--
-- Name: teams teams_club_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_club_id_name_key UNIQUE (club_id, name);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: match_game_sets match_game_sets_match_game_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_game_sets
    ADD CONSTRAINT match_game_sets_match_game_id_fkey FOREIGN KEY (match_game_id) REFERENCES public.match_games(id) ON DELETE CASCADE;


--
-- Name: match_games match_games_away_player_1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_away_player_1_id_fkey FOREIGN KEY (away_player_1_id) REFERENCES public.players(id);


--
-- Name: match_games match_games_away_player_2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_away_player_2_id_fkey FOREIGN KEY (away_player_2_id) REFERENCES public.players(id);


--
-- Name: match_games match_games_home_player_1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_home_player_1_id_fkey FOREIGN KEY (home_player_1_id) REFERENCES public.players(id);


--
-- Name: match_games match_games_home_player_2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_home_player_2_id_fkey FOREIGN KEY (home_player_2_id) REFERENCES public.players(id);


--
-- Name: match_games match_games_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(id) ON DELETE CASCADE;


--
-- Name: match_games match_games_venue_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_games
    ADD CONSTRAINT match_games_venue_club_id_fkey FOREIGN KEY (venue_club_id) REFERENCES public.clubs(id);


--
-- Name: matches matches_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: matches matches_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: team_players team_players_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_players
    ADD CONSTRAINT team_players_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(id) ON DELETE CASCADE;


--
-- Name: team_players team_players_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_players
    ADD CONSTRAINT team_players_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: teams teams_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict E0TRUEX5mAHAARsTm4ZLuBwNXZSoJMJR8NPLM47R1QHXvVEn1cXui0lxM5kMtJf

