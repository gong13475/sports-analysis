import streamlit as st
import pandas as pd
import sqlite3
import requests
from io import StringIO
from datetime import datetime

# ==============================
# 기본 설정
# ==============================

st.set_page_config(
    page_title="해외배당 분석",
    page_icon="⚽",
    layout="centered"
)

DB_FILE = "historical_odds.db"
BASE_URL = "https://www.football-data.co.uk/mmz4281"


# ==============================
# 리그
# ==============================

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
    "그리스 1부": ("G1", "Greece", 1)
}

SEASONS = {
    "2024/25": "2425",
    "2023/24": "2324",
    "2022/23": "2223",
    "2021/22": "2122",
    "2020/21": "2021"
}


# ==============================
# DB 만들기
# ==============================

def create_database():

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
        odds_type TEXT,
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


create_database()


# ==============================
# DB 경기수
# ==============================

def database_count():

    conn = sqlite3.connect(DB_FILE)

    value = conn.execute(
        "SELECT COUNT(*) FROM matches"
    ).fetchone()[0]

    conn.close()

    return int(value)


# ==============================
# DB 읽기
# ==============================

def read_database():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query(
        "SELECT * FROM matches",
        conn
    )

    conn.close()

    return df


# ==============================
# CSV 다운로드
# ==============================

def download_csv(season_code, league_code):

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
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code != 200:

            return None, (
                "HTTP 오류 "
                + str(response.status_code)
            )

        response.encoding = "latin1"

        if len(response.text) < 500:

            return None, "파일 내용이 없습니다."

        df = pd.read_csv(
            StringIO(response.text)
        )

        return df, None

    except Exception as error:

        return None, str(error)


# ==============================
# 숫자 변환
# ==============================

def convert_number(value):

    try:

        if pd.isna(value):
            return None

        number = float(value)

        if number <= 1:
            return None

        return number

    except Exception:

        return None


# ==============================
# Bet365 컬럼 찾기
# ==============================

def get_bet365_columns(df):

    if all(
        column in df.columns
        for column in [
            "B365CH",
            "B365CD",
            "B365CA"
        ]
    ):

        return (
            "B365CH",
            "B365CD",
            "B365CA",
            "마감배당"
        )

    if all(
        column in df.columns
        for column in [
            "B365H",
            "B365D",
            "B365A"
        ]
    ):

        return (
            "B365H",
            "B365D",
            "B365A",
            "일반배당"
        )

    return (
        None,
        None,
        None,
        "배당없음"
    )


# ==============================
# 경기 저장
# ==============================

def save_to_database(
    df,
    league_name,
    season_name
):

    required_columns = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTR"
    ]

    missing = []

    for column in required_columns:

        if column not in df.columns:
            missing.append(column)

    if missing:

        return (
            0,
            0,
            "필수 컬럼 없음: "
            + ", ".join(missing)
        )

    code, country, division = LEAGUES[
        league_name
    ]

    home_col, draw_col, away_col, odds_type = (
        get_bet365_columns(df)
    )

    conn = sqlite3.connect(DB_FILE)

    processed = 0
    inserted = 0

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

            match_date = str(
                row["Date"]
            ).strip()

            if home == "" or away == "":
                continue

            if home_col is not None:

                home_odds = convert_number(
                    row[home_col]
                )

                draw_odds = convert_number(
                    row[draw_col]
                )

                away_odds = convert_number(
                    row[away_col]
                )

            else:

                home_odds = None
                draw_odds = None
                away_odds = None

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
                    odds_type,
                    source,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    country,
                    league_name,
                    division,
                    season_name,
                    match_date,
                    home,
                    away,
                    result,
                    home_odds,
                    draw_odds,
                    away_odds,
                    odds_type,
                    "Football-Data.co.uk",
                    datetime.now().isoformat()
                )
            )

            processed += 1

            if cursor.rowcount == 1:
                inserted += 1

        except Exception:
            continue

    conn.commit()
    conn.close()

    return (
        inserted,
        processed,
        odds_type
    )


# ==============================
# 데이터 수집
# ==============================

def collect_data(
    selected_leagues,
    selected_seasons
):

    total_jobs = (
        len(selected_leagues)
        * len(selected_seasons)
    )

    job_number = 0
    total_inserted = 0
    total_processed = 0

    progress = st.progress(0)

    for league_name in selected_leagues:

        league_code = LEAGUES[
            league_name
        ][0]

        for season_name in selected_seasons:

            job_number += 1

            progress.progress(
                job_number / total_jobs
            )

            st.write(
                "📥 "
                + league_name
                + " / "
                + season_name
            )

            df, error = download_csv(
                SEASONS[season_name],
                league_code
            )

            if error is not None:

                st.error(
                    "다운로드 실패: "
                    + error
                )

                continue

            inserted, processed, odds_type = (
                save_to_database(
                    df,
                    league_name,
                    season_name
                )
            )

            total_inserted += inserted
            total_processed += processed

            st.success(
                "CSV "
                + str(len(df))
                + "행 / 처리 "
                + str(processed)
                + " / 신규 "
                + str(inserted)
                + " / "
                + odds_type
            )

    progress.progress(1.0)

    return (
        total_inserted,
        total_processed
    )


# ==============================
# 배당 분석
# ==============================

def analyze_odds(
    df,
    home_odds,
    draw_odds,
    away_odds,
    tolerance,
    selected_league
):

    if df.empty:
        return None

    if selected_league != "전체":

        df = df[
            df["league"]
            == selected_league
        ]

    if df.empty:
        return None

    df = df.dropna(
        subset=[
            "bet365_home",
            "bet365_draw",
            "bet365_away"
        ]
    ).copy()

    if df.empty:
        return None

    df["승차이"] = abs(
        df["bet365_home"]
        - home_odds
    )

    df["무차이"] = abs(
        df["bet365_draw"]
        - draw_odds
    )

    df["패차이"] = abs(
        df["bet365_away"]
        - away_odds
    )

    similar = df[
        (df["승차이"] <= tolerance)
        &
        (df["무차이"] <= tolerance)
        &
        (df["패차이"] <= tolerance)
    ].copy()

    if similar.empty:
        return None

    similar["총차이"] = (
        similar["승차이"]
        + similar["무차이"]
        + similar["패차이"]
    )

    similar = similar.sort_values(
        "총차이"
    )

    total = len(similar)

    win_count = int(
        (similar["result"] == "H").sum()
    )

    draw_count = int(
        (similar["result"] == "D").sum()
    )

    loss_count = int(
        (similar["result"] == "A").sum()
    )

    return {
        "data": similar,
        "total": total,
        "win_count": win_count,
        "draw_count": draw_count,
        "loss_count": loss_count,
        "win_pct": win_count / total * 100,
        "draw_pct": draw_count / total * 100,
        "loss_pct": loss_count / total * 100
    }


# ==============================
# 화면
# ==============================

st.title("⚽ 해외 배당 분석")

st.caption(
    "과거 경기결과 + Bet365 배당 비교"
)

current_count = database_count()

st.metric(
    "현재 historical_odds.db 경기수",
    str(current_count)
    + " 경기"
)


# ==============================
# 데이터 수집 메뉴
# ==============================

with st.expander(
    "📥 과거 데이터 DB 만들기",
    expanded=True
):

    selected_leagues = st.multiselect(
        "리그 선택",
        list(LEAGUES.keys()),
        default=[
            "잉글랜드 1부"
        ]
    )

    selected_seasons = st.multiselect(
        "시즌 선택",
        list(SEASONS.keys()),
        default=[
            "2024/25"
        ]
    )

    if st.button(
        "🚀 데이터 수집 시작",
        type="primary",
        use_container_width=True
    ):

        if len(selected_leagues) == 0:

            st.error(
                "리그를 선택하세요."
            )

        elif len(selected_seasons) == 0:

            st.error(
                "시즌을 선택하세요."
            )

        else:

            before = database_count()

            inserted, processed = collect_data(
                selected_leagues,
                selected_seasons
            )

            after = database_count()

            st.success(
                "수집 완료"
            )

            st.write(
                "기존 DB: "
                + str(before)
                + "경기"
            )

            st.write(
                "처리: "
                + str(processed)
                + "경기"
            )

            st.write(
                "신규 저장: "
                + str(inserted)
                + "경기"
            )

            st.write(
                "현재 DB: "
                + str(after)
                + "경기"
            )


# ==============================
# 현재 경기 입력
# ==============================

st.divider()

st.subheader(
    "🎯 현재 경기"
)

home_team = st.text_input(
    "홈팀",
    placeholder="예: Liverpool"
)

away_team = st.text_input(
    "원정팀",
    placeholder="예: Chelsea"
)

selected_league = st.selectbox(
    "분석 리그",
    ["전체"] + list(LEAGUES.keys())
)


# ==============================
# 배당 입력
# ==============================

st.subheader(
    "💰 승무패 배당"
)

col1, col2, col3 = st.columns(3)

with col1:

    home_odds = st.number_input(
        "승",
        min_value=1.01,
        max_value=100.0,
        value=1.85,
        step=0.01
    )

with col2:

    draw_odds = st.number_input(
        "무",
        min_value=1.01,
        max_value=100.0,
        value=3.60,
        step=0.01
    )

with col3:

    away_odds = st.number_input(
        "패",
        min_value=1.01,
        max_value=100.0,
        value=4.20,
        step=0.01
    )


tolerance = st.select_slider(
    "유사배당 허용범위",
    options=[
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.40,
        0.50
    ],
    value=0.20
)


# ==============================
# 분석
# ==============================

if st.button(
    "🔍 승무패 분석",
    type="primary",
    use_container_width=True
):

    database = read_database()

    if database.empty:

        st.error(
            "historical_odds.db가 비어 있습니다."
        )

        st.info(
            "먼저 위의 "
            "'데이터 수집 시작'을 눌러주세요."
        )

    else:

        result = analyze_odds(
            database,
            home_odds,
            draw_odds,
            away_odds,
            tolerance,
            selected_league
        )

        if result is None:

            st.warning(
                "현재 배당과 비슷한 "
                "과거 경기가 없습니다."
            )

            st.info(
                "유사배당 허용범위를 "
                "0.30 또는 0.40으로 "
                "높여보세요."
            )

        else:

            win = result["win_pct"]
            draw = result["draw_pct"]
            loss = result["loss_pct"]

            st.divider()

            st.subheader(
                "📊 분석 결과"
            )

            a, b, c = st.columns(3)

            with a:

                st.metric(
                    "🟢 승",
                    f"{win:.2f}%"
                )

            with b:

                st.metric(
                    "🔵 무",
                    f"{draw:.2f}%"
                )

            with c:

                st.metric(
                    "🔴 패",
                    f"{loss:.2f}%"
                )

            probability = {
                "승": win,
                "무": draw,
                "패": loss
            }

            best = max(
                probability,
                key=probability.get
            )

            st.success(
                "🏆 과거 최다 결과: "
                + best
                + " "
                + f"{probability[best]:.2f}%"
            )

            st.write(
                "유사 경기 수: "
                + str(result["total"])
            )

            result_table = pd.DataFrame({
                "결과": [
                    "승",
                    "무",
                    "패"
                ],
                "경기수": [
                    result["win_count"],
                    result["draw_count"],
                    result["loss_count"]
                ],
                "확률": [
                    f"{win:.2f}%",
                    f"{draw:.2f}%",
                    f"{loss:.2f}%"
                ]
            })

            st.dataframe(
                result_table,
                use_container_width=True,
                hide_index=True
            )

            st.subheader(
                "📋 유사배당 경기"
            )

            table = result["data"][
                [
                    "season",
                    "match_date",
                    "home_team",
                    "away_team",
                    "bet365_home",
                    "bet365_draw",
                    "bet365_away",
                    "result"
                ]
            ].head(100).copy()

            table.columns = [
                "시즌",
                "날짜",
                "홈팀",
                "원정팀",
                "승배당",
                "무배당",
                "패배당",
                "결과"
            ]

            table["결과"] = table[
                "결과"
            ].replace({
                "H": "승",
                "D": "무",
                "A": "패"
            })

            st.dataframe(
                table,
                use_container_width=True,
                hide_index=True
            )


# ==============================
# CSV 다운로드
# ==============================

st.divider()

database = read_database()

if not database.empty:

    csv_data = database.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        "📥 historical_odds.csv 다운로드",
        data=csv_data,
        file_name="historical_odds.csv",
        mime="text/csv",
        use_container_width=True
    )

else:

    st.info(
        "DB에 데이터가 들어오면 "
        "CSV 다운로드가 가능합니다."
    )


st.caption(
    "과거 통계는 미래 경기 결과를 보장하지 않습니다."
    )
