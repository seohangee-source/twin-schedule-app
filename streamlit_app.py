import json
import sqlite3
from datetime import date, datetime, timedelta
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


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


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

    conn.commit()
    conn.close()


def add_schedule(twin,title,category,d,t,memo):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO schedules(
    twin,title,category,event_date,event_time,memo,status
    ) VALUES(?,?,?,?,?,?,?)
    """,(twin,title,category,str(d),str(t),memo,"예정"))

    conn.commit()
    conn.close()


def load_schedules():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM schedules ORDER BY event_date,event_time",conn)
    conn.close()

    if not df.empty:
        df["event_date"] = pd.to_datetime(df["event_date"])

    return df


def update_status(id,status):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE schedules SET status=? WHERE id=?",(status,id))

    conn.commit()
    conn.close()


def delete_schedule(id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM schedules WHERE id=?",(id,))

    conn.commit()
    conn.close()


init_db()

df = load_schedules()

today = date.today()

total = len(df)
today_count = len(df[df["event_date"].dt.date == today]) if not df.empty else 0
open_count = len(df[df["status"]=="예정"]) if not df.empty else 0
done_count = len(df[df["status"]=="완료"]) if not df.empty else 0


st.markdown(
    "<h2 style='margin:0; font-size:2.0rem;'>서현우❤️서지후 일정관리</h2>",
    unsafe_allow_html=True
)

m1,m2,m3,m4 = st.columns(4)

m1.metric("전체 일정",f"{total:02d}건")
m2.metric("오늘 일정",f"{today_count:02d}건")
m3.metric("예정",f"{open_count:02d}건")
m4.metric("완료",f"{done_count:02d}건")


with st.expander("빠른 일정 등록",expanded=True):

    with st.form("add_form",clear_on_submit=True):

        c1,c2 = st.columns(2)

        with c1:
            twin = st.selectbox("대상",["첫째","둘째","공통"])

        with c2:
            category = st.selectbox("분류",["일정","병원","학습","행사","가족"])

        title = st.text_input("일정")

        c3,c4 = st.columns(2)

        with c3:
            d = st.date_input("날짜")

        with c4:
            t = st.time_input("시간")

        memo = st.text_area("메모")

        ok = st.form_submit_button("저장")

        if ok:

            if title.strip()=="":
                st.error("일정을 입력하세요")

            else:

                add_schedule(
                    twin,
                    title,
                    category,
                    d,
                    t,
                    memo
                )

                st.success("저장 완료")
                st.rerun()


st.divider()

tab1,tab2,tab3 = st.tabs(["홈","달력","백업"])


with tab1:

    if df.empty:
        st.info("등록된 일정 없음")

    else:

        for _,row in df.iterrows():

            with st.container(border=True):

                st.write("일정 :",row["title"])
                st.write("대상 :",row["twin"])
                st.write("날짜 :",row["event_date"].strftime("%Y-%m-%d"),row["event_time"])
                st.write("상태 :",row["status"])

                if row["memo"]:
                    st.caption(row["memo"])

                c1,c2,c3 = st.columns(3)

                with c1:
                    if st.button("완료",key=f"d{row['id']}"):
                        update_status(row["id"],"완료")
                        st.rerun()

                with c2:
                    if st.button("예정",key=f"p{row['id']}"):
                        update_status(row["id"],"예정")
                        st.rerun()

                with c3:
                    if st.button("삭제",key=f"x{row['id']}"):
                        delete_schedule(row["id"])
                        st.rerun()


with tab2:

    st.subheader("달력")

    month = st.date_input("기준월",value=date.today().replace(day=1))

    year = month.year
    m = month.month

    cal = calendar.Calendar().monthdatescalendar(year,m)

    for week in cal:

        cols = st.columns(7)

        for i,d in enumerate(week):

            with cols[i]:

                st.write(d.day)

                if not df.empty:

                    items = df[df["event_date"].dt.date==d]

                    for _,r in items.iterrows():

                        st.caption(r["title"])


with tab3:

    st.subheader("백업")

    if not df.empty:

        export = df.copy()

        csv = export.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "CSV 다운로드",
            csv,
            "schedule_backup.csv",
            "text/csv"
        )