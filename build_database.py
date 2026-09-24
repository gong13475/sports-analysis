import sqlite3
import requests
import os
import time
from datetime import datetime

# =========================================================
# 기본 설정
# =========================================================

DB_FILE = "historical_odds.db"

API_KEY = os.getenv("ODDS_API_KEY", "")

BASE_URL = "https://api.the-odds-api.com/v4"


# =========================================================
# 스포츠 목록
# =========================================================

SPORTS = {

    # 야구
    "MLB": "baseball_mlb",
    "KBO": "baseball_kbo",
    "NPB": "baseball_npb",

    # 농구
    "NBA": "basketball_nba",
    "EUROLEAGUE": "basketball_euroleague",

    # 축구
    "EPL": "soccer_epl",
    "LALIGA": "soccer_spain_la_liga",
    "BUNDESLIGA": "soccer_germany_bundesliga",
    "SERIEA": "soccer_italy_serie_a",
    "LIGUE1": "soccer_france_ligue_one",
    "EREDIVISIE": "soccer_netherlands_eredivisie",
    "KLEAGUE1": "soccer_korea_kleague1",
}


# =========================================================
# 축구 여부
# =========================================================

SOCCER_SPORTS = {
    "EPL",
    "LALIGA",
    "BUNDESLIGA",
    "SERIEA",
    "LIGUE1",
    "EREDIVISIE",
    "KLEAGUE1",
}


# =========================================================
# DB 생성
# =========================================================

def create_database():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_games (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            game_id TEXT,

            sport TEXT,

            league TEXT,

            game_date TEXT,

            home_team TEXT,

            away_team TEXT,

            home_odds REAL,

            draw_odds REAL,

            away_odds REAL,

            bookmaker TEXT,

            home_score REAL,

            away_score REAL,

            actual_result TEXT,

            completed INTEGER DEFAULT 0,

            source TEXT,

            created_at TEXT,

            updated_at TEXT,

            UNIQUE(
                game_id,
                bookmaker
            )
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_game_date

        ON historical_games(game_date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_sport

        ON historical_games(sport)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_result

        ON historical_games(actual_result)
    """)

    conn.commit()

    conn.close()


# =========================================================
# 결과 계산
# =========================================================

def calculate_result(
    sport,
    home_score,
    away_score
):

    if home_score is None:
        return None

    if away_score is None:
        return None

    try:

        home_score = float(home_score)
        away_score = float(away_score)

    except:

        return None


    # 축구
    if sport in SOCCER_SPORTS:

        if home_score > away_score:
            return "승"

        elif home_score < away_score:
            return "패"

        else:
            return "무"


    # 야구 / 농구 / 배구
    else:

        if home_score > away_score:
            return "승"

        elif home_score < away_score:
            return "패"

        return None


# =========================================================
# API 호출
# =========================================================

def api_get(
    url,
    params
):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        if response.status_code == 200:

            return response.json()


        print(
            "API 오류:",
            response.status_code
        )

        print(
            response.text[:500]
        )

        return None


    except Exception as e:

        print(
            "API 접속 오류:",
            e
        )

        return None


# =========================================================
# 현재 / 최근 경기 결과 가져오기
# =========================================================

def get_recent_scores(
    sport_name,
    sport_key
):

    url = (
        f"{BASE_URL}/sports/"
        f"{sport_key}/scores/"
    )

    params = {

        "apiKey": API_KEY,

        "daysFrom": 3,

        "dateFormat": "iso"
    }

    return api_get(
        url,
        params
    )


# =========================================================
# 실제 결과 DB 저장
# =========================================================

def update_scores():

    print()
    print(
        "================================"
    )
    print(
        "최근 실제 경기 결과 업데이트"
    )
    print(
        "================================"
    )


    conn = sqlite3.connect(
        DB_FILE
    )

    cursor = conn.cursor()


    total_updated = 0


    for sport_name, sport_key in SPORTS.items():

        print()
        print(
            f"[{sport_name}] 결과 확인"
        )


        games = get_recent_scores(
            sport_name,
            sport_key
        )


        if not games:

            print(
                "경기 결과 없음"
            )

            continue


        for game in games:

            if not game.get(
                "completed",
                False
            ):

                continue


            game_id = game.get(
                "id"
            )

            home_team = game.get(
                "home_team",
                ""
            )

            away_team = game.get(
                "away_team",
                ""
            )

            game_date = game.get(
                "commence_time",
                ""
            )

            scores = game.get(
                "scores"
            )


            if not scores:

                continue


            home_score = None
            away_score = None


            for score in scores:

                name = score.get(
                    "name",
                    ""
                )

                value = score.get(
                    "score"
                )


                if name == home_team:

                    try:

                        home_score = float(
                            value
                        )

                    except:

                        pass


                elif name == away_team:

                    try:

                        away_score = float(
                            value
                        )

                    except:

                        pass


            if (
                home_score is None
                or
                away_score is None
            ):

                continue


            result = calculate_result(
                sport_name,
                home_score,
                away_score
            )


            # 배당 DB에 있는 모든 북메이커 경기 업데이트
            cursor.execute("""
                UPDATE historical_games

                SET

                    home_score=?,

                    away_score=?,

                    actual_result=?,

                    completed=1,

                    updated_at=?

                WHERE

                    game_id=?
            """, (

                home_score,

                away_score,

                result,

                datetime.utcnow()
                .isoformat(),

                game_id
            ))


            updated = cursor.rowcount


            if updated > 0:

                total_updated += updated

                print(
                    f"{home_team} "
                    f"{home_score}"
                    f" - "
                    f"{away_score} "
                    f"{away_team}"
                    f" → "
                    f"{result}"
                )


    conn.commit()

    conn.close()


    print()
    print(
        "결과 업데이트:",
        total_updated,
        "건"
    )


# =========================================================
# 경기 배당 저장
# =========================================================

def save_odds_games(
    sport_name,
    games
):

    if not games:

        return 0


    conn = sqlite3.connect(
        DB_FILE
    )

    cursor = conn.cursor()


    saved_count = 0


    for game in games:

        game_id = game.get(
            "id"
        )

        home_team = game.get(
            "home_team",
            ""
        )

        away_team = game.get(
            "away_team",
            ""
        )

        game_date = game.get(
            "commence_time",
            ""
        )


        bookmakers = game.get(
            "bookmakers",
            []
        )


        for bookmaker in bookmakers:

            bookmaker_name = bookmaker.get(
                "title",
                ""
            )


            markets = bookmaker.get(
                "markets",
                []
            )


            for market in markets:

                if market.get(
                    "key"
                ) != "h2h":

                    continue


                outcomes = market.get(
                    "outcomes",
                    []
                )


                home_odds = None

                away_odds = None

                draw_odds = None


                for outcome in outcomes:

                    name = outcome.get(
                        "name",
                        ""
                    )

                    price = outcome.get(
                        "price"
                    )


                    try:

                        price = float(
                            price
                        )

                    except:

                        continue


                    if name == home_team:

                        home_odds = price


                    elif name == away_team:

                        away_odds = price


                    elif name.lower() == "draw":

                        draw_odds = price


                # 최소 홈/원정 배당 확인
                if (
                    home_odds is None
                    or
                    away_odds is None
                ):

                    continue


                now = datetime.utcnow().isoformat()


                try:

                    cursor.execute("""
                        INSERT OR IGNORE INTO
                        historical_games
                        (

                            game_id,

                            sport,

                            league,

                            game_date,

                            home_team,

                            away_team,

                            home_odds,

                            draw_odds,

                            away_odds,

                            bookmaker,

                            source,

                            created_at,

                            updated_at

                        )

                        VALUES
                        (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        )
                    """, (

                        game_id,

                        sport_name,

                        sport_name,

                        game_date,

                        home_team,

                        away_team,

                        home_odds,

                        draw_odds,

                        away_odds,

                        bookmaker_name,

                        "The Odds API",

                        now,

                        now
                    ))


                    if cursor.rowcount > 0:

                        saved_count += 1


                except Exception as e:

                    print(
                        "DB 저장 오류:",
                        e
                    )


    conn.commit()

    conn.close()


    return saved_count


# =========================================================
# 현재 배당 가져오기
# =========================================================

def collect_current_odds():

    print()
    print(
        "================================"
    )
    print(
        "현재 경기 배당 수집"
    )
    print(
        "================================"
    )


    total_saved = 0


    for sport_name, sport_key in SPORTS.items():

        print()
        print(
            f"[{sport_name}]"
        )


        url = (
            f"{BASE_URL}/sports/"
            f"{sport_key}/odds/"
        )


        params = {

            "apiKey": API_KEY,

            "regions": "us",

            "markets": "h2h",

            "oddsFormat": "decimal"
        }


        games = api_get(
            url,
            params
        )


        if not games:

            print(
                "배당 데이터 없음"
            )

            continue


        saved = save_odds_games(
            sport_name,
            games
        )


        total_saved += saved


        print(
            "수집 경기:",
            len(games)
        )

        print(
            "저장 배당:",
            saved
        )


        time.sleep(
            0.5
        )


    print()

    print(
        "전체 저장:",
        total_saved
    )


# =========================================================
# DB 통계
# =========================================================

def show_statistics():

    conn = sqlite3.connect(
        DB_FILE
    )

    cursor = conn.cursor()


    total = cursor.execute("""
        SELECT COUNT(*)
        FROM historical_games
    """).fetchone()[0]


    completed = cursor.execute("""
        SELECT COUNT(*)
        FROM historical_games
        WHERE actual_result IS NOT NULL
    """).fetchone()[0]


    sports = cursor.execute("""
        SELECT
            sport,
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN actual_result IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS completed

        FROM historical_games

        GROUP BY sport

        ORDER BY total DESC
    """).fetchall()


    conn.close()


    print()
    print(
        "================================"
    )
    print(
        "historical_odds.db 통계"
    )
    print(
        "================================"
    )

    print(
        "전체 배당 데이터:",
        total
    )

    print(
        "실제 결과 연결:",
        completed
    )


    print()

    for sport, total_count, completed_count in sports:

        print(
            f"{sport}: "
            f"{total_count}경기 / "
            f"결과 {completed_count}경기"
        )


# =========================================================
# 메인
# =========================================================

def main():

    print()
    print(
        "========================================"
    )
    print(
        " 스포츠 역사 배당 / 결과 DB 구축"
    )
    print(
        "========================================"
    )


    # 1. DB 생성

    create_database()


    # 2. API KEY 확인

    if not API_KEY:

        print()
        print(
            "⚠️ ODDS_API_KEY가 없습니다."
        )

        print()
        print(
            "Streamlit Secrets 또는"
        )

        print(
            "환경변수 ODDS_API_KEY를"
        )

        print(
            "설정해야 합니다."
        )

        print()

        show_statistics()

        return


    # 3. 현재/최근 배당 수집

    collect_current_odds()


    # 4. 실제 경기 결과 업데이트

    update_scores()


    # 5. 최종 통계

    show_statistics()


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":

    main()
