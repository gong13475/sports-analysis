import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from historical_db import build_database
import os
import sqlite3
st.set_page_config(
    page_title="전종목 해외배당 분석",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽🏀⚾🏒🎾 전종목 해외배당 분석")
if not os.path.exists("historical.db"):
    with st.spinner("📊 과거 5년 배당 DB를 준비하는 중입니다..."):
        try:
            build_database()
            st.success("✅ 과거 배당 DB 준비 완료")
        except Exception as e:
            st.warning(f"과거 DB 생성 오류: {e}")
st.caption("최신 해외배당 → 배당확률 → 승/무/패 분석")

# =========================================================
# API KEY
# =========================================================

st.sidebar.header("⚙️ 설정")

api_key = st.sidebar.text_input(
    "The Odds API Key",
    type="password"
)

# =========================================================
# 스포츠 목록
# =========================================================

def get_sports():

    if not api_key:
        return []

    url = "https://api.the-odds-api.com/v4/sports/"

    try:
        r = requests.get(
            url,
            params={"apiKey": api_key},
            timeout=30
        )

        if r.status_code != 200:
            return []

        return r.json()

    except:
        return []


# =========================================================
# 배당 가져오기
# =========================================================

def get_odds(sport_key):

    url = (
        f"https://api.the-odds-api.com/v4/"
        f"sports/{sport_key}/odds/"
    )

    params = {
        "apiKey": api_key,
        "regions": "uk,eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    try:

        r = requests.get(
            url,
            params=params,
            timeout=30
        )

        if r.status_code != 200:

            st.error(
                f"배당 API 오류: {r.status_code}"
            )

            return []

        return r.json()

    except Exception as e:

        st.error(str(e))
        return []


# =========================================================
# 배당 → 확률
# =========================================================

def calculate_probability(odds):

    values = []

    for x in odds:
        if x and x > 0:
            values.append(1 / x)
        else:
            values.append(0)

    total = sum(values)

    if total == 0:
        return [0 for x in values]

    return [
        x / total * 100
        for x in values
    ]


# =========================================================
# 경기 분석
# =========================================================

def analyze_game(game):

    home = game.get("home_team", "")
    away = game.get("away_team", "")

    rows = []

    for bookmaker in game.get("bookmakers", []):

        markets = bookmaker.get("markets", [])

        if not markets:
            continue

        outcomes = markets[0].get(
            "outcomes", []
        )

        prices = {}

        for item in outcomes:

            name = item.get("name")
            price = item.get("price")

            if name == home:
                prices["home"] = price

            elif name == away:
                prices["away"] = price

            elif name.lower() == "draw":
                prices["draw"] = price

        if (
            "home" in prices
            and "away" in prices
        ):

            rows.append({
                "업체": bookmaker.get(
                    "title", ""
                ),
                "승": prices["home"],
                "무": prices.get("draw"),
                "패": prices["away"]
            })

    if not rows:
        return None

    df = pd.DataFrame(rows)

    avg_home = df["승"].mean()
    avg_away = df["패"].mean()

    has_draw = df["무"].notna().any()

    if has_draw:

        avg_draw = df["무"].mean()

        probabilities = calculate_probability([
            avg_home,
            avg_draw,
            avg_away
        ])

        p_home = probabilities[0]
        p_draw = probabilities[1]
        p_away = probabilities[2]

        recommendation = max(
            {
                "승": p_home,
                "무": p_draw,
                "패": p_away
            },
            key={
                "승": p_home,
                "무": p_draw,
                "패": p_away
            }.get
        )

    else:

        probabilities = calculate_probability([
            avg_home,
            avg_away
        ])

        p_home = probabilities[0]
        p_draw = 0
        p_away = probabilities[1]

        recommendation = (
            "승"
            if p_home >= p_away
            else "패"
        )

    return {
        "경기": f"{home} vs {away}",
        "시간": game.get(
            "commence_time", ""
        ),
        "승배당": avg_home,
        "무배당": avg_draw
        if has_draw else None,
        "패배당": avg_away,
        "승확률": p_home,
        "무확률": p_draw,
        "패확률": p_away,
        "추천": recommendation,
        "업체수": len(rows),
        "업체별": df
    }


# =========================================================
# API KEY 확인
# =========================================================
    }

# =========================================================
# 과거 5년 배당구간 분석
# =========================================================

def historical_probability(
    home_odds,
    draw_odds,
    away_odds
):

    if not os.path.exists("historical.db"):
        return None

    try:

        conn = sqlite3.connect(
            "historical.db"
        )

        query = """
        SELECT result, COUNT(*) AS cnt
        FROM matches
        WHERE home_odds BETWEEN ? AND ?
        AND away_odds BETWEEN ? AND ?
        GROUP BY result
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=[
                home_odds - 0.05,
                home_odds + 0.05,
                away_odds - 0.05,
                away_odds + 0.05
            ]
        )

        conn.close()

        if df.empty:
            return None

        total = df["cnt"].sum()

        result = {
            "승": 0,
            "무": 0,
            "패": 0
        }

        for _, row in df.iterrows():

            if row["result"] == "H":
                result["승"] = (
                    row["cnt"] / total * 100
                )

            elif row["result"] == "D":
                result["무"] = (
                    row["cnt"] / total * 100
                )

            elif row["result"] == "A":
                result["패"] = (
                    row["cnt"] / total * 100
                )

        result["경기수"] = int(total)

        return result

    except Exception:
        return None


# =========================================================
# API KEY 확인
if not api_key:

    st.info(
        "👈 왼쪽에 The Odds API Key를 입력하세요."
    )

    st.stop()


# =========================================================
# 스포츠 목록
# =========================================================

sports = get_sports()

if not sports:

    st.error(
        "스포츠 목록을 가져오지 못했습니다."
    )

    st.stop()


# =========================================================
# 스포츠 선택
# =========================================================

sport_names = {}

for sport in sports:

    title = sport.get(
        "title",
        sport.get("key", "")
    )

    key = sport.get("key")

    sport_names[title] = key


selected_name = st.sidebar.selectbox(
    "🏆 종목 / 리그",
    sorted(sport_names.keys())
)

selected_sport = sport_names[selected_name]


# =========================================================
# 경기 불러오기
# =========================================================

if st.button(
    "🔄 최신 해외배당 불러오기",
    type="primary"
):

    with st.spinner(
        "최신 배당을 가져오는 중..."
    ):

        games = get_odds(
            selected_sport
        )

    if not games:

        st.warning(
            "현재 배당이 있는 경기가 없습니다."
        )

        st.stop()

    results = []

    for game in games:

        result = analyze_game(game)

        if result:
            results.append(result)

    if not results:

        st.warning(
            "분석 가능한 경기가 없습니다."
        )

        st.stop()

    st.success(
        f"{len(results)}경기 분석 완료"
    )


    # =====================================================
    # 전체 경기표
    # =====================================================

    table = []

    for r in results:

        table.append({
            "경기": r["경기"],
            "승": f"{r['승배당']:.2f}",
            "무": (
                "-"
                if r["무배당"] is None
                else f"{r['무배당']:.2f}"
            ),
            "패": f"{r['패배당']:.2f}",
            "승확률": f"{r['승확률']:.1f}%",
            "무확률": (
                "-"
                if r["무배당"] is None
                else f"{r['무확률']:.1f}%"
            ),
            "패확률": f"{r['패확률']:.1f}%",
            "추천": r["추천"],
            "업체수": r["업체수"]
        })

    df_table = pd.DataFrame(table)

    st.subheader(
        f"📋 {selected_name}"
    )

    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 무승부 가능성
    # =====================================================

    draw_games = [
        x for x in results
        if x["무배당"] is not None
    ]

    if draw_games:

        st.subheader(
            "⚠️ 무승부 가능성 높은 경기"
        )

        draw_games = sorted(
            draw_games,
            key=lambda x: x["무확률"],
            reverse=True
        )

        for r in draw_games[:10]:

            if r["무확률"] >= 25:

                st.warning(
                    f"{r['경기']}  "
                    f"→ 무 {r['무확률']:.1f}%"
                )


    # =====================================================
    # 고확률 경기
    # =====================================================

    st.subheader(
        "🔥 고확률 경기"
    )

    high_games = sorted(
        results,
        key=lambda x: max(
            x["승확률"],
            x["무확률"],
            x["패확률"]
        ),
        reverse=True
    )

    for r in high_games[:10]:

        best = max(
            r["승확률"],
            r["무확률"],
            r["패확률"]
        )

        if best >= 50:

            st.success(
                f"⭐ {r['경기']}  "
                f"→ {r['추천']} "
                f"{best:.1f}%"
            )


    # =====================================================
    # 상세 분석
    # =====================================================

    st.subheader(
        "📊 경기 상세 분석"
    )

    for r in results:

        st.markdown(
            f"### ⚽ {r['경기']}"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "승",
                f"{r['승확률']:.1f}%",
                f"배당 {r['승배당']:.2f}"
            )

        with c2:

            if r["무배당"] is not None:

                st.metric(
                    "무",
                    f"{r['무확률']:.1f}%",
                    f"배당 {r['무배당']:.2f}"
                )

            else:

                st.metric(
                    "무",
                    "해당없음"
                )

        with c3:

            st.metric(
                "패",
                f"{r['패확률']:.1f}%",
                f"배당 {r['패배당']:.2f}"
            )

        st.write(
            f"⭐ 추천: **{r['추천']}**"
        )

        with st.expander(
            "🌎 해외업체별 배당"
        ):

            st.dataframe(
                r["업체별"],
                use_container_width=True,
                hide_index=True
            )

        st.divider()


    # =====================================================
    # CSV 다운로드
    # =====================================================

    csv = df_table.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        "📥 분석결과 CSV 저장",
        csv,
        "sports_analysis.csv",
        "text/csv"
    )
