import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
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

st.title("⚽ 전종목 해외배당 승무패 분석")
st.caption("해외배당 평균값을 기준으로 승/무/패 확률을 계산합니다.")

# =========================================================
# API 설정
# =========================================================

API_KEY = st.sidebar.text_input(
    "The Odds API Key",
    type="password",
    help="The Odds API의 API Key를 입력하세요."
)

SPORTS = {
    "축구 - EPL": "soccer_epl",
    "축구 - 챔피언스리그": "soccer_uefa_champs_league",
    "축구 - 라리가": "soccer_spain_la_liga",
    "축구 - 분데스리가": "soccer_germany_bundesliga",
    "축구 - 세리에A": "soccer_italy_serie_a",
    "축구 - 리그1": "soccer_france_ligue_one",
    "축구 - K리그": "soccer_korea_k_league_1",
    "축구 - J리그": "soccer_japan_j_league",
    "축구 전체": "soccer"
}

sport_name = st.sidebar.selectbox(
    "종목 선택",
    list(SPORTS.keys())
)

sport_key = SPORTS[sport_name]

# =========================================================
# 데이터베이스
# =========================================================

DB_FILE = "historical_odds.db"


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
# API 데이터 가져오기
# =========================================================

@st.cache_data(ttl=60)
def get_odds(api_key, sport):
    if not api_key:
        return None, "API Key를 입력해주세요."

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
            timeout=20
        )

        if response.status_code != 200:
            return None, f"API 오류: {response.status_code}\n{response.text}"

        return response.json(), None

    except requests.exceptions.RequestException as e:
        return None, f"네트워크 오류: {e}"


# =========================================================
# 배당 데이터 분석
# =========================================================

def get_average_odds(game):
    """
    여러 해외사이트의 승/무/패 배당을 평균 계산
    """

    home_odds = []
    draw_odds = []
    away_odds = []

    bookmakers = game.get("bookmakers", [])

    for bookmaker in bookmakers:

        markets = bookmaker.get("markets", [])

        for market in markets:

            if market.get("key") != "h2h":
                continue

            outcomes = market.get("outcomes", [])

            for outcome in outcomes:

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

                elif name in ["Draw", "무승부"]:
                    draw_odds.append(price)

    avg_home = np.mean(home_odds) if home_odds else None
    avg_draw = np.mean(draw_odds) if draw_odds else None
    avg_away = np.mean(away_odds) if away_odds else None

    return avg_home, avg_draw, avg_away, len(bookmakers)


# =========================================================
# 배당 → 확률 변환
# =========================================================

def odds_to_probability(home, draw, away):

    if not home or not draw or not away:
        return None

    try:

        p_home = 1 / home
        p_draw = 1 / draw
        p_away = 1 / away

        total = p_home + p_draw + p_away

        home_prob = p_home / total * 100
        draw_prob = p_draw / total * 100
        away_prob = p_away / total * 100

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

def odds_range(odds):

    if odds is None:
        return "-"

    if odds < 1.30:
        return "1.00~1.29"

    elif odds < 1.50:
        return "1.30~1.49"

    elif odds < 1.70:
        return "1.50~1.69"

    elif odds < 2.00:
        return "1.70~1.99"

    elif odds < 2.50:
        return "2.00~2.49"

    elif odds < 3.00:
        return "2.50~2.99"

    elif odds < 4.00:
        return "3.00~3.99"

    else:
        return "4.00+"


# =========================================================
# 경기 분석
# =========================================================

def analyze_game(game):

    home = game.get("home_team", "")
    away = game.get("away_team", "")

    avg_home, avg_draw, avg_away, bookmaker_count = get_average_odds(game)

    probabilities = odds_to_probability(
        avg_home,
        avg_draw,
        avg_away
    )

    if probabilities:

        home_prob, draw_prob, away_prob = probabilities

        probs = {
            "승": home_prob,
            "무": draw_prob,
            "패": away_prob
        }

        predicted = max(
            probs,
            key=probs.get
        )

        predicted_probability = probs[predicted]

    else:

        home_prob = None
        draw_prob = None
        away_prob = None
        predicted = "-"
        predicted_probability = None

    return {
        "경기": f"{home} vs {away}",
        "시간": game.get(
            "commence_time",
            ""
        ),

        "승배당": avg_home,
        "무배당": avg_draw,
        "패배당": avg_away,

        "승확률": home_prob,
        "무확률": draw_prob,
        "패확률": away_prob,

        "추천": predicted,
        "추천확률": predicted_probability,

        "승배당구간": odds_range(avg_home),
        "무배당구간": odds_range(avg_draw),
        "패배당구간": odds_range(avg_away),

        "사이트수": bookmaker_count
    }


# =========================================================
# 데이터 저장
# =========================================================

def save_history(games):

    conn = sqlite3.connect(DB_FILE)

    for game in games:

        home = game.get("home_team", "")
        away = game.get("away_team", "")

        avg_home, avg_draw, avg_away, bookmaker_count = get_average_odds(game)

        game_id = game.get(
            "id",
            f"{home}_{away}_{game.get('commence_time', '')}"
        )

        conn.execute("""
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
        """, (
            game_id,
            sport_key,
            game.get("commence_time", ""),
            home,
            away,
            avg_home,
            avg_draw,
            avg_away,
            bookmaker_count,
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()


# =========================================================
# 기록 데이터 조회
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
# 실행 버튼
# =========================================================

if st.sidebar.button(
    "🔄 해외배당 가져오기",
    type="primary"
):

    if not API_KEY:

        st.error(
            "먼저 The Odds API Key를 입력해주세요."
        )

    else:

        with st.spinner(
            "해외 배당 데이터를 가져오는 중..."
        ):

            games, error = get_odds(
                API_KEY,
                sport_key
            )

        if error:

            st.error(error)

        elif not games:

            st.warning(
                "현재 가져올 수 있는 경기가 없습니다."
            )

        else:

            # 데이터 저장
            save_history(games)

            # 분석
            analysis = []

            for game in games:

                result = analyze_game(game)

                # 배당이 정상적인 경기만 표시
                if (
                    result["승배당"] is not None
                    and result["무배당"] is not None
                    and result["패배당"] is not None
                ):

                    analysis.append(result)

            df = pd.DataFrame(analysis)

            if df.empty:

                st.warning(
                    "승/무/패 배당 데이터를 찾지 못했습니다."
                )

            else:

                st.session_state["analysis_df"] = df

                st.success(
                    f"{len(df)}경기 분석 완료"
                )


# =========================================================
# 분석 결과 표시
# =========================================================

if "analysis_df" in st.session_state:

    df = st.session_state["analysis_df"].copy()

    st.subheader("📊 전체 경기 분석")

    # -----------------------------------------------------
    # 필터
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        min_prob = st.number_input(
            "최소 추천확률",
            min_value=0,
            max_value=100,
            value=50
        )

    with col2:

        result_filter = st.selectbox(
            "결과 필터",
            ["전체", "승", "무", "패"]
        )

    with col3:

        min_sites = st.number_input(
            "최소 해외사이트 수",
            min_value=1,
            max_value=50,
            value=3
        )

    with col4:

        sort_option = st.selectbox(
            "정렬",
            [
                "추천확률 높은순",
                "승확률 높은순",
                "무확률 높은순",
                "패확률 높은순"
            ]
        )

    # -----------------------------------------------------
    # 필터 적용
    # -----------------------------------------------------

    filtered = df.copy()

    filtered = filtered[
        filtered["추천확률"].fillna(0) >= min_prob
    ]

    filtered = filtered[
        filtered["사이트수"].fillna(0) >= min_sites
    ]

    if result_filter != "전체":

        filtered = filtered[
            filtered["추천"] == result_filter
        ]

    # -----------------------------------------------------
    # 정렬
    # -----------------------------------------------------

    sort_columns = {
        "추천확률 높은순": "추천확률",
        "승확률 높은순": "승확률",
        "무확률 높은순": "무확률",
        "패확률 높은순": "패확률"
    }

    sort_column = sort_columns[sort_option]

    filtered = filtered.sort_values(
        sort_column,
        ascending=False
    )

    # -----------------------------------------------------
    # 화면 표시용 데이터
    # -----------------------------------------------------

    display_df = filtered.copy()

    display_df["승배당"] = display_df["승배당"].round(2)
    display_df["무배당"] = display_df["무배당"].round(2)
    display_df["패배당"] = display_df["패배당"].round(2)

    display_df["승확률"] = (
        display_df["승확률"].round(1).astype(str) + "%"
    )

    display_df["무확률"] = (
        display_df["무확률"].round(1).astype(str) + "%"
    )

    display_df["패확률"] = (
        display_df["패확률"].round(1).astype(str) + "%"
    )

    display_df["추천확률"] = (
        display_df["추천확률"].round(1).astype(str) + "%"
    )

    display_df = display_df[
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
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 추천 경기
    # =====================================================

    st.subheader("🔥 추천 경기")

    if not filtered.empty:

        top_games = filtered.head(10)

        for _, row in top_games.iterrows():

            recommendation = row["추천"]

            if recommendation == "승":
                color = "green"

            elif recommendation == "무":
                color = "orange"

            else:
                color = "red"

            st.markdown(
                f"""
                <div style="
                    padding:12px;
                    margin:5px 0;
                    border-radius:10px;
                    background-color:#f5f5f5;
                    border-left:6px solid {color};
                ">
                    <b>{row['경기']}</b><br>
                    추천: <b>{recommendation}</b>
                    &nbsp;&nbsp;
                    추천확률: <b>{row['추천확률']:.1f}%</b><br>
                    승 {row['승배당']:.2f}
                    &nbsp; | &nbsp;
                    무 {row['무배당']:.2f}
                    &nbsp; | &nbsp;
                    패 {row['패배당']:.2f}
                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "조건에 맞는 추천 경기가 없습니다."
        )


# =========================================================
# 무승부 후보
# =========================================================

st.subheader("🤝 무승부 후보")

if "analysis_df" in st.session_state:

    draw_df = st.session_state["analysis_df"].copy()

    draw_df = draw_df.sort_values(
        "무확률",
        ascending=False
    ).head(10)

    if not draw_df.empty:

        draw_display = draw_df[
            [
                "경기",
                "무배당",
                "무확률",
                "승배당",
                "패배당",
                "사이트수"
            ]
        ].copy()

        draw_display["무배당"] = (
            draw_display["무배당"].round(2)
        )

        draw_display["무확률"] = (
            draw_display["무확률"].round(1).astype(str)
            + "%"
        )

        draw_display["승배당"] = (
            draw_display["승배당"].round(2)
        )

        draw_display["패배당"] = (
            draw_display["패배당"].round(2)
        )

        st.dataframe(
            draw_display,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# 배당구간 분석
# =========================================================

st.subheader("📈 현재 배당구간 분석")

if "analysis_df" in st.session_state:

    temp = st.session_state["analysis_df"].copy()

    range_df = (
        temp.groupby("승배당구간")
        .agg(
            경기수=("경기", "count"),
            평균승확률=("승확률", "mean")
        )
        .reset_index()
    )

    range_df["평균승확률"] = (
        range_df["평균승확률"].round(2)
    )

    st.dataframe(
        range_df,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# 과거 배당 데이터
# =========================================================

st.subheader("🗄️ 저장된 해외배당 기록")

history_df = load_history()

if not history_df.empty:

    st.write(
        f"저장된 데이터: **{len(history_df):,}건**"
    )

    st.dataframe(
        history_df.head(100),
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "아직 저장된 과거 배당 데이터가 없습니다."
    )


# =========================================================
# CSV 다운로드
# =========================================================

if "analysis_df" in st.session_state:

    csv = st.session_state[
        "analysis_df"
    ].to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        label="📥 분석 결과 CSV 다운로드",
        data=csv,
        file_name="해외배당_분석.csv",
        mime="text/csv"
    )


# =========================================================
# 하단 안내
# =========================================================

st.divider()

st.caption(
    "※ 배당으로 계산한 확률은 실제 경기 결과를 보장하지 않습니다. "
    "해외 배당사의 마진 및 시장 변동에 따라 실제 확률과 차이가 있을 수 있습니다."
)
