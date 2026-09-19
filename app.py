import streamlit as st
import pandas as pd
import sqlite3
import requests
from io import StringIO
from datetime import datetime


# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="해외 배당 분석",
    page_icon="⚽",
    layout="centered"
)

DB_FILE = "historical_odds.db"

BASE_URL = "https://www.football-data.co.uk/mmz4281"


# =========================================================
# 리그
# =========================================================

LEAGUES = {
    "잉글랜드 1부": ("E0", "England", 1),
    "잉글랜드 2부": ("E1", "England", 2),
    "잉글랜드 3부": ("E2", "England", 3),
    "잉글랜드 4부": ("E3", "England", 4),

    "독일 1부": ("D1", "Germany", 1),
    "독일 2부": ("D2", "Germany", 2),

    "이탈리아 1부": ("I1", "Italy", 1),
    "이탈리아 2부": ("I2", "Italy", 2),

    "스페인 1부": ("SP1", "Spain", 1),
    "스페인 2부": ("SP2", "Spain", 2),

    "프랑스 1부": ("F1", "France", 1),
    "프랑스 2부": ("F2", "France", 2),

    "네덜란드 1부": ("N1", "Netherlands", 1),
    "벨기에 1부": ("B1", "Belgium", 1),
    "포르투갈 1부": ("P1", "Portugal", 1),

    "스코틀랜드 1부": ("SC0", "Scotland", 1),
    "스코틀랜드 2부": ("SC1", "Scotland", 2),

    "터키 1부": ("T1", "Turkey", 1),
    "그리스 1부": ("G1", "Greece", 1),
}


# =========================================================
# 시즌
# =========================================================

SEASONS = {
    "2025/26": "2526",
    "2024/25": "2425",
    "2023/24": "2324",
    "2022/23": "2223",
    "2021/22": "2122",
}


# =========================================================
# DB 생성
# =========================================================

def init_db():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            country TEXT,
            league TEXT,
            division INTEGER,
            season TEXT,

            match_date TEXT,

            home_team TEXT,
            away_team TEXT,

            result TEXT,

            bet365_home REAL,
            bet365_draw REAL,
            bet365_away REAL,

            source TEXT,

            created_at TEXT,

            UNIQUE(
                league,
                season,
                match_date,
                home_team,
                away_team
            )
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# DB 경기수
# =========================================================

def get_db_count():

    try:

        conn = sqlite3.connect(DB_FILE)

        count = conn.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        conn.close()

        return int(count)

    except Exception:

        return 0


# =========================================================
# DB 불러오기
# =========================================================

def load_data():

    try:

        conn = sqlite3.connect(DB_FILE)

        df = pd.read_sql_query(
            "SELECT * FROM matches",
            conn
        )

        conn.close()

        return df

    except Exception:

        return pd.DataFrame()


# =========================================================
# CSV 다운로드
# =========================================================

def download_csv(
    season_code,
    league_code
):

    url = (
        BASE_URL
        + "/"
        + season_code
        + "/"
        + league_code
        + ".csv"
    )

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        if response.status_code != 200:

            return None, (
                f"HTTP 오류 "
                f"{response.status_code}"
            ), url


        if len(response.content) < 500:

            return None, (
                "다운로드된 파일이 "
                "너무 작습니다."
            ), url


        response.encoding = "latin1"

        df = pd.read_csv(
            StringIO(response.text)
        )

        return df, None, url


    except Exception as e:

        return None, str(e), url


# =========================================================
# 숫자 변환
# =========================================================

def to_number(value):

    try:

        if pd.isna(value):
            return None

        value = float(value)

        if value <= 1:
            return None

        return value

    except Exception:

        return None


# =========================================================
# 데이터 저장
# =========================================================

def save_matches(
    df,
    league_name,
    season_name
):

    if df is None or df.empty:

        return 0, 0, "CSV가 비어 있습니다."


    required = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTR"
    ]


    missing = [
        x for x in required
        if x not in df.columns
    ]


    if missing:

        return (
            0,
            0,
            "필수 컬럼 없음: "
            + ", ".join(missing)
        )


    league_info = LEAGUES[
        league_name
    ]


    # Bet365 마감배당
    # 없으면 일반 Bet365 배당을 보조 사용
    if all(
        x in df.columns
        for x in [
            "B365CH",
            "B365CD",
            "B365CA"
        ]
    ):

        bh_col = "B365CH"
        bd_col = "B365CD"
        ba_col = "B365CA"

        odds_type = "마감배당"

    elif all(
        x in df.columns
        for x in [
            "B365H",
            "B365D",
            "B365A"
        ]
    ):

        bh_col = "B365H"
        bd_col = "B365D"
        ba_col = "B365A"

        odds_type = "일반배당"

    else:

        bh_col = None
        bd_col = None
        ba_col = None

        odds_type = "Bet365 배당 없음"


    conn = sqlite3.connect(
        DB_FILE
    )


    saved = 0
    total = 0


    for _, row in df.iterrows():

        try:

            result = str(
                row["FTR"]
            ).strip().upper()


            if result not in [
                "H",
                "D",
                "A"
            ]:

                continue


            home = str(
                row["HomeTeam"]
            ).strip()

            away = str(
                row["AwayTeam"]
            ).strip()

            date = str(
                row["Date"]
            ).strip()


            if not home or not away:
                continue


            if bh_col:

                bh = to_number(
                    row[bh_col]
                )

                bd = to_number(
                    row[bd_col]
                )

                ba = to_number(
                    row[ba_col]
                )

            else:

                bh = None
                bd = None
                ba = None


            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO matches (

                    country,
                    league,
                    division,
                    season,

                    match_date,

                    home_team,
                    away_team,

                    result,

                    bet365_home,
                    bet365_draw,
                    bet365_away,

                    source,
                    created_at
                )

                VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
                """,

                (
                    league_info[1],
                    league_name,
                    league_info[2],
                    season_name,

                    date,

                    home,
                    away,

                    result,

                    bh,
                    bd,
                    ba,

                    "Football-Data.co.uk",

                    datetime.now().isoformat()
                )
            )


            if cursor.rowcount > 0:
                saved += 1


            total += 1


        except Exception:

            continue


    conn.commit()
    conn.close()


    return (
        saved,
        total,
        odds_type
    )


# =========================================================
# 데이터 수집
# =========================================================

def collect_data(
    leagues,
    seasons
):

    total_saved = 0
    total_downloaded = 0

    total_jobs = (
        len(leagues)
        *
        len(seasons)
    )

    current_job = 0

    progress = st.progress(0)


    for league in leagues:

        league_code = LEAGUES[
            league
        ][0]


        for season in seasons:

            current_job += 1

            progress.progress(
                current_job / total_jobs
            )


            st.write(
                f"📥 {league} "
                f"/ {season}"
            )


            df, error, url = download_csv(
                SEASONS[season],
                league_code
            )


            if error:

                st.error(
                    f"❌ 다운로드 실패: "
                    f"{error}"
                )

                continue


            st.success(
                f"✅ CSV 다운로드 성공 "
                f"({len(df):,}행)"
            )


            saved, processed, odds_type = (
                save_matches(
                    df,
                    league,
                    season
                )
            )


            total_downloaded += processed
            total_saved += saved


            st.info(
                f"경기 처리: {processed:,} "
                f"/ 신규 저장: {saved:,} "
                f"/ 배당: {odds_type}"
            )


    progress.progress(1.0)


    return (
        total_saved,
        total_downloaded
    )


# =========================================================
# 유사배당 분석
# =========================================================

def analyze_odds(
    df,
    home_odds,
    draw_odds,
    away_odds,
    tolerance,
    league
):

    if df.empty:
        return None


    if league != "전체":

        df = df[
            df["league"] == league
        ]


    if df.empty:
        return None


    # Bet365 배당이 없는 행 제거
    df = df.dropna(
        subset=[
            "bet365_home",
            "bet365_draw",
            "bet365_away"
        ]
    )


    if df.empty:
        return None


    df = df.copy()


    df["diff_home"] = abs(
        df["bet365_home"]
        - home_odds
