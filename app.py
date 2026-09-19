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


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.block-container {
    max-width: 750px;
    padding: 1rem;
}

h1 {
    text-align: center;
}

div.stButton > button {
    width: 100%;
    min-height: 50px;
    font-size: 17px;
    font-weight: bold;
}

.success-box {
    background: #e9f7ef;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
}

.error-box
