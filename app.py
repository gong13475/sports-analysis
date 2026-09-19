import os
import sqlite3
from io import StringIO
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="해외배당 승무패 분석",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_FILE = os.path.join(
    BASE_DIR,
    "historical_odds.db"
)

BASE_URL = (
    "https://www.football-data.co.uk/mmz4281"
)


# =========================================================
# 시즌
#
# 2020/21 ~ 2026/27
#
# 중요:
# 2020/21 = 2021
# 2021/22 = 2122
# =========================================================

SEASONS = {
    "2026/27": "2627",
    "2025/26": "2526",
    "2024/25": "2425",
    "2023/24": "2324",
    "2022/23": "2223",
    "2021/22": "2122",
    "2020/21": "2021"
}


# =========================================================
# 리그 목록
# =========================================================

LEAGUES = {

    # England
    "잉글랜드 1부": ("E0", "England", 1),
    "잉글랜드 2부": ("E1", "England", 2),
    "잉글랜드 3부": ("E2", "England", 3),
    "잉글랜드 4부": ("E3", "England", 4),
    "잉글랜드 5부": ("EC", "England", 5),

    # Scotland
    "스코틀랜드 1부": ("SC0", "Scotland", 1),
    "스코틀랜드 2부": ("SC1", "Scotland", 2),
    "스코틀랜드 3부": ("SC2", "Scotland", 3),
    "스코틀랜드 4부": ("SC3", "Scotland", 4),

    # Germany
    "독일 1부": ("D1", "Germany", 1),
    "독일 2부": ("D2", "Germany", 2),

    # Italy
    "이탈리아 1부": ("I1", "Italy", 1),
    "이탈리아 2부": ("I2", "Italy", 2),

    # Spain
    "스페인 1부": ("SP1", "Spain", 1),
    "스페인 2부": ("SP2", "Spain", 2),

    # France
    "프랑스 1부": ("F1", "France", 1),
    "프랑스 2부": ("F2", "France", 2),

    # Netherlands
    "네덜란드 1부": ("N1", "Netherlands", 1),

    # Belgium
    "벨기에 1부": ("B1", "Belgium", 1),

    # Portugal
    "포르투갈 1부": ("P1", "Portugal", 1),

    # Turkey
    "터키 1부": ("T1", "Turkey", 1),

    # Greece
    "그리스 1부": ("G1", "Greece", 1),

    # Worldwide additional leagues
    "아르헨티나 1부": ("ARG", "Argentina", 1),
    "오스트리아 1부": ("AUT", "Austria", 1),
    "브라질 1부": ("BRA", "Brazil", 1),
    "중국 1부": ("CHN", "China", 1),
    "덴마크 1부": ("DNK", "Denmark", 1),
    "핀란드 1부": ("FIN", "Finland", 1),
    "아일랜드 1부": ("IRL", "Ireland", 1),
    "일본 1부": ("JPN", "Japan", 1),
    "멕시코 1부": ("MEX", "Mexico", 1),
    "노르웨이 1부": ("NOR", "Norway", 1),
    "폴란드 1부": ("POL", "Poland", 1),
    "루마니아 1부": ("ROU", "Romania", 1),
    "러시아 1부": ("RUS", "Russia", 1),
    "스웨덴 1부": ("SWE", "Sweden", 1),
    "스위스 1부": ("SWZ", "Switzerland", 1),
    "미국 MLS": ("USA", "USA", 1)
}


# =========================================================
# 배당 사이트
#
# Closing Odds를 먼저 사용
# 없으면 일반 Odds 사용
# =========================================================

BOOKMAKERS = {

    "Bet365": {
        "normal": ("B365H", "B365D", "B365A"),
        "closing": ("B365CH", "B365CD", "B365CA")
    },

    "William Hill": {
        "normal": ("WHH", "WHD", "WHA"),
        "closing": ("WHCH", "WHCD", "WHCA")
    },

    "Bet&Win": {
        "normal": ("BWH", "BWD", "BWA"),
        "closing": ("BWCH", "BWCD", "BWCA")
    },

    "Ladbrokes": {
        "normal": ("LBH", "LBD", "LBA"),
        "closing": ("LBCH", "LBCD", "LBCA")
    },

    "Gamebookers": {
        "normal": ("GBH", "GBD", "GBA"),
        "closing": ("GBCH", "GBCD", "GBCA")
    },

    "Interwetten": {
        "normal": ("IWH", "IWD", "IWA"),
        "closing": ("IWCH", "IWCD", "IWCA")
    },

    "VC Bet": {
        "normal": ("VCH", "VCD", "VCA"),
        "closing": ("VCCH", "VCCD", "VCCA")
    },

    "Stan James": {
        "normal": ("SJH", "SJD", "SJA"),
        "closing": ("SJCH", "SJCD", "SJCA")
    },

    "Pinnacle": {
        "normal": ("PSH", "PSD", "PSA"),
        "closing": ("PSCH", "PSCD", "PSCA")
    },

    "Betfair": {
        "normal": ("BFH", "BFD", "BFA"),
        "closing": ("BFCH", "BFCD", "BFCA")
    }
}


# =========================================================
# DB 생성
# =========================================================

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS odds (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            match_id INTEGER,

            bookmaker TEXT,

            odds_type TEXT,

            home_odds REAL,
            draw_odds REAL,
            away_odds REAL,

            UNIQUE(
                match_id,
                bookmaker,
                odds_type
            )
        )
    """)

    conn.commit()
    conn.close()


create_database()


# =========================================================
# 숫자 변환
# =========================================================

def safe_float(value):

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


# =========================================================
# CSV 다운로드
# =========================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False
)
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
            timeout=25,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        if response.status_code != 200:
            return None

        if len(response.content) < 200:
            return None

        response.encoding = "latin1"

        text = response.text

        if "HomeTeam" not in text:
            return None

        return pd.read_csv(
            StringIO(text)
        )

    except Exception:
        return None


# =========================================================
# 컬럼 존재 여부
# =========================================================

def columns_exist(
    df,
    columns
):

    return all(
        col in df.columns
        for col in columns
    )


# =========================================================
# 사이트 검색
# =========================================================

def detect_bookmakers(df):

    found = {}

    for name, config in BOOKMAKERS.items():

        closing = config["closing"]
        normal = config["normal"]

        if columns_exist(
            df,
            closing
        ):

            found[name] = {
                "home": closing[0],
                "draw": closing[1],
                "away": closing[2],
                "type": "마감"
            }

        elif columns_exist(
            df,
            normal
        ):

            found[name] = {
                "home": normal[0],
                "draw": normal[1],
                "away": normal[2],
                "type": "일반"
            }

    return found


# =========================================================
# 데이터 저장
# =========================================================

def save_dataframe(
    df,
    league_name,
    season_name
):

    required = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTR"
    ]

    if not columns_exist(
        df,
        required
    ):
        return 0, set()

    country = LEAGUES[
        league_name
    ][1]

    division = LEAGUES[
        league_name
    ][2]

    bookmakers = detect_bookmakers(
        df
    )

    conn = sqlite3.connect(
        DB_FILE
    )

    match_count = 0

    site_names = set()

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

            if (
                home == ""
                or away == ""
                or match_date == ""
            ):
                continue

            conn.execute("""
                INSERT OR IGNORE INTO matches (

                    country,
                    league,
                    division,
                    season,
                    match_date,
                    home_team,
                    away_team,
                    result,
                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                country,
                league_name,
                division,
                season_name,
                match_date,
                home,
                away,
                result,
                datetime.now().isoformat()
            ))

            match = conn.execute("""
                SELECT id
                FROM matches

                WHERE league = ?
                AND season = ?
                AND match_date = ?
                AND home_team = ?
                AND away_team = ?
            """, (
                league_name,
                season_name,
                match_date,
                home,
                away
            )).fetchone()

            if match is None:
                continue

            match_id = match[0]

            for site, config in bookmakers.items():

                home_odds = safe_float(
                    row[config["home"]]
                )

                draw_odds = safe_float(
                    row[config["draw"]]
                )

                away_odds = safe_float(
                    row[config["away"]]
                )

                if (
                    home_odds is None
                    or draw_odds is None
                    or away_odds is None
                ):
                    continue

                conn.execute("""
                    INSERT OR REPLACE INTO odds (

                        match_id,
                        bookmaker,
                        odds_type,
                        home_odds,
                        draw_odds,
                        away_odds

                    )

                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    site,
                    config["type"],
                    home_odds,
                    draw_odds,
                    away_odds
                ))

                site_names.add(site)

            match_count += 1

        except Exception:
            continue

    conn.commit()
    conn.close()

    return match_count, site_names


# =========================================================
# 전체 데이터 업데이트
# =========================================================

def update_all_data():

    total_jobs = (
        len(SEASONS)
        *
        len(LEAGUES)
    )

    job = 0
    total_matches = 0
    all_sites = set()

    progress = st.progress(0)

    status = st.empty()

    for season_name, season_code in SEASONS.items():

        for league_name in LEAGUES:

            job += 1

            progress.progress(
                job / total_jobs
            )

            status.write(
                f"📥 {job}/{total_jobs} "
                f"| {season_name} "
                f"| {league_name}"
            )

            league_code = LEAGUES[
                league_name
            ][0]

            df = download_csv(
                season_code,
                league_code
            )

            if df is None:
                continue

            count, sites = save_dataframe(
                df,
                league_name,
                season_name
            )

            total_matches += count

            all_sites.update(
                sites
            )

    progress.progress(1.0)

    status.success(
        "✅ 데이터 업데이트 완료"
    )

    return (
        total_matches,
        all_sites
    )


# =========================================================
# DB 데이터 읽기
# =========================================================

@st.cache_data(
    ttl=60
)
def load_database():

    conn = sqlite3.connect(
        DB_FILE
    )

    query = """
        SELECT

            m.country,
            m.league,
            m.division,
            m.season,
            m.match_date,

            m.home_team,
            m.away_team,
            m.result,

            o.bookmaker,
            o.odds_type,

            o.home_odds,
            o.draw_odds,
            o.away_odds

        FROM matches m

        INNER JOIN odds o

        ON m.id = o.match_id
    """

    df = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    return df


# =========================================================
# 유사 배당 분석
# =========================================================

def analyze_bookmaker(
    df,
    bookmaker,
    home_odds,
    draw_odds,
    away_odds,
    tolerance
):

    data = df[
        df["bookmaker"]
        ==
        bookmaker
    ].copy()

    if data.empty:
        return None

    data = data.dropna(
        subset=[
            "home_odds",
            "draw_odds",
            "away_odds",
            "result"
        ]
    )

    if data.empty:
        return None

    data["diff_home"] = (
        data["home_odds"]
        -
        home_odds
    ).abs()

    data["diff_draw"] = (
        data["draw_odds"]
        -
        draw_odds
    ).abs()

    data["diff_away"] = (
        data["away_odds"]
        -
        away_odds
    ).abs()

    data["distance"] = (
        data["diff_home"]
        +
        data["diff_draw"]
        +
        data["diff_away"]
    )

    similar = data[
        (data["diff_home"] <= tolerance)
        &
        (data["diff_draw"] <= tolerance)
        &
        (data["diff_away"] <= tolerance)
    ].copy()

    if similar.empty:
        return None

    total = len(similar)

    win = int(
        (
            similar["result"]
            ==
            "H"
        ).sum()
    )

    draw = int(
        (
            similar["result"]
            ==
            "D"
        ).sum()
    )

    loss = int(
        (
            similar["result"]
            ==
            "A"
        ).sum()
    )

    return {
        "total": total,
        "win": win,
        "draw": draw,
        "loss": loss,
        "win_pct": win / total * 100,
        "draw_pct": draw / total * 100,
        "loss_pct": loss / total * 100,
        "data": similar.sort_values(
            "distance"
        )
    }


# =========================================================
# 화면
# =========================================================

st.title(
    "⚽ 해외배당 승무패 분석"
)

st.caption(
    "2020/21 ~ 2026/27 · 마감배당 우선 · 해외사이트별 분석"
)


# =========================================================
# DB 업데이트
# =========================================================

st.subheader(
    "📚 데이터 관리"
)

if st.button(
    "🔄 2020~2026 전체 데이터 업데이트",
    use_container_width=True
):

    with st.spinner(
        "전세계 축구 데이터를 수집하고 있습니다..."
    ):

        total, sites = update_all_data()

    st.cache_data.clear()

    st.success(
        f"완료! 처리 경기: {total:,}건"
    )

    st.info(
        "사용 가능한 해외사이트: "
        + ", ".join(
            sorted(sites)
        )
    )

    st.rerun()


# =========================================================
# DB 읽기
# =========================================================

try:

    db = load_database()

except Exception:

    db = pd.DataFrame()


# =========================================================
# DB가 비어있는 경우
# =========================================================

if db.empty:

    st.warning(
        "⚠️ historical_odds.db에 데이터가 없습니다."
    )

    st.info(
        "위의 "
        "'2020~2026 전체 데이터 업데이트' "
        "버튼을 한 번 눌러주세요."
    )

    st.stop()


# =========================================================
# 데이터 현황
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "배당 데이터",
        f"{len(db):,}"
    )

with c2:

    st.metric(
        "해외사이트",
        db["bookmaker"].nunique()
    )

with c3:

    st.metric(
        "리그",
        db["league"].nunique()
    )

with c4:

    st.metric(
        "시즌",
        db["season"].nunique()
    )


# =========================================================
# 배당 입력
# =========================================================

st.divider()

st.header(
    "🎯 현재 경기 배당 입력"
)

st.write(
    "팀 이름은 입력하지 않습니다."
)

st.write(
    "승·무·패 배당만 입력하면 자동으로 "
    "2020/21~2026/27 과거 경기와 비교합니다."
)


col1, col2, col3 = st.columns(3)


with col1:

    home_odds = st.number_input(
        "🟢 승 배당",
        min_value=1.01,
        max_value=100.0,
        value=1.85,
        step=0.01
    )


with col2:

    draw_odds = st.number_input(
        "🔵 무 배당",
        min_value=1.01,
        max_value=100.0,
        value=3.60,
        step=0.01
    )


with col3:

    away_odds = st.number_input(
        "🔴 패 배당",
        min_value=1.01,
        max_value=100.0,
        value=4.20,
        step=0.01
    )


# =========================================================
# 허용범위
# =========================================================

tolerance = st.slider(
    "유사배당 허용범위",
    min_value=0.05,
    max_value=0.50,
    value=0.20,
    step=0.05
)


st.caption(
    f"입력 배당: "
    f"{home_odds:.2f} / "
    f"{draw_odds:.2f} / "
    f"{away_odds:.2f}"
)


# =========================================================
# 사이트 목록
# =========================================================

bookmakers = sorted(
    db["bookmaker"]
    .dropna()
    .unique()
    .tolist()
)


# =========================================================
# 분석
# =========================================================

results = {}

for bookmaker in bookmakers:

    result = analyze_bookmaker(
        db,
        bookmaker,
        home_odds,
        draw_odds,
        away_odds,
        tolerance
    )

    if result is not None:

        results[
            bookmaker
        ] = result


# =========================================================
# 결과
# =========================================================

st.divider()

st.header(
    "📊 해외사이트별 전체 결과"
)


if not results:

    st.warning(
        "현재 배당과 유사한 과거 경기가 없습니다."
    )

    st.info(
        "유사배당 허용범위를 조금 높여보세요."
    )

else:

    # =====================================================
    # 전체 합계
    # =====================================================

    total_sample = sum(
        r["total"]
        for r in results.values()
    )

    total_win = sum(
        r["win"]
        for r in results.values()
    )

    total_draw = sum(
        r["draw"]
        for r in results.values()
    )

    total_loss = sum(
        r["loss"]
        for r in results.values()
    )

    overall_win = (
        total_win
        /
        total_sample
        *
        100
    )

    overall_draw = (
        total_draw
        /
        total_sample
        *
        100
    )

    overall_loss = (
        total_loss
        /
        total_sample
        *
        100
    )


    # =====================================================
    # 전체 결과
    # =====================================================

    st.subheader(
        "🏆 전체 사이트 종합"
    )

    overall_col1, overall_col2, overall_col3, overall_col4 = (
        st.columns(4)
    )

    with overall_col1:

        st.metric(
            "승",
            f"{overall_win:.2f}%"
        )

    with overall_col2:

        st.metric(
            "무",
            f"{overall_draw:.2f}%"
        )

    with overall_col3:

        st.metric(
            "패",
            f"{overall_loss:.2f}%"
        )

    with overall_col4:

        st.metric(
            "총 표본",
            f"{total_sample:,}"
        )


    # =====================================================
    # 가장 높은 결과
    # =====================================================

    overall_values = {

        "승": overall_win,

        "무": overall_draw,

        "패": overall_loss
    }

    best_result = max(
        overall_values,
        key=overall_values.get
    )

    best_value = (
        overall_values[
            best_result
        ]
    )

    st.success(
        f"🔥 전체 사이트에서 가장 많이 나온 결과: "
        f"{best_result} "
        f"({best_value:.2f}%)"
    )


    # =====================================================
    # 사이트별 결과
    # =====================================================

    st.subheader(
        "🌍 사이트별 결과"
    )

    table_rows = []

    for bookmaker, r in results.items():

        table_rows.append({

            "사이트":
                bookmaker,

            "표본":
                r["total"],

            "승":
                f"{r['win_pct']:.2f}%",

            "무":
                f"{r['draw_pct']:.2f}%",

            "패":
                f"{r['loss_pct']:.2f}%",

            "최다결과":
                max(
                    {
                        "승": r["win_pct"],
                        "무": r["draw_pct"],
                        "패": r["loss_pct"]
                    },
                    key={
                        "승": r["win_pct"],
                        "무": r["draw_pct"],
                        "패": r["loss_pct"]
                    }.get
                )

        })


    result_table = pd.DataFrame(
        table_rows
    )


    result_table = result_table.sort_values(
        "표본",
        ascending=False
    )


    # =====================================================
    # 핵심: 사이트별 전체 결과를 한 화면
    # =====================================================

    st.dataframe(
        result_table,
        use_container_width=True,
        hide_index=True,
        height=500
    )


    # =====================================================
    # 사이트별 상세 카드
    # =====================================================

    st.subheader(
        "📌 사이트별 상세"
    )

    # 3개씩 한 줄
    site_list = list(
        results.keys()
    )

    for i in range(
        0,
        len(site_list),
        3
    ):

        row_sites = site_list[
            i:i + 3
        ]

        cols = st.columns(3)

        for col, bookmaker in zip(
            cols,
            row_sites
        ):

            r = results[
                bookmaker
            ]

            with col:

                st.markdown(
                    f"### {bookmaker}"
                )

                st.metric(
                    "표본",
                    f"{r['total']:,}건"
                )

                st.write(
                    f"🟢 승 **{r['win_pct']:.2f}%**"
                )

                st.write(
                    f"🔵 무 **{r['draw_pct']:.2f}%**"
                )

                st.write(
                    f"🔴 패 **{r['loss_pct']:.2f}%**"
                )


# =========================================================
# 과거 실제 경기 상세
# =========================================================

st.divider()

st.header(
    "🔎 유사배당 실제 경기"
)

selected_site = st.selectbox(
    "사이트 선택",
    sorted(
        results.keys()
    )
)


if selected_site in results:

    r = results[
        selected_site
    ]

    detail = r[
        "data"
    ].head(100).copy()

    detail["결과"] = (
        detail["result"]
        .replace({
            "H": "승",
            "D": "무",
            "A": "패"
        })
    )

    detail = detail[

        [
            "season",
            "league",
            "match_date",
            "home_team",
            "away_team",
            "home_odds",
            "draw_odds",
            "away_odds",
            "result"
        ]

    ]

    detail.columns = [

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

    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
        height=450
    )


# =========================================================
# DB 데이터 현황
# =========================================================

st.divider()

st.header(
    "📈 저장된 데이터 현황"
)


season_summary = (
    db
    .groupby(
        "season"
    )
    .size()
    .reset_index(
        name="배당건수"
    )
    .sort_values(
        "season",
        ascending=False
    )
)


st.dataframe(
    season_summary,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 사이트별 DB 데이터
# =========================================================

st.subheader(
    "🌐 DB 사이트별 데이터"
)


site_summary = (
    db
    .groupby(
        "bookmaker"
    )
    .size()
    .reset_index(
        name="배당건수"
    )
    .sort_values(
        "배당건수",
        ascending=False
    )
)


st.dataframe(
    site_summary,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 리그별 데이터
# =========================================================

st.subheader(
    "🏟️ 리그별 데이터"
)


league_summary = (
    db
    .groupby(
        [
            "country",
            "league"
        ]
    )
    .size()
    .reset_index(
        name="배당건수"
    )
    .sort_values(
        "배당건수",
        ascending=False
    )
)


st.dataframe(
    league_summary,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# CSV 다운로드
# =========================================================

st.divider()

st.header(
    "📥 데이터 다운로드"
)


csv_data = db.to_csv(
    index=False,
    encoding="utf-8-sig"
)


st.download_button(
    "📥 전체 데이터 CSV 저장",
    data=csv_data,
    file_name="historical_odds_2020_2026.csv",
    mime="text/csv",
    use_container_width=True
)


# =========================================================
# 안내
# =========================================================

st.divider()

st.caption(
    "데이터 출처: Football-Data.co.uk"
)

st.caption(
    "가능한 경우 마감배당(Closing Odds)을 우선 사용합니다."
)

st.caption(
    "2020/21 ~ 2026/27 현재까지의 데이터를 사용합니다."
)

st.caption(
    "리그 및 시즌에 따라 제공되는 배당사이트가 다를 수 있습니다."
)

st.caption(
    "과거 빈도 통계는 미래 경기 결과를 보장하지 않습니다."
)
