import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="승무패 배당 분석",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ 해외 승무패 배당 분석")
st.caption("해외 최신 배당을 승·무·패 확률로 변환합니다.")

# -----------------------------
# 설정
# -----------------------------

sports = {
    "EPL": "soccer_epl",
    "스페인 라리가": "soccer_spain_la_liga",
    "독일 분데스리가": "soccer_germany_bundesliga",
    "이탈리아 세리에A": "soccer_italy_serie_a",
    "프랑스 리그1": "soccer_france_ligue_one"
}

st.sidebar.header("⚙️ 설정")

api_key = st.sidebar.text_input(
    "The Odds API Key",
    type="password"
)

league_name = st.sidebar.selectbox(
    "리그",
    list(sports.keys())
)

sport = sports[league_name]

regions = st.sidebar.multiselect(
    "해외 배당지역",
    ["uk", "eu", "us", "au"],
    default=["uk", "eu"]
)

# -----------------------------
# 확률 계산
# -----------------------------

def calculate_probability(home, draw, away):

    a = 1 / home
    b = 1 / draw
    c = 1 / away

    total = a + b + c

    return (
        a / total * 100,
        b / total * 100,
        c / total * 100
    )

# -----------------------------
# 배당 가져오기
# -----------------------------

def get_odds():

    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"

    params = {
        "apiKey": api_key,
        "regions": ",".join(regions),
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    if response.status_code != 200:

        st.error(
            f"배당 API 오류: {response.status_code}"
        )

        st.code(response.text)

        return []

    return response.json()

# -----------------------------
# 경기 분석
# -----------------------------

def analyze(game):

    home = game["home_team"]
    away = game["away_team"]

    rows = []

    for bookmaker in game.get("bookmakers", []):

        markets = bookmaker.get("markets", [])

        if not markets:
            continue

        outcomes = markets[0].get(
            "outcomes", []
        )

        home_odds = None
        draw_odds = None
        away_odds = None

        for item in outcomes:

            name = item["name"]
            price = item["price"]

            if name == home:
                home_odds = price

            elif name == away:
                away_odds = price

            elif name.lower() == "draw":
                draw_odds = price

        if (
            home_odds
            and draw_odds
            and away_odds
        ):

            rows.append({
                "업체": bookmaker["title"],
                "승": home_odds,
                "무": draw_odds,
                "패": away_odds
            })

    if not rows:
        return None

    df = pd.DataFrame(rows)

    avg_home = df["승"].mean()
    avg_draw = df["무"].mean()
    avg_away = df["패"].mean()

    p_home, p_draw, p_away = calculate_probability(
        avg_home,
        avg_draw,
        avg_away
    )

    probabilities = {
        "승": p_home,
        "무": p_draw,
        "패": p_away
    }

    recommendation = max(
        probabilities,
        key=probabilities.get
    )

    return {
        "경기": f"{home} vs {away}",
        "시간": game.get("commence_time", ""),
        "승배당": avg_home,
        "무배당": avg_draw,
        "패배당": avg_away,
        "승확률": p_home,
        "무확률": p_draw,
        "패확률": p_away,
        "추천": recommendation,
        "업체수": len(rows),
        "업체별": df
    }

# -----------------------------
# 실행
# -----------------------------

if st.button(
    "🔄 최신 배당 불러오기",
    type="primary"
):

    if not api_key:

        st.warning(
            "왼쪽에 The Odds API Key를 입력하세요."
        )

        st.stop()

    with st.spinner(
        "해외 배당을 불러오는 중..."
    ):

        games = get_odds()

    if not games:
st.warning(
    "배당 데이터가 없습니다."
)
