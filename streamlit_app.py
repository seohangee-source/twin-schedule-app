import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

st.set_page_config(
    page_title="쌍둥이 일정관리",
    page_icon="📱",
    layout="wide"
)

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

conn = sqlite3.connect("twin_schedule.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS schedules(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    twin TEXT,
    title TEXT,
    category TEXT,
    event_date TEXT,
    event_time TEXT,
    memo TEXT,
    status TEXT DEFAULT '예정',
    repeat_rule TEXT DEFAULT '없음',
    remind_days_before INTEGER DEFAULT 0,
    photo_path TEXT,
    created_at TEXT
)
""")
conn.commit()

st.markdown("""
<div class="hero">
    <h2>📱 쌍둥이 일정관리</h2>
    <p>휴대폰처럼 사용하는 일정관리 앱</p>
</div>
""", unsafe_allow_html=True)

st.subheader("➕ 일정 등록")

col1, col2 = st.columns(2)
with col1:
    twin = st.selectbox("대상", ["첫째", "둘째", "공통"])
with col2:
    title = st.text_input("일정")

col3, col4 = st.columns(2)
with col3:
    d = st.date_input("날짜")
with col4:
    t = st.time_input("시간")

memo = st.text_area("메모")

if st.button("저장"):
    if not title.strip():
        st.error("일정을 입력하세요.")
    else:
        cursor.execute("""
        INSERT INTO schedules (
            twin, title, category, event_date, event_time, memo,
            status, repeat_rule, remind_days_before, photo_path, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            twin,
            title.strip(),
            "일정",
            str(d),
            str(t)[:5],
            memo,
            "예정",
            "없음",
            0,
            None,
            datetime.now().isoformat(timespec="seconds")
        ))
        conn.commit()
        st.success("저장 완료")
        st.rerun()

df = pd.read_sql("""
SELECT
    id,
    twin,
    title,
    event_date,
    event_time,
    memo,
    status
FROM schedules
ORDER BY event_date, event_time
""", conn)

st.subheader("📅 일정 목록")

if df.empty:
    st.info("등록된 일정이 없습니다.")

for _, row in df.iterrows():
    tag_class = "common"
    if row["twin"] == "첫째":
        tag_class = "first"
    elif row["twin"] == "둘째":
        tag_class = "second"

    st.markdown(f"""
    <div class="card">
        <span class="tag {tag_class}">{row["twin"]}</span>
        <span class="tag">{row["status"]}</span>
        <h4>{row["title"]}</h4>
        <p>📅 {row["event_date"]} ⏰ {row["event_time"]}</p>
        <p>{row["memo"] if row["memo"] else ""}</p>
    </div>
    """, unsafe_allow_html=True)

st.subheader("📊 일정 데이터")

if not df.empty:
    chart_df = df.copy()
    chart_df["event_date"] = pd.to_datetime(chart_df["event_date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["event_date"])
    if not chart_df.empty:
        chart = chart_df.groupby("event_date").count()["id"]
        st.line_chart(chart)

st.subheader("⬇ 일정 다운로드")

if not df.empty:
    export_df = df.rename(columns={
        "twin": "대상",
        "title": "일정",
        "event_date": "날짜",
        "event_time": "시간",
        "memo": "메모",
        "status": "상태"
    })
    csv = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV 다운로드",
        csv,
        "schedule.csv",
        "text/csv"
    )