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
    page_title="해외배당 분석",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed"
)

DB_FILE = "historical_odds.db"

BASE_URL = "https://www.football-data.co.uk/mmz4281"


# =========================================================
# 휴대폰 화면 CSS
# =========================================================

st.markdown("""
<style>

.block-container {
    max-width: 720px;
    padding: 1rem;
}

h1 {
    text-align: center;
    font-size: 28px !important;
}

div.stButton > button {
    width: 100%;
    min-height: 50px;
    font-size: 17px;
    font-weight: bold;
    border-radius: 10px;
}

.result-box {
    background: #f5f7fa;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    margin: 10px 0;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 리그 목록
# =========================================================

LEAGUES = {

    "잉글랜드 1부": ("England", "E0", 1),
    "잉글랜드 2부": ("England", "E1", 2),
    "잉글랜드 3부": ("England", "E2", 3),
    "잉글랜드 4부": ("England", "E3", 4),

    "스코틀랜드 1부": ("Scotland", "SC0", 1),
    "스코틀랜드 2부": ("Scotland", "SC1", 2),
    "스코틀랜드 3부": ("Scotland", "SC2", 3),
    "스코틀랜드 4부": ("Scotland", "SC3", 4),

    "독일 1부": ("Germany", "D1", 1),
    "독일 2부": ("Germany", "D2", 2),

    "이탈리아 1부": ("Italy", "I1", 1),
    "이탈리아 2부": ("Italy", "I2", 2),

    "스페인 1부": ("Spain", "SP1", 1),
    "스페인 2부": ("Spain", "SP2", 2),

    "프랑스 1부": ("France", "F1", 1),
    "프랑스 2부": ("France", "F2", 2),

    "네덜란드 1부": ("Netherlands", "N1", 1),
    "벨기에 1부": ("Belgium", "B1", 1),
    "포르투갈 1부": ("Portugal", "P1", 1),
    "터키 1부": ("Turkey", "T1", 1),
    "그리스 1부": ("Greece", "G1", 1),

    # 추가 국가
    "아르헨티나 1부": ("Argentina", "ARG", 1),
    "오스트리아 1부": ("Austria", "AUT", 1),
    "브라질 1부": ("Brazil", "BRA", 1),
    "중국 1부": ("China", "CHN", 1),
    "덴마크 1부": ("Denmark", "DEN", 1),
    "핀란드 1부": ("Finland", "FIN", 1),
    "아일랜드 1부": ("Ireland", "IRL", 1),
    "일본 1부": ("Japan", "JPN", 1),
    "멕시코 1부": ("Mexico", "MEX", 1),
    "노르웨이 1부": ("Norway", "NOR", 1),
    "폴란드 1부": ("Poland", "POL", 1),
    "루마니아 1부": ("Romania", "ROM", 1),
    "러시아 1부": ("Russia", "RUS", 1),
    "스웨덴 1부": ("Sweden", "SWE", 1),
    "스위스 1부": ("Switzerland", "SWZ", 1),
    "미국 1부": ("USA", "USA", 1),
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

        pinnacle_home REAL,
        pinnacle_draw REAL,
        pinnacle_away REAL,

        william_home REAL,
        william_draw REAL,
        william_away REAL,

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
# CSV 다운로드
# =========================================================

def download_csv(
    season_code,
    league_code
):

    url = (
        f"{BASE_URL}/"
        f"{season_code}/"
        f"{league_code}.csv"
    )

    try:

        r = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        if r.status_code != 200:
            return None

        if len(r.content) < 100:
            return None

        r.encoding = "latin1"

        return pd.read_csv(
            StringIO(r.text)
        )

    except Exception:

        return None


# =========================================================
# 컬럼 찾기
# =========================================================

def find_col(
    df,
    names
):

    for name in names:

        if name in df.columns:
            return name

    return None


# =========================================================
# 마감배당 컬럼 찾기
# =========================================================

def odds_columns(df):

    return {

        "bet365_home":
            find_col(
                df,
                ["B365CH"]
            ),

        "bet365_draw":
            find_col(
                df,
                ["B365CD"]
            ),

        "bet365_away":
            find_col(
                df,
                ["B365CA"]
            ),

        "pinnacle_home":
            find_col(
                df,
                ["PSCH"]
            ),

        "pinnacle_draw":
            find_col(
                df,
                ["PSCD"]
            ),

        "pinnacle_away":
            find_col(
                df,
                ["PSCA"]
            ),

        "william_home":
            find_col(
                df,
                ["WHCH"]
            ),

        "william_draw":
            find_col(
                df,
                ["WHCD"]
            ),

        "william_away":
            find_col(
                df,
                ["WHCA"]
            ),
    }


# =========================================================
# 데이터 저장
# =========================================================

def save_dataframe(
    raw,
    league_name,
    season_name
):

    if raw is None:
        return 0

    if "FTR" not in raw.columns:
        return 0

    if "HomeTeam" not in raw.columns:
        return 0

    if "AwayTeam" not in raw.columns:
        return 0

    info = LEAGUES[
        league_name
    ]

    country = info[0]
    division = info[2]

    oc = odds_columns(raw)

    conn = sqlite3.connect(
        DB_FILE
    )

    saved = 0

    for _, row in raw.iterrows():

        try:

            result = str(
                row.get(
                    "FTR",
                    ""
                )
            ).strip().upper()

            if result not in [
                "H",
                "D",
                "A"
            ]:
                continue

            home_team = str(
                row.get(
                    "HomeTeam",
                    ""
                )
            )

            away_team = str(
                row.get(
                    "AwayTeam",
                    ""
                )
            )

            match_date = str(
                row.get(
                    "Date",
                    ""
                )
            )


            def number(
                col
            ):

                if not col:
                    return None

                value = pd.to_numeric(
                    row.get(col),
                    errors="coerce"
                )

                if pd.isna(value):
                    return None

                return float(value)


            bh = number(
                oc["bet365_home"]
            )

            bd = number(
                oc["bet365_draw"]
            )

            ba = number(
                oc["bet365_away"]
            )


            ph = number(
                oc["pinnacle_home"]
            )

            pd_ = number(
                oc["pinnacle_draw"]
            )

            pa = number(
                oc["pinnacle_away"]
            )


            wh = number(
                oc["william_home"]
            )

            wd = number(
                oc["william_draw"]
            )

            wa = number(
                oc["william_away"]
            )


            cur = conn.execute(
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

                    pinnacle_home,
                    pinnacle_draw,
                    pinnacle_away,

                    william_home,
                    william_draw,
                    william_away,

                    source,
                    created_at

                )

                VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
                """,

                (
                    country,
                    league_name,
                    division,
                    season_name,

                    match_date,

                    home_team,
                    away_team,

                    result,

                    bh,
                    bd,
                    ba,

                    ph,
                    pd_,
                    pa,

                    wh,
                    wd,
                    wa,

                    "football-data.co.uk",

                    datetime.now().isoformat()
                )
            )

            if cur.rowcount > 0:
                saved += 1

        except Exception:
            continue


    conn.commit()
    conn.close()

    return saved


# =========================================================
# DB 읽기
# =========================================================

def load_db():

    conn = sqlite3.connect(
        DB_FILE
    )

    df = pd.read_sql_query(
        "SELECT * FROM matches",
        conn
    )

    conn.close()

    return df


# =========================================================
# 데이터 전체 수집
# =========================================================

def collect_all(
    selected_leagues,
    selected_seasons
):

    total_files = 0
    total_matches = 0

    progress = st.progress(0)

    total = (
        len(selected_leagues)
        *
        len(selected_seasons)
    )

    current = 0

    status = st.empty()

    for league in selected_leagues:

        info = LEAGUES[
            league
        ]

        league_code = info[1]

        for season in selected_seasons:

            season_code = SEASONS[
                season
            ]

            current += 1

            progress.progress(
                min(
                    current / total,
                    1.0
                )
            )

            status.write(
                f"📥 {league} / {season}"
            )

            raw = download_csv(
                season_code,
                league_code
            )

            if raw is None:
                continue

            saved = save_dataframe(
                raw,
                league,
                season
            )

            total_files += 1
            total_matches += saved


    status.success(
        f"완료: {total_files}개 파일 / "
        f"{total_matches:,}경기 신규 저장"
    )

    return total_matches


# =========================================================
# 유사배당 분석
# =========================================================

def analyze(
    df,
    site,
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


    columns = {

        "Bet365": (
            "bet365_home",
            "bet365_draw",
            "bet365_away"
        ),

        "Pinnacle": (
            "pinnacle_home",
            "pinnacle_draw",
            "pinnacle_away"
        ),

        "William Hill": (
            "william_home",
            "william_draw",
            "william_away"
        )
    }

    hcol, dcol, acol = columns[
        site
    ]


    x = df.copy()


    for col in [
        hcol,
        dcol,
        acol
    ]:

        x[col] = pd.to_numeric(
            x[col],
            errors="coerce"
        )


    x = x.dropna(
        subset=[
            hcol,
            dcol,
            acol
        ]
    )


    if x.empty:
        return None


    x["차이"] = (

        abs(
            x[hcol] - home_odds
        )

        +

        abs(
            x[dcol] - draw_odds
        )

        +

        abs(
            x[acol] - away_odds
        )
    )


    x = x[
        (abs(x[hcol] - home_odds) <= tolerance)
        &
        (abs(x[dcol] - draw_odds) <= tolerance)
        &
        (abs(x[acol] - away_odds) <= tolerance)
    ]


    if x.empty:
        return None


    x = x.sort_values(
        "차이"
    )


    total = len(x)

    wins = (
        x["result"] == "H"
    ).sum()

    draws = (
        x["result"] == "D"
    ).sum()

    losses = (
        x["result"] == "A"
    ).sum()


    return {

        "data": x,

        "total": total,

        "wins": wins,

        "draws": draws,

        "losses": losses,

        "win_pct":
            wins / total * 100,

        "draw_pct":
            draws / total * 100,

        "loss_pct":
            losses / total * 100
    }


# =========================================================
# 제목
# =========================================================

st.title(
    "⚽ 해외배당 자동분석"
)

st.caption(
    "실제 과거 마감배당 + 경기결과를 "
    "기준으로 유사배당 통계를 계산합니다."
)


# =========================================================
# 데이터 수집 영역
# =========================================================

with st.expander(
    "📥 과거 데이터 DB 만들기",
    expanded=False
):

    st.write(
        "API 키 없이 공개 CSV 데이터를 받아 "
        "historical_odds.db에 저장합니다."
    )

    collect_leagues = st.multiselect(
        "수집할 리그",
        list(LEAGUES.keys()),
        default=[
            "잉글랜드 1부",
            "잉글랜드 2부",
            "잉글랜드 3부",
            "독일 1부",
            "독일 2부",
            "이탈리아 1부",
            "이탈리아 2부",
            "스페인 1부",
            "스페인 2부",
            "프랑스 1부",
            "프랑스 2부"
        ]
    )


    collect_seasons = st.multiselect(
        "수집할 시즌",
        list(SEASONS.keys()),
        default=list(
            SEASONS.keys()
        )
    )


    if st.button(
        "📥 선택 데이터 DB에 넣기",
        type="primary",
        use_container_width=True
    ):

        if not collect_leagues:

            st.error(
                "리그를 하나 이상 선택하세요."
            )

        elif not collect_seasons:

            st.error(
                "시즌을 하나 이상 선택하세요."
            )

        else:

            collect_all(
                collect_leagues,
                collect_seasons
            )

            st.rerun()


# =========================================================
# DB 현황
# =========================================================

db = load_db()


m1, m2, m3 = st.columns(3)

with m1:
    st.metric(
        "DB 경기",
        f"{len(db):,}"
    )

with m2:
    st.metric(
        "리그",
        f"{db['league'].nunique() if len(db) else 0:,}"
    )

with m3:
    st.metric(
        "시즌",
        f"{db['season'].nunique() if len(db) else 0:,}"
    )


# =========================================================
# 경기 입력
# =========================================================

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


league = st.selectbox(
    "분석 리그",
    ["전체"] + list(
        LEAGUES.keys()
    )
)


site = st.selectbox(
    "해외사이트",
    [
        "Bet365",
        "Pinnacle",
        "William Hill"
    ]
)


# =========================================================
# 배당 입력
# =========================================================

st.subheader(
    "💰 마감 직전 배당"
)


c1, c2, c3 = st.columns(3)

with c1:

    home_odds = st.number_input(
        "승",
        min_value=1.01,
        max_value=100.0,
        value=1.85,
        step=0.01,
        format="%.2f"
    )

with c2:

    draw_odds = st.number_input(
        "무",
        min_value=1.01,
        max_value=100.0,
        value=3.60,
        step=0.01,
        format="%.2f"
    )

with c3:

    away_odds = st.number_input(
        "패",
        min_value=1.01,
        max_value=100.0,
        value=4.20,
        step=0.01,
        format="%.2f"
    )


# =========================================================
# 허용범위
# =========================================================

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
    value=0.10
)


# =========================================================
# 분석
# =========================================================

if st.button(
    "🔍 분석하기",
    type="primary",
    use_container_width=True
):

    if db.empty:

        st.error(
            "DB에 데이터가 없습니다."
        )

        st.info(
            "위의 '과거 데이터 DB 만들기'에서 "
            "먼저 데이터를 받아주세요."
        )

        st.stop()


    result = analyze(
        db,
        site,
        home_odds,
        draw_odds,
        away_odds,
        tolerance,
        league
    )


    if result is None:

        st.warning(
            "조건에 맞는 과거 유사경기가 없습니다."
        )

        st.info(
            "유사배당 허용범위를 "
            "±0.20 또는 ±0.30으로 높여보세요."
        )

        st.stop()


    win = result["win_pct"]
    draw = result["draw_pct"]
    loss = result["loss_pct"]


    # =====================================================
    # 결과
    # =====================================================

    st.divider()

    st.subheader(
        "📊 과거 유사배당 결과"
    )


    p1, p2, p3 = st.columns(3)

    with p1:

        st.metric(
            "🟢 승",
            f"{win:.2f}%"
        )

    with p2:

        st.metric(
            "🔵 무",
            f"{draw:.2f}%"
        )

    with p3:

        st.metric(
            "🔴 패",
            f"{loss:.2f}%"
        )


    probabilities = {

        "승": win,
        "무": draw,
        "패": loss
    }


    prediction = max(
        probabilities,
        key=probabilities.get
    )


    prediction_pct = probabilities[
        prediction
    ]


    st.markdown(
        f"""
        <div class="result-box">

        <h2>🏆 가장 많이 나온 결과</h2>

        <h1>{prediction}</h1>

        <h3>{prediction_pct:.2f}%</h3>

        <p>
        과거 유사경기 {result["total"]:,}경기 기준
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # 무승부 경고
    # =====================================================

    if draw >= 30:

        st.error(
            f"🤝 무승부 {draw:.2f}% "
            "→ 매우 높은 편"
        )

    elif draw >= 25:

        st.warning(
            f"🤝 무승부 {draw:.2f}% "
            "→ 높은 편"
        )

    else:

        st.success(
            f"🤝 무승부 {draw:.2f}%"
        )


    # =====================================================
    # 실제 건수
    # =====================================================

    count_df = pd.DataFrame({

        "결과": [
            "승",
            "무",
            "패"
        ],

        "경기수": [
            result["wins"],
            result["draws"],
            result["losses"]
        ],

        "확률": [
            f"{win:.2f}%",
            f"{draw:.2f}%",
            f"{loss:.2f}%"
        ]
    })


    st.dataframe(
        count_df,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 유사 경기
    # =====================================================

    st.subheader(
        "📋 유사 마감배당 경기"
    )


    x = result["data"].copy()


    hcol, dcol, acol = {

        "Bet365": (
            "bet365_home",
            "bet365_draw",
            "bet365_away"
        ),

        "Pinnacle": (
            "pinnacle_home",
            "pinnacle_draw",
            "pinnacle_away"
        ),

        "William Hill": (
            "william_home",
            "william_draw",
            "william_away"
        )

    }[site]


    display = x[
        [
            "season",
            "match_date",
            "home_team",
            "away_team",
            hcol,
            dcol,
            acol,
            "result",
            "차이"
        ]
    ].head(100).copy()


    display.columns = [

        "시즌",
        "날짜",
        "홈팀",
        "원정팀",
        "승배당",
        "무배당",
        "패배당",
        "결과",
        "배당차이"
    ]


    display["결과"] = display[
        "결과"
    ].replace({

        "H": "승",
        "D": "무",
        "A": "패"
    })


    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# CSV 다운로드
# =========================================================

if not db.empty:

    st.divider()

    st.subheader(
        "📥 DB 다운로드"
    )


    csv = db.to_csv(
        index=False,
        encoding="utf-8-sig"
    )


    st.download_button(
        "historical_odds.csv 저장",
        data=csv,
        file_name="historical_odds.csv",
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
    "본 프로그램은 과거 유사 마감배당과 "
    "실제 경기 결과의 통계를 보여주는 도구이며 "
    "미래 경기 결과를 보장하지 않습니다."
)
