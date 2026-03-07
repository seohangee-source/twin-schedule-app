import json
import sqlite3
from datetime import date, datetime, timedelta, time as dtime
from pathlib import Path
import calendar

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="쌍둥이 일정관리 앱 2.1",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "twin_schedule.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

TWIN_OPTIONS = ["첫째", "둘째", "공통"]
CATEGORY_OPTIONS = ["일정", "병원", "학습", "행사", "가족", "준비물", "사진기록"]
STATUS_OPTIONS = ["예정", "완료", "보류"]
REPEAT_OPTIONS = ["없음", "매일", "매주", "매월"]
ALERT_OPTIONS = [0, 1, 2, 3, 7]


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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
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
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            phone TEXT,
            note TEXT,
            created_at TEXT
        )
        """
    )

    ensure_column(cur, "schedules", "category", "TEXT")
    ensure_column(cur, "schedules", "status", "TEXT", "DEFAULT '예정'")
    ensure_column(cur, "schedules", "repeat_rule", "TEXT", "DEFAULT '없음'")
    ensure_column(cur, "schedules", "remind_days_before", "INTEGER", "DEFAULT 0")
    ensure_column(cur, "schedules", "photo_path", "TEXT")
    ensure_column(cur, "schedules", "created_at", "TEXT")

    conn.commit()
    conn.close()


def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe = uploaded_file.name.replace(" ", "_")
    path = UPLOAD_DIR / f"{ts}_{safe}"
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def add_schedule(payload):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO schedules (
            twin, title, category, event_date, event_time, memo,
            status, repeat_rule, remind_days_before, photo_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["twin"],
            payload["title"],
            payload["category"],
            payload["event_date"],
            payload["event_time"],
            payload.get("memo", ""),
            payload.get("status", "예정"),
            payload.get("repeat_rule", "없음"),
            int(payload.get("remind_days_before", 0)),
            payload.get("photo_path"),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()


def update_schedule_status(schedule_id, new_status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE schedules SET status=? WHERE id=?", (new_status, int(schedule_id)))
    conn.commit()
    conn.close()


def delete_schedule(schedule_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT photo_path FROM schedules WHERE id=?", (int(schedule_id),))
    row = cur.fetchone()
    if row and row["photo_path"]:
        p = Path(row["photo_path"])
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    cur.execute("DELETE FROM schedules WHERE id=?", (int(schedule_id),))
    conn.commit()
    conn.close()


def add_family_member(name, role, phone, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO family_members (name, role, phone, note, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, role, phone, note, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def delete_family_member(member_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM family_members WHERE id=?", (int(member_id),))
    conn.commit()
    conn.close()


def load_schedules():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM schedules ORDER BY event_date, event_time, id", conn)
    conn.close()
    if not df.empty:
        df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    return df


def load_family_members():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM family_members ORDER BY id", conn)
    conn.close()
    return df


def seed_if_empty():
    df = load_schedules()
    if not df.empty:
        return

    sample = [
        {
            "twin": "첫째",
            "title": "소아과 정기검진",
            "category": "병원",
            "event_date": str(date.today()),
            "event_time": "10:30",
            "memo": "예방접종 수첩 챙기기",
            "status": "예정",
            "repeat_rule": "없음",
            "remind_days_before": 1,
            "photo_path": None,
        },
        {
            "twin": "둘째",
            "title": "수영 수업",
            "category": "학습",
            "event_date": str(date.today() + timedelta(days=1)),
            "event_time": "16:20",
            "memo": "수영복, 수건 준비",
            "status": "예정",
            "repeat_rule": "매주",
            "remind_days_before": 1,
            "photo_path": None,
        },
        {
            "twin": "공통",
            "title": "가족 나들이",
            "category": "가족",
            "event_date": str(date.today() + timedelta(days=2)),
            "event_time": "11:00",
            "memo": "간식과 물 챙기기",
            "status": "예정",
            "repeat_rule": "없음",
            "remind_days_before": 1,
            "photo_path": None,
        },
    ]

    for item in sample:
        add_schedule(item)

    fam = load_family_members()
    if fam.empty:
        add_family_member("엄마", "보호자", "010-0000-0000", "주중 일정 관리")
        add_family_member("아빠", "보호자", "010-1111-1111", "병원 및 주말 일정")


def expand_repeating_events(df, start_date, end_date):
    if df.empty:
        return df.copy()

    rows = []
    for _, r in df.iterrows():
        base = pd.to_datetime(r["event_date"]).date() if pd.notnull(r["event_date"]) else None
        if not base:
            continue

        rule = r.get("repeat_rule", "없음") or "없음"

        if rule == "없음":
            if start_date <= base <= end_date:
                rr = r.copy()
                rr["display_date"] = pd.to_datetime(base)
                rows.append(rr)
            continue

        cur = base
        while cur <= end_date:
            if cur >= start_date:
                rr = r.copy()
                rr["display_date"] = pd.to_datetime(cur)
                rows.append(rr)

            if rule == "매일":
                cur += timedelta(days=1)
            elif rule == "매주":
                cur += timedelta(days=7)
            elif rule == "매월":
                y = cur.year + (1 if cur.month == 12 else 0)
                m = 1 if cur.month == 12 else cur.month + 1
                cur = date(y, m, min(cur.day, 28))
            else:
                break

    out = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not out.empty:
        out["display_date"] = pd.to_datetime(out["display_date"])
        out = out.sort_values(["display_date", "event_time", "id"]).reset_index(drop=True)
    return out


def filter_occurrences(df, twin_filter, category_filter, status_filter, keyword, start_date, end_date):
    if df.empty:
        return df

    out = df.copy()

    if twin_filter != "전체":
        out = out[out["twin"] == twin_filter]
    if category_filter != "전체":
        out = out[out["category"] == category_filter]
    if status_filter != "전체":
        out = out[out["status"] == status_filter]
    if keyword.strip():
        key = keyword.strip().lower()
        out = out[
            out[["title", "memo", "category", "twin"]]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.lower()
            .str.contains(key, regex=False)
        ]

    out = out[(out["display_date"].dt.date >= start_date) & (out["display_date"].dt.date <= end_date)]
    return out.reset_index(drop=True)


def build_export_df(df):
    if df.empty:
        return pd.DataFrame(columns=["ID", "대상", "일정", "분류", "날짜", "시간", "상태", "반복", "알림", "메모"])

    x = df.copy()
    x["날짜"] = x["display_date"].dt.strftime("%Y-%m-%d")
    return x[
        ["id", "twin", "title", "category", "날짜", "event_time", "status", "repeat_rule", "remind_days_before", "memo"]
    ].rename(
        columns={
            "id": "ID",
            "twin": "대상",
            "title": "일정",
            "category": "분류",
            "event_time": "시간",
            "status": "상태",
            "repeat_rule": "반복",
            "remind_days_before": "알림",
            "memo": "메모",
        }
    )


def build_backup_json():
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "schedules": load_schedules().assign(event_date=lambda x: x["event_date"].astype(str)).to_dict(orient="records"),
        "family_members": load_family_members().to_dict(orient="records"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def get_stats(df):
    if df.empty:
        return {"total": 0, "today": 0, "open": 0, "done": 0}

    today_ = date.today()
    return {
        "total": len(df),
        "today": int((df["display_date"].dt.date == today_).sum()),
        "open": int((df["status"] == "예정").sum()),
        "done": int((df["status"] == "완료").sum()),
    }


def build_kakao_message_preview(df):
    today_ = date.today()
    alerts = []

    if df.empty:
        return "오늘 보낼 알림 대상이 없습니다."

    for _, row in df.iterrows():
        remind = int(row.get("remind_days_before", 0) or 0)
        gap = (row["display_date"].date() - today_).days
        if row["status"] != "완료" and gap == remind:
            alerts.append(f"- {row['display_date'].strftime('%m/%d')} {row['event_time']} | {row['twin']} | {row['title']}")

    if not alerts:
        return "오늘 보낼 알림 대상이 없습니다."

    return "[쌍둥이 일정 알림]\n" + "\n".join(alerts)


def render_calendar_table(df, month_date):
    year = month_date.year
    month = month_date.month
    cal = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)

    items = {}
    if not df.empty:
        for _, row in df.iterrows():
            d = row["display_date"].date()
            if d.year == year and d.month == month:
                items.setdefault(d, []).append(row)

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    header_cols = st.columns(7)
    for i, w in enumerate(weekdays):
        header_cols[i].markdown(f"**{w}**")

    for week in cal:
        cols = st.columns(7)
        for i, d in enumerate(week):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{d.day}**")
                    day_items = items.get(d, [])
                    for item in day_items[:3]:
                        st.caption(f"{item['event_time']} {item['title']}")
                    if len(day_items) > 3:
                        st.caption(f"+{len(day_items)-3}건")


init_db()
seed_if_empty()

base_df = load_schedules()
window_start = date.today() - timedelta(days=14)
window_end = date.today() + timedelta(days=60)
occ_df = expand_repeating_events(base_df, window_start, window_end)
stats = get_stats(occ_df)

st.title("📅 쌍둥이 일정관리 앱 2.1")
st.caption("안정형 UI 버전 · 달력 · 가족공유 · 사진앨범 · 카카오 알림용 메시지 · 백업")

m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 일정", stats["total"])
m2.metric("오늘 일정", stats["today"])
m3.metric("예정", stats["open"])
m4.metric("완료", stats["done"])

with st.expander("빠른 일정 등록", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            twin = st.selectbox("대상", TWIN_OPTIONS)
        with c2:
            category = st.selectbox("분류", CATEGORY_OPTIONS)

        title = st.text_input("일정명", placeholder="예: 소아과, 수영수업, 가족외식")

        c3, c4 = st.columns(2)
        with c3:
            event_date = st.date_input("날짜", value=date.today())
        with c4:
            event_time = st.time_input("시간", value=dtime(9, 0))

        memo = st.text_area("메모", height=80)

        c5, c6, c7 = st.columns(3)
        with c5:
            repeat_rule = st.selectbox("반복", REPEAT_OPTIONS)
        with c6:
            status = st.selectbox("상태", STATUS_OPTIONS)
        with c7:
            remind = st.selectbox("알림", ALERT_OPTIONS)

        photo = st.file_uploader("사진 첨부", type=["png", "jpg", "jpeg", "webp"])
        ok = st.form_submit_button("일정 저장")

        if ok:
            if not title.strip():
                st.error("일정명을 입력하세요.")
            else:
                add_schedule(
                    {
                        "twin": twin,
                        "title": title.strip(),
                        "category": category,
                        "event_date": str(event_date),
                        "event_time": str(event_time)[:5],
                        "memo": memo.strip(),
                        "status": status,
                        "repeat_rule": repeat_rule,
                        "remind_days_before": remind,
                        "photo_path": save_uploaded_file(photo),
                    }
                )
                st.success("일정이 저장되었습니다.")
                st.rerun()

f1, f2, f3, f4 = st.columns([1, 1, 1, 1.5])
with f1:
    twin_filter = st.selectbox("대상 필터", ["전체"] + TWIN_OPTIONS)
with f2:
    category_filter = st.selectbox("분류 필터", ["전체"] + CATEGORY_OPTIONS)
with f3:
    status_filter = st.selectbox("상태 필터", ["전체"] + STATUS_OPTIONS)
with f4:
    keyword = st.text_input("검색", placeholder="일정명 / 메모")

filtered_df = filter_occurrences(
    occ_df,
    twin_filter,
    category_filter,
    status_filter,
    keyword,
    window_start,
    window_end,
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["홈", "달력", "사진 앨범", "가족 공유", "카카오 알림", "백업"]
)

with tab1:
    if filtered_df.empty:
        st.info("조건에 맞는 일정이 없습니다.")
    else:
        grouped = list(filtered_df.groupby(filtered_df["display_date"].dt.strftime("%Y-%m-%d")))
        for day, group in grouped:
            dt = pd.to_datetime(day)
            weekday = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
            st.subheader(f"{dt.month}.{dt.day} ({weekday})")

            for _, row in group.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['title']}**")
                    st.write(f"대상: {row['twin']} | 분류: {row['category']} | 상태: {row['status']}")
                    st.write(f"일시: {row['display_date'].strftime('%Y-%m-%d')} {row['event_time']}")
                    st.write(f"반복: {row.get('repeat_rule', '없음')} | 알림: {row.get('remind_days_before', 0)}일 전")
                    if row["memo"]:
                        st.caption(row["memo"])

                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if row["status"] != "완료" and st.button("완료", key=f"done_{row['id']}_{day}"):
                            update_schedule_status(row["id"], "완료")
                            st.rerun()
                    with b2:
                        if row["status"] != "보류" and st.button("보류", key=f"hold_{row['id']}_{day}"):
                            update_schedule_status(row["id"], "보류")
                            st.rerun()
                    with b3:
                        if st.button("삭제", key=f"del_{row['id']}_{day}"):
                            delete_schedule(row["id"])
                            st.rerun()

                    photo_path = row.get("photo_path")
                    if pd.notnull(photo_path) and str(photo_path).strip():
                        p = Path(photo_path)
                        if p.exists():
                            st.image(str(p), width=260)

with tab2:
    month_pick = st.date_input("기준월", value=date.today().replace(day=1))
    render_calendar_table(filtered_df, month_pick)

with tab3:
    photo_df = filtered_df[filtered_df["photo_path"].fillna("").astype(str).str.len() > 0].copy() if not filtered_df.empty else pd.DataFrame()
    if photo_df.empty:
        st.info("등록된 사진 앨범이 없습니다.")
    else:
        cols = st.columns(2)
        for i, (_, row) in enumerate(photo_df.iterrows()):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"{row['twin']} · {row['display_date'].strftime('%Y-%m-%d')} · {row['event_time']}")
                    p = Path(row["photo_path"])
                    if p.exists():
                        st.image(str(p), width="stretch")
                    if row["memo"]:
                        st.caption(row["memo"])

with tab4:
    with st.expander("가족 구성원 등록", expanded=True):
        with st.form("family_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("이름")
                role = st.text_input("역할")
            with c2:
                phone = st.text_input("연락처")
                note = st.text_input("메모")
            ok = st.form_submit_button("저장")
            if ok:
                if not name.strip():
                    st.error("이름을 입력하세요.")
                else:
                    add_family_member(name.strip(), role.strip(), phone.strip(), note.strip())
                    st.success("저장되었습니다.")
                    st.rerun()

    fam = load_family_members()
    if fam.empty:
        st.caption("등록된 가족 구성원이 없습니다.")
    else:
        for _, row in fam.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['name']}**")
                st.caption(f"역할: {row['role'] or '-'}")
                st.caption(f"연락처: {row['phone'] or '-'}")
                st.caption(f"메모: {row['note'] or '-'}")
                if st.button(f"구성원 삭제 #{row['id']}", key=f"family_del_{row['id']}"):
                    delete_family_member(row["id"])
                    st.rerun()

with tab5:
    msg = build_kakao_message_preview(filtered_df)
    st.text_area("오늘 발송 메시지 미리보기", value=msg, height=180)
    st.caption("현재 버전은 카카오 알림톡 실제 발송이 아니라 발송 대상 선별과 메시지 포맷 생성 단계입니다.")

with tab6:
    export_df = build_export_df(filtered_df)
    st.dataframe(export_df, use_container_width=True, hide_index=True)

    st.download_button(
        "CSV 다운로드",
        data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="twin_schedule_export.csv",
        mime="text/csv",
    )

    st.download_button(
        "JSON 백업",
        data=build_backup_json(),
        file_name="twin_schedule_backup.json",
        mime="application/json",
    )

    st.caption("장기 운영은 SQLite 대신 외부 DB, 업로드는 외부 스토리지로 전환하는 것이 적합합니다.")