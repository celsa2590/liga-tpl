
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .db import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .db import engine

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
