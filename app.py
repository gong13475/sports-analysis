import streamlit as st
import sqlite3
import pandas as pd
import os

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


# =========================================================
# 모바일 화면용 CSS
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: Arial, sans-serif;
}

.block-container {
    max-width: 700px;
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

h1 {
    font-size: 28px !important;
    text-align: center;
}

h2 {
    font-size: 22px !important;
}

div.stButton > button {
    width: 100%;
    height: 52px;
    font-size: 18px;
    font-weight: bold;
    border-radius: 10px;
}

div[data-testid="stMetric"] {
    background: #f5f7fa;
    padding: 10px;
    border-radius: 10px;
}

.result-box {
    padding: 18px;
    border-radius: 12px;
    background: #f5f7fa;
    margin: 10px 0;
    text-align: center;
}

.win {
    color: #008000;
    font-weight: bold;
}

.draw {
    color: #0066cc;
    font-weight: bold;
}

.lose {
    color: #cc0000;
    font-weight: bold;
}

.small {
    color: #666;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DB 생성
# =========================================================

def create_database():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            site TEXT,
            country TEXT,
            league TEXT,
            division INTEGER,
            season TEXT,

            match_date TEXT,

            home_team TEXT,
            away_team TEXT,

            home_odds REAL,
            draw_odds REAL,
            away_odds REAL,

            result TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


create_database()


# =========================================================
# DB 불러오기
# =========================================================

def load_data():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query(
        "SELECT * FROM matches",
        conn
    )

    conn.close()

    return df


# =========================================================
# 데이터 저장
# =========================================================

def save_match(
    site,
    country,
    league,
    division,
    season,
    match_date,
    home_team,
    away_team,
    home_odds,
    draw_odds,
    away_odds,
    result
):

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        INSERT INTO matches (

            site,
            country,
            league,
            division,
            season,

            match_date,

            home_team,
            away_team,

            home_odds,
            draw_odds,
            away_odds,

            result
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        site,
        country,
        league,
        division,
        season,

        match_date,

        home_team,
        away_team,

        home_odds,
        draw_odds,
        away_odds,

        result
    ))

    conn.commit()
    conn.close()


# =========================================================
# 유사 배당 검색
# =========================================================

def find_similar_matches(
    df,
    site,
    home_odds,
    draw_odds,
    away_odds,
    tolerance
):

    if df.empty:
        return pd.DataFrame()

    x = df.copy()

    # 사이트 필터
    x = x[
        x["site"].astype(str) == site
    ]

    if x.empty:
        return pd.DataFrame()

    # 숫자 변환
    for col in [
        "home_odds",
        "draw_odds",
        "away_odds"
    ]:

        x[col] = pd.to_numeric(
            x[col],
            errors="coerce"
        )

    x["result"] = x["result"].astype(str).str.upper()

    # 결측 제거
    x = x.dropna(
        subset=[
            "home_odds",
            "draw_odds",
            "away_odds",
            "result"
        ]
    )

    if x.empty:
        return pd.DataFrame()

    # 입력 배당과의 차이
    x["home_diff"] = (
        abs(x["home_odds"] - home_odds)
    )

    x["draw_diff"] = (
        abs(x["draw_odds"] - draw_odds)
    )

    x["away_diff"] = (
        abs(x["away_odds"] - away_odds)
    )

    # 세 배당 모두 허용범위 안
    x = x[
        (x["home_diff"] <= tolerance)
        &
        (x["draw_diff"] <= tolerance)
        &
        (x["away_diff"] <= tolerance)
    ]

    if x.empty:
        return pd.DataFrame()

    # 가장 비슷한 배당부터
    x["total_diff"] = (
        x["home_diff"]
        +
        x["draw_diff"]
        +
        x["away_diff"]
    )

    x = x.sort_values(
        "total_diff"
    )

    return x


# =========================================================
# 확률 계산
# =========================================================

def calculate_probability(df):

    if df.empty:
        return None

    total = len(df)

    home_count = (
        df["result"] == "H"
    ).sum()

    draw_count = (
        df["result"] == "D"
    ).sum()

    away_count = (
        df["result"] == "A"
    ).sum()

    home_pct = (
        home_count / total * 100
    )

    draw_pct = (
        draw_count / total * 100
    )

    away_pct = (
        away_count / total * 100
    )

    return {
        "total": total,

        "home_count": home_count,
        "draw_count": draw_count,
        "away_count": away_count,

        "home_pct": home_pct,
        "draw_pct": draw_pct,
        "away_pct": away_pct
    }


# =========================================================
# 제목
# =========================================================

st.title("⚽ 해외배당 자동분석")

st.caption(
    "승·무·패 마감배당을 입력하면 "
    "과거 유사 배당 경기의 실제 결과를 계산합니다."
)


# =========================================================
# 경기 정보
# =========================================================

st.subheader("📌 경기 정보")

home_team = st.text_input(
    "홈팀",
    placeholder="예: Liverpool"
)

away_team = st.text_input(
    "원정팀",
    placeholder="예: Chelsea"
)


# =========================================================
# 리그
# =========================================================

league_list = [

    "전체",

    "잉글랜드 1부",
    "잉글랜드 2부",
    "잉글랜드 3부",

    "독일 1부",
    "독일 2부",

    "스페인 1부",
    "스페인 2부",

    "이탈리아 1부",
    "이탈리아 2부",

    "프랑스 1부",
    "프랑스 2부",

    "네덜란드 1부",

    "포르투갈 1부",

    "벨기에 1부",

    "스코틀랜드 1부",
    "스코틀랜드 2부",

    "터키 1부",

    "그리스 1부"
]

league = st.selectbox(
    "리그",
    league_list
)


# =========================================================
# 사이트
# =========================================================

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

st.subheader("💰 마감배당 입력")

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
    "유사 배당 범위",
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

st.caption(
    f"현재 설정: 각 배당 ±{tolerance:.2f}"
)


# =========================================================
# 분석 버튼
# =========================================================

analyze_button = st.button(
    "🔍 배당 분석하기",
    type="primary"
)


# =========================================================
# 분석 실행
# =========================================================

if analyze_button:

    df = load_data()

    if df.empty:

        st.error(
            "현재 historical_odds.db에 "
            "과거 경기 데이터가 없습니다."
        )

        st.info(
            "먼저 과거 경기 데이터를 DB에 넣어주세요."
        )

        st.stop()


    # 리그 필터
    filtered = df.copy()

    if league != "전체":

        filtered = filtered[
            filtered["league"]
            .astype(str)
            .str.contains(
                league,
                case=False,
                na=False
            )
        ]


    result_df = find_similar_matches(
        filtered,
        site,
        home_odds,
        draw_odds,
        away_odds,
        tolerance
    )


    # =====================================================
    # 데이터 없음
    # =====================================================

    if result_df.empty:

        st.warning(
            "조건에 맞는 과거 경기를 찾지 못했습니다."
        )

        st.write(
            "유사 배당 범위를 "
            f"±{tolerance:.2f}에서 "
            "±0.20 또는 ±0.30으로 넓혀보세요."
        )

        st.stop()


    # =====================================================
    # 확률
    # =====================================================

    result = calculate_probability(
        result_df
    )


    home_pct = result["home_pct"]
    draw_pct = result["draw_pct"]
    away_pct = result["away_pct"]


    # =====================================================
    # 최종 결과
    # =====================================================

    probabilities = {

        "승": home_pct,

        "무": draw_pct,

        "패": away_pct
    }

    prediction = max(
        probabilities,
        key=probabilities.get
    )

    prediction_pct = probabilities[
        prediction
    ]


    # =====================================================
    # 결과 제목
    # =====================================================

    st.divider()

    st.subheader("📊 분석 결과")


    # =====================================================
    # 배당 표시
    # =====================================================

    a, b, c = st.columns(3)

    with a:
        st.metric(
            "승 배당",
            f"{home_odds:.2f}"
        )

    with b:
        st.metric(
            "무 배당",
            f"{draw_odds:.2f}"
        )

    with c:
        st.metric(
            "패 배당",
            f"{away_odds:.2f}"
        )


    # =====================================================
    # 확률
    # =====================================================

    st.markdown(
        '<div class="result-box">',
        unsafe_allow_html=True
    )

    p1, p2, p3 = st.columns(3)

    with p1:

        st.metric(
            "🟢 승",
            f"{home_pct:.2f}%"
        )

    with p2:

        st.metric(
            "🔵 무",
            f"{draw_pct:.2f}%"
        )

    with p3:

        st.metric(
            "🔴 패",
            f"{away_pct:.2f}%"
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


    # =====================================================
    # 최고 확률
    # =====================================================

    if prediction == "승":

        color = "win"
        emoji = "🟢"

    elif prediction == "무":

        color = "draw"
        emoji = "🔵"

    else:

        color = "lose"
        emoji = "🔴"


    st.markdown(
        f"""
        <div class="result-box">

        <h2>
        {emoji} 최다 발생 결과
        </h2>

        <h1 class="{color}">
        {prediction}
        </h1>

        <h3>
        과거 유사배당 결과
        {prediction_pct:.2f}%
        </h3>

        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # 표본수
    # =====================================================

    st.metric(
        "📚 유사 경기 수",
        f"{result['total']:,}경기"
    )


    # =====================================================
    # 무승부 분석
    # =====================================================

    st.subheader("🤝 무승부 분석")

    if draw_pct >= 30:

        st.error(
            f"무승부율 {draw_pct:.2f}% "
            "→ 상당히 높은 편"
        )

    elif draw_pct >= 25:

        st.warning(
            f"무승부율 {draw_pct:.2f}% "
            "→ 주의할 필요가 있습니다."
        )

    else:

        st.success(
            f"무승부율 {draw_pct:.2f}% "
            "→ 상대적으로 낮은 편"
        )


    # =====================================================
    # 승/무/패 카운트
    # =====================================================

    st.subheader("📈 실제 경기 결과")

    count_df = pd.DataFrame({

        "결과": [
            "승",
            "무",
            "패"
        ],

        "경기수": [
            result["home_count"],
            result["draw_count"],
            result["away_count"]
        ],

        "비율": [
            f"{home_pct:.2f}%",
            f"{draw_pct:.2f}%",
            f"{away_pct:.2f}%"
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

    st.subheader("📋 유사 마감배당 경기")

    show = result_df.copy()

    show = show[[
        "season",
        "match_date",
        "home_team",
        "away_team",
        "home_odds",
        "draw_odds",
        "away_odds",
        "result"
    ]]

    show.columns = [

        "시즌",
        "날짜",
        "홈팀",
        "원정팀",
        "승배당",
        "무배당",
        "패배당",
        "결과"
    ]

    st.dataframe(
        show.head(100),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# DB 관리
# =========================================================

st.divider()

st.subheader("🗄️ 데이터베이스")

db = load_data()


m1, m2 = st.columns(2)

with m1:

    st.metric(
        "전체 경기",
        f"{len(db):,}"
    )

with m2:

    if len(db):

        st.metric(
            "사이트",
            f"{db['site'].nunique():,}"
        )

    else:

        st.metric(
            "사이트",
            "0"
        )


# =========================================================
# CSV 다운로드
# =========================================================

if not db.empty:

    csv_data = db.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        "📥 DB 전체 CSV 저장",
        data=csv_data,
        file_name="historical_odds.csv",
        mime="text/csv",
        use_container_width=True
    )


# =========================================================
# 데이터 직접 입력
# =========================================================

with st.expander(
    "➕ 과거 경기 1건 직접 추가"
):

    st.write(
        "API 없이 테스트하거나 "
        "직접 확보한 데이터를 넣을 때 사용합니다."
    )

    add_site = st.selectbox(
        "사이트",
        [
            "Bet365",
            "Pinnacle",
            "William Hill"
        ],
        key="add_site"
    )

    add_league = st.text_input(
        "리그",
        value="잉글랜드 1부",
        key="add_league"
    )

    add_season = st.text_input(
        "시즌",
        value="2024/25",
        key="add_season"
    )

    add_date = st.text_input(
        "경기 날짜",
        value="2025-01-01",
        key="add_date"
    )

    add_home = st.text_input(
        "홈팀",
        key="add_home"
    )

    add_away = st.text_input(
        "원정팀",
        key="add_away"
    )

    a1, a2, a3 = st.columns(3)

    with a1:

        add_h = st.number_input(
            "승배당",
            min_value=1.01,
            value=1.85,
            step=0.01,
            key="add_h"
        )

    with a2:

        add_d = st.number_input(
            "무배당",
            min_value=1.01,
            value=3.60,
            step=0.01,
            key="add_d"
        )

    with a3:

        add_a = st.number_input(
            "패배당",
            min_value=1.01,
            value=4.20,
            step=0.01,
            key="add_a"
        )


    add_result = st.selectbox(
        "실제 경기 결과",
        [
            "H",
            "D",
            "A"
        ],
        format_func=lambda x: {
            "H": "승",
            "D": "무",
            "A": "패"
        }[x],
        key="add_result"
    )


    if st.button(
        "💾 경기 저장",
        use_container_width=True
    ):

        save_match(

            site=add_site,

            country="",

            league=add_league,

            division=1,

            season=add_season,

            match_date=add_date,

            home_team=add_home,

            away_team=add_away,

            home_odds=add_h,

            draw_odds=add_d,

            away_odds=add_a,

            result=add_result
        )

        st.success(
            "경기를 DB에 저장했습니다."
        )

        st.rerun()


# =========================================================
# 주의사항
# =========================================================

st.divider()

st.caption(
    "※ 과거 유사배당의 실제 결과를 통계적으로 보여주는 "
    "분석 프로그램입니다."
)

st.caption(
    "※ 통계 결과가 미래 경기 결과를 보장하지 않습니다."
)
