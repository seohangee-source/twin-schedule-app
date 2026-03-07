import sqlite3
from datetime import date, datetime
from pathlib import Path
import calendar

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="서현우 서지후 일정관리",
    page_icon="📅",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "twin_schedule.db"

CATEGORY_OPTIONS = [
    "일정",
    "병원",
    "어린이집",
    "유치원",
    "체험행사",
    "수유리행사",
    "가족"
]

st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 1.2rem;
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(cur, table_name, column_name, col_type, default_sql=""):
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = [r[1] for r in cur.fetchall()]
    if column_name not in cols:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type} {default_sql}")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS schedules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        twin TEXT,
        title TEXT,
        category TEXT,
        event_date TEXT,
        event_time TEXT,
        memo TEXT,
        status TEXT DEFAULT '예정'
    )
    """)

    ensure_column(cur, "schedules", "category", "TEXT")
    ensure_column(cur, "schedules", "status", "TEXT", "DEFAULT '예정'")

    conn.commit()
    conn.close()


def add_schedule(twin, title, category, d, t, memo):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO schedules(
        twin, title, category, event_date, event_time, memo, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        twin,
        title,
        category,
        str(d),
        str(t)[:5],
        memo,
        "예정"
    ))

    conn.commit()
    conn.close()


def load_schedules():
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM schedules ORDER BY event_date, event_time, id",
        conn
    )
    conn.close()

    if not df.empty:
        df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")

    return df


def update_status(schedule_id, status):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "UPDATE schedules SET status=? WHERE id=?",
        (status, int(schedule_id))
    )

    conn.commit()
    conn.close()


def delete_schedule(schedule_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM schedules WHERE id=?",
        (int(schedule_id),)
    )

    conn.commit()
    conn.close()


def seed_if_empty():
    df = load_schedules()
    if not df.empty:
        return

    add_schedule("첫째", "소아과 검진", "병원", date.today(), "10:30", "예방접종 수첩 챙기기")


init_db()
seed_if_empty()

df = load_schedules()

today = date.today()

if df.empty:
    total = 0
    today_count = 0
    open_count = 0
    done_count = 0
else:
    total = len(df)
    today_count = len(df[df["event_date"].dt.date == today])
    open_count = len(df[df["status"] == "예정"])
    done_count = len(df[df["status"] == "완료"])

st.markdown(
    "<h2 style='margin:0; font-size:1.6rem;'>서현우❤️서지후 일정관리</h2>",
    unsafe_allow_html=True
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 일정", f"{total:02d}건")
m2.metric("오늘 일정", f"{today_count:02d}건")
m3.metric("예정", f"{open_count:02d}건")
m4.metric("완료", f"{done_count:02d}건")

with st.expander("빠른 일정 등록", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            twin = st.selectbox("대상", ["첫째", "둘째", "공통"])

        with c2:
            category = st.selectbox("분류", CATEGORY_OPTIONS)

        title = st.text_input("일정")

        c3, c4 = st.columns(2)
        with c3:
            d = st.date_input("날짜")
        with c4:
            t = st.time_input("시간")

        memo = st.text_area("메모")
        ok = st.form_submit_button("저장")

        if ok:
            if title.strip() == "":
                st.error("일정을 입력하세요")
            else:
                add_schedule(
                    twin=twin,
                    title=title.strip(),
                    category=category,
                    d=d,
                    t=t,
                    memo=memo.strip()
                )
                st.success("저장 완료")
                st.rerun()

st.divider()

f1, f2, f3, f4 = st.columns([1, 1, 1, 1.4])

with f1:
    twin_filter = st.selectbox("대상 필터", ["전체", "첫째", "둘째", "공통"])

with f2:
    category_filter = st.selectbox("분류 필터", ["전체"] + CATEGORY_OPTIONS)

with f3:
    status_filter = st.selectbox("상태 필터", ["전체", "예정", "완료"])

with f4:
    keyword = st.text_input("검색", placeholder="일정명 / 메모")

filtered_df = df.copy()

if not filtered_df.empty:
    if twin_filter != "전체":
        filtered_df = filtered_df[filtered_df["twin"] == twin_filter]

    if category_filter != "전체":
        filtered_df = filtered_df[filtered_df["category"] == category_filter]

    if status_filter != "전체":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]

    if keyword.strip():
        key = keyword.strip().lower()
        filtered_df = filtered_df[
            filtered_df[["title", "memo", "category", "twin"]]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.lower()
            .str.contains(key, regex=False)
        ]

tab1, tab2, tab3 = st.tabs(["홈", "달력", "백업"])

with tab1:
    if filtered_df.empty:
        st.info("등록된 일정 없음")
    else:
        for _, row in filtered_df.iterrows():
            with st.container(border=True):
                st.write("일정 :", row["title"])
                st.write("대상 :", row["twin"])
                st.write("분류 :", row["category"])
                st.write("날짜 :", row["event_date"].strftime("%Y-%m-%d"), row["event_time"])
                st.write("상태 :", row["status"])

                if row["memo"]:
                    st.caption(row["memo"])

                c1, c2, c3 = st.columns(3)

                with c1:
                    if row["status"] != "완료":
                        if st.button("완료", key=f"d{row['id']}"):
                            update_status(row["id"], "완료")
                            st.rerun()

                with c2:
                    if row["status"] != "예정":
                        if st.button("예정", key=f"p{row['id']}"):
                            update_status(row["id"], "예정")
                            st.rerun()

                with c3:
                    if st.button("삭제", key=f"x{row['id']}"):
                        delete_schedule(row["id"])
                        st.rerun()

with tab2:
    st.subheader("달력")
    month_input = st.date_input("기준월", value=date.today().replace(day=1))

    year = month_input.year
    month = month_input.month

    cal = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)

    week_header = st.columns(7)
    for i, w in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        week_header[i].markdown(f"**{w}**")

    for week in cal:
        cols = st.columns(7)
        for i, d in enumerate(week):
            with cols[i]:
                with st.container(border=True):
                    st.write(d.day)

                    if not filtered_df.empty:
                        items = filtered_df[filtered_df["event_date"].dt.date == d]
                        for _, r in items.iterrows():
                            st.caption(f"{r['title']}")

with tab3:
    st.subheader("백업")

    if filtered_df.empty:
        st.info("내보낼 데이터가 없습니다.")
    else:
        export = filtered_df.copy()
        export["event_date"] = export["event_date"].dt.strftime("%Y-%m-%d")

        st.dataframe(export, use_container_width=True, hide_index=True)

        csv = export.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "CSV 다운로드",
            csv,
            "schedule_backup.csv",
            "text/csv"
        )