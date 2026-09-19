import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import requests
from io import StringIO
from datetime import datetime


# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="해외축구 배당 자동분석",
    page_icon="⚽",
    layout="wide"
)

DB_FILE = "historical_odds.db"

BASE_URL = "https://www.football-data.co.uk/mmz4281"


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.big-title {
    font-size: 32px;
    font-weight: 800;
}

.section-title {
    font-size: 22px;
    font-weight: 700;
    margin-top: 25px;
}

.result-box {
    padding: 18px;
    border-radius: 12px;
    background-color: #f5f7fa;
    margin-top: 10px;
}

.win {
    color: #008000;
    font-weight: 800;
}

.draw {
    color: #0066cc;
    font-weight: 800;
}

.lose {
    color: #cc0000;
    font-weight: 800;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 리그
# =========================================================

LEAGUES = {

    "잉글랜드 1부 EPL": {
        "country": "England",
        "code": "E0",
        "division": 1
    },

    "잉글랜드 2부 Championship": {
        "country": "England",
        "code": "E1",
        "division": 2
    },

    "잉글랜드 3부 League One": {
        "country": "England",
        "code": "E2",
        "division": 3
    },

    "잉글랜드 4부 League Two": {
        "country": "England",
        "code": "E3",
        "division": 4
    },

    "독일 1부 Bundesliga": {
        "country": "Germany",
        "code": "D1",
        "division": 1
    },

    "독일 2부 Bundesliga 2": {
        "country": "Germany",
        "code": "D2",
        "division": 2
    },

    "이탈리아 1부 Serie A": {
        "country": "Italy",
        "code": "I1",
        "division": 1
    },

    "이탈리아 2부 Serie B": {
        "country": "Italy",
        "code": "I2",
        "division": 2
    },

    "스페인 1부 La Liga": {
        "country": "Spain",
        "code": "SP1",
        "division": 1
    },

    "스페인 2부 Segunda": {
        "country": "Spain",
        "code": "SP2",
        "division": 2
    },

    "프랑스 1부 Ligue 1": {
        "country": "France",
        "code": "F1",
        "division": 1
    },

    "프랑스 2부 Ligue 2": {
        "country": "France",
        "code": "F2",
        "division": 2
    },

    "네덜란드 1부 Eredivisie": {
        "country": "Netherlands",
        "code": "N1",
        "division": 1
    },

    "네덜란드 2부 Eerste": {
        "country": "Netherlands",
        "code": "N2",
        "division": 2
    },

    "포르투갈 1부": {
        "country": "Portugal",
        "code": "P1",
        "division": 1
    },

    "벨기에 1부": {
        "country": "Belgium",
        "code": "B1",
        "division": 1
    },

    "스코틀랜드 1부 Premiership": {
        "country": "Scotland",
        "code": "SC0",
        "division": 1
    },

    "스코틀랜드 2부 Championship": {
        "country": "Scotland",
        "code": "SC1",
        "division": 2
    },

    "스코틀랜드 3부 League One": {
        "country": "Scotland",
        "code": "SC2",
        "division": 3
    },

    "스코틀랜드 4부 League Two": {
        "country": "Scotland",
        "code": "SC3",
        "division": 4
    },

    "터키 1부": {
        "country": "Turkey",
        "code": "T1",
        "division": 1
    },

    "그리스 1부": {
        "country": "Greece",
        "code": "G1",
        "division": 1
    }
}


# =========================================================
# 시즌
# =========================================================

SEASONS = {
    "2025/26": "2526",
    "2024/25": "2425",
    "2023/24": "2324",
    "2022/23": "2223",
    "2021/22": "2122"
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

        date TEXT,
        home_team TEXT,
        away_team TEXT,

        result TEXT,

        b365_home REAL,
        b365_draw REAL,
        b365_away REAL,

        pinnacle_home REAL,
        pinnacle_draw REAL,
        pinnacle_away REAL,

        william_home REAL,
        william_draw REAL,
        william_away REAL,

        created_at TEXT,

        UNIQUE(
            league,
            season,
            date,
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

@st.cache_data(ttl=1800)
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

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code != 200:
            return None

        response.encoding = "latin1"

        return pd.read_csv(
            StringIO(response.text)
        )

    except Exception:

        return None


# =========================================================
# 컬럼 찾기
# =========================================================

def find_column(
    df,
    names
):

    for name in names:

        if name in df.columns:
            return name

    return None


# =========================================================
# 배당 컬럼
# =========================================================

def get_odds_columns(df):

    return {

        # Bet365
        "b365_home": find_column(
            df,
            ["B365CH", "B365H"]
        ),

        "b365_draw": find_column(
            df,
            ["B365CD", "B365D"]
        ),

        "b365_away": find_column(
            df,
            ["B365CA", "B365A"]
        ),

        # Pinnacle
        "pinnacle_home": find_column(
            df,
            ["PSCH", "PSH"]
        ),

        "pinnacle_draw": find_column(
            df,
            ["PSCD", "PSD"]
      
