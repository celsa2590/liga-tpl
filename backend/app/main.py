
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .db import engine
from fastapi import Header
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "cambia-esto-por-una-clave-larga-y-secreta")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

def normalize_rut(rut: str) -> str:
    if not rut:
        return ""

    cleaned = re.sub(r"[^0-9kK]", "", rut).upper()
    if len(cleaned) < 2:
        return ""

    body = cleaned[:-1]
    dv = cleaned[-1]
    return f"{body}-{dv}"

def is_valid_rut(rut: str) -> bool:
    rut = normalize_rut(rut)
    if not rut or "-" not in rut:
        return False

    body, dv = rut.split("-")
    if not body.isdigit():
        return False

    reversed_digits = list(map(int, reversed(body)))
    factors = [2, 3, 4, 5, 6, 7]
    s = 0

    for i, digit in enumerate(reversed_digits):
      s += digit * factors[i % len(factors)]

    mod = 11 - (s % 11)
    expected = "0" if mod == 11 else "K" if mod == 10 else str(mod)

    return dv == expected

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_admin_jwt(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")

    token = authorization.replace("Bearer ", "").strip()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

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


@app.post("/admin/login")
def admin_login(payload: dict = Body(...)):
    query = text("""
        SELECT id, username, password_hash, is_active
        FROM admin_users
        WHERE username = :username
        LIMIT 1
    """)

    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña son obligatorios")

    with engine.connect() as conn:
        result = conn.execute(query, {"username": username}).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not result.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    if not verify_password(password, result.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_access_token({"sub": result.username})

    return {
        "status": "ok",
        "access_token": token,
        "token_type": "bearer",
        "username": result.username
    }

@app.get("/standings")
def get_standings():
    query = text("""
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY
                    total_points DESC,
                    (won_games - lost_games) DESC,
                    won_games DESC,
                    sets_diff DESC,
                    sets_for DESC,
                    team_name ASC
            ) AS position,
            season_name,
            team_id,
            team_name,
            club_name,
            played_games,
            won_games,
            lost_games,
            (won_games - lost_games) AS games_diff,
            sets_for,
            sets_against,
            sets_diff,
            bonus_points,
            total_points
        FROM standings
        WHERE season_name = 'Liga San Miguel 2026'
        ORDER BY
            total_points DESC,
            (won_games - lost_games) DESC,
            won_games DESC,
            sets_diff DESC,
            sets_for DESC,
            team_name ASC
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
            p.position,
            p.photo_url,
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


@app.get("/players/ranking")
def get_player_ranking():
    query = text("""
        SELECT *
        FROM player_ranking
        ORDER BY ranking_points DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        return [dict(row._mapping) for row in result]


@app.get("/selectives")
def get_selectives():
    query = text("""
        SELECT
            id,
            club_name,
            title,
            selective_date,
            status,
            notes
        FROM selectives
        ORDER BY selective_date, id
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows


@app.get("/selective/{selective_id}")
def get_selective_detail(selective_id: int):
    with engine.connect() as conn:
        selective = conn.execute(text("""
            SELECT
                id,
                club_name,
                title,
                selective_date,
                status,
                notes
            FROM selectives
            WHERE id = :selective_id
        """), {"selective_id": selective_id}).mappings().first()

        if not selective:
            raise HTTPException(status_code=404, detail="Selectivo no encontrado")

        courts = conn.execute(text("""
            SELECT
                id,
                selective_id,
                name,
                display_order
            FROM selective_courts
            WHERE selective_id = :selective_id
            ORDER BY display_order, id
        """), {"selective_id": selective_id}).mappings().all()

        categories = conn.execute(text("""
            SELECT
                id,
                selective_id,
                gender,
                category_name,
                selective_date,
                start_time,
                end_time,
                match_duration_minutes,
                changeover_minutes,
                points_win,
                points_draw,
                points_loss
            FROM selective_categories
            WHERE selective_id = :selective_id
            ORDER BY selective_date, start_time, id
        """), {"selective_id": selective_id}).mappings().all()

    return {
        "selective": dict(selective),
        "courts": [dict(c) for c in courts],
        "categories": [dict(c) for c in categories]
    }


@app.get("/selective-category/{category_id}/matches")
def get_selective_category_matches(category_id: int):
    query = text("""
        SELECT
            sm.id,
            sm.selective_category_id,
            sm.round_number,
            sm.display_order,
            sm.stage,
            sm.court_id,
            sc.name AS court_name,
            sm.pair_1_id,
            p1.pair_name AS pair_1_name,
            sm.pair_2_id,
            p2.pair_name AS pair_2_name,
            sm.pair_1_games,
            sm.pair_2_games,
            sm.result_status,
            sm.played_at,
            sm.notes
        FROM selective_matches sm
        LEFT JOIN selective_courts sc
          ON sc.id = sm.court_id
        JOIN selective_pairs p1
          ON p1.id = sm.pair_1_id
        JOIN selective_pairs p2
          ON p2.id = sm.pair_2_id
        WHERE sm.selective_category_id = :category_id
        ORDER BY sm.round_number, sm.display_order, sm.id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"category_id": category_id})
        rows = [dict(row._mapping) for row in result]

    return rows


@app.get("/selective-category/{category_id}/standings")
def get_selective_category_standings(category_id: int):
    query = text("""
        SELECT
            selective_category_id,
            pair_id,
            pair_name,
            pj,
            gf,
            gc,
            dg,
            pts
        FROM selective_standings
        WHERE selective_category_id = :category_id
        ORDER BY pts DESC, dg DESC, gf DESC, pair_name
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"category_id": category_id})
        rows = [dict(row._mapping) for row in result]

    return rows


@app.get("/selective-category/{category_id}/pairs")
def get_selective_category_pairs(category_id: int):
    query = text("""
        SELECT
            sp.id,
            sp.selective_category_id,
            sp.pair_name,
            sp.group_name,
            p1.first_name || ' ' || p1.last_name AS player_1_name,
            p2.first_name || ' ' || p2.last_name AS player_2_name
        FROM selective_pairs sp
        JOIN selective_players p1 ON p1.id = sp.player_1_id
        JOIN selective_players p2 ON p2.id = sp.player_2_id
        WHERE sp.selective_category_id = :category_id
        ORDER BY sp.pair_name
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"category_id": category_id})
        rows = [dict(row._mapping) for row in result]

    return rows


@app.post("/admin/selective-pair/{pair_id}/group")
def update_selective_pair_group(
    pair_id: int,
    payload: dict = Body(...),
    authorization: str = Header(None)
):
    verify_admin_jwt(authorization)

    group_name = payload.get("group_name")

    if group_name not in ("A", "B", None, ""):
        raise HTTPException(status_code=400, detail="group_name debe ser 'A', 'B' o vacío")

    query = text("""
        UPDATE selective_pairs
        SET group_name = :group_name,
            updated_at = NOW()
        WHERE id = :pair_id
        RETURNING id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {
            "pair_id": pair_id,
            "group_name": group_name if group_name else None
        }).fetchone()
        conn.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Pareja no encontrada")

    return {"status": "ok", "pair_id": pair_id, "group_name": group_name}


@app.get("/selective-category/{category_id}/group-standings")
def get_selective_category_group_standings(category_id: int):
    query = text("""
        SELECT
            selective_category_id,
            group_name,
            pair_id,
            pair_name,
            pj,
            gf,
            gc,
            dg,
            pts
        FROM selective_group_standings
        WHERE selective_category_id = :category_id
        ORDER BY group_name, pts DESC, dg DESC, gf DESC, pair_name
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"category_id": category_id})
        rows = [dict(row._mapping) for row in result]

    grouped = {"A": [], "B": []}
    for row in rows:
        if row["group_name"] in grouped:
            grouped[row["group_name"]].append(row)

    return grouped



@app.get("/selective-category/{category_id}/finalists")
def get_selective_category_finalists(category_id: int):
    with engine.connect() as conn:
        category = conn.execute(text("""
            SELECT
                id,
                selective_id,
                gender,
                category_name
            FROM selective_categories
            WHERE id = :category_id
        """), {"category_id": category_id}).mappings().first()

        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # CASO FEMENINO:
        # las primeras 2 del americano pasan directo a la final
        if (category["gender"] or "").lower() == "femenino":
            rows = conn.execute(text("""
                SELECT
                    pair_id,
                    pair_name,
                    pts,
                    dg,
                    gf
                FROM selective_standings
                WHERE selective_category_id = :category_id
                ORDER BY pts DESC, dg DESC, gf DESC, pair_name
                LIMIT 2
            """), {"category_id": category_id}).mappings().all()

            return {
                "mode": "top2",
                "category_id": category_id,
                "finalists": [dict(r) for r in rows]
            }

        # CASO MASCULINO:
        # aquí el backend debe devolver las 2 parejas ya definidas
        # por ahora lo sacamos desde una tabla de soporte
        rows = conn.execute(text("""
            SELECT
                selective_category_id,
                slot_number,
                pair_id,
                pair_name,
                source_label
            FROM selective_finalists
            WHERE selective_category_id = :category_id
            ORDER BY slot_number
        """), {"category_id": category_id}).mappings().all()

        return {
            "mode": "slots",
            "category_id": category_id,
            "finalists": [dict(r) for r in rows]
        }



@app.get("/home")
def get_home_data():
    standings_query = text("""
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

    matches_query = text("""
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

    next_round_query = text("""
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

    try:
        with engine.connect() as conn:
            standings_result = conn.execute(standings_query)
            standings_rows = [dict(row._mapping) for row in standings_result]

            matches_result = conn.execute(matches_query)
            matches_rows = [dict(row._mapping) for row in matches_result]

            next_round_result = conn.execute(next_round_query).fetchone()

        next_round = {
            "round_number": next_round_result.round_number if next_round_result else None,
            "date": next_round_result.next_date.isoformat() if next_round_result and next_round_result.next_date else None
        }

        return {
            "standings": standings_rows,
            "matches": matches_rows,
            "next_round": next_round
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cargando portada: {str(e)}")


@app.post("/admin/selective-category/{category_id}/generate-round-robin")
def generate_selective_round_robin(
    category_id: int,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    verify_admin_jwt(authorization)

    court_ids = payload.get("court_ids", [])

    with engine.connect() as conn:
        category = conn.execute(text("""
            SELECT
                id,
                selective_id,
                category_name
            FROM selective_categories
            WHERE id = :category_id
        """), {"category_id": category_id}).mappings().first()

        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        pairs = conn.execute(text("""
            SELECT
                id,
                pair_name
            FROM selective_pairs
            WHERE selective_category_id = :category_id
            ORDER BY pair_name, id
        """), {"category_id": category_id}).mappings().all()

        if len(pairs) < 2:
            raise HTTPException(status_code=400, detail="Debes tener al menos 2 parejas para generar cruces")

        existing = conn.execute(text("""
            SELECT id
            FROM selective_matches
            WHERE selective_category_id = :category_id
              AND stage = 'group_stage'
            LIMIT 1
        """), {"category_id": category_id}).fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="Los cruces ya fueron generados para esta categoría")

        # obtener canchas del selectivo si no se enviaron manualmente
        if not court_ids:
            db_courts = conn.execute(text("""
                SELECT id
                FROM selective_courts
                WHERE selective_id = :selective_id
                ORDER BY display_order, id
            """), {"selective_id": category["selective_id"]}).fetchall()

            court_ids = [row.id for row in db_courts]

        if not court_ids:
            court_ids = [None]

        # round robin tipo "circle method"
        participants = [dict(p) for p in pairs]

        is_odd = len(participants) % 2 == 1
        if is_odd:
            participants.append({"id": None, "pair_name": "BYE"})

        n = len(participants)
        rounds = []
        arr = participants[:]

        for _ in range(n - 1):
            current_round = []
            for i in range(n // 2):
                p1 = arr[i]
                p2 = arr[n - 1 - i]

                # evitar BYE
                if p1["id"] is not None and p2["id"] is not None:
                    current_round.append((p1, p2))

            rounds.append(current_round)

            # rotación manteniendo fijo el primero
            arr = [arr[0]] + [arr[-1]] + arr[1:-1]

        display_order = 1

        for round_idx, matches in enumerate(rounds, start=1):
            for match_idx, (p1, p2) in enumerate(matches, start=1):
                court_id = court_ids[(match_idx - 1) % len(court_ids)]

                conn.execute(text("""
                    INSERT INTO selective_matches
                    (
                        selective_category_id,
                        round_number,
                        display_order,
                        court_id,
                        pair_1_id,
                        pair_2_id,
                        pair_1_games,
                        pair_2_games,
                        result_status,
                        stage,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        :category_id,
                        :round_number,
                        :display_order,
                        :court_id,
                        :pair_1_id,
                        :pair_2_id,
                        NULL,
                        NULL,
                        'scheduled',
                        'group_stage',
                        NOW(),
                        NOW()
                    )
                """), {
                    "category_id": category_id,
                    "round_number": round_idx,
                    "display_order": display_order,
                    "court_id": court_id,
                    "pair_1_id": p1["id"],
                    "pair_2_id": p2["id"]
                })

                display_order += 1

        conn.commit()

    return {
        "status": "ok",
        "message": "Cruces round robin generados"
    }





@app.post("/admin/selective-category/{category_id}/generate-semifinals")
def generate_selective_semifinals(
    category_id: int,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    verify_admin_jwt(authorization)

    court_a_id = payload.get("court_a_id")
    court_b_id = payload.get("court_b_id")

    with engine.connect() as conn:


category = conn.execute(text("""
    SELECT id, selective_id
    FROM selective_categories
    WHERE id = :category_id
"""), {"category_id": category_id}).mappings().first()

if not category:
    raise HTTPException(status_code=404, detail="Categoría no encontrada")

courts = conn.execute(text("""
    SELECT id
    FROM selective_courts
    WHERE selective_id = :selective_id
    ORDER BY display_order, id
"""), {"selective_id": category["selective_id"]}).mappings().all()

if not court_a_id:
    court_a_id = courts[0]["id"] if len(courts) >= 1 else None

if not court_b_id:
    court_b_id = courts[1]["id"] if len(courts) >= 2 else court_a_id

        standings = conn.execute(text("""
            SELECT
                group_name,
                pair_id,
                pair_name,
                pts,
                dg,
                gf
            FROM selective_group_standings
            WHERE selective_category_id = :category_id
            ORDER BY group_name, pts DESC, dg DESC, gf DESC, pair_name
        """), {"category_id": category_id}).mappings().all()

        by_group = {"A": [], "B": []}
        for row in standings:
            if row["group_name"] in by_group:
                by_group[row["group_name"]].append(dict(row))

        if len(by_group["A"]) < 2 or len(by_group["B"]) < 2:
            raise HTTPException(status_code=400, detail="Debes tener al menos 2 parejas clasificadas por grupo")

        existing = conn.execute(text("""
            SELECT id
            FROM selective_matches
            WHERE selective_category_id = :category_id
              AND stage = 'semifinal'
        """), {"category_id": category_id}).fetchall()

        if existing:
            raise HTTPException(status_code=400, detail="Las semifinales ya fueron generadas")

        a1 = by_group["A"][0]["pair_id"]
        a2 = by_group["A"][1]["pair_id"]
        b1 = by_group["B"][0]["pair_id"]
        b2 = by_group["B"][1]["pair_id"]

        conn.execute(text("""
            INSERT INTO selective_matches
            (selective_category_id, round_number, display_order, court_id, pair_1_id, pair_2_id, result_status, stage, created_at, updated_at)
            VALUES
            (:category_id, 4, 1, :court_a_id, :a1, :b2, 'scheduled', 'semifinal', NOW(), NOW()),
            (:category_id, 4, 2, :court_b_id, :b1, :a2, 'scheduled', 'semifinal', NOW(), NOW())
        """), {
            "category_id": category_id,
            "court_a_id": court_a_id,
            "court_b_id": court_b_id,
            "a1": a1,
            "a2": a2,
            "b1": b1,
            "b2": b2
        })

        conn.commit()

    return {"status": "ok", "message": "Semifinales generadas"}


@app.post("/admin/selective-category/{category_id}/generate-final")
def generate_selective_final(
    category_id: int,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    verify_admin_jwt(authorization)

    court_id = payload.get("court_id")

    with engine.connect() as conn:

category = conn.execute(text("""
    SELECT id, selective_id
    FROM selective_categories
    WHERE id = :category_id
"""), {"category_id": category_id}).mappings().first()

if not category:
    raise HTTPException(status_code=404, detail="Categoría no encontrada")

courts = conn.execute(text("""
    SELECT id
    FROM selective_courts
    WHERE selective_id = :selective_id
    ORDER BY display_order, id
"""), {"selective_id": category["selective_id"]}).mappings().all()

if not court_id:
    court_id = courts[0]["id"] if courts else None

        semifinals = conn.execute(text("""
            SELECT
                id,
                pair_1_id,
                pair_2_id,
                pair_1_games,
                pair_2_games,
                result_status
            FROM selective_matches
            WHERE selective_category_id = :category_id
              AND stage = 'semifinal'
            ORDER BY display_order, id
        """), {"category_id": category_id}).mappings().all()

        if len(semifinals) < 2:
            raise HTTPException(status_code=400, detail="Primero debes generar las semifinales")

        winners = []
        for match in semifinals:
            if match["result_status"] != "finished":
                raise HTTPException(status_code=400, detail="Debes completar las semifinales antes de generar la final")

            if match["pair_1_games"] > match["pair_2_games"]:
                winners.append(match["pair_1_id"])
            elif match["pair_2_games"] > match["pair_1_games"]:
                winners.append(match["pair_2_id"])
            else:
                raise HTTPException(status_code=400, detail="Una semifinal no puede terminar empatada si quieres generar la final")

        existing = conn.execute(text("""
            SELECT id
            FROM selective_matches
            WHERE selective_category_id = :category_id
              AND stage = 'final'
        """), {"category_id": category_id}).fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="La final ya fue generada")

        conn.execute(text("""
            INSERT INTO selective_matches
            (selective_category_id, round_number, display_order, court_id, pair_1_id, pair_2_id, result_status, stage, created_at, updated_at)
            VALUES
            (:category_id, 5, 1, :court_id, :winner_1, :winner_2, 'scheduled', 'final', NOW(), NOW())
        """), {
            "category_id": category_id,
            "court_id": court_id,
            "winner_1": winners[0],
            "winner_2": winners[1]
        })

        conn.commit()

    return {"status": "ok", "message": "Final generada"}


@app.post("/admin/selective-category/{category_id}/generate-final-arena")
def generate_selective_final_arena(
    category_id: int,
    payload: dict = Body(default={}),
    authorization: str = Header(None)
):
    verify_admin_jwt(authorization)

    court_id = payload.get("court_id")

    with engine.connect() as conn:

        # 1. Obtener tabla
        standings = conn.execute(text("""
            SELECT
                pair_id,
                pair_name,
                pts,
                dg,
                gf
            FROM selective_standings
            WHERE selective_category_id = :category_id
            ORDER BY pts DESC, dg DESC, gf DESC, pair_name
        """), {"category_id": category_id}).mappings().all()

        if len(standings) < 2:
            raise HTTPException(status_code=400, detail="No hay suficientes parejas")

        pair1 = standings[0]["pair_id"]
        pair2 = standings[1]["pair_id"]

        # 2. Verificar si ya existe final
        existing = conn.execute(text("""
            SELECT id
            FROM selective_matches
            WHERE selective_category_id = :category_id
              AND stage = 'final'
        """), {"category_id": category_id}).fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="La final ya fue generada")

        # 3. Crear final
        conn.execute(text("""
            INSERT INTO selective_matches
            (selective_category_id, round_number, display_order, court_id,
             pair_1_id, pair_2_id, result_status, stage, created_at, updated_at)
            VALUES
            (:category_id, 5, 1, :court_id,
             :pair1, :pair2, 'scheduled', 'final', NOW(), NOW())
        """), {
            "category_id": category_id,
            "court_id": court_id,
            "pair1": pair1,
            "pair2": pair2
        })

        conn.commit()

    return {"status": "ok", "message": "Final Arena generada"}




@app.post("/admin/selective-match/{match_id}/result")
def update_selective_match_result(
    match_id: int,
    payload: dict = Body(...),
    authorization: str = Header(None)
):
    verify_admin_jwt(authorization)

    pair_1_games = payload.get("pair_1_games")
    pair_2_games = payload.get("pair_2_games")

    if pair_1_games is None or pair_2_games is None:
        raise HTTPException(status_code=400, detail="Debes enviar pair_1_games y pair_2_games")

    query = text("""
        UPDATE selective_matches
        SET
            pair_1_games = :pair_1_games,
            pair_2_games = :pair_2_games,
            result_status = 'finished',
            played_at = NOW(),
            updated_at = NOW()
        WHERE id = :match_id
        RETURNING id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {
            "match_id": match_id,
            "pair_1_games": pair_1_games,
            "pair_2_games": pair_2_games
        }).fetchone()
        conn.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Match no encontrado")

    return {"status": "ok", "match_id": match_id}


@app.get("/admin/matches")
def get_admin_matches(authorization: str = Header(None)):
    verify_admin_jwt(authorization)
    query = text("""
        SELECT
            mg.id AS match_game_id,
            mg.home_player_1_id,
            mg.home_player_2_id,
            mg.away_player_1_id,
            mg.away_player_2_id,
            ms.match_id,
            ms.season_name,
            ms.round_number,
            ms.home_team_name,
            ms.away_team_name,
            ms.venue_club,
            ms.scheduled_at,
            ms.game_number,
            ms.category,
            m.home_team_id,
            m.away_team_id,
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

        JOIN matches m
          ON m.id = ms.match_id

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
def update_match(match_id: int, payload: dict = Body(...), authorization: str = Header(None)):
    verify_admin_jwt(authorization)

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



@app.get("/players/stats")
def get_players_stats():
    query = text("""
        WITH player_points AS (
            SELECT
                p.id AS player_id,
                p.first_name,
                p.last_name,
                p.nickname,
                p.category,
                p.position,
                p.photo_url,
                t.id AS team_id,
                t.name AS team_name,
                c.name AS club_name,

                COALESCE(COUNT(mg.id) FILTER (
                    WHERE mg.home_sets IS NOT NULL AND mg.away_sets IS NOT NULL
                ), 0) AS matches_played,

                COALESCE(COUNT(mg.id) FILTER (
                    WHERE mg.home_sets IS NOT NULL AND mg.away_sets IS NOT NULL
                    AND (
                        (p.id IN (mg.home_player_1_id, mg.home_player_2_id) AND mg.home_sets > mg.away_sets)
                        OR
                        (p.id IN (mg.away_player_1_id, mg.away_player_2_id) AND mg.away_sets > mg.home_sets)
                    )
                ), 0) AS wins,

                COALESCE(COUNT(mg.id) FILTER (
                    WHERE mg.home_sets IS NOT NULL AND mg.away_sets IS NOT NULL
                    AND (
                        (p.id IN (mg.home_player_1_id, mg.home_player_2_id) AND mg.home_sets < mg.away_sets)
                        OR
                        (p.id IN (mg.away_player_1_id, mg.away_player_2_id) AND mg.away_sets < mg.home_sets)
                    )
                ), 0) AS losses,

                COALESCE(SUM(
                    CASE
                        WHEN p.id IN (mg.home_player_1_id, mg.home_player_2_id) THEN mg.home_sets
                        WHEN p.id IN (mg.away_player_1_id, mg.away_player_2_id) THEN mg.away_sets
                        ELSE 0
                    END
                ), 0) AS sets_won,

                COALESCE(SUM(
                    CASE
                        WHEN p.id IN (mg.home_player_1_id, mg.home_player_2_id) THEN mg.away_sets
                        WHEN p.id IN (mg.away_player_1_id, mg.away_player_2_id) THEN mg.home_sets
                        ELSE 0
                    END
                ), 0) AS sets_lost,

                1000 + COALESCE(SUM(
                    CASE
                        WHEN mg.home_sets IS NULL OR mg.away_sets IS NULL THEN 0

                        -- FINAL: ajustar round_number si la final usa otro número
                        WHEN m.round_number = 7
                             AND p.id IN (mg.home_player_1_id, mg.home_player_2_id)
                             AND mg.home_sets > mg.away_sets THEN 30

                        WHEN m.round_number = 7
                             AND p.id IN (mg.away_player_1_id, mg.away_player_2_id)
                             AND mg.away_sets > mg.home_sets THEN 30

                        WHEN m.round_number = 7 THEN 0

                        -- FASE REGULAR
                        WHEN p.id IN (mg.home_player_1_id, mg.home_player_2_id)
                             AND mg.home_sets > mg.away_sets THEN 15

                        WHEN p.id IN (mg.away_player_1_id, mg.away_player_2_id)
                             AND mg.away_sets > mg.home_sets THEN 20

                        WHEN p.id IN (mg.home_player_1_id, mg.home_player_2_id)
                             AND mg.home_sets < mg.away_sets THEN -15

                        WHEN p.id IN (mg.away_player_1_id, mg.away_player_2_id)
                             AND mg.away_sets < mg.home_sets THEN -10

                        ELSE 0
                    END
                ), 0) AS ranking_points

            FROM players p
            LEFT JOIN team_players tp ON tp.player_id = p.id
            LEFT JOIN teams t ON t.id = tp.team_id
            LEFT JOIN clubs c ON c.id = t.club_id
            LEFT JOIN match_games mg ON p.id IN (
                mg.home_player_1_id,
                mg.home_player_2_id,
                mg.away_player_1_id,
                mg.away_player_2_id
            )
            LEFT JOIN matches m ON m.id = mg.match_id
            GROUP BY
                p.id, p.first_name, p.last_name, p.nickname,
                p.category, p.position, p.photo_url,
                t.id, t.name, c.name
        )
        SELECT *
        FROM player_points
        ORDER BY ranking_points DESC, wins DESC, sets_won DESC, first_name ASC;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        return [dict(row._mapping) for row in result]




@app.post("/registration")
def create_registration(payload: dict = Body(...)):
    rut = normalize_rut(payload.get("rut", ""))

    if not rut:
        raise HTTPException(status_code=400, detail="El RUT es obligatorio")

    if not is_valid_rut(rut):
        raise HTTPException(status_code=400, detail="RUT inválido")

    required_fields = ["team_id", "first_name", "last_name", "category"]
    for field in required_fields:
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"Falta el campo obligatorio: {field}")

    check_player_query = text("""
        SELECT id
        FROM players
        WHERE rut = :rut
        LIMIT 1
    """)

    check_pending_query = text("""
        SELECT id
        FROM pending_players
        WHERE rut = :rut
          AND status IN ('pending', 'approved')
        LIMIT 1
    """)

    insert_query = text("""
        INSERT INTO pending_players (
            team_id,
            contact_name,
            contact_email,
            contact_phone,
            first_name,
            last_name,
            rut,
            nickname,
            category,
            position
        ) VALUES (
            :team_id,
            :contact_name,
            :contact_email,
            :contact_phone,
            :first_name,
            :last_name,
            :rut,
            :nickname,
            :category,
            :position
        )
        RETURNING id
    """)

    try:
        with engine.connect() as conn:
            existing_player = conn.execute(check_player_query, {"rut": rut}).fetchone()
            if existing_player:
                raise HTTPException(status_code=409, detail="RUT ya está inscrito")

            existing_pending = conn.execute(check_pending_query, {"rut": rut}).fetchone()
            if existing_pending:
                raise HTTPException(status_code=409, detail="RUT ya está inscrito")

            result = conn.execute(insert_query, {
                "team_id": payload.get("team_id"),
                "contact_name": payload.get("contact_name"),
                "contact_email": payload.get("contact_email"),
                "contact_phone": payload.get("contact_phone"),
                "first_name": payload.get("first_name"),
                "last_name": payload.get("last_name"),
                "rut": rut,
                "nickname": payload.get("nickname"),
                "category": payload.get("category"),
                "position": payload.get("position"),
            })
            row = result.fetchone()
            conn.commit()

        return {"status": "ok", "pending_id": row.id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando inscripción: {str(e)}")







@app.get("/teams")
def get_teams():
    query = text("""
        SELECT
            t.id,
            t.name,
            c.name AS club_name
        FROM teams t
        JOIN clubs c ON c.id = t.club_id
        ORDER BY t.name
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows


@app.post("/admin/pending-player/{pending_id}/approve")
def approve_pending_player(pending_id: int, authorization: str = Header(None)):
    verify_admin_jwt(authorization)

    get_pending_query = text("""
        SELECT *
        FROM pending_players
        WHERE id = :pending_id
          AND status = 'pending'
    """)

    insert_player_query = text("""
        INSERT INTO players (
            first_name,
            last_name,
            nickname,
            category,
            position,
            photo_url,
            ranking_points
        ) VALUES (
            :first_name,
            :last_name,
            :nickname,
            :category,
            :position,
            :photo_url,
            0
        )
        RETURNING id
    """)

    insert_team_player_query = text("""
        INSERT INTO team_players (
            team_id,
            player_id,
            active
        ) VALUES (
            :team_id,
            :player_id,
            true
        )
    """)

    update_pending_query = text("""
        UPDATE pending_players
        SET status = 'approved',
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = :pending_id
    """)

    try:
        with engine.connect() as conn:
            pending = conn.execute(
                get_pending_query,
                {"pending_id": pending_id}
            ).fetchone()

            if not pending:
                raise HTTPException(status_code=404, detail="Inscripción pendiente no encontrada")

            player = conn.execute(
                insert_player_query,
                {
                    "first_name": pending.first_name,
                    "last_name": pending.last_name,
                    "nickname": pending.nickname,
                    "category": pending.category,
                    "position": pending.position,
                    "photo_url": None,
                }
            ).fetchone()

            conn.execute(
                insert_team_player_query,
                {
                    "team_id": pending.team_id,
                    "player_id": player.id
                }
            )

            conn.execute(
                update_pending_query,
                {"pending_id": pending_id}
            )

            conn.commit()

        return {"status": "ok", "player_id": player.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error aprobando inscripción: {str(e)}")


@app.get("/admin/pending-players")
def get_admin_pending_players(authorization: str = Header(None)):
    verify_admin_jwt(authorization)

    query = text("""
        SELECT
            pp.id,
            pp.team_id,
            t.name AS team_name,
            c.name AS club_name,
            pp.contact_name,
            pp.contact_email,
            pp.contact_phone,
            pp.first_name,
            pp.last_name,
            pp.nickname,
            pp.category,
            pp.position,
            pp.photo_url,
            pp.status,
            pp.submitted_at,
            pp.reviewed_at
        FROM pending_players pp
        JOIN teams t ON t.id = pp.team_id
        JOIN clubs c ON c.id = t.club_id
        ORDER BY pp.submitted_at DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows



@app.post("/admin/pending-player/{pending_id}/reject")
def reject_pending_player(pending_id: int, authorization: str = Header(None)):
    verify_admin_jwt(authorization)

    query = text("""
        UPDATE pending_players
        SET status = 'rejected',
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = :pending_id
          AND status = 'pending'
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"pending_id": pending_id})
        conn.commit()

    return {"status": "ok", "pending_id": pending_id}

@app.get("/admin/team-players")
def get_admin_team_players(authorization: str = Header(None)):
    verify_admin_jwt(authorization)

    query = text("""
        SELECT
            tp.team_id,
            t.name AS team_name,
            p.id AS player_id,
            p.first_name,
            p.last_name,
            p.nickname,
            p.category,
            p.position
        FROM team_players tp
        JOIN teams t ON t.id = tp.team_id
        JOIN players p ON p.id = tp.player_id
        WHERE tp.active = true
        ORDER BY t.name, p.category, p.first_name, p.last_name
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]

    return rows


@app.put("/admin/match-game/{match_id}/{game_number}/players")
def update_match_game_players(match_id: int, game_number: int, payload: dict = Body(...), authorization: str = Header(None)):
    verify_admin_jwt(authorization)

    query = text("""
        UPDATE match_games
        SET
            home_player_1_id = :home_player_1_id,
            home_player_2_id = :home_player_2_id,
            away_player_1_id = :away_player_1_id,
            away_player_2_id = :away_player_2_id
        WHERE match_id = :match_id
          AND game_number = :game_number
    """)

    with engine.connect() as conn:
        conn.execute(query, {
            "match_id": match_id,
            "game_number": game_number,
            "home_player_1_id": payload.get("home_player_1_id"),
            "home_player_2_id": payload.get("home_player_2_id"),
            "away_player_1_id": payload.get("away_player_1_id"),
            "away_player_2_id": payload.get("away_player_2_id"),
        })
        conn.commit()

    return {"status": "ok", "match_id": match_id, "game_number": game_number}



