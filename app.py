import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os


# =========================================================
# 기본 설정
# =========================================================

DB_FILE = "historical_odds.db"

st.set_page_config(
    page_title="전종목 승무패 분석",
    page_icon="🏆",
    layout="wide"
)


# =========================================================
# DB 초기화
# =========================================================

def init_database():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    # 역사적 경기 데이터
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

    # 사용자 예측 기록
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

            market_home_prob REAL,

            market_draw_prob REAL,

            market_away_prob REAL,

            historical_home_prob REAL,

            historical_draw_prob REAL,

            historical_away_prob REAL,

            final_home_prob REAL,

            final_draw_prob REAL,

            final_away_prob REAL,

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

def get_connection():

    return sqlite3.connect(DB_FILE)


# =========================================================
# 배당 → 확률
# =========================================================

def calculate_market_probability(
    home_odds,
    draw_odds,
    away_odds
):

    values = []

    if home_odds and home_odds > 1:

        values.append(
            1 / home_odds
        )

    else:

        values.append(0)


    if draw_odds is not None:

        if draw_odds > 1:

            values.append(
                1 / draw_odds
            )

        else:

            values.append(0)


    if away_odds and away_odds > 1:

        values.append(
            1 / away_odds
        )

    else:

        values.append(0)


    total = sum(values)


    if total <= 0:

        return []


    return [
        value / total * 100
        for value in values
    ]


# =========================================================
# 과거 배당구간 실제 결과 검색
# =========================================================

def get_historical_statistics(
    sport,
    home_odds,
    draw_odds,
    away_odds
):

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            *
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


    # 종목 필터
    df = df[
        df["sport"] == sport
    ]


    if df.empty:

        return None


    # -----------------------------------------
    # 홈/원정 배당 범위
    # -----------------------------------------

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


    # -----------------------------------------
    # 축구 무 배당
    # -----------------------------------------

    if draw_odds is not None:

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
    ].copy()


    if matched.empty:

        return None


    total = len(
        matched
    )


    result_counts = (
        matched[
            "actual_result"
        ]
        .value_counts()
    )


    home_count = int(
        result_counts.get(
            "승",
            0
        )
    )


    draw_count = int(
        result_counts.get(
            "무",
            0
        )
    )


    away_count = int(
        result_counts.get(
            "패",
            0
        )
    )


    return {

        "total":
            total,

        "승_건수":
            home_count,

        "무_건수":
            draw_count,

        "패_건수":
            away_count,

        "승":
            home_count
            /
            total
            *
            100,

        "무":
            draw_count
            /
            total
            *
            100,

        "패":
            away_count
            /
            total
            *
            100
    }


# =========================================================
# 예측 저장
# =========================================================

def save_prediction(
    sport,
    league,
    home_team,
    away_team,
    home_odds,
    draw_odds,
    away_odds,
    market_probs,
    historical,
    final_probs,
    predicted
):

    market_home = (
        market_probs[0]
        if len(market_probs) > 0
        else None
    )

    market_draw = (
        market_probs[1]
        if len(market_probs) == 3
        else None
    )

    market_away = (
        market_probs[2]
        if len(market_probs) == 3
        else market_probs[1]
    )


    historical_home = (
        historical["승"]
        if historical
        else None
    )

    historical_draw = (
        historical["무"]
        if historical
        else None
    )

    historical_away = (
        historical["패"]
        if historical
        else None
    )


    final_home = final_probs.get(
        "승"
    )

    final_draw = final_probs.get(
        "무"
    )

    final_away = final_probs.get(
        "패"
    )


    conn = get_connection()

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

            market_home_prob,

            market_draw_prob,

            market_away_prob,

            historical_home_prob,

            historical_draw_prob,

            historical_away_prob,

            final_home_prob,

            final_draw_prob,

            final_away_prob,

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

            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            sport,

            league,

            home_team,

            away_team,

            home_odds,

            draw_odds,

            away_odds,

            market_home,

            market_draw,

            market_away,

            historical_home,

            historical_draw,

            historical_away,

            final_home,

            final_draw,

            final_away,

            predicted
        )
    )

    conn.commit()

    conn.close()


# =========================================================
# 종목 선택
# =========================================================

st.title(
    "🏆 전종목 스포츠 배당 분석"
)

st.caption(
    "배당 입력 → 과거 실제 경기 결과 → 확률 분석 → 최종 예측"
)


sport = st.radio(
    "종목 선택",
    [
        "⚽ 축구",
        "⚾ 야구",
        "🏀 농구",
        "🏐 배구"
    ],
    horizontal=True
)


if sport == "⚽ 축구":

    sport_name = "EPL"

    sport_title = "축구"

    is_soccer = True

elif sport == "⚾ 야구":

    sport_name = "MLB"

    sport_title = "야구"

    is_soccer = False

elif sport == "🏀 농구":

    sport_name = "NBA"

    sport_title = "농구"

    is_soccer = False

else:

    sport_name = "VOLLEYBALL"

    sport_title = "배구"

    is_soccer = False


# =========================================================
# 경기 입력
# =========================================================

st.subheader(
    "🏟️ 경기 정보"
)


c1, c2 = st.columns(2)


with c1:

    home_team = st.text_input(
        "홈팀",
        placeholder="예: LA다저스"
    )


with c2:

    away_team = st.text_input(
        "원정팀",
        placeholder="예: 샌디에이고"
    )


league = st.text_input(
    "리그",
    value=sport_name,
    placeholder="예: MLB / EPL / NBA"
)


# =========================================================
# 배당 입력
# =========================================================

st.subheader(
    "💰 배당 입력"
)


if is_soccer:

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
            "홈팀 승 배당",
            min_value=1.01,
            value=1.70,
            step=0.01
        )


    with c2:

        away_odds = st.number_input(
            "원정팀 승 배당",
            min_value=1.01,
            value=2.10,
            step=0.01
        )


    draw_odds = None


# =========================================================
# 분석 버튼
# =========================================================

analyze = st.button(
    "🔍 분석하기",
    type="primary",
    use_container_width=True
)


if analyze:

    if not home_team or not away_team:

        st.warning(
            "홈팀과 원정팀을 입력하세요."
        )

        st.stop()


    # -----------------------------------------
    # 배당 확률
    # -----------------------------------------

    market_probs = (
        calculate_market_probability(
            home_odds,
            draw_odds,
            away_odds
        )
    )


    if is_soccer:

        market_home = market_probs[0]

        market_draw = market_probs[1]

        market_away = market_probs[2]

    else:

        market_home = market_probs[0]

        market_draw = None

        market_away = market_probs[1]


    # -----------------------------------------
    # 과거 실제 결과
    # -----------------------------------------

    historical = (
        get_historical_statistics(
            sport_name,
            home_odds,
            draw_odds,
            away_odds
        )
    )


    st.divider()

    st.subheader(
        "📊 배당 기반 확률"
    )


    if is_soccer:

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
                "홈팀 승",
                f"{market_home:.1f}%"
            )


        with c2:

            st.metric(
                "원정팀 승",
                f"{market_away:.1f}%"
            )


    # -----------------------------------------
    # 과거 결과
    # -----------------------------------------

    st.subheader(
        "📚 과거 동일 배당구간 실제 결과"
    )


    if historical:

        st.info(
            f"유사 배당 경기 "
            f"**{historical['total']}경기**"
        )


        if is_soccer:

            c1, c2, c3 = st.columns(3)


            with c1:

                st.metric(
                    "승",
                    f"{historical['승']:.1f}%",
                    f"{historical['승_건수']}경기"
                )


            with c2:

                st.metric(
                    "무",
                    f"{historical['무']:.1f}%",
                    f"{historical['무_건수']}경기"
                )


            with c3:

                st.metric(
                    "패",
                    f"{historical['패']:.1f}%",
                    f"{historical['패_건수']}경기"
                )


        else:

            c1, c2 = st.columns(2)


            with c1:

                st.metric(
                    "홈팀 승",
                    f"{historical['승']:.1f}%",
                    f"{historical['승_건수']}경기"
                )


            with c2:

                st.metric(
                    "원정팀 승",
                    f"{historical['패']:.1f}%",
                    f"{historical['패_건수']}경기"
                )


    else:

        st.warning(
            "현재 DB에 해당 배당구간의 "
            "실제 경기 결과가 없습니다."
        )


    # -----------------------------------------
    # 최종 확률
    # -----------------------------------------

    if historical:

        final_home = (
            market_home * 0.5
            +
            historical["승"] * 0.5
        )


        final_away = (
            market_away * 0.5
            +
            historical["패"] * 0.5
        )


        if is_soccer:

            final_draw = (
                market_draw * 0.5
                +
                historical["무"] * 0.5
            )

        else:

            final_draw = None


    else:

        final_home = market_home

        final_away = market_away

        final_draw = market_draw


    # -----------------------------------------
    # 최종 확률 정규화
    # -----------------------------------------

    if is_soccer:

        total_final = (
            final_home
            +
            final_draw
            +
            final_away
        )


        if total_final > 0:

            final_home = (
                final_home
                /
                total_final
                *
                100
            )

            final_draw = (
                final_draw
                /
                total_final
                *
                100
            )

            final_away = (
                final_away
                /
                total_final
                *
                100
            )


    else:

        total_final = (
            final_home
            +
            final_away
        )


        if total_final > 0:

            final_home = (
                final_home
                /
                total_final
                *
                100
            )

            final_away = (
                final_away
                /
                total_final
                *
                100
            )


    # -----------------------------------------
    # 추천
    # -----------------------------------------

    final_probs = {

        "승":
            final_home,

        "패":
            final_away
    }


    if is_soccer:

        final_probs["무"] = (
            final_draw
        )


    predicted = max(
        final_probs,
        key=final_probs.get
    )


    # -----------------------------------------
    # 최종 결과
    # -----------------------------------------

    st.divider()

    st.subheader(
        "🎯 최종 예측"
    )


    if is_soccer:

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
                "홈팀 승",
                f"{final_home:.1f}%"
            )


        with c2:

            st.metric(
                "원정팀 승",
                f"{final_away:.1f}%"
            )


    st.success(
        f"### {home_team} vs {away_team}\n\n"
        f"## 🎯 최종 추천: {predicted}"
    )


    # -----------------------------------------
    # 저장
    # -----------------------------------------

    save_prediction(

        sport_name,

        league,

        home_team,

        away_team,

        home_odds,

        draw_odds,

        away_odds,

        market_probs,

        historical,

        final_probs,

        predicted
    )


    st.info(
        "예측 결과가 DB에 저장되었습니다."
    )


# =========================================================
# 경기 종료 후 실제 결과 입력
# =========================================================

st.divider()

st.subheader(
    "✅ 경기 종료 후 실제 결과"
)


conn = get_connection()


pending = pd.read_sql_query(
    """
    SELECT *
    FROM predictions

    WHERE actual_result IS NULL

    ORDER BY id DESC

    LIMIT 30
    """,
    conn
)


conn.close()


if not pending.empty:

    for _, row in pending.iterrows():

        prediction_id = int(
            row["id"]
        )


        with st.container(
            border=True
        ):

            st.write(
                f"**#{prediction_id} "
                f"{row['sport']} | "
                f"{row['home_team']} "
                f"vs "
                f"{row['away_team']}**"
            )


            if row["sport"] in [
                "EPL",
                "LALIGA",
                "BUNDESLIGA",
                "SERIEA",
                "LIGUE1",
                "EREDIVISIE",
                "KLEAGUE1"
            ]:

                actual = st.selectbox(
                    "실제 결과",
                    [
                        "승",
                        "무",
                        "패"
                    ],
                    key=f"actual_{prediction_id}"
                )

            else:

                actual = st.selectbox(
                    "실제 결과",
                    [
                        "승",
                        "패"
                    ],
                    key=f"actual_{prediction_id}"
                )


            if st.button(
                "실제 결과 저장",
                key=f"save_actual_{prediction_id}"
            ):

                correct = (
                    1
                    if row["predicted"]
                    == actual
                    else 0
                )


                conn = get_connection()


                conn.execute(
                    """
                    UPDATE predictions

                    SET
                        actual_result=?,
                        correct=?

                    WHERE id=?
                    """,
                    (
                        actual,
                        correct,
                        prediction_id
                    )
                )


                conn.commit()

                conn.close()


                st.success(
                    "실제 결과가 저장되었습니다."
                )


                st.rerun()


else:

    st.info(
        "결과 입력을 기다리는 예측 경기가 없습니다."
    )


# =========================================================
# 누적 적중률
# =========================================================

st.divider()

st.subheader(
    "📈 누적 예측 성적"
)


conn = get_connection()


results = pd.read_sql_query(
    """
    SELECT *
    FROM predictions

    WHERE actual_result IS NOT NULL
    """,
    conn
)


conn.close()


if not results.empty:

    total = len(
        results
    )


    correct = int(
        results["correct"]
        .sum()
    )


    accuracy = (
        correct
        /
        total
        *
        100
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        st.metric(
            "결과 경기",
            f"{total}경기"
        )


    with c2:

        st.metric(
            "적중",
            f"{correct}경기"
        )


    with c3:

        st.metric(
            "전체 적중률",
            f"{accuracy:.1f}%"
        )


    # -----------------------------------------
    # 종목별
    # -----------------------------------------

    st.subheader(
        "종목별 적중률"
    )


    stats = (
        results
        .groupby("sport")
        .agg(
            경기수=(
                "correct",
                "count"
            ),

            적중=(
                "correct",
                "sum"
            )
        )
        .reset_index()
    )


    stats["적중률"] = (
        stats["적중"]
        /
        stats["경기수"]
        *
        100
    ).round(1)


    st.dataframe(
        stats,
        use_container_width=True,
        hide_index=True
    )


    # -----------------------------------------
    # 최근 경기
    # -----------------------------------------

    st.subheader(
        "최근 예측 결과"
    )


    display_df = results[
        [
            "created_at",
            "sport",
            "home_team",
            "away_team",
            "predicted",
            "actual_result",
            "correct"
        ]
    ].copy()


    display_df[
        "correct"
    ] = display_df[
        "correct"
    ].map(
        {
            1: "⭕ 적중",
            0: "❌ 미적중"
        }
    )


    display_df.columns = [
        "분석시간",
        "종목",
        "홈팀",
        "원정팀",
        "예측",
        "실제결과",
        "결과"
    ]


    st.dataframe(
        display_df.head(50),
        use_container_width=True,
        hide_index=True
    )


else:

    st.info(
        "경기가 종료되고 실제 결과를 입력하면 "
        "적중률이 표시됩니다."
    )


# =========================================================
# DB 상태
# =========================================================

st.divider()

with st.expander(
    "🗄️ 현재 DB 상태"
):

    conn = get_connection()

    try:

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM historical_games
            """
        ).fetchone()[0]


        completed = conn.execute(
            """
            SELECT COUNT(*)
            FROM historical_games

            WHERE actual_result IS NOT NULL
            """
        ).fetchone()[0]


        st.write(
            f"전체 과거 배당 데이터: "
            f"**{count:,}건**"
        )


        st.write(
            f"실제 결과가 연결된 경기: "
            f"**{completed:,}건**"
        )


    except Exception as e:

        st.error(
            f"DB 확인 오류: {e}"
        )


    finally:

        conn.close()
