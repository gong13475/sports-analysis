import streamlit as st
import pandas as pd
import sqlite3
import requests
from io import StringIO
from datetime import datetime


# =========================================================
# 설정
# =========================================================

st.set_page_config(
    page_title="해외배당 분석",
    page_icon="⚽",
    layout="centered"
)

DB_FILE = "historical_odds.db"
BASE_URL = "https://www.football-data.co.uk/mmz4281"


# =========================================================
# 리그
# =========================================================

LEAGUES = {
    "잉글랜드 1부": ("E0", "England", 1),
    "잉글랜드 2부": ("E1", "England", 2),
    "잉글랜드 3부": ("E2", "England", 3),
    "독일 1부": ("D1", "Germany", 1),
    "독일 2부": ("D2", "Germany", 2),
    "이탈리아 1부": ("I1", "Italy", 1),
    "이탈리아 2부": ("I2", "Italy", 2),
    "스페인 1부": ("SP1", "Spain", 1),
    "스페인 2부": ("SP2", "Spain", 2),
    "프랑스 1부": ("F1", "France", 1),
    "프랑스 2부": ("F2", "France", 2),
    "네덜란드 1부": ("N1", "Netherlands", 1),
    "벨기에 1부": ("B1", "Belgium", 1
