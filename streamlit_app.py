import sqlite3
from datetime import date, time as dtime
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
    "가족행사",
    "어린이집 및 유치원",
    "병원",
    "진월일정",
    "수유리일정",
    "기타 일정"
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
.cal-item-family {
    background: #ffe4ec;
    color: #9f1239;
}
.cal-item-school {
    background: #e0f2fe;
    color: #075985;
}
.cal-item-hospital {
    background: #ede9fe;
    color: #5b21b6;
}
.cal-item-jinwol {
    background: #dcfce7;
    color: #166534;
}
.cal-item-suyuri {
    background: #fef3c7;
    color: #92400e;
}
.cal-item-etc {
    background: #e5e7eb;
    color: #374151;
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

    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0.3rem !important;
    }
    div[data-testid="column"] {
        min-width: 0 !important;
    }

    label p {
        font-size: 0.68rem !important;
        line-height: 1.0 !important;
    }
    div[data-baseweb="select"] > div {
        font-size: 0.72rem !important;
        min-height: 2.25rem !important;
    }
    input {
        font-size: 0.72rem !important;
    }

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

    # 기존 데이터 통합/정리
    cur.execute("UPDATE schedules SET category='어린이집 및 유치원' WHERE category='어린이집'")
    cur.execute("UPDATE schedules SET category='어린이집 및 유치원' WHERE category='유치원'")

    cur.execute("UPDATE schedules SET category='진월일정' WHERE category='체험행사'")
    cur.execute("UPDATE schedules SET category='진월일정' WHERE category='지원행사'")
    cur.execute("UPDATE schedules SET category='진월일정' WHERE category='진월행사'")
    cur.execute("UPDATE schedules SET category='진월일정' WHERE category='진월 행사'")

    cur.execute("UPDATE schedules SET category='수유리일정' WHERE category='수유리행사'")
    cur.execute("UPDATE schedules SET category='수유리일정' WHERE category='수류리행사'")
    cur.execute("UPDATE schedules SET category='수유리일정' WHERE category='수유리 행사'")

    cur.execute("UPDATE schedules SET category='가족행사' WHERE category='가족'")
    cur.execute("UPDATE schedules SET category='기타 일정' WHERE category='일정'")

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


def update_schedule(schedule_id, title, category, d, t, memo):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    UPDATE schedules
    SET title=?, category=?, event_date=?, event_time=?, memo=?
    WHERE id=?
    """, (
        title,
        category,
        str(d),
        str(t)[:5],
        memo,
        int(schedule_id)
    ))

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

    add_schedule(
        "첫째",
        "소아과 검진",
        "병원",
        date.today(),
        "10:30",
        "예방접종 수첩 챙기기"
    )


def category_class(category: str) -> str:
    if category == "가족행사":
        return "cal-item cal-item-family"
    if category == "어린이집 및 유치원":
        return "cal-item cal-item-school"
    if category == "병원":
        return "cal-item cal-item-hospital"
    if category == "진월일정":
        return "cal-item cal-item-jinwol"
    if category == "수유리일정":
        return "cal-item cal-item-suyuri"
    return "cal-item cal-item-etc"


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
                cls = category_class(str(item.get("category", "")))
                title = str(item.get("title", ""))
                time_txt = str(item.get("event_time", ""))
                html.append(f"<div class='{cls}'>{time_txt} {title}</div>")

            if len(items) > 2:
                html.append(f"<div class='cal-item cal-item-etc'>+{len(items)-2}건</div>")

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
                        category = str(item.get("category", ""))
                        title = str(item.get("title", ""))
                        time_txt = str(item.get("event_time", ""))

                        if category == "가족행사":
                            st.caption(f"🩷 {time_txt} {title}")
                        elif category == "어린이집 및 유치원":
                            st.caption(f"🩵 {time_txt} {title}")
                        elif category == "병원":
                            st.caption(f"💜 {time_txt} {title}")
                        elif category == "진월일정":
                            st.caption(f"💚 {time_txt} {title}")
                        elif category == "수유리일정":
                            st.caption(f"🟨 {time_txt} {title}")
                        else:
                            st.caption(f"⬜ {time_txt} {title}")

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

col1, col2, col3 = st.columns(3)

with col1:
    twin_filter = st.selectbox("대상", ["전체", "첫째", "둘째", "공통"])

with col2:
    category_filter = st.selectbox("분류", ["전체"] + CATEGORY_OPTIONS)

with col3:
    status_filter = st.selectbox("상태", ["전체", "예정", "완료"])

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
    if "edit_id" in st.session_state:
        edit_df = df[df["id"] == st.session_state["edit_id"]]
        if not edit_df.empty:
            edit_row = edit_df.iloc[0]

            st.subheader("일정 수정")
            with st.form("edit_form"):
                edit_title = st.text_input("일정", edit_row["title"])

                edit_category = st.selectbox(
                    "분류",
                    CATEGORY_OPTIONS,
                    index=CATEGORY_OPTIONS.index(edit_row["category"]) if edit_row["category"] in CATEGORY_OPTIONS else 0
                )

                edit_date = st.date_input(
                    "날짜",
                    value=pd.to_datetime(edit_row["event_date"]).date()
                )

                try:
                    hh, mm = str(edit_row["event_time"])[:5].split(":")
                    edit_time_default = dtime(int(hh), int(mm))
                except Exception:
                    edit_time_default = dtime(9, 0)

                edit_time = st.time_input("시간", value=edit_time_default)
                edit_memo = st.text_area("메모", edit_row["memo"] if pd.notnull(edit_row["memo"]) else "")

                e1, e2 = st.columns(2)
                with e1:
                    save_edit = st.form_submit_button("수정 저장")
                with e2:
                    cancel_edit = st.form_submit_button("수정 취소")

                if save_edit:
                    if edit_title.strip() == "":
                        st.error("일정을 입력하세요")
                    else:
                        update_schedule(
                            edit_row["id"],
                            edit_title.strip(),
                            edit_category,
                            edit_date,
                            edit_time,
                            edit_memo.strip()
                        )
                        del st.session_state["edit_id"]
                        st.success("수정 완료")
                        st.rerun()

                if cancel_edit:
                    del st.session_state["edit_id"]
                    st.rerun()

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

                c1, c2, c3, c4 = st.columns(4)

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

                with c4:
                    if st.button("수정", key=f"edit{row['id']}"):
                        st.session_state["edit_id"] = row["id"]
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