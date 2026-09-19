import streamlit as st
import requests
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime

# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="전종목 해외배당 분석",
    page_icon="⚽",
    layout="wide"
)

DB_FILE = "historical_odds.db"


# =========================================================
# 데이터베이스 자동 생성
# =========================================================

def init_database():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS odds_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            sport TEXT,
            commence_time TEXT,
            home_team TEXT,
            away_team TEXT,
            home_odds REAL,
            draw_odds REAL,
            away_odds REAL,
            bookmaker_count INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# 화면
# =========================================================

st.title("⚽ 전종목 해외배당 승무패 분석")

st.write(
    "해외 배당을 수집하여 승/무/패 확률과 "
    "배당구간을 분석합니다."
)


# =========================================================
# 사이드바
# =========================================================

st.sidebar.header("⚙️ 설정")

API_KEY = st.sidebar.text_input(
    "The Odds API Key",
    type="password"
)

SPORTS = {
    "축구 - EPL": "soccer_epl",
    "축구 - 챔피언스리그": "soccer_uefa_champs_league",
    "축구 - 라리가": "soccer_spain_la_liga",
    "축구 - 분데스리가": "soccer_germany_bundesliga",
    "축구 - 세리에A": "soccer_italy_serie_a",
    "축구 - 리그1": "soccer_france_ligue_one",
    "축구 - K리그": "soccer_korea_k_league_1",
    "축구 - J리그": "soccer_japan_j_league"
}

sport_name = st.sidebar.selectbox(
    "종목",
    list(SPORTS.keys())
)

sport_key = SPORTS[sport_name]


# =========================================================
# 해외배당 가져오기
# =========================================================

def get_odds(api_key, sport):

    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": api_key,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            return None, (
                f"API 오류 {response.status_code}\n"
                f"{response.text}"
            )

        return response.json(), None

    except Exception as e:

        return None, str(e)


# =========================================================
# 해외사이트 배당 평균
# =========================================================

def get_average_odds(game):

    home_odds = []
    draw_odds = []
    away_odds = []

    bookmakers = game.get("bookmakers", [])

    for bookmaker in bookmakers:

        for market in bookmaker.get("markets", []):

            if market.get("key") != "h2h":
                continue

            for outcome in market.get("outcomes", []):

                name = outcome.get("name")
                price = outcome.get("price")

                if price is None:
                    continue

                try:
                    price = float(price)
                except:
                    continue

                if name == game.get("home_team"):

                    home_odds.append(price)

                elif name == game.get("away_team"):

                    away_odds.append(price)

                elif name.lower() in [
                    "draw",
                    "무",
                    "무승부"
                ]:

                    draw_odds.append(price)

    home = (
        round(float(np.mean(home_odds)), 3)
        if home_odds else None
    )

    draw = (
        round(float(np.mean(draw_odds)), 3)
        if draw_odds else None
    )

    away = (
        round(float(np.mean(away_odds)), 3)
        if away_odds else None
    )

    return home, draw, away, len(bookmakers)


# =========================================================
# 배당 → 확률
# =========================================================

def calculate_probability(
    home_odds,
    draw_odds,
    away_odds
):

    if not all([
        home_odds,
        draw_odds,
        away_odds
    ]):
        return None

    try:

        home_raw = 1 / home_odds
        draw_raw = 1 / draw_odds
        away_raw = 1 / away_odds

        total = (
            home_raw +
            draw_raw +
            away_raw
        )

        home_prob = home_raw / total * 100
        draw_prob = draw_raw / total * 100
        away_prob = away_raw / total * 100

        return (
            round(home_prob, 2),
            round(draw_prob, 2),
            round(away_prob, 2)
        )

    except:

        return None


# =========================================================
# 배당구간
# =========================================================

def get_odds_range(odds):

    if odds is None:
        return "-"

    if odds < 1.30:
        return "1.00~1.29"

    if odds < 1.50:
        return "1.30~1.49"

    if odds < 1.70:
        return "1.50~1.69"

    if odds < 2.00:
        return "1.70~1.99"

    if odds < 2.50:
        return "2.00~2.49"

    if odds < 3.00:
        return "2.50~2.99"

    if odds < 4.00:
        return "3.00~3.99"

    return "4.00+"


# =========================================================
# 경기 분석
# =========================================================

def analyze_game(game):

    home_team = game.get(
        "home_team",
        ""
    )

    away_team = game.get(
        "away_team",
        ""
    )

    home_odds, draw_odds, away_odds, sites = (
        get_average_odds(game)
    )

    probabilities = calculate_probability(
        home_odds,
        draw_odds,
        away_odds
    )

    if probabilities:

        home_prob = probabilities[0]
        draw_prob = probabilities[1]
        away_prob = probabilities[2]

        result_map = {
            "승": home_prob,
            "무": draw_prob,
            "패": away_prob
        }

        recommendation = max(
            result_map,
            key=result_map.get
        )

        recommendation_prob = result_map[
            recommendation
        ]

    else:

        home_prob = None
        draw_prob = None
        away_prob = None

        recommendation = "-"
        recommendation_prob = None

    return {

        "경기":
            f"{home_team} vs {away_team}",

        "시간":
            game.get(
                "commence_time",
                ""
            ),

        "승배당":
            home_odds,

        "무배당":
            draw_odds,

        "패배당":
            away_odds,

        "승확률":
            home_prob,

        "무확률":
            draw_prob,

        "패확률":
            away_prob,

        "추천":
            recommendation,

        "추천확률":
            recommendation_prob,

        "승배당구간":
            get_odds_range(home_odds),

        "무배당구간":
            get_odds_range(draw_odds),

        "패배당구간":
            get_odds_range(away_odds),

        "사이트수":
            sites
    }


# =========================================================
# DB 저장
# =========================================================

def save_games(games):

    conn = sqlite3.connect(DB_FILE)

    saved = 0

    for game in games:

        home_team = game.get(
            "home_team",
            ""
        )

        away_team = game.get(
            "away_team",
            ""
        )

        commence_time = game.get(
            "commence_time",
            ""
        )

        home_odds, draw_odds, away_odds, sites = (
            get_average_odds(game)
        )

        game_id = game.get("id")

        if not game_id:

            game_id = (
                home_team +
                "_" +
                away_team +
                "_" +
                commence_time
            )

        conn.execute(
            """
            INSERT INTO odds_history (
                game_id,
                sport,
                commence_time,
                home_team,
                away_team,
                home_odds,
                draw_odds,
                away_odds,
                bookmaker_count,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                sport_key,
                commence_time,
                home_team,
                away_team,
                home_odds,
                draw_odds,
                away_odds,
                sites,
                datetime.now().isoformat()
            )
        )

        saved += 1

    conn.commit()
    conn.close()

    return saved


# =========================================================
# DB 불러오기
# =========================================================

def load_history():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query(
        """
        SELECT *
        FROM odds_history
        ORDER BY created_at DESC
        """,
        conn
    )

    conn.close()

    return df


# =========================================================
# 배당 가져오기 버튼
# =========================================================

if st.sidebar.button(
    "🔄 해외배당 가져오기",
    type="primary"
):

    if not API_KEY:

        st.error(
            "왼쪽에 The Odds API Key를 입력해주세요."
        )

    else:

        with st.spinner(
            "해외배당을 가져오는 중..."
        ):

            games, error = get_odds(
                API_KEY,
                sport_key
            )

        if error:

            st.error(error)

        elif not games:

            st.warning(
                "현재 경기 데이터가 없습니다."
            )

        else:

            saved_count = save_games(games)

            results = []

            for game in games:

                result = analyze_game(game)

                if (
                    result["승배당"] is not None
                    and
                    result["무배당"] is not None
                    and
                    result["패배당"] is not None
                ):

                    results.append(result)

            if results:

                st.session_state[
                    "analysis_df"
                ] = pd.DataFrame(results)

                st.success(
                    f"{len(results)}경기 분석 완료 / "
                    f"{saved_count}건 DB 저장"
                )

            else:

                st.warning(
                    "승무패 배당 데이터를 찾지 못했습니다."
                )


# =========================================================
# 분석 결과
# =========================================================

if "analysis_df" in st.session_state:

    df = st.session_state[
        "analysis_df"
    ].copy()

    st.header("📊 경기별 해외배당 분석")

    # -----------------------------------------------------
    # 필터
    # -----------------------------------------------------

    c1, c2, c3 = st.columns(3)

    with c1:

        min_probability = st.slider(
            "최소 추천확률",
            0,
            100,
            50
        )

    with c2:

        result_filter = st.selectbox(
            "추천 결과",
            [
                "전체",
                "승",
                "무",
                "패"
            ]
        )

    with c3:

        min_sites = st.number_input(
            "최소 해외사이트",
            1,
            50,
            3
        )

    filtered = df.copy()

    filtered = filtered[
        filtered["추천확률"].fillna(0)
        >= min_probability
    ]

    filtered = filtered[
        filtered["사이트수"]
        >= min_sites
    ]

    if result_filter != "전체":

        filtered = filtered[
            filtered["추천"]
            == result_filter
        ]

    filtered = filtered.sort_values(
        "추천확률",
        ascending=False
    )

    # -----------------------------------------------------
    # 통계 카드
    # -----------------------------------------------------

    a, b, c, d = st.columns(4)

    with a:
        st.metric(
            "전체 경기",
            len(df)
        )

    with b:
        st.metric(
            "승 추천",
            len(
                filtered[
                    filtered["추천"] == "승"
                ]
            )
        )

    with c:
        st.metric(
            "무 추천",
            len(
                filtered[
                    filtered["추천"] == "무"
                ]
            )
        )

    with d:
        st.metric(
            "패 추천",
            len(
                filtered[
                    filtered["추천"] == "패"
                ]
            )
        )

    # -----------------------------------------------------
    # 표
    # -----------------------------------------------------

    table = filtered.copy()

    for col in [
        "승배당",
        "무배당",
        "패배당"
    ]:

        table[col] = table[col].round(2)

    for col in [
        "승확률",
        "무확률",
        "패확률",
        "추천확률"
    ]:

        table[col] = (
            table[col]
            .round(1)
            .astype(str)
            + "%"
        )

    table = table[
        [
            "경기",
            "시간",
            "승배당",
            "무배당",
            "패배당",
            "승확률",
            "무확률",
            "패확률",
            "추천",
            "추천확률",
            "사이트수"
        ]
    ]

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# 무승부 후보
# =========================================================

if "analysis_df" in st.session_state:

    st.header("🤝 무승부 후보")

    draw = (
        st.session_state[
            "analysis_df"
        ]
        .copy()
        .sort_values(
            "무확률",
            ascending=False
        )
        .head(10)
    )

    if not draw.empty:

        draw_table = draw[
            [
                "경기",
                "무배당",
                "무확률",
                "승배당",
                "패배당",
                "사이트수"
            ]
        ].copy()

        draw_table["무배당"] = (
            draw_table["무배당"].round(2)
        )

        draw_table["무확률"] = (
            draw_table["무확률"]
            .round(1)
            .astype(str)
            + "%"
        )

        draw_table["승배당"] = (
            draw_table["승배당"].round(2)
        )

        draw_table["패배당"] = (
            draw_table["패배당"].round(2)
        )

        st.dataframe(
            draw_table,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# 배당 구간 분석
# =========================================================

if "analysis_df" in st.session_state:

    st.header("📈 승 배당구간 분석")

    range_data = (
        st.session_state[
            "analysis_df"
        ]
        .groupby("승배당구간")
        .agg(
            경기수=("경기", "count"),
            평균승확률=("승확률", "mean")
        )
        .reset_index()
    )

    range_data["평균승확률"] = (
        range_data["평균승확률"]
        .round(2)
    )

    st.dataframe(
        range_data,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# 저장된 DB
# =========================================================

st.header("🗄️ historical_odds.db")

history = load_history()

if history.empty:

    st.info(
        "아직 저장된 배당 데이터가 없습니다."
    )

else:

    st.write(
        f"현재 저장된 배당 데이터: "
        f"**{len(history):,}건**"
    )

    st.dataframe(
        history.head(100),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# CSV 다운로드
# =========================================================

if "analysis_df" in st.session_state:

    csv_data = (
        st.session_state[
            "analysis_df"
        ]
        .to_csv(
            index=False,
            encoding="utf-8-sig"
        )
    )

    st.download_button(
        "📥 분석결과 CSV 저장",
        csv_data,
        "해외배당분석.csv",
        "text/csv"
    )


# =========================================================
# 안내
# =========================================================

st.divider()

st.caption(
    "※ 본 프로그램의 확률은 해외배당을 기반으로 계산한 "
    "시장 암시확률이며 실제 경기 결과를 보장하지 않습니다."
)
