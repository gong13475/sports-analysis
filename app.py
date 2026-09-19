import os
import sqlite3
from io import StringIO
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


# ============================================================
# 1. 기본 설정
# ============================================================

st.set_page_config(
    page_title="해외 배당 승무패 분석",
    page_icon="⚽",
    layout="centered"
)

APP_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_FILE = os.path.join(
    APP_DIR,
    "historical_odds.db"
)

BASE_URL = (
    "https://www.football-data.co.uk/mmz4281"
)


# ============================================================
# 2. 리그
# ============================================================

LEAGUES = {

    "잉글랜드 1부": {
        "code": "E0",
        "country": "England",
        "division": 1
    },

    "잉글랜드 2부": {
        "code": "E1",
        "country": "England",
        "division": 2
    },

    "잉글랜드 3부": {
        "code": "E2",
        "country": "England",
        "division": 3
    },

    "잉글랜드 4부": {
        "code": "E3",
        "country": "England",
        "division": 4
    },

    "독일 1부": {
        "code": "D1",
        "country": "Germany",
        "division": 1
    },

    "독일 2부": {
        "code": "D2",
        "country": "Germany",
        "division": 2
    },

    "이탈리아 1부": {
        "code": "I1",
        "country": "Italy",
        "division": 1
    },

    "이탈리아 2부": {
        "code": "I2",
        "country": "Italy",
        "division": 2
    },

    "스페인 1부": {
        "code": "SP1",
        "country": "Spain",
        "division": 1
    },

    "스페인 2부": {
        "code": "SP2",
        "country": "Spain",
        "division": 2
    },

    "프랑스 1부": {
        "code": "F1",
        "country": "France",
        "division": 1
    },

    "프랑스 2부": {
        "code": "F2",
        "country": "France",
        "division": 2
    },

    "네덜란드 1부": {
        "code": "N1",
        "country": "Netherlands",
        "division": 1
    },

    "벨기에 1부": {
        "code": "B1",
        "country": "Belgium",
        "division": 1
    },

    "포르투갈 1부": {
        "code": "P1",
        "country": "Portugal",
        "division": 1
    },

    "스코틀랜드 1부": {
        "code": "SC0",
        "country": "Scotland",
        "division": 1
    },

    "스코틀랜드 2부": {
        "code": "SC1",
        "country": "Scotland",
        "division": 2
    },

    "터키 1부": {
        "code": "T1",
        "country": "Turkey",
        "division": 1
    },

    "그리스 1부": {
        "code": "G1",
        "country": "Greece",
        "division": 1
    }
}


# ============================================================
# 3. 시즌
# ============================================================

SEASONS = {

    "2024/25": "2425",
    "2023/24": "2324",
    "2022/23": "2223",
    "2021/22": "2122",
    "2020/21": "2021",
    "2019/20": "1920",
    "2018/19": "1819",
    "2017/18": "1718",
    "2016/17": "1617",
    "2015/16": "1516"

}


# ============================================================
# 4. DB 생성
# ============================================================

def create_database():

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
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
        """
    )

    conn.commit()
    conn.close()


# 프로그램 시작 시 DB 생성
create_database()


# ============================================================
# 5. DB 경기수
# ============================================================

def get_database_count():

    try:

        conn = sqlite3.connect(DB_FILE)

        row = conn.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()

        conn.close()

        if row is None:
            return 0

        return int(row[0])

    except Exception:

        return 0


# ============================================================
# 6. DB 읽기
# ============================================================

def read_database():

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


# ============================================================
# 7. CSV 다운로드
# ============================================================

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
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                )
            }
        )

        if response.status_code != 200:

            return (
                None,
                "HTTP 오류: "
                + str(response.status_code),
                url
            )

        if len(response.content) < 500:

            return (
                None,
                "다운로드 파일이 비어 있거나 너무 작습니다.",
                url
            )

        response.encoding = "latin1"

        df = pd.read_csv(
            StringIO(response.text)
        )

        return (
            df,
            None,
            url
        )

    except Exception as error:

        return (
            None,
            str(error),
            url
        )


# ============================================================
# 8. 숫자 변환
# ============================================================

def to_number(value):

    try:

        if pd.isna(value):
            return None

        value = str(value).strip()

        if value == "":
            return None

        number = float(value)

        if number <= 1:
            return None

        return number

    except Exception:

        return None


# ============================================================
# 9. Bet365 컬럼 찾기
# ============================================================

def find_bet365_columns(df):

    # 마감배당
    if all(
        x in df.columns
        for x in [
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

    # 일반 Bet365 배당
    if all(
        x in df.columns
        for x in [
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


# ============================================================
# 10. 필수 컬럼 검사
# ============================================================

def check_required_columns(df):

    required = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTR"
    ]

    missing = []

    for column in required:

        if column not in df.columns:
            missing.append(column)

    return missing


# ============================================================
# 11. DB 저장
# ============================================================

def save_matches(
    df,
    league_name,
    season_name
):

    missing = check_required_columns(df)

    if len(missing) > 0:

        return (
            0,
            0,
            "필수 컬럼 없음: "
            + ", ".join(missing)
        )

    league_info = LEAGUES[
        league_name
    ]

    (
        home_col,
        draw_col,
        away_col,
        odds_type
    ) = find_bet365_columns(df)

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

            home_team = str(
                row["HomeTeam"]
            ).strip()

            away_team = str(
                row["AwayTeam"]
            ).strip()

            match_date = str(
                row["Date"]
            ).strip()

            if not home_team:
                continue

            if not away_team:
                continue

            # ------------------------------
            # 배당
            # ------------------------------

            if home_col is not None:

                home_odds = to_number(
                    row[home_col]
                )

                draw_odds = to_number(
                    row[draw_col]
                )

                away_odds = to_number(
                    row[away_col]
                )

            else:

                home_odds = None
                draw_odds = None
                away_odds = None

            # ------------------------------
            # 저장
            # ------------------------------

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

                VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?,
                    ?, ?, ?,
                    ?,
                    ?, ?
                )
                """,
                (
                    league_info["country"],
                    league_name,
                    league_info["division"],
                    season_name,

                    match_date,

                    home_team,
                    away_team,

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


# ============================================================
# 12. 데이터 수집
# ============================================================

def collect_data(
    selected_leagues,
    selected_seasons
):

    total_jobs = (
        len(selected_leagues)
        *
        len(selected_seasons)
    )

    current_job = 0

    total_inserted = 0
    total_processed = 0

    progress = st.progress(0)

    for league_name in selected_leagues:

        league_code = LEAGUES[
            league_name
        ]["code"]

        for season_name in selected_seasons:

            current_job += 1

            progress.progress(
                current_job / total_jobs
            )

            st.divider()

            st.write(
                "📥 "
                + league_name
                + " / "
                + season_name
            )

            # ------------------------------
            # URL
            # ------------------------------

            df, error, url = download_csv(
                SEASONS[season_name],
                league_code
            )

            st.write("요청 주소")

            st.code(url)

            # ------------------------------
            # 다운로드 실패
            # ------------------------------

            if error is not None:

                st.error(
                    "❌ CSV 다운로드 실패"
                )

                st.code(error)

                continue

            # ------------------------------
            # 다운로드 성공
            # ------------------------------

            if df is None:

                st.error(
                    "❌ CSV 데이터가 없습니다."
                )

                continue

            st.success(
                "✅ CSV 다운로드 성공"
            )

            st.write(
                "CSV 행 수:",
                len(df)
            )

            # ------------------------------
            # 컬럼 확인
            # ------------------------------

            with st.expander(
                "CSV 컬럼 확인"
            ):

                st.write(
                    list(df.columns)
                )

            # ------------------------------
            # 필수 컬럼
            # ------------------------------

            missing = check_required_columns(
                df
            )

            if len(missing) > 0:

                st.error(
                    "❌ 필수 컬럼이 없습니다."
                )

                st.write(
                    missing
                )

                continue

            st.success(
                "✅ 경기 결과 컬럼 확인"
            )

            # ------------------------------
            # Bet365 확인
            # ------------------------------

            (
                home_col,
                draw_col,
                away_col,
                odds_type
            ) = find_bet365_columns(df)

            if home_col is None:

                st.warning(
                    "⚠️ Bet365 배당 컬럼이 없습니다."
                )

                st.write(
                    "경기 결과는 저장할 수 있지만 "
                    "배당 분석에는 사용할 수 없습니다."
                )

            else:

                st.success(
                    "✅ Bet365 배당 컬럼 확인"
                )

                st.write(
                    "승:",
                    home_col
                )

                st.write(
                    "무:",
                    draw_col
                )

                st.write(
                    "패:",
                    away_col
                )

                st.write(
                    "종류:",
                    odds_type
                )

            # ------------------------------
            # DB 저장
            # ------------------------------

            (
                inserted,
                processed,
                save_result
            ) = save_matches(
                df,
                league_name,
                season_name
            )

            total_inserted += inserted
            total_processed += processed

            st.write(
                "처리 경기:",
                processed
            )

            st.write(
                "신규 저장:",
                inserted
            )

            st.write(
                "저장 상태:",
                save_result
            )

            # ------------------------------
            # 실제 DB 확인
            # ------------------------------

            current_count = (
                get_database_count()
            )

            st.metric(
                "현재 historical_odds.db",
                f"{current_count:,} 경기"
            )

    progress.progress(1.0)

    st.divider()

    final_count = get_database_count()

    st.success(
        "🎉 데이터 수집 완료"
    )

    st.write(
        "총 처리:",
        total_processed
    )

    st.write(
        "총 신규 저장:",
        total_inserted
    )

    st.write(
        "최종 DB 경기:",
        final_count
    )

    return (
        total_inserted,
        total_processed
    )


# ============================================================
# 13. 배당 분석
# ============================================================

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

    # 리그 선택
    if selected_league != "전체":

        df = df[
            df["league"]
            ==
            selected_league
        ]

    if df.empty:
        return None

    required_odds = [
        "bet365_home",
        "bet365_draw",
        "bet365_away"
    ]

    for column in required_odds:

        if column not in df.columns:
            return None

    # 배당 없는 경기 제거
    df = df.dropna(
        subset=required_odds
    ).copy()

    if df.empty:
        return None

    # ------------------------------
    # 배당 차이
    # ------------------------------

    df["승차이"] = abs(
        df["bet365_home"]
        -
        home_odds
    )

    df["무차이"] = abs(
        df["bet365_draw"]
        -
        draw_odds
    )

    df["패차이"] = abs(
        df["bet365_away"]
        -
        away_odds
    )

    # ------------------------------
    # 유사배당
    # ------------------------------

    similar = df[
        (df["승차이"] <= tolerance)
        &
        (df["무차이"] <= tolerance)
        &
        (df["패차이"] <= tolerance)
    ].copy()

    if similar.empty:
        return None

    # 전체 차이
    similar["총차이"] = (
        similar["승차이"]
        +
        similar["무차이"]
        +
        similar["패차이"]
    )

    similar = similar.sort_values(
        "총차이"
    )

    total = len(similar)

    win_count = int(
        (
            similar["result"]
            ==
            "H"
        ).sum()
    )

    draw_count = int(
        (
            similar["result"]
            ==
            "D"
        ).sum()
    )

    loss_count = int(
        (
            similar["result"]
            ==
            "A"
        ).sum()
    )

    return {

        "data": similar,

        "total": total,

        "win_count": win_count,

        "draw_count": draw_count,

        "loss_count": loss_count,

        "win_pct":
            win_count
            /
            total
            *
            100,

        "draw_pct":
            draw_count
            /
            total
            *
            100,

        "loss_pct":
            loss_count
            /
            total
            *
            100
    }


# ============================================================
# 14. 제목
# ============================================================

st.title(
    "⚽ 해외 배당 승무패 분석"
)

st.caption(
    "과거 Bet365 배당 + 경기 결과 기반"
)


# ============================================================
# 15. DB 상태
# ============================================================

st.subheader(
    "🗄️ DB 상태"
)

st.write(
    "사용 중인 DB 위치:"
)

st.code(DB_FILE)

if os.path.exists(DB_FILE):

    file_size = os.path.getsize(
        DB_FILE
    )

    st.success(
        "DB 파일 존재 / "
        + f"{file_size:,} bytes"
    )

else:

    st.warning(
        "DB 파일이 없습니다."
    )


database_count = get_database_count()

st.metric(
    "현재 DB 경기수",
    f"{database_count:,} 경기"
)


# ============================================================
# 16. DB 초기화
# ============================================================

st.subheader(
    "🧹 DB 관리"
)

if st.button(
    "⚠️ 기존 DB 초기화",
    use_container_width=True
):

    try:

        if os.path.exists(DB_FILE):

            os.remove(DB_FILE)

        create_database()

        st.success(
            "DB 초기화 완료"
        )

        st.rerun()

    except Exception as error:

        st.error(
            "DB 초기화 실패"
        )

        st.code(
            str(error)
        )


# ============================================================
# 17. 데이터 수집 설정
# ============================================================

st.divider()

st.subheader(
    "📥 과거 데이터 수집"
)

st.info(
    "처음에는 잉글랜드 1부 + 2024/25 "
    "한 개만 테스트하세요."
)


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


# ============================================================
# 18. 데이터 수집 버튼
# ============================================================

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

        collect_data(
            selected_leagues,
            selected_seasons
        )


# ============================================================
# 19. 현재 경기
# ============================================================

st.divider()

st.subheader(
    "🎯 현재 경기 분석"
)

home_team = st.text_input(
    "홈팀",
    placeholder="예: Liverpool"
)

away_team = st.text_input(
    "원정팀",
    placeholder="예: Chelsea"
)


selected_analysis_league = st.selectbox(
    "분석 리그",
    ["전체"]
    +
    list(LEAGUES.keys())
)


# ============================================================
# 20. 배당 입력
# ============================================================

st.subheader(
    "💰 현재 승무패 배당"
)

col1, col2, col3 = st.columns(3)


with col1:

    current_home_odds = (
        st.number_input(
            "승",
            min_value=1.01,
            max_value=100.0,
            value=1.85,
            step=0.01
        )
    )


with col2:

    current_draw_odds = (
        st.number_input(
            "무",
            min_value=1.01,
            max_value=100.0,
            value=3.60,
            step=0.01
        )
    )


with col3:

    current_away_odds = (
        st.number_input(
            "패",
            min_value=1.01,
            max_value=100.0,
            value=4.20,
            step=0.01
        )
    )


# ============================================================
# 21. 유사배당 범위
# ============================================================

tolerance = st.select_slider(
    "🔎 유사배당 허용범위",
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


st.caption(
    "예: 0.20이면 각 배당 ±0.20 범위의 "
    "과거 경기를 검색합니다."
)


# ============================================================
# 22. 분석
# ============================================================

if st.button(
    "🔍 승무패 분석하기",
    type="primary",
    use_container_width=True
):

    database = read_database()

    if database.empty:

        st.error(
            "❌ historical_odds.db가 비어 있습니다."
        )

        st.info(
            "먼저 위의 "
            "'🚀 데이터 수집 시작'을 눌러주세요."
        )

    else:

        analysis = analyze_odds(
            database,

            current_home_odds,

            current_draw_odds,

            current_away_odds,

            tolerance,

            selected_analysis_league
        )

        if analysis is None:

            st.warning(
                "⚠️ 현재 배당과 비슷한 "
                "과거 경기가 없습니다."
            )

            st.info(
                "유사배당 범위를 "
                "0.30~0.50으로 높여보세요."
            )

        else:

            win_pct = analysis[
                "win_pct"
            ]

            draw_pct = analysis[
                "draw_pct"
            ]

            loss_pct = analysis[
                "loss_pct"
            ]

            st.divider()

            st.subheader(
                "📊 분석 결과"
            )

            a, b, c = st.columns(3)


            with a:

                st.metric(
                    "🟢 승",
                    f"{win_pct:.2f}%"
                )


            with b:

                st.metric(
                    "🔵 무",
                    f"{draw_pct:.2f}%"
                )


            with c:

                st.metric(
                    "🔴 패",
                    f"{loss_pct:.2f}%"
                )


            probabilities = {

                "승": win_pct,

                "무": draw_pct,

                "패": loss_pct

            }


            best = max(
                probabilities,
                key=probabilities.get
            )


            st.success(
                "🏆 과거 최다 결과: "
                + best
                + " / "
                + f"{probabilities[best]:.2f}%"
            )


            st.write(
                "유사 경기 수:",
                analysis["total"]
            )


            # ------------------------------
            # 결과표
            # ------------------------------

            result_table = pd.DataFrame({

                "결과": [
                    "승",
                    "무",
                    "패"
                ],

                "경기수": [

                    analysis["win_count"],

                    analysis["draw_count"],

                    analysis["loss_count"]

                ],

                "확률": [

                    f"{win_pct:.2f}%",

                    f"{draw_pct:.2f}%",

                    f"{loss_pct:.2f}%"

                ]

            })


            st.dataframe(
                result_table,
                use_container_width=True,
                hide_index=True
            )


            # ------------------------------
            # 유사 경기
            # ------------------------------

            st.subheader(
                "📋 유사배당 경기"
            )


            display = analysis[
                "data"
            ][
                [
                    "season",
                    "league",
                    "match_date",
                    "home_team",
                    "away_team",
                    "bet365_home",
                    "bet365_draw",
                    "bet365_away",
                    "result"
                ]
            ].head(100).copy()


            display.columns = [

                "시즌",
                "리그",
                "날짜",
                "홈팀",
                "원정팀",
                "승배당",
                "무배당",
                "패배당",
                "결과"

            ]


            display["결과"] = (
                display["결과"]
                .replace(
                    {
                        "H": "승",
                        "D": "무",
                        "A": "패"
                    }
                )
            )


            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# 23. DB 데이터 확인
# ============================================================

st.divider()

st.subheader(
    "📋 DB 저장 데이터 확인"
)

database = read_database()


if database.empty:

    st.warning(
        "현재 DB에는 저장된 경기가 없습니다."
    )

else:

    st.success(
        "총 "
        + f"{len(database):,}"
        + " 경기 저장됨"
    )

    # 리그별 통계

    league_summary = (
        database
        .groupby("league")
        .size()
        .reset_index(
            name="경기수"
        )
        .sort_values(
            "경기수",
            ascending=False
        )
    )


    st.write(
        "리그별 경기수"
    )


    st.dataframe(
        league_summary,
        use_container_width=True,
        hide_index=True
    )


    # 최근 데이터

    st.write(
        "최근 저장 데이터"
    )


    recent = database.tail(
        100
    ).copy()


    recent["result"] = (
        recent["result"]
        .replace(
            {
                "H": "승",
                "D": "무",
                "A": "패"
            }
        )
    )


    recent_columns = [

        "season",
        "league",
        "match_date",
        "home_team",
        "away_team",
        "bet365_home",
        "bet365_draw",
        "bet365_away",
        "result"

    ]


    recent_columns = [
        x
        for x in recent_columns
        if x in recent.columns
    ]


    st.dataframe(
        recent[recent_columns],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 24. CSV 다운로드
# ============================================================

st.divider()

st.subheader(
    "📥 DB 다운로드"
)


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
        "DB에 데이터가 저장되면 "
        "CSV 다운로드가 가능합니다."
    )


# ============================================================
# 25. 안내
# ============================================================

st.divider()

st.caption(
    "데이터 출처: Football-Data.co.uk"
)

st.caption(
    "Bet365 마감배당 컬럼이 존재하면 "
    "마감배당을 우선 사용합니다."
)

st.caption(
    "마감배당이 없으면 일반 Bet365 배당을 사용합니다."
)

st.caption(
    "과거 통계는 미래 경기 결과를 보장하지 않습니다."
)
