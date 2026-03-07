import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os

# ---------------------------
# 기본 설정
# ---------------------------
st.set_page_config(
    page_title="쌍둥이 일정관리",
    page_icon="📱",
    layout="wide"
)

# ---------------------------
# CSS (모바일 UI 스타일)
# ---------------------------
st.markdown("""
<style>

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
}

.hero {
    background: linear-gradient(135deg,#111827,#334155);
    color:white;
    padding:25px;
    border-radius:20px;
    margin-bottom:20px;
}

.card {
    background:white;
    padding:15px;
    border-radius:15px;
    box-shadow:0 5px 15px rgba(0,0,0,0.05);
    margin-bottom:15px;
}

.tag {
    padding:4px 10px;
    border-radius:20px;
    font-size:12px;
    margin-right:6px;
}

.first {
    background:#ffe4ec;
    color:#9f1239;
}

.second {
    background:#dbeafe;
    color:#1d4ed8;
}

.common {
    background:#dcfce7;
    color:#166534;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------
# DB
# ---------------------------
conn = sqlite3.connect("twin_schedule.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS schedules(
id INTEGER PRIMARY KEY AUTOINCREMENT,
twin TEXT,
title TEXT,
date TEXT,
time TEXT,
memo TEXT
)
""")

conn.commit()

# ---------------------------
# 헤더
# ---------------------------
st.markdown("""
<div class="hero">
<h2>📱 쌍둥이 일정관리</h2>
<p>휴대폰처럼 사용하는 일정관리 앱</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# 일정 등록
# ---------------------------
st.subheader("➕ 일정 등록")

col1,col2 = st.columns(2)

with col1:
    twin = st.selectbox("대상",["첫째","둘째","공통"])

with col2:
    title = st.text_input("일정")

col3,col4 = st.columns(2)

with col3:
    d = st.date_input("날짜")

with col4:
    t = st.time_input("시간")

memo = st.text_area("메모")

if st.button("저장"):
    
    cursor.execute("""
    INSERT INTO schedules (twin,title,date,time,memo)
    VALUES (?,?,?,?,?)
    """,(twin,title,str(d),str(t),memo))
    
    conn.commit()
    st.success("저장 완료")
    st.experimental_rerun()

# ---------------------------
# 일정 불러오기
# ---------------------------
df = pd.read_sql("SELECT * FROM schedules ORDER BY date,time",conn)

st.subheader("📅 일정 목록")

if df.empty:
    st.info("등록된 일정이 없습니다")

for i,row in df.iterrows():

    tag_class = "common"
    
    if row["twin"]=="첫째":
        tag_class="first"
    elif row["twin"]=="둘째":
        tag_class="second"

    st.markdown(f"""
    <div class="card">
    
    <span class="tag {tag_class}">{row["twin"]}</span>
    
    <h4>{row["title"]}</h4>
    
    <p>📅 {row["date"]} ⏰ {row["time"]}</p>
    
    <p>{row["memo"]}</p>
    
    </div>
    """,unsafe_allow_html=True)

# ---------------------------
# 캘린더
# ---------------------------
st.subheader("📊 일정 데이터")

if not df.empty:

    df["date"]=pd.to_datetime(df["date"])
    
    chart=df.groupby("date").count()["id"]
    
    st.line_chart(chart)

# ---------------------------
# 다운로드
# ---------------------------
st.subheader("⬇ 일정 다운로드")

if not df.empty:

    csv=df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "CSV 다운로드",
        csv,
        "schedule.csv",
        "text/csv"
    )