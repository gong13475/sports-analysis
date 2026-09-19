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
    page_title="해외 배당 분석",
    page_icon="⚽",
    layout="centered"
)

DB_FILE = "historical_odds.db"

BASE_URL = "https://www.football-data.co.uk/mmz4281"


# =========================================================
