# ============================================================
# SPORTS ANALYZER PRO - FINAL
# ============================================================
# 무료 공개 스포츠 데이터 분석 프로그램
#
# 주요 기능
# ------------------------------------------------------------
# 1. 공개 데이터 수집
# 2. 사이트별 독립 수집
# 3. 자동 재시도
# 4. Timeout 처리
# 5. Connection 오류 처리
# 6. 부분 저장
# 7. 중복 경기 제거
# 8. 경기 결과 저장
# 9. 배당 저장
# 10. 승/무/패 확률
# 11. No-Vig 확률
# 12. EV 계산
# 13. 배당구간 분석
# 14. 백테스트
# 15. ROI
# 16. 최대 낙폭
# 17. 연속 적중/실패
# 18. 종목별 분석
# 19. 리그별 분석
# 20. 연도별 분석
# 21. 데이터 출처별 로그
# 22. CSV Import
# 23. CSV Export
# 24. 오류가 나도 전체 프로그램 계속 실행
#
# 실행
# ------------------------------------------------------------
# pip install -r requirements.txt
# streamlit run app.py
# ============================================================

import sqlite3
import json
import time
import math
import hashlib
import traceback
from pathlib import Path
from datetime import datetime, timezone

import requests
import pandas as pd
import numpy as np
import streamlit as st


# ============================================================
# 기본 설정
# ============================================================

APP_NAME = "Sports Analyzer PRO"

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = DATA_DIR / "export"
IMPORT_DIR = DATA_DIR / "import"

DB_PATH = DATA_DIR / "sports.db"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

IMPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 공개 데이터 주소
# ============================================================

SPORTSCORE_BASE = (
    "https://sportscore.com"
)

SPORTSCORE_MATCH_URL = (
    SPORTSCORE_BASE
    + "/api/widget/matches/"
)

ONEML_ODDS_URL = (
    "https://1.ml/api/v1/odds"
)

SPORTSRC_BASE = (
    "https://api.sportsrc.org/"
)


# ============================================================
# 수집 설정
# ============================================================

REQUEST_TIMEOUT = 15

MAX_RETRY = 3

RETRY_DELAY = 2

SPORTS = [
    "football",
    "basketball",
    "cricket",
    "tennis",
]


USER_AGENT = (
    "SportsAnalyzerPRO/1.0 "
    "public-data-client"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


# ============================================================
# Streamlit
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🏆",
    layout="wide",
)


# ============================================================
# 시간
# ============================================================

def now_utc():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# 안전 문자열
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, float):

        if np.isnan(value):
            return ""

    return str(value).strip()


# ============================================================
# 안전 숫자
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        if isinstance(value, str):

            value = (
                value
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except Exception:

        return None


# ============================================================
# DB
# ============================================================

def get_connection():

    return sqlite3.connect(
        DB_PATH,
        timeout=30,
    )


def init_database():

    con = get_connection()

    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_key TEXT UNIQUE,

            source TEXT,

            sport TEXT,

            league TEXT,

            country TEXT,

            match_date TEXT,

            home_team TEXT,

            away_team TEXT,

            home_score REAL,

            away_score REAL,

            status TEXT,

            result TEXT,

            home_odds REAL,

            draw_odds REAL,

            away_odds REAL,

            over25_odds REAL,

            under25_odds REAL,

            odds_source TEXT,

            odds_updated TEXT,

            raw_json TEXT,

            created_at TEXT,

            updated_at TEXT

        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_match_date
        ON matches(match_date)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_match_sport
        ON matches(sport)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_match_teams
        ON matches(
            home_team,
            away_team
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS source_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source TEXT,

            success INTEGER,

            rows INTEGER,

            attempt INTEGER,

            message TEXT,

            created_at TEXT

        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS odds_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_key TEXT,

            bookmaker TEXT,

            home_odds REAL,

            draw_odds REAL,

            away_odds REAL,

            captured_at TEXT

        )
    """)

    con.commit()

    con.close()


init_database()


# ============================================================
# 로그
# ============================================================

def write_log(
    source,
    success,
    rows=0,
    attempt=0,
    message="",
):

    try:

        con = get_connection()

        con.execute("""
            INSERT INTO source_log
            (
                source,
                success,
                rows,
                attempt,
                message,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            source,
            1 if success else 0,
            int(rows),
            int(attempt),
            clean_text(message)[:2000],
            now_utc(),
        ))

        con.commit()

        con.close()

    except Exception:

        pass


# ============================================================
# HTTP GET
# ============================================================

def request_json(
    url,
    params=None,
    source="unknown",
):

    last_error = ""

    for attempt in range(
        1,
        MAX_RETRY + 1
    ):

        try:

            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:

                last_error = (
                    "HTTP 429 - rate limited"
                )

                time.sleep(
                    RETRY_DELAY * attempt
                )

                continue

            if response.status_code in (
                403,
                401,
            ):

                last_error = (
                    f"HTTP {response.status_code}"
                )

                write_log(
                    source,
                    False,
                    0,
                    attempt,
                    last_error,
                )

                return None

            response.raise_for_status()

            try:

                data = response.json()

            except Exception:

                last_error = (
                    "응답이 JSON 형식이 아님"
                )

                write_log(
                    source,
                    False,
                    0,
                    attempt,
                    last_error,
                )

                continue

            write_log(
                source,
                True,
                1,
                attempt,
                "success",
            )

            return data

        except requests.exceptions.Timeout as e:

            last_error = (
                f"Timeout: {e}"
            )

        except requests.exceptions.ConnectionError as e:

            last_error = (
                f"ConnectionError: {e}"
            )

        except requests.exceptions.RequestException as e:

            last_error = (
                f"RequestException: {e}"
            )

        except Exception as e:

            last_error = (
                f"UnknownError: {e}"
            )

        write_log(
            source,
            False,
            0,
            attempt,
            last_error,
        )

        time.sleep(
            RETRY_DELAY * attempt
        )

    return None


# ============================================================
# 정규화
# ============================================================

def normalize_team(value):

    value = clean_text(
        value
    ).lower()

    chars = []

    for char in value:

        if char.isalnum():

            chars.append(char)

    return "".join(chars)


def make_event_key(
    sport,
    date,
    home,
    away,
):

    raw = "|".join([
        normalize_team(sport),
        clean_text(date)[:16],
        normalize_team(home),
        normalize_team(away),
    ])

    return hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# 딕셔너리 검색
# ============================================================

def get_value(
    data,
    keys,
):

    if not isinstance(
        data,
        dict
    ):

        return None

    lower = {
        str(k).lower(): v
        for k, v in data.items()
    }

    for key in keys:

        if key in data:

            return data[key]

        key_lower = key.lower()

        if key_lower in lower:

            return lower[key_lower]

    return None


# ============================================================
# 리스트 검색
# ============================================================

def find_list(data):

    if isinstance(
        data,
        list
    ):

        return data

    if not isinstance(
        data,
        dict
    ):

        return []

    possible = [
        "matches",
        "games",
        "events",
        "data",
        "results",
        "fixtures",
        "items",
    ]

    for key in possible:

        value = get_value(
            data,
            [key]
        )

        if isinstance(
            value,
            list
        ):

            return value

    for value in data.values():

        if isinstance(
            value,
            list
        ):

            return value

    return []


# ============================================================
# SportScore
# ============================================================

def fetch_sportscore(
    sport,
    limit=100,
):

    source = (
        f"SportScore/{sport}"
    )

    data = request_json(
        SPORTSCORE_MATCH_URL,
        params={
            "sport": sport,
            "limit": limit,
        },
        source=source,
    )

    if data is None:

        return []

    rows = find_list(
        data
    )

    output = []

    for item in rows:

        try:

            if not isinstance(
                item,
                dict
            ):

                continue

            home = get_value(
                item,
                [
                    "home",
                    "homeTeam",
                    "home_team",
                ],
            )

            away = get_value(
                item,
                [
                    "away",
                    "awayTeam",
                    "away_team",
                ],
            )

            if isinstance(
                home,
                dict
            ):

                home = get_value(
                    home,
                    [
                        "name",
                        "title",
                    ],
                )

            if isinstance(
                away,
                dict
            ):

                away = get_value(
                    away,
                    [
                        "name",
                        "title",
                    ],
                )

            home = clean_text(
                home
            )

            away = clean_text(
                away
            )

            if not home or not away:

                continue

            date = get_value(
                item,
                [
                    "startTime",
                    "start_time",
                    "commence_time",
                    "date",
                    "start",
                ],
            )

            league = get_value(
                item,
                [
                    "competition",
                    "league",
                    "tournament",
                ],
            )

            if isinstance(
                league,
                dict
            ):

                league = get_value(
                    league,
                    [
                        "name",
                        "title",
                    ],
                )

            hs = get_value(
                item,
                [
                    "homeScore",
                    "home_score",
                ],
            )

            aws = get_value(
                item,
                [
                    "awayScore",
                    "away_score",
                ],
            )

            if isinstance(
                hs,
                dict
            ):

                hs = get_value(
                    hs,
                    [
                        "current",
                        "score",
                        "value",
                    ],
                )

            if isinstance(
                aws,
                dict
            ):

                aws = get_value(
                    aws,
                    [
                        "current",
                        "score",
                        "value",
                    ],
                )

            output.append({

                "source":
                    "SportScore",

                "sport":
                    sport,

                "league":
                    clean_text(
                        league
                    ),

                "country":
                    "",

                "match_date":
                    clean_text(
                        date
                    ),

                "home_team":
                    home,

                "away_team":
                    away,

                "home_score":
                    safe_float(hs),

                "away_score":
                    safe_float(aws),

                "status":
                    clean_text(
                        get_value(
                            item,
                            [
                                "status",
                                "state",
                            ],
                        )
                    ),

                "raw_json":
                    json.dumps(
                        item,
                        ensure_ascii=False,
                        default=str,
                    ),

            })

        except Exception as e:

            write_log(
                source,
                False,
                0,
                0,
                f"item error: {e}",
            )

            continue

    write_log(
        source,
        True,
        len(output),
        0,
        "parsed",
    )

    return output


# ============================================================
# SportSRC
# ============================================================

def fetch_sportsrc(
    sport,
):

    source = (
        f"SportSRC/{sport}"
    )

    data = request_json(
        SPORTSRC_BASE,
        params={
            "data": "matches",
            "category": sport,
        },
        source=source,
    )

    if data is None:

        return []

    rows = find_list(
        data
    )

    output = []

    for item in rows:

        try:

            if not isinstance(
                item,
                dict
            ):

                continue

            home = get_value(
                item,
                [
                    "home",
                    "homeTeam",
                    "home_team",
                    "team1",
                ],
            )

            away = get_value(
                item,
                [
                    "away",
                    "awayTeam",
                    "away_team",
                    "team2",
                ],
            )

            if isinstance(
                home,
                dict
            ):

                home = get_value(
                    home,
                    [
                        "name",
                        "title",
                    ],
                )

            if isinstance(
                away,
                dict
            ):

                away = get_value(
                    away,
                    [
                        "name",
                        "title",
                    ],
                )

            home = clean_text(
                home
            )

            away = clean_text(
                away
            )

            if not home or not away:

                continue

            date = get_value(
                item,
                [
                    "date",
                    "startTime",
                    "start_time",
                    "timestamp",
                ],
            )

            output.append({

                "source":
                    "SportSRC",

                "sport":
                    sport,

                "league":
                    clean_text(
                        get_value(
                            item,
                            [
                                "league",
                                "competition",
                            ],
                        )
                    ),

                "country":
                    "",

                "match_date":
                    clean_text(date),

                "home_team":
                    home,

                "away_team":
                    away,

                "home_score":
                    safe_float(
                        get_value(
                            item,
                            [
                                "homeScore",
                                "home_score",
                            ],
                        )
                    ),

                "away_score":
                    safe_float(
                        get_value(
                            item,
                            [
                                "awayScore",
                                "away_score",
                            ],
                        )
                    ),

                "status":
                    clean_text(
                        get_value(
                            item,
                            [
                                "status",
                                "state",
                            ],
                        )
                    ),

                "raw_json":
                    json.dumps(
                        item,
                        ensure_ascii=False,
                        default=str,
                    ),

            })

        except Exception as e:

            write_log(
                source,
                False,
                0,
                0,
                f"item error: {e}",
            )

            continue

    write_log(
        source,
        True,
        len(output),
        0,
        "parsed",
    )

    return output


# ============================================================
# 결과
# ============================================================

def calculate_result(
    home_score,
    away_score,
):

    h = safe_float(
        home_score
    )

    a = safe_float(
        away_score
    )

    if h is None or a is None:

        return None

    if h > a:
        return "H"

    if h < a:
        return "A"

    return "D"


# ============================================================
# 안전한 경기 저장
# ============================================================

def save_match(
    match
):

    try:

        sport = clean_text(
            match.get("sport")
        )

        date = clean_text(
            match.get("match_date")
        )

        home = clean_text(
            match.get("home_team")
        )

        away = clean_text(
            match.get("away_team")
        )

        if not home or not away:

            return False

        key = make_event_key(
            sport,
            date,
            home,
            away,
        )

        result = match.get(
            "result"
        )

        if not result:

            result = calculate_result(
                match.get(
                    "home_score"
                ),
                match.get(
                    "away_score"
                ),
            )

        con = get_connection()

        existing = con.execute(
            """
            SELECT id
            FROM matches
            WHERE event_key=?
            """,
            (key,),
        ).fetchone()

        values = (

            match.get(
                "source",
                ""
            ),

            sport,

            match.get(
                "league",
                ""
            ),

            match.get(
                "country",
                ""
            ),

            date,

            home,

            away,

            safe_float(
                match.get(
                    "home_score"
                )
            ),

            safe_float(
                match.get(
                    "away_score"
                )
            ),

            match.get(
                "status",
                ""
            ),

            result,

            safe_float(
                match.get(
                    "home_odds"
                )
            ),

            safe_float(
                match.get(
                    "draw_odds"
                )
            ),

            safe_float(
                match.get(
                    "away_odds"
                )
            ),

            safe_float(
                match.get(
                    "over25_odds"
                )
            ),

            safe_float(
                match.get(
                    "under25_odds"
                )
            ),

            match.get(
                "odds_source",
                ""
            ),

            match.get(
                "odds_updated",
                ""
            ),

            match.get(
                "raw_json",
                ""
            ),

            now_utc(),

            now_utc(),

        )

        if existing:

            con.execute(
                """
                UPDATE matches
                SET
                    source=?,
                    sport=?,
                    league=?,
                    country=?,
                    match_date=?,
                    home_team=?,
                    away_team=?,
                    home_score=
                        COALESCE(
                            ?,
                            home_score
                        ),
                    away_score=
                        COALESCE(
                            ?,
                            away_score
                        ),
                    status=?,
                    result=
                        COALESCE(
                            ?,
                            result
                        ),
                    home_odds=
                        COALESCE(
                            ?,
                            home_odds
                        ),
                    draw_odds=
                        COALESCE(
                            ?,
                            draw_odds
                        ),
                    away_odds=
                        COALESCE(
                            ?,
                            away_odds
                        ),
                    over25_odds=
                        COALESCE(
                            ?,
                            over25_odds
                        ),
                    under25_odds=
                        COALESCE(
                            ?,
                            under25_odds
                        ),
                    odds_source=?,
                    odds_updated=?,
                    raw_json=?,
                    updated_at=?
                WHERE event_key=?
                """,
                values + (
                    key,
                ),
            )

        else:

            con.execute(
                """
                INSERT INTO matches
                (
                    event_key,
                    source,
                    sport,
                    league,
                    country,
                    match_date,
                    home_team,
                    away_team,
                    home_score,
                    away_score,
                    status,
                    result,
                    home_odds,
                    draw_odds,
                    away_odds,
                    over25_odds,
                    under25_odds,
                    odds_source,
                    odds_updated,
                    raw_json,
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
                    key,
                ) + values,
            )

        con.commit()

        con.close()

        return True

    except Exception as e:

        write_log(
            "DATABASE",
            False,
            0,
            0,
            traceback.format_exc(),
        )

        return False


# ============================================================
# 안전 수집
# ============================================================

def safe_collect(
    function,
    *args,
    source_name="unknown",
    **kwargs,
):

    try:

        rows = function(
            *args,
            **kwargs
        )

        if rows is None:

            return []

        return rows

    except Exception:

        write_log(
            source_name,
            False,
            0,
            0,
            traceback.format_exc(),
        )

        return []


# ============================================================
# 전체 수집
# ============================================================

def collect_all(
    selected_sports
):

    total = 0

    errors = []

    progress = st.progress(
        0
    )

    total_steps = (
        len(selected_sports) * 2
    )

    current_step = 0

    for sport in selected_sports:

        # ----------------------------------------------------
        # SportScore
        # ----------------------------------------------------

        rows = safe_collect(
            fetch_sportscore,
            sport,
            100,
            source_name=
            f"SportScore/{sport}",
        )

        for row in rows:

            try:

                row["result"] = (
                    calculate_result(
                        row.get(
                            "home_score"
                        ),
                        row.get(
                            "away_score"
                        ),
                    )
                )

                if save_match(row):

                    total += 1

            except Exception as e:

                errors.append(
                    str(e)
                )

                write_log(
                    f"SportScore/{sport}",
                    False,
                    0,
                    0,
                    str(e),
                )

                continue

        current_step += 1

        progress.progress(
            min(
                current_step
                /
                max(
                    total_steps,
                    1
                ),
                1.0,
            )
        )

        # ----------------------------------------------------
        # SportSRC
        # ----------------------------------------------------

        rows = safe_collect(
            fetch_sportsrc,
            sport,
            source_name=
            f"SportSRC/{sport}",
        )

        for row in rows:

            try:

                row["result"] = (
                    calculate_result(
                        row.get(
                            "home_score"
                        ),
                        row.get(
                            "away_score"
                        ),
                    )
                )

                if save_match(row):

                    total += 1

            except Exception as e:

                errors.append(
                    str(e)
                )

                continue

        current_step += 1

        progress.progress(
            min(
                current_step
                /
                max(
                    total_steps,
                    1
                ),
                1.0,
            )
        )

    progress.empty()

    return total, errors


# ============================================================
# DB 읽기
# ============================================================

def load_matches():

    try:

        con = get_connection()

        df = pd.read_sql_query(
            """
            SELECT *
            FROM matches
            ORDER BY match_date
            """,
            con,
        )

        con.close()

    except Exception:

        return pd.DataFrame()

    if df.empty:

        return df

    df["match_date"] = pd.to_datetime(
        df["match_date"],
        errors="coerce",
    )

    df["result"] = df.apply(
        lambda row:
        row["result"]
        if clean_text(
            row["result"]
        )
        else calculate_result(
            row["home_score"],
            row["away_score"],
        ),
        axis=1,
    )

    return df


# ============================================================
# No-Vig
# ============================================================

def no_vig_probability(
    home,
    draw,
    away,
):

    values = [
        safe_float(home),
        safe_float(draw),
        safe_float(away),
    ]

    inv = []

    for value in values:

        if (
            value is None
            or value <= 1
        ):

            inv.append(0)

        else:

            inv.append(
                1 / value
            )

    total = sum(inv)

    if total <= 0:

        return [
            0,
            0,
            0
        ]

    return [
        x / total
        for x in inv
    ]


# ============================================================
# EV
# ============================================================

def calculate_ev(
    probability,
    odds,
):

    p = safe_float(
        probability
    )

    o = safe_float(
        odds
    )

    if (
        p is None
        or o is None
        or o <= 1
    ):

        return None

    return (
        p * o
    ) - 1


# ============================================================
# 배당구간
# ============================================================

def odds_bucket(
    odds
):

    value = safe_float(
        odds
    )

    if value is None:

        return "N/A"

    if value < 1.30:

        return "1.01~1.29"

    if value < 1.40:

        return "1.30~1.39"

    if value < 1.50:

        return "1.40~1.49"

    if value < 1.60:

        return "1.50~1.59"

    if value < 1.70:

        return "1.60~1.69"

    if value < 1.80:

        return "1.70~1.79"

    if value < 2.00:

        return "1.80~1.99"

    if value < 2.50:

        return "2.00~2.49"

    return "2.50+"


# ============================================================
# 백테스트
# ============================================================

def run_backtest(
    df,
    min_odds,
    max_odds,
    min_probability,
):

    if df.empty:

        return pd.DataFrame()

    data = df.copy()

    data = data[
        data["home_odds"].notna()
        &
        data["draw_odds"].notna()
        &
        data["away_odds"].notna()
    ]

    data = data[
        data["result"].isin(
            [
                "H",
                "D",
                "A",
            ]
        )
    ]

    rows = []

    for _, row in data.iterrows():

        probs = no_vig_probability(
            row["home_odds"],
            row["draw_odds"],
            row["away_odds"],
        )

        labels = [
            "H",
            "D",
            "A",
        ]

        odds = [
            row["home_odds"],
            row["draw_odds"],
            row["away_odds"],
        ]

        index = int(
            np.argmax(
                probs
            )
        )

        prediction = (
            labels[index]
        )

        probability = (
            probs[index]
        )

        selected_odds = safe_float(
            odds[index]
        )

        if selected_odds is None:

            continue

        if not (
            min_odds
            <= selected_odds
            <= max_odds
        ):

            continue

        if (
            probability
            <
            min_probability
        ):

            continue

        hit = (
            prediction
            ==
            row["result"]
        )

        profit = (
            selected_odds - 1
            if hit
            else -1
        )

        ev = calculate_ev(
            probability,
            selected_odds,
        )

        rows.append({

            "date":
                row["match_date"],

            "sport":
                row["sport"],

            "league":
                row["league"],

            "home":
                row["home_team"],

            "away":
                row["away_team"],

            "prediction":
                prediction,

            "probability":
                probability,

            "odds":
                selected_odds,

            "EV":
                ev,

            "result":
                row["result"],

            "hit":
                hit,

            "profit":
                profit,

        })

    result = pd.DataFrame(
        rows
    )

    if result.empty:

        return result

    result = result.sort_values(
        "date"
    )

    result["cum_profit"] = (
        result["profit"]
        .cumsum()
    )

    result["peak"] = (
        result["cum_profit"]
        .cummax()
    )

    result["drawdown"] = (
        result["cum_profit"]
        -
        result["peak"]
    )

    result["ROI"] = (
        result["cum_profit"]
        /
        np.arange(
            1,
            len(result) + 1
        )
        *
        100
    )

    return result


# ============================================================
# 통계
# ============================================================

def calculate_metrics(
    data
):

    if data.empty:

        return {

            "games": 0,
            "hits": 0,
            "hit_rate": 0,
            "profit": 0,
            "roi": 0,
            "max_drawdown": 0,
            "avg_odds": 0,
            "avg_ev": 0,

        }

    games = len(data)

    hits = int(
        data["hit"].sum()
    )

    profit = float(
        data["profit"].sum()
    )

    roi = (
        profit
        /
        games
        *
        100
    )

    max_drawdown = abs(
        float(
            data["drawdown"].min()
        )
    )

    return {

        "games":
            games,

        "hits":
            hits,

        "hit_rate":
            hits
            /
            games
            *
            100,

        "profit":
            profit,

        "roi":
            roi,

        "max_drawdown":
            max_drawdown,

        "avg_odds":
            float(
                data["odds"].mean()
            ),

        "avg_ev":
            float(
                data["EV"].mean()
            ),

    }


# ============================================================
# 연속 적중 / 실패
# ============================================================

def streak_stats(
    data
):

    if data.empty:

        return 0, 0

    current_win = 0
    current_loss = 0

    max_win = 0
    max_loss = 0

    for hit in data["hit"]:

        if hit:

            current_win += 1
            current_loss = 0

        else:

            current_loss += 1
            current_win = 0

        max_win = max(
            max_win,
            current_win,
        )

        max_loss = max(
            max_loss,
            current_loss,
        )

    return (
        max_win,
        max_loss,
    )


# ============================================================
# 연도분리
# ============================================================

def split_periods(
    df
):

    if df.empty:

        return (
            df,
            df,
            df,
        )

    temp = df.copy()

    temp["year"] = (
        pd.to_datetime(
            temp["match_date"],
            errors="coerce",
        )
        .dt.year
    )

    train = temp[
        temp["year"] <= 2024
    ]

    validation = temp[
        temp["year"] == 2025
    ]

    test = temp[
        temp["year"] >= 2026
    ]

    return (
        train,
        validation,
        test,
    )


# ============================================================
# CSV Import
# ============================================================

COLUMN_MAP = {

    "Date":
        "match_date",

    "date":
        "match_date",

    "HomeTeam":
        "home_team",

    "home":
        "home_team",

    "home_team":
        "home_team",

    "AwayTeam":
        "away_team",

    "away":
        "away_team",

    "away_team":
        "away_team",

    "FTHG":
        "home_score",

    "FTAG":
        "away_score",

    "FTR":
        "result",

    "B365H":
        "home_odds",

    "B365D":
        "draw_odds",

    "B365A":
        "away_odds",

    "AvgH":
        "home_odds",

    "AvgD":
        "draw_odds",

    "AvgA":
        "away_odds",

}


def import_csv(
    uploaded_file
):

    try:

        try:

            df = pd.read_csv(
                uploaded_file,
                encoding="utf-8",
            )

        except Exception:

            uploaded_file.seek(
                0
            )

            df = pd.read_csv(
                uploaded_file,
                encoding="cp949",
            )

        rename = {}

        for col in df.columns:

            if col in COLUMN_MAP:

                rename[col] = (
                    COLUMN_MAP[col]
                )

        df = df.rename(
            columns=rename
        )

        required = [
            "match_date",
            "home_team",
            "away_team",
        ]

        for col in required:

            if col not in df.columns:

                df[col] = ""

        numeric_cols = [

            "home_score",
            "away_score",
            "home_odds",
            "draw_odds",
            "away_odds",
            "over25_odds",
            "under25_odds",

        ]

        for col in numeric_cols:

            if col not in df.columns:

                df[col] = np.nan

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

        count = 0

        for _, row in df.iterrows():

            home = clean_text(
                row[
                    "home_team"
                ]
            )

            away = clean_text(
                row[
                    "away_team"
                ]
            )

            if not home or not away:

                continue

            match = {

                "source":
                    "CSV",

                "sport":
                    "Football",

                "league":
                    "",

                "country":
                    "",

                "match_date":
                    str(
                        row[
                            "match_date"
                        ]
                    ),

                "home_team":
                    home,

                "away_team":
                    away,

                "home_score":
                    safe_float(
                        row[
                            "home_score"
                        ]
                    ),

                "away_score":
                    safe_float(
                        row[
                            "away_score"
                        ]
                    ),

                "status":
                    "finished",

                "result":
                    clean_text(
                        row.get(
                            "result",
                            ""
                        )
                    ),

                "home_odds":
                    safe_float(
                        row[
                            "home_odds"
                        ]
                    ),

                "draw_odds":
                    safe_float(
                        row[
                            "draw_odds"
                        ]
                    ),

                "away_odds":
                    safe_float(
                        row[
                            "away_odds"
                        ]
                    ),

                "over25_odds":
                    safe_float(
                        row[
                            "over25_odds"
                        ]
                    ),

                "under25_odds":
                    safe_float(
                        row[
                            "under25_odds"
                        ]
                    ),

            }

            if save_match(
                match
            ):

                count += 1

        return count, None

    except Exception as e:

        return (
            0,
            traceback.format_exc()
        )


# ============================================================
# UI Sidebar
# ============================================================

st.sidebar.title(
    "⚙️ 설정"
)

st.sidebar.info(
    "API 키 입력 없이 공개 데이터만 사용"
)

selected_sports = (
    st.sidebar.multiselect(
        "수집 종목",
        SPORTS,
        default=SPORTS,
    )
)


# ============================================================
# 수집 버튼
# ============================================================

st.sidebar.divider()

if st.sidebar.button(
    "🔄 전체 데이터 수집",
    use_container_width=True,
):

    with st.spinner(
        "데이터를 안전하게 수집하는 중..."
    ):

        total, errors = (
            collect_all(
                selected_sports
            )
        )

    if errors:

        st.sidebar.warning(
            f"{total:,}건 저장 / "
            f"{len(errors)}건 오류"
        )

    else:

        st.sidebar.success(
            f"{total:,}건 처리 완료"
        )

    st.rerun()


# ============================================================
# CSV
# ============================================================

st.sidebar.divider()

st.sidebar.subheader(
    "📂 과거 경기 데이터"
)

uploaded_files = (
    st.sidebar.file_uploader(
        "CSV 업로드",
        type=["csv"],
        accept_multiple_files=True,
    )
)

if uploaded_files:

    for file in uploaded_files:

        count, error = (
            import_csv(file)
        )

        if error:

            st.sidebar.error(
                f"{file.name} 오류"
            )

        else:

            st.sidebar.success(
                f"{file.name}: "
                f"{count:,}건"
            )


# ============================================================
# 분석 설정
# ============================================================

st.sidebar.divider()

st.sidebar.subheader(
    "📊 분석 조건"
)

min_odds = (
    st.sidebar.number_input(
        "최소 배당",
        min_value=1.01,
        max_value=20.0,
        value=1.40,
        step=0.01,
    )
)

max_odds = (
    st.sidebar.number_input(
        "최대 배당",
        min_value=1.02,
        max_value=50.0,
        value=2.50,
        step=0.01,
    )
)

min_probability = (
    st.sidebar.slider(
        "최소 확률",
        0.30,
        0.90,
        0.55,
        0.01,
    )
)

min_ev = (
    st.sidebar.slider(
        "최소 EV",
        -0.20,
        0.30,
        0.03,
        0.01,
    )
)

min_sample = (
    st.sidebar.number_input(
        "최소 표본",
        min_value=10,
        max_value=100000,
        value=300,
        step=10,
    )
)


# ============================================================
# 데이터
# ============================================================

df = load_matches()


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏆 SPORTS ANALYZER PRO"
)

st.caption(
    "무료 공개 스포츠 데이터 · "
    "배당 · 결과 · EV · ROI · 백테스트"
)


# ============================================================
# 기본 지표
# ============================================================

if df.empty:

    st.warning(
        "데이터가 없습니다. "
        "왼쪽에서 데이터를 수집하거나 "
        "CSV를 업로드하세요."
    )

else:

    c1, c2, c3, c4, c5 = (
        st.columns(5)
    )

    c1.metric(
        "전체 경기",
        f"{len(df):,}",
    )

    c2.metric(
        "종목",
        df[
            "sport"
        ].nunique(),
    )

    c3.metric(
        "리그",
        df[
            "league"
        ]
        .replace(
            "",
            np.nan
        )
        .nunique(),
    )

    c4.metric(
        "결과",
        f"{df['result'].notna().sum():,}",
    )

    c5.metric(
        "배당",
        f"{df['home_odds'].notna().sum():,}",
    )


# ============================================================
# TAB
# ============================================================

tabs = st.tabs([
    "🔥 경기분석",
    "📊 백테스트",
    "💰 ROI",
    "📈 배당통계",
    "🏆 종목/리그",
    "🗄️ 데이터",
    "⚙️ 수집상태",
])


# ============================================================
# TAB 1
# ============================================================

with tabs[0]:

    st.subheader(
        "🔥 VALUE 경기"
    )

    if df.empty:

        st.info(
            "데이터가 없습니다."
        )

    else:

        work = df.copy()

        work = work[
            work[
                "home_odds"
            ].notna()
            &
            work[
                "draw_odds"
            ].notna()
            &
            work[
                "away_odds"
            ].notna()
        ]

        rows = []

        for _, row in work.iterrows():

            probs = (
                no_vig_probability(
                    row[
                        "home_odds"
                    ],
                    row[
                        "draw_odds"
                    ],
                    row[
                        "away_odds"
                    ],
                )
            )

            labels = [
                "홈승",
                "무",
                "원정승",
            ]

            odds = [
                row[
                    "home_odds"
                ],
                row[
                    "draw_odds"
                ],
                row[
                    "away_odds"
                ],
            ]

            index = int(
                np.argmax(
                    probs
                )
            )

            probability = (
                probs[index]
            )

            selected_odds = (
                safe_float(
                    odds[index]
                )
            )

            ev = calculate_ev(
                probability,
                selected_odds,
            )

            rows.append({

                "시간":
                    row[
                        "match_date"
                    ],

                "종목":
                    row[
                        "sport"
                    ],

                "리그":
                    row[
                        "league"
                    ],

                "경기":
                    (
                        f"{row['home_team']}"
                        f" vs "
                        f"{row['away_team']}"
                    ),

                "추천":
                    labels[index],

                "확률":
                    probability,

                "배당":
                    selected_odds,

                "EV":
                    ev,

            })

        analysis = pd.DataFrame(
            rows
        )

        if not analysis.empty:

            analysis = analysis[
                analysis[
                    "EV"
                ].notna()
            ]

            analysis = analysis[
                analysis[
                    "EV"
                ]
                >= min_ev
            ]

            analysis = (
                analysis
                .sort_values(
                    [
                        "EV",
                        "확률",
                    ],
                    ascending=False,
                )
                .head(100)
            )

            if not analysis.empty:

                analysis["판정"] = (
                    np.where(
                        analysis[
                            "EV"
                        ] >= 0.10,
                        "🔥 강한 VALUE",
                        np.where(
                            analysis[
                                "EV"
                            ] >= 0.03,
                            "🟢 VALUE",
                            "⚪ 일반",
                        ),
                    )
                )

                st.dataframe(
                    analysis.style.format({
                        "확률":
                            "{:.2%}",
                        "배당":
                            "{:.2f}",
                        "EV":
                            "{:+.2%}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "현재 조건을 만족하는 경기가 없습니다."
                )


# ============================================================
# TAB 2
# ============================================================

with tabs[1]:

    st.subheader(
        "📊 백테스트"
    )

    bt = run_backtest(
        df,
        min_odds,
        max_odds,
        min_probability,
    )

    if bt.empty:

        st.info(
            "백테스트 가능한 데이터가 없습니다."
        )

    else:

        m = calculate_metrics(
            bt
        )

        c1, c2, c3, c4, c5, c6 = (
            st.columns(6)
        )

        c1.metric(
            "경기",
            f"{m['games']:,}"
        )

        c2.metric(
            "적중률",
            f"{m['hit_rate']:.2f}%"
        )

        c3.metric(
            "ROI",
            f"{m['roi']:+.2f}%"
        )

        c4.metric(
            "수익",
            f"{m['profit']:+.2f}u"
        )

        c5.metric(
            "평균배당",
            f"{m['avg_odds']:.2f}"
        )

        c6.metric(
            "최대낙폭",
            f"{m['max_drawdown']:.2f}u"
        )

        if (
            m["games"]
            >= min_sample
            and m["roi"] > 0
        ):

            st.success(
                "🟢 백테스트 양의 ROI"
            )

        elif (
            m["games"]
            < min_sample
        ):

            st.warning(
                "⚠️ 표본 부족"
            )

        else:

            st.error(
                "🔴 현재 조건 ROI 음수"
            )

        st.subheader(
            "누적 수익"
        )

        chart = bt[
            [
                "date",
                "cum_profit",
            ]
        ].copy()

        chart = chart.set_index(
            "date"
        )

        st.line_chart(
            chart
        )

        win_streak, loss_streak = (
            streak_stats(bt)
        )

        st.write(
            f"최대 연속 적중: "
            f"**{win_streak}회**"
        )

        st.write(
            f"최대 연속 실패: "
            f"**{loss_streak}회**"
        )


# ============================================================
# TAB 3
# ============================================================

with tabs[2]:

    st.subheader(
        "💰 기간별 ROI 검증"
    )

    train, validation, test = (
        split_periods(df)
    )

    periods = [
        (
            "2020~2024",
            train,
        ),
        (
            "2025",
            validation,
        ),
        (
            "2026~",
            test,
        ),
    ]

    result_rows = []

    for name, part in periods:

        x = run_backtest(
            part,
            min_odds,
            max_odds,
            min_probability,
        )

        m = calculate_metrics(
            x
        )

        result_rows.append({

            "기간":
                name,

            "경기":
                m["games"],

            "적중":
                m["hits"],

            "적중률":
                m["hit_rate"],

            "ROI":
                m["roi"],

            "수익":
                m["profit"],

            "최대낙폭":
                m["max_drawdown"],

        })

    result = pd.DataFrame(
        result_rows
    )

    st.dataframe(
        result.style.format({
            "적중률":
                "{:.2f}%",
            "ROI":
                "{:+.2f}%",
            "수익":
                "{:+.2f}",
            "최대낙폭":
                "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 4
# ============================================================

with tabs[3]:

    st.subheader(
        "📈 배당구간별 실제 승률"
    )

    if df.empty:

        st.info(
            "데이터가 없습니다."
        )

    else:

        x = df.copy()

        x = x[
            x[
                "home_odds"
            ].notna()
        ]

        if not x.empty:

            x[
                "배당구간"
            ] = x[
                "home_odds"
            ].apply(
                odds_bucket
            )

            summary = (
                x.groupby(
                    "배당구간"
                )
                .agg(

                    경기수=(
                        "result",
                        "count",
                    ),

                    홈승=(
                        "result",
                        lambda x:
                        (x == "H").sum(),
                    ),

                    무=(
                        "result",
                        lambda x:
                        (x == "D").sum(),
                    ),

                    원정승=(
                        "result",
                        lambda x:
                        (x == "A").sum(),
                    ),

                )
                .reset_index()
            )

            summary[
                "홈승률"
            ] = (
                summary[
                    "홈승"
                ]
                /
                summary[
                    "경기수"
                ]
                *
                100
            )

            summary[
                "무승부율"
            ] = (
                summary[
                    "무"
                ]
                /
                summary[
                    "경기수"
                ]
                *
                100
            )

            summary[
                "원정승률"
            ] = (
                summary[
                    "원정승"
                ]
                /
                summary[
                    "경기수"
                ]
                *
                100
            )

            st.dataframe(
                summary.style.format({
                    "홈승률":
                        "{:.2f}%",
                    "무승부율":
                        "{:.2f}%",
                    "원정승률":
                        "{:.2f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# TAB 5
# ============================================================

with tabs[4]:

    st.subheader(
        "🏆 종목별 ROI"
    )

    bt = run_backtest(
        df,
        min_odds,
        max_odds,
        min_probability,
    )

    if not bt.empty:

        sport_table = (
            bt.groupby(
                "sport"
            )
            .agg(

                경기수=(
                    "hit",
                    "count",
                ),

                적중=(
                    "hit",
                    "sum",
                ),

                수익=(
                    "profit",
                    "sum",
                ),

            )
            .reset_index()
        )

        sport_table[
            "적중률"
        ] = (
            sport_table[
                "적중"
            ]
            /
            sport_table[
                "경기수"
            ]
            *
            100
        )

        sport_table[
            "ROI"
        ] = (
            sport_table[
                "수익"
            ]
            /
            sport_table[
                "경기수"
            ]
            *
            100
        )

        st.dataframe(
            sport_table.style.format({
                "적중률":
                    "{:.2f}%",
                "ROI":
                    "{:+.2f}%",
                "수익":
                    "{:+.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(
            "리그별"
        )

        league_table = (
            bt.groupby(
                [
                    "sport",
                    "league",
                ]
            )
            .agg(

                경기수=(
                    "hit",
                    "count",
                ),

                적중=(
                    "hit",
                    "sum",
                ),

                수익=(
                    "profit",
                    "sum",
                ),

            )
            .reset_index()
        )

        league_table[
            "적중률"
        ] = (
            league_table[
                "적중"
            ]
            /
            league_table[
                "경기수"
            ]
            *
            100
        )

        league_table[
            "ROI"
        ] = (
            league_table[
                "수익"
            ]
            /
            league_table[
                "경기수"
            ]
            *
            100
        )

        st.dataframe(
            league_table.sort_values(
                "ROI",
                ascending=False,
            ).style.format({
                "적중률":
                    "{:.2f}%",
                "ROI":
                    "{:+.2f}%",
                "수익":
                    "{:+.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB 6
# ============================================================

with tabs[5]:

    st.subheader(
        "🗄️ 경기 데이터"
    )

    if df.empty:

        st.info(
            "데이터 없음"
        )

    else:

        st.dataframe(
            df.tail(1000),
            use_container_width=True,
            hide_index=True,
        )

        csv = (
            df.to_csv(
                index=False
            )
            .encode(
                "utf-8-sig"
            )
        )

        st.download_button(
            "⬇️ CSV 다운로드",
            csv,
            "sports_data.csv",
            "text/csv",
            use_container_width=True,
        )


# ============================================================
# TAB 7
# ============================================================

with tabs[6]:

    st.subheader(
        "⚙️ 데이터 수집 상태"
    )

    try:

        con = get_connection()

        logs = pd.read_sql_query(
            """
            SELECT
                source,
                MAX(created_at)
                    AS last_time,
                SUM(
                    CASE
                    WHEN success=1
                    THEN 1
                    ELSE 0
                    END
                ) AS success_count,
                COUNT(*) AS call_count,
                SUM(rows) AS rows
            FROM source_log
            GROUP BY source
            ORDER BY source
            """,
            con,
        )

        con.close()

        if logs.empty:

            st.info(
                "수집 기록 없음"
            )

        else:

            st.dataframe(
                logs,
                use_container_width=True,
                hide_index=True,
            )

    except Exception as e:

        st.error(
            str(e)
        )

    st.markdown(
        """
### 오류 처리

- 연결 실패 → 자동 재시도
- Timeout → 자동 재시도
- HTTP 429 → 대기 후 재시도
- HTTP 403/401 → 해당 출처만 중단
- JSON 파싱 실패 → 해당 출처만 건너뜀
- 개별 경기 오류 → 해당 경기만 건너뜀
- DB 저장 오류 → 전체 수집 중단하지 않음
- 중복 경기 → 자동 병합
- 오류 → `source_log`에 기록
"""
    )


# ============================================================
# Footer
# ============================================================

st.divider()

st.caption(
    "Sports Analyzer PRO | "
    "공개 데이터 기반 분석 프로그램"
)

st.warning(
    "과거 백테스트 결과는 미래 수익을 보장하지 않습니다."
)
