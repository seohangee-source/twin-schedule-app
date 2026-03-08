import sqlite3
from datetime import date
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
.stat-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 8px;
    margin-bottom: 12px;
}
.stat-box {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 8px 6px;
    text-align: center;
    background: #ffffff;
}
.stat-label {
    font-size: 0.78rem;
    color: #4b5563;
    line-height: 1.1;
    margin-bottom: 4px;
    white-space: nowrap;
}
.stat-value {
    font-size: 1.15rem;
    font-weight: 700;
    color: #111827;
    line-height: 1.0;
    white-space: nowrap;
}

@media (max-width: 768px) {
    .stat-row {
        gap: 4px;
    }
    .stat-box {
        padding: 6px 2px;
    }
    .stat-label {
        font-size: 0.56rem;
        margin-bottom: 2px;
    }
    .stat-value {
        font-size: 0.88rem;
    }
}

.cal-wrap {
    width: 100%;
    overflow-x: auto;
}
.cal-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 4px;
    table-layout: fixed;
}
.cal-table th {
    font-size: 0.82rem;
    font-weight: 700;
    text-align: center;
    padding: 6px 0;
    color: #374151;
}
.cal-table td {
    vertical-align: top;
    height: 88px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #ffffff;
    padding: 4px;
}
.cal-other {
    background: #f9fafb !important;
    color: #9ca3af;
}
.cal-day {
    font-size: 0.78rem;
    font-weight: 700;
    margin-bottom: 4px;
}
.cal-item {
    font-size: 0.62rem;
    line-height: 1.2;
    background: #eff6ff;
    color: #1d4ed8;
    border-radius: 6px;
    padding: 2px 4px;
    margin-bottom: 3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cal-item-child1 {
    background: #ffe4ec;
    color: #9f1239;
}
.cal-item-child2 {
    background: #dbeafe;
    color: #1d4ed8;
}
.cal-item-common {
    background: #dcfce7;
    color: #166534;
}

@media (max-width: 768px) {
    .cal-table th {
        font-size: 0.68rem;
        padding: 4px 0;
    }
    .cal-table td {
        height: 64px;
        padding: 3px;
    }
    .cal-day {
        font-size: 0.66rem;
        margin-bottom: 2px;
    }
    .cal-item {
        font-size: 0.52rem;
        padding: 1px 3px;
        border-radius: 4px;
        margin-bottom: 2px;
    }
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


def render_mobile_calendar(df, month_input):
    year = month_input.year
    month = month_input.month

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    item_map = {}
    if not df.empty:
        temp = df.copy()
        temp["event_date_only"] = temp["event_date"].dt.date

        for _, row in temp.iterrows():
            d = row["event_date_only"]
            item_map.setdefault(d, []).append(row)

    html = []
    html.append("<div class='cal-wrap'>")
    html.append("<table class='cal-table'>")
    html.append("<thead><tr>")
    for w in ["월", "화", "수", "목", "금", "토", "일"]:
        html.append(f"<th>{w}</th>")
    html.append("</tr></thead><tbody>")

    for week in month_days:
        html.append("<tr>")
        for d in week:
            td_class = ""
            if d.month != month:
                td_class = "cal-other"

            html.append(f"<td class='{td_class}'>")
            html.append(f"<div class='cal-day'>{d.day}</div>")

            items = item_map.get(d, [])
            for item in items[:2]:
                twin = str(item.get("twin", "공통"))
                if twin == "첫째":
                    cls = "cal-item cal-item-child1"
                elif twin == "둘째":
                    cls = "cal-item cal-item-child2"
                else:
                    cls = "cal-item cal-item-common"

                title = str(item.get("title", ""))
                time_txt = str(item.get("event_time", ""))
                html.append(f"<div class='{cls}'>{time_txt} {title}</div>")

            if len(items) > 2:
                html.append(f"<div class='cal-item'>+{len(items)-2}건</div>")

            html.append("</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")

    st.markdown("".join(html), unsafe_allow_html=True)


def render_desktop_calendar(df, month_input):
    year = month_input.year
    month = month_input.month

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    item_map = {}
    if not df.empty:
        temp = df.copy()
        temp["event_date_only"] = temp["event_date"].dt.date
        for _, row in temp.iterrows():
            d = row["event_date_only"]
            item_map.setdefault(d, []).append(row)

    week_header = st.columns(7)
    for i, w in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        week_header[i].markdown(f"**{w}**")

    for week in month_days:
        cols = st.columns(7)
        for i, d in enumerate(week):
            with cols[i]:
                with st.container(border=True):
                    if d.month != month:
                        st.caption(d.day)
                    else:
                        st.write(f"**{d.day}**")

                    items = item_map.get(d, [])
                    for item in items[:3]:
                        twin = str(item.get("twin", "공통"))
                        title = str(item.get("title", ""))
                        time_txt = str(item.get("event_time", ""))

                        if twin == "첫째":
                            st.caption(f"🩷 {time_txt} {title}")
                        elif twin == "둘째":
                            st.caption(f"🩵 {time_txt} {title}")
                        else:
                            st.caption(f"💚 {time_txt} {title}")

                    if len(items) > 3:
                        st.caption(f"+{len(items)-3}건")


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

st.markdown(
    f"""
    <div class="stat-row">
        <div class="stat-box">
            <div class="stat-label">전체</div>
            <div class="stat-value">{total:02d}건</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">오늘</div>
            <div class="stat-value">{today_count:02d}건</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">예정</div>
            <div class="stat-value">{open_count:02d}건</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">완료</div>
            <div class="stat-value">{done_count:02d}건</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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

    c1, c2 = st.columns([1, 1])
    with c1:
        month_input = st.date_input("기준월", value=date.today().replace(day=1))
    with c2:
        calendar_view = st.radio(
            "보기 방식",
            ["핸드폰 타입", "데스크탑 타입"],
            horizontal=True
        )

    if calendar_view == "핸드폰 타입":
        render_mobile_calendar(filtered_df, month_input)
    else:
        render_desktop_calendar(filtered_df, month_input)

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