import streamlit as st
import sqlite3
import requests
import pandas as pd
from datetime import datetime


# =========================================================
# 기본 설정
# =========================================================

DB_FILE = "historical_odds.db"

BASE_URL = "https://api.the-odds-api.com/v4"

st.set_page_config(
    page_title="전종목 해외배당 분석",
    page_icon="⚽",
    layout="wide"
)


# =========================================================
# DB 생성
# =========================================================

def init_database():

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

            UNIQUE(game_id, bookmaker)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            created_at TEXT,

            sport TEXT,

            league TEXT,

            home_team TEXT,

            away_team TEXT,

            home_odds REAL,

            draw_odds REAL,

            away_odds REAL,

            predicted TEXT,

            actual_result TEXT,

            correct INTEGER
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# DB 연결
# =========================================================

def db():

    return sqlite3.connect(DB_FILE)


# =========================================================
# API 테스트
# =========================================================

def test_api(api_key):

    if not api_key:

        return False, "API 키가 없습니다."

    try:

        response = requests.get(

            BASE_URL + "/sports/",

            params={
                "apiKey": api_key
            },

            timeout=15
        )


        if response.status_code == 200:

            return True, "API 연결 성공"

        return False, (
            f"API 오류 "
            f"{response.status_code}: "
            f"{response.text[:200]}"
        )


    except Exception as e:

        return False, str(e)


# =========================================================
# 현재 배당 가져오기
# =========================================================

def get_odds(
    api_key,
    sport_key
):

    url = (
        f"{BASE_URL}/sports/"
        f"{sport_key}/odds/"
    )


    params = {

        "apiKey": api_key,

        "regions": "us",

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

            return None


        return response.json()


    except:

        return None


# =========================================================
# 최근 경기 결과
# =========================================================

def get_scores(
    api_key,
    sport_key
):

    url = (
        f"{BASE_URL}/sports/"
        f"{sport_key}/scores/"
    )


    params = {

        "apiKey": api_key,

        "daysFrom": 3,

        "dateFormat": "iso"
    }


    try:

        response = requests.get(

            url,

            params=params,

            timeout=30
        )


        if response.status_code != 200:

            return None


        return response.json()


    except:

        return None


# =========================================================
# 실제 결과 계산
# =========================================================

def result_from_score(
    sport,
    home_score,
    away_score
):

    if home_score is None:
        return None

    if away_score is None:
        return None


    if home_score > away_score:

        return "승"

    elif home_score < away_score:

        return "패"

    else:

        if sport == "축구":

            return "무"

        return None


# =========================================================
# 결과 DB 저장
# =========================================================

def update_results(
    api_key,
    sports
):

    total = 0


    conn = db()

    cursor = conn.cursor()


    for sport_name, sport_key in sports.items():

        games = get_scores(
            api_key,
            sport_key
        )


        if not games:

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

            home = game.get(
                "home_team",
                ""
            )

            away = game.get(
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


            for item in scores:

                name = item.get(
                    "name",
                    ""
                )

                score = item.get(
                    "score"
                )


                try:

                    score = float(score)

                except:

                    continue


                if name == home:

                    home_score = score

                elif name == away:

                    away_score = score


            if (
                home_score is None
                or
                away_score is None
            ):

                continue


            result = result_from_score(

                sport_name,

                home_score,

                away_score
            )


            cursor.execute(
                """
                UPDATE historical_games

                SET

                    home_score=?,

                    away_score=?,

                    actual_result=?,

                    completed=1,

                    updated_at=?

                WHERE game_id=?
                """,

                (

                    home_score,

                    away_score,

                    result,

                    datetime.now()
                    .isoformat(),

                    game_id
                )
            )


            total += cursor.rowcount


    conn.commit()

    conn.close()


    return total


# =========================================================
# 배당 DB 저장
# =========================================================

def save_odds(
    sport_name,
    games
):

    if not games:

        return 0


    conn = db()

    cursor = conn.cursor()

    total = 0


    for game in games:

        game_id = game.get(
            "id"
        )

        home = game.get(
            "home_team",
            ""
        )

        away = game.get(
            "away_team",
            ""
        )

        game_date = game.get(
            "commence_time",
            ""
        )


        for bookmaker in game.get(
            "bookmakers",
            []
        ):

            bookmaker_name = bookmaker.get(
                "title",
                ""
            )


            for market in bookmaker.get(
                "markets",
                []
            ):

                if market.get(
                    "key"
                ) != "h2h":

                    continue


                home_odds = None

                draw_odds = None

                away_odds = None


                for outcome in market.get(
                    "outcomes",
                    []
                ):

                    name = outcome.get(
                        "name",
                        ""
                    )

                    price = outcome.get(
                        "price"
                    )


                    try:

                        price = float(price)

                    except:

                        continue


                    if name == home:

                        home_odds = price

                    elif name == away:

                        away_odds = price

                    elif name.lower() == "draw":

                        draw_odds = price


                if (
                    home_odds is None
                    or
                    away_odds is None
                ):

                    continue


                now = datetime.now().isoformat()


                cursor.execute(
                    """
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
                    """,

                    (

                        game_id,

                        sport_name,

                        sport_name,

                        game_date,

                        home,

                        away,

                        home_odds,

                        draw_odds,

                        away_odds,

                        bookmaker_name,

                        "The Odds API",

                        now,

                        now
                    )
                )


                if cursor.rowcount > 0:

                    total += 1


    conn.commit()

    conn.close()


    return total


# =========================================================
# 배당 확률
# =========================================================

def odds_probability(
    home,
    draw,
    away
):

    values = []

    values.append(
        1 / home
    )


    if draw:

        values.append(
            1 / draw
        )


    values.append(
        1 / away
    )


    total = sum(values)


    return [
        x / total * 100
        for x in values
    ]


# =========================================================
# 과거 DB 분석
# =========================================================

def historical_analysis(

    sport,
    home_odds,
    draw_odds,
    away_odds

):

    conn = db()


    df = pd.read_sql_query(

        """
        SELECT *
        FROM historical_games

        WHERE
            actual_result IS NOT NULL

        AND
            home_odds IS NOT NULL

        AND
            away_odds IS NOT NULL
        """,

        conn
    )


    conn.close()


    if df.empty:

        return None


    df = df[
        df["sport"] == sport
    ]


    if df.empty:

        return None


    condition = (

        abs(
            df["home_odds"]
            -
            home_odds
        )
        <=
        0.15

    ) & (

        abs(
            df["away_odds"]
            -
            away_odds
        )
        <=
        0.25
    )


    if draw_odds:

        condition &= (

            df["draw_odds"].notna()

        ) & (

            abs(
                df["draw_odds"]
                -
                draw_odds
            )
            <=
            0.35
        )


    matched = df[
        condition
    ]


    if matched.empty:

        return None


    total = len(matched)


    win = int(
        (
            matched[
                "actual_result"
            ]
            ==
            "승"
        ).sum()
    )


    draw = int(
        (
            matched[
                "actual_result"
            ]
            ==
            "무"
        ).sum()
    )


    lose = int(
        (
            matched[
                "actual_result"
            ]
            ==
            "패"
        ).sum()
    )


    return {

        "total": total,

        "승건수": win,

        "무건수": draw,

        "패건수": lose,

        "승": win / total * 100,

        "무": draw / total * 100,

        "패": lose / total * 100
    }


# =========================================================
# 화면
# =========================================================

st.title(
    "🏆 전종목 해외배당 분석"
)

st.caption(
    "배당 입력 → 과거 실제 경기 결과 → 확률 분석"
)


# =========================================================
# API 키 입력
# =========================================================

with st.sidebar:

    st.header(
        "⚙️ API 설정"
    )


    api_key = st.text_input(

        "The Odds API Key",

        type="password",

        placeholder="API 키 입력"
    )


    if st.button(
        "🔑 API 연결 테스트",
        use_container_width=True
    ):

        ok, message = test_api(
            api_key
        )


        if ok:

            st.success(
                "🟢 " + message
            )

        else:

            st.error(
                "🔴 " + message
            )


    st.info(
        "API 키는 화면에 입력해서 사용할 수 있습니다."
    )


# =========================================================
# 스포츠
# =========================================================

sports = {

    "⚽ 축구": "soccer_epl",

    "⚾ MLB": "baseball_mlb",

    "⚾ KBO": "baseball_kbo",

    "⚾ NPB": "baseball_npb",

    "🏀 NBA": "basketball_nba",

    "🏀 유로리그": "basketball_euroleague"
}


sport_select = st.radio(

    "종목",

    list(sports.keys()),

    horizontal=True
)


sport_key = sports[
    sport_select
]


if sport_select == "⚽ 축구":

    sport_type = "축구"

else:

    sport_type = "야구" if "⚾" in sport_select else "농구"


# =========================================================
# DB 업데이트
# =========================================================

st.subheader(
    "🗄️ 데이터 업데이트"
)


c1, c2 = st.columns(2)


with c1:

    if st.button(
        "📥 현재 배당 가져오기",
        use_container_width=True
    ):

        if not api_key:

            st.error(
                "먼저 API 키를 입력하세요."
            )

        else:

            games = get_odds(
                api_key,
                sport_key
            )


            if games:

                saved = save_odds(

                    sport_type,

                    games
                )


                st.success(
                    f"배당 {saved}건 저장 완료"
                )

            else:

                st.warning(
                    "배당 데이터를 가져오지 못했습니다."
                )


with c2:

    if st.button(
        "🏁 실제 경기결과 업데이트",
        use_container_width=True
    ):

        if not api_key:

            st.error(
                "먼저 API 키를 입력하세요."
            )

        else:

            updated = update_results(

                api_key,

                {
                    sport_type:
                    sport_key
                }
            )


            st.success(
                f"실제 결과 {updated}건 업데이트"
            )


# =========================================================
# DB 현황
# =========================================================

conn = db()


total_db = conn.execute(
    """
    SELECT COUNT(*)
    FROM historical_games
    """
).fetchone()[0]


completed_db = conn.execute(
    """
    SELECT COUNT(*)
    FROM historical_games
    WHERE actual_result IS NOT NULL
    """
).fetchone()[0]


conn.close()


st.info(
    f"현재 DB: "
    f"전체 {total_db:,}건 / "
    f"실제 결과 {completed_db:,}건"
)


# =========================================================
# 경기 입력
# =========================================================

st.divider()

st.subheader(
    "🏟️ 경기 입력"
)


c1, c2 = st.columns(2)


with c1:

    home_team = st.text_input(
        "홈팀",
        placeholder="홈팀 이름"
    )


with c2:

    away_team = st.text_input(
        "원정팀",
        placeholder="원정팀 이름"
    )


# =========================================================
# 배당 입력
# =========================================================

st.subheader(
    "💰 배당 입력"
)


if sport_type == "축구":

    c1, c2, c3 = st.columns(3)


    with c1:

        home_odds = st.number_input(
            "승 배당",
            min_value=1.01,
            value=1.70,
            step=0.01
        )


    with c2:

        draw_odds = st.number_input(
            "무 배당",
            min_value=1.01,
            value=3.60,
            step=0.01
        )


    with c3:

        away_odds = st.number_input(
            "패 배당",
            min_value=1.01,
            value=4.50,
            step=0.01
        )


else:

    c1, c2 = st.columns(2)


    with c1:

        home_odds = st.number_input(
            "홈 승 배당",
            min_value=1.01,
            value=1.70,
            step=0.01
        )


    with c2:

        away_odds = st.number_input(
            "원정 승 배당",
            min_value=1.01,
            value=2.10,
            step=0.01
        )


    draw_odds = None


# =========================================================
# 분석
# =========================================================

if st.button(
    "🔍 경기 분석",
    type="primary",
    use_container_width=True
):

    if not home_team or not away_team:

        st.warning(
            "홈팀과 원정팀을 입력하세요."
        )

        st.stop()


    probabilities = odds_probability(

        home_odds,

        draw_odds,

        away_odds
    )


    if sport_type == "축구":

        market_home = probabilities[0]

        market_draw = probabilities[1]

        market_away = probabilities[2]

    else:

        market_home = probabilities[0]

        market_draw = None

        market_away = probabilities[1]


    # -----------------------------------------
    # 배당 확률
    # -----------------------------------------

    st.divider()

    st.subheader(
        "📊 배당 기준 확률"
    )


    if sport_type == "축구":

        c1, c2, c3 = st.columns(3)


        with c1:

            st.metric(
                "승",
                f"{market_home:.1f}%"
            )


        with c2:

            st.metric(
                "무",
                f"{market_draw:.1f}%"
            )


        with c3:

            st.metric(
                "패",
                f"{market_away:.1f}%"
            )

    else:

        c1, c2 = st.columns(2)


        with c1:

            st.metric(
                "홈 승",
                f"{market_home:.1f}%"
            )


        with c2:

            st.metric(
                "원정 승",
                f"{market_away:.1f}%"
            )


    # -----------------------------------------
    # 과거 결과
    # -----------------------------------------

    history = historical_analysis(

        sport_type,

        home_odds,

        draw_odds,

        away_odds
    )


    st.subheader(
        "📚 과거 동일 배당 실제 결과"
    )


    if history:

        st.write(
            f"유사 경기 "
            f"**{history['total']}경기**"
        )


        if sport_type == "축구":

            c1, c2, c3 = st.columns(3)


            with c1:

                st.metric(
                    "승",
                    f"{history['승']:.1f}%",
                    f"{history['승건수']}경기"
                )


            with c2:

                st.metric(
                    "무",
                    f"{history['무']:.1f}%",
                    f"{history['무건수']}경기"
                )


            with c3:

                st.metric(
                    "패",
                    f"{history['패']:.1f}%",
                    f"{history['패건수']}경기"
                )


        else:

            c1, c2 = st.columns(2)


            with c1:

                st.metric(
                    "홈 승",
                    f"{history['승']:.1f}%",
                    f"{history['승건수']}경기"
                )


            with c2:

                st.metric(
                    "원정 승",
                    f"{history['패']:.1f}%",
                    f"{history['패건수']}경기"
                )


    else:

        st.warning(
            "현재 DB에 유사 배당의 "
            "실제 경기 결과가 없습니다."
        )


    # -----------------------------------------
    # 최종 예측
    # -----------------------------------------

    if history:

        final_home = (
            market_home * 0.5
            +
            history["승"] * 0.5
        )


        final_away = (
            market_away * 0.5
            +
            history["패"] * 0.5
        )


        if sport_type == "축구":

            final_draw = (
                market_draw * 0.5
                +
                history["무"] * 0.5
            )

        else:

            final_draw = None

    else:

        final_home = market_home

        final_away = market_away

        final_draw = market_draw


    if sport_type == "축구":

        total = (
            final_home
            +
            final_draw
            +
            final_away
        )


        final_home = (
            final_home
            /
            total
            *
            100
        )


        final_draw = (
            final_draw
            /
            total
            *
            100
        )


        final_away = (
            final_away
            /
            total
            *
            100
        )


        results = {

            "승": final_home,

            "무": final_draw,

            "패": final_away
        }


    else:

        total = (
            final_home
            +
            final_away
        )


        final_home = (
            final_home
            /
            total
            *
            100
        )


        final_away = (
            final_away
            /
            total
            *
            100
        )


        results = {

            "승": final_home,

            "패": final_away
        }


    prediction = max(
        results,
        key=results.get
    )


    # -----------------------------------------
    # 최종 표시
    # -----------------------------------------

    st.divider()

    st.subheader(
        "🎯 최종 예측"
    )


    if sport_type == "축구":

        c1, c2, c3 = st.columns(3)


        with c1:

            st.metric(
                "승",
                f"{final_home:.1f}%"
            )


        with c2:

            st.metric(
                "무",
                f"{final_draw:.1f}%"
            )


        with c3:

            st.metric(
                "패",
                f"{final_away:.1f}%"
            )


    else:

        c1, c2 = st.columns(2)


        with c1:

            st.metric(
                "홈 승",
                f"{final_home:.1f}%"
            )


        with c2:

            st.metric(
                "원정 승",
                f"{final_away:.1f}%"
            )


    st.success(
        f"🎯 최종 추천: **{prediction}**"
    )


    # -----------------------------------------
    # 예측 저장
    # -----------------------------------------

    conn = db()


    conn.execute(
        """
        INSERT INTO predictions
        (

            created_at,

            sport,

            league,

            home_team,

            away_team,

            home_odds,

            draw_odds,

            away_odds,

            predicted

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
            ?
        )
        """,

        (

            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            sport_type,

            sport_select,

            home_team,

            away_team,

            home_odds,

            draw_odds,

            away_odds,

            prediction
        )
    )


    conn.commit()

    conn.close()


    st.info(
        "예측 결과를 DB에 저장했습니다."
)
