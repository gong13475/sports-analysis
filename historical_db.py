import sqlite3
import requests
import pandas as pd
from io import StringIO
from pathlib import Path

DB_FILE = "historical.db"

# 최근 5시즌 EPL 데이터
SEASONS = [
    "2122",
    "2223",
    "2324",
    "2425",
    "2526"
]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{}/E0.csv"


def create_database():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season TEXT,
            date TEXT,
            home TEXT,
            away TEXT,
            result TEXT,
            home_odds REAL,
            draw_odds REAL,
            away_odds REAL
        )
    """)

    conn.commit()

    return conn


def download_season(season):

    url = BASE_URL.format(season)

    try:

        response = requests.get(
            url,
            timeout=30
        )

        if response.status_code != 200:
            return None

        return pd.read_csv(
            StringIO(
                response.content.decode(
                    "latin1"
                )
            )
        )

    except Exception as e:

        print(
            f"{season} 다운로드 오류:",
            e
        )

        return None


def find_odds_column(df, names):

    for name in names:

        if name in df.columns:
            return name

    return None


def save_season(conn, season, df):

    home_odds = find_odds_column(
        df,
        ["B365H", "AvgH", "MaxH"]
    )

    draw_odds = find_odds_column(
        df,
        ["B365D", "AvgD", "MaxD"]
    )

    away_odds = find_odds_column(
        df,
        ["B365A", "AvgA", "MaxA"]
    )

    required = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTR"
    ]

    for col in required:

        if col not in df.columns:
            return

    count = 0

    for _, row in df.iterrows():

        try:

            h = (
                float(row[home_odds])
                if home_odds
                else None
            )

            d = (
                float(row[draw_odds])
                if draw_odds
                else None
            )

            a = (
                float(row[away_odds])
                if away_odds
                else None
            )

            conn.execute("""
                INSERT INTO matches (
                    season,
                    date,
                    home,
                    away,
                    result,
                    home_odds,
                    draw_odds,
                    away_odds
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                season,
                str(row["Date"]),
                row["HomeTeam"],
                row["AwayTeam"],
                row["FTR"],
                h,
                d,
                a
            ))

            count += 1

        except Exception:
            continue

    conn.commit()

    print(
        season,
        "저장:",
        count,
        "경기"
    )


def build_database():

    conn = create_database()

    for season in SEASONS:

        print(
            "다운로드:",
            season
        )

        df = download_season(
            season
        )

        if df is not None:

            save_season(
                conn,
                season,
                df
            )

    conn.close()

    print(
        "historical.db 생성 완료"
    )


if __name__ == "__main__":

    build_database()
