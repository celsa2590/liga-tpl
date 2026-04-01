
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .db import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .db import engine
from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Liga San Miguel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/next-round")
def get_next_round():
    query = text("""
        SELECT
            round_number,
            MIN(scheduled_at) AS next_date
        FROM match_schedule
        WHERE season_name = 'Liga San Miguel 2026'
          AND scheduled_at >= NOW()
        GROUP BY round_number
        ORDER BY next_date
        LIMIT 1
    """)

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    if not result:
        return {"round_number": None, "date": None}

    return {
        "round_number": result.round_number,
        "date": result.next_date.isoformat() if result.next_date else None
    }

@app.get("/")
def root():
    return {"message": "API de la Liga San Miguel funcionando"}


@app.get("/standings")
def get_standings():
    query = text("""
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY total_points DESC, sets_diff DESC, won_games DESC, team_name ASC
            ) AS position,
            season_name,
            team_id,
            team_name,
            club_name,
            played_games,
            won_games,
            lost_games,
            sets_for,
            sets_against,
            sets_diff,
            bonus_points,
            total_points
        FROM standings
        WHERE season_name = 'Liga San Miguel 2026'
        ORDER BY total_points DESC, sets_diff DESC, won_games DESC, team_name ASC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows


@app.get("/matches")
def get_matches():
    query = text("""
        SELECT
            match_id,
            season_name,
            round_number,
            home_team_id,
            home_team_name,
            away_team_id,
            away_team_name,
            game_number,
            category,
            venue_club,
            scheduled_at,
            home_player_1,
            home_player_2,
            away_player_1,
            away_player_2,
            home_sets,
            away_sets,
            result_status
        FROM match_schedule
        WHERE season_name = 'Liga San Miguel 2026'
        ORDER BY round_number, scheduled_at
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows
from fastapi import Body

@app.put("/match_game/{match_id}/{game_number}")
def update_match_game(match_id: int, game_number: int, home_sets: int = Body(...), away_sets: int = Body(...)):

    query = text("""
        UPDATE match_games
        SET home_sets = :home_sets,
            away_sets = :away_sets
        WHERE match_id = :match_id
        AND game_number = :game_number
    """)

    with engine.connect() as conn:
        conn.execute(query,{
            "home_sets":home_sets,
            "away_sets":away_sets,
            "match_id":match_id,
            "game_number":game_number
        })
        conn.commit()

    return {"status":"ok"}

@app.get("/players")
def get_players():
    query = text("""
        SELECT
            t.id AS team_id,
            t.name AS team_name,
            c.name AS club_name,
            p.id AS player_id,
            p.first_name,
            p.last_name,
            p.nickname,
            p.category,
            p.ranking_points
        FROM team_players tp
        JOIN teams t ON t.id = tp.team_id
        JOIN clubs c ON c.id = t.club_id
        JOIN players p ON p.id = tp.player_id
        WHERE tp.active = TRUE
        ORDER BY t.name, p.first_name, p.last_name
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows


@app.get("/admin/matches")
def get_admin_matches():
    query = text("""
        SELECT
            mg.id AS match_game_id,
            ms.match_id,
            ms.season_name,
            ms.round_number,
            ms.home_team_name,
            ms.away_team_name,
            ms.venue_club,
            ms.scheduled_at,
            ms.game_number,
            ms.home_player_1,
            ms.home_player_2,
            ms.away_player_1,
            ms.away_player_2,
            ms.home_sets,
            ms.away_sets,
            s1.home_games AS set1_home_games,
            s1.away_games AS set1_away_games,
            s2.home_games AS set2_home_games,
            s2.away_games AS set2_away_games,
            s3.home_games AS set3_home_games,
            s3.away_games AS set3_away_games
        FROM match_schedule ms
        JOIN match_games mg
          ON mg.match_id = ms.match_id
         AND mg.game_number = ms.game_number
        LEFT JOIN match_game_sets s1
          ON s1.match_game_id = mg.id AND s1.set_number = 1
        LEFT JOIN match_game_sets s2
          ON s2.match_game_id = mg.id AND s2.set_number = 2
        LEFT JOIN match_game_sets s3
          ON s3.match_game_id = mg.id AND s3.set_number = 3
        ORDER BY ms.round_number, ms.match_id, ms.game_number
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows

@app.put("/admin/match/{match_id}")
def update_match(match_id: int, payload: dict = Body(...)):
    games = payload.get("games", [])

    update_match_query = text("""
        UPDATE match_games
        SET home_sets = :home_sets,
            away_sets = :away_sets
        WHERE match_id = :match_id
          AND game_number = :game_number
    """)

    get_match_game_id_query = text("""
        SELECT id
        FROM match_games
        WHERE match_id = :match_id
          AND game_number = :game_number
    """)

    delete_sets_query = text("""
        DELETE FROM match_game_sets
        WHERE match_game_id = :match_game_id
    """)

    insert_set_query = text("""
        INSERT INTO match_game_sets (
            match_game_id,
            set_number,
            home_games,
            away_games
        ) VALUES (
            :match_game_id,
            :set_number,
            :home_games,
            :away_games
        )
    """)

    with engine.connect() as conn:
        for game in games:
            conn.execute(
                update_match_query,
                {
                    "match_id": match_id,
                    "game_number": game["game_number"],
                    "home_sets": game["home_sets"],
                    "away_sets": game["away_sets"],
                },
            )

            result = conn.execute(
                get_match_game_id_query,
                {
                    "match_id": match_id,
                    "game_number": game["game_number"],
                },
            ).fetchone()

            if result:
                match_game_id = result.id

                conn.execute(
                    delete_sets_query,
                    {"match_game_id": match_game_id}
                )

                for set_number, set_data in enumerate(game.get("sets", []), start=1):
                    home_games = set_data.get("home_games")
                    away_games = set_data.get("away_games")

                    if home_games is None and away_games is None:
                        continue

                    conn.execute(
                        insert_set_query,
                        {
                            "match_game_id": match_game_id,
                            "set_number": set_number,
                            "home_games": home_games,
                            "away_games": away_games,
                        },
                    )

        conn.commit()

    return {"status": "ok", "match_id": match_id}


router = APIRouter()

@router.get("/players/stats")
def get_players_stats():
    query = """
    WITH player_team AS (
      SELECT DISTINCT ON (tp.player_id)
        tp.player_id,
        tp.team_id
      FROM team_players tp
      WHERE tp.active = true
      ORDER BY tp.player_id, tp.joined_at DESC, tp.id DESC
    ),
    player_games AS (
      SELECT
        mg.match_id,
        mg.id AS match_game_id,
        mg.game_number,
        mg.category,
        mg.home_sets,
        mg.away_sets,
        m.home_team_id,
        m.away_team_id,
        mg.home_player_1_id AS player_id,
        'home' AS side
      FROM match_games mg
      JOIN matches m ON m.id = mg.match_id
      WHERE mg.home_player_1_id IS NOT NULL

      UNION ALL

      SELECT
        mg.match_id,
        mg.id AS match_game_id,
        mg.game_number,
        mg.category,
        mg.home_sets,
        mg.away_sets,
        m.home_team_id,
        m.away_team_id,
        mg.home_player_2_id AS player_id,
        'home' AS side
      FROM match_games mg
      JOIN matches m ON m.id = mg.match_id
      WHERE mg.home_player_2_id IS NOT NULL

      UNION ALL

      SELECT
        mg.match_id,
        mg.id AS match_game_id,
        mg.game_number,
        mg.category,
        mg.home_sets,
        mg.away_sets,
        m.home_team_id,
        m.away_team_id,
        mg.away_player_1_id AS player_id,
        'away' AS side
      FROM match_games mg
      JOIN matches m ON m.id = mg.match_id
      WHERE mg.away_player_1_id IS NOT NULL

      UNION ALL

      SELECT
        mg.match_id,
        mg.id AS match_game_id,
        mg.game_number,
        mg.category,
        mg.home_sets,
        mg.away_sets,
        m.home_team_id,
        m.away_team_id,
        mg.away_player_2_id AS player_id,
        'away' AS side
      FROM match_games mg
      JOIN matches m ON m.id = mg.match_id
      WHERE mg.away_player_2_id IS NOT NULL
    ),
    player_games_with_team AS (
      SELECT
        pg.*,
        pt.team_id AS player_team_id
      FROM player_games pg
      LEFT JOIN player_team pt
        ON pt.player_id = pg.player_id
    ),
    player_stats AS (
      SELECT
        pg.player_id,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL THEN 1
        END) AS matches_played,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND (
             (pg.side = 'home' AND pg.home_sets > pg.away_sets) OR
             (pg.side = 'away' AND pg.away_sets > pg.home_sets)
           )
          THEN 1
        END) AS wins,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND (
             (pg.side = 'home' AND pg.home_sets < pg.away_sets) OR
             (pg.side = 'away' AND pg.away_sets < pg.home_sets)
           )
          THEN 1
        END) AS losses,

        COALESCE(SUM(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
          THEN CASE WHEN pg.side = 'home' THEN pg.home_sets ELSE pg.away_sets END
          ELSE 0
        END), 0) AS sets_won,

        COALESCE(SUM(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
          THEN CASE WHEN pg.side = 'home' THEN pg.away_sets ELSE pg.home_sets END
          ELSE 0
        END), 0) AS sets_lost,

        AVG(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
          THEN CASE WHEN pg.side = 'home' THEN pg.home_sets ELSE pg.away_sets END
        END) AS avg_sets_won,

        AVG(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
          THEN CASE WHEN pg.side = 'home' THEN pg.away_sets ELSE pg.home_sets END
        END) AS avg_sets_lost,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND pg.player_team_id = pg.home_team_id
          THEN 1
        END) AS home_matches,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND pg.player_team_id = pg.away_team_id
          THEN 1
        END) AS away_matches,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND pg.player_team_id = pg.home_team_id
           AND (
             (pg.side = 'home' AND pg.home_sets > pg.away_sets) OR
             (pg.side = 'away' AND pg.away_sets > pg.home_sets)
           )
          THEN 1
        END) AS home_wins,

        COUNT(CASE
          WHEN pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND pg.player_team_id = pg.away_team_id
           AND (
             (pg.side = 'home' AND pg.home_sets > pg.away_sets) OR
             (pg.side = 'away' AND pg.away_sets > pg.home_sets)
           )
          THEN 1
        END) AS away_wins,

        COUNT(CASE
          WHEN pg.game_number = 3
           AND pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
          THEN 1
        END) AS super_tiebreak_played,

        COUNT(CASE
          WHEN pg.game_number = 3
           AND pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND (
             (pg.side = 'home' AND pg.home_sets > pg.away_sets) OR
             (pg.side = 'away' AND pg.away_sets > pg.home_sets)
           )
          THEN 1
        END) AS super_tiebreak_won,

        COUNT(CASE
          WHEN pg.game_number = 3
           AND pg.home_sets IS NOT NULL AND pg.away_sets IS NOT NULL
           AND (
             (pg.side = 'home' AND pg.home_sets < pg.away_sets) OR
             (pg.side = 'away' AND pg.away_sets < pg.home_sets)
           )
          THEN 1
        END) AS super_tiebreak_lost

      FROM player_games_with_team pg
      GROUP BY pg.player_id
    )

    SELECT
      p.id AS player_id,
      p.first_name,
      p.last_name,
      p.nickname,
      p.category,
      p.ranking_points,
      pt.team_id,
      t.name AS team_name,
      c.name AS club_name,
      COALESCE(ps.matches_played, 0) AS matches_played,
      COALESCE(ps.wins, 0) AS wins,
      COALESCE(ps.losses, 0) AS losses,
      COALESCE(ps.sets_won, 0) AS sets_won,
      COALESCE(ps.sets_lost, 0) AS sets_lost,
      COALESCE(ROUND(ps.avg_sets_won::numeric, 2), 0) AS avg_sets_won,
      COALESCE(ROUND(ps.avg_sets_lost::numeric, 2), 0) AS avg_sets_lost,
      CASE
        WHEN COALESCE(ps.home_matches, 0) = 0 THEN 0
        ELSE ROUND((ps.home_wins::numeric / ps.home_matches::numeric) * 100, 1)
      END AS home_win_pct,
      CASE
        WHEN COALESCE(ps.away_matches, 0) = 0 THEN 0
        ELSE ROUND((ps.away_wins::numeric / ps.away_matches::numeric) * 100, 1)
      END AS away_win_pct,
      COALESCE(ps.super_tiebreak_played, 0) AS super_tiebreak_played,
      COALESCE(ps.super_tiebreak_won, 0) AS super_tiebreak_won,
      COALESCE(ps.super_tiebreak_lost, 0) AS super_tiebreak_lost
    FROM players p
    LEFT JOIN player_team pt
      ON pt.player_id = p.id
    LEFT JOIN teams t
      ON t.id = pt.team_id
    LEFT JOIN clubs c
      ON c.id = t.club_id
    LEFT JOIN player_stats ps
      ON ps.player_id = p.id
    ORDER BY
      p.category NULLS LAST,
      p.ranking_points DESC,
      p.last_name,
      p.first_name;
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas de jugadores: {str(e)}")
