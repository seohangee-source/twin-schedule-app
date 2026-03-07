import json
import sqlite3
from datetime import date, datetime, timedelta, time as dtime
from pathlib import Path
import calendar

import pandas as pd
import streamlit as st

# =========================================================
# 앱 2.0 : 쌍둥이 일정관리 (모바일 앱 UI 지향)
# 기능:
# - 월간 달력 UI
# - 일정 등록/수정/상태변경/삭제
# - 가족 공유 메모 / 보호자 관리
# - 사진 앨범
# - CSV/JSON 백업
# - 카카오 알림 연동용 메시지 포맷 생성(실제 발송은 별도 API 필요)
# - 안드로이드 앱 변환용 래핑 전제의 웹앱 구조
# =========================================================

st.set_page_config(
    page_title="쌍둥이 일정관리 앱 2.0",
    page_icon="📱",
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

COLOR_MAP = {
    "첫째": {"bg": "#fff1f5", "line": "#e11d48", "chip": "#ffe4ec", "text": "#9f1239"},
    "둘째": {"bg": "#eff6ff", "line": "#2563eb", "chip": "#dbeafe", "text": "#1d4ed8"},
    "공통": {"bg": "#f0fdf4", "line": "#16a34a", "chip": "#dcfce7", "text": "#166534"},
}


def inject_css():
    st.markdown(
        """
        <style>
            html, body, [class*="css"] {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
            }
            .block-container {
                max-width: 1040px;
                padding-top: 0.9rem;
                padding-bottom: 6rem;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }
            .hero {
                border-radius: 30px;
                padding: 22px 20px;
                background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
                color: white;
                box-shadow: 0 16px 40px rgba(15,23,42,0.18);
                margin-bottom: 14px;
            }
            .hero-title {
                font-size: 1.6rem;
                font-weight: 800;
                margin-bottom: 6px;
            }
            .hero-sub {
                font-size: 0.93rem;
                opacity: 0.92;
                line-height: 1.55;
            }
            .hero-stats {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 8px;
                margin-top: 14px;
            }
            .hero-stat {
                background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.10);
                backdrop-filter: blur(8px);
                border-radius: 18px;
                padding: 10px 8px;
                text-align: center;
            }
            .hero-stat-label {font-size: 0.74rem; opacity: 0.86;}
            .hero-stat-value {font-size: 1.1rem; font-weight: 800; margin-top: 2px;}
            .section-card {
                background: white;
                border: 1px solid #eef2f7;
                border-radius: 24px;
                padding: 14px;
                box-shadow: 0 10px 24px rgba(15,23,42,0.05);
                margin-bottom: 12px;
            }
            .section-title {
                font-size: 1.02rem;
                font-weight: 800;
                color: #111827;
                margin: 2px 0 10px 2px;
            }
            .pill {
                display: inline-block;
                border-radius: 999px;
                padding: 6px 11px;
                font-size: 0.76rem;
                font-weight: 700;
                margin-right: 6px;
                margin-bottom: 6px;
            }
            .timeline-day {
                font-size: 0.92rem;
                font-weight: 800;
                margin: 14px 0 8px 2px;
                color: #0f172a;
            }
            .timeline-item {
                border-radius: 22px;
                padding: 14px 14px 12px 14px;
                margin-bottom: 10px;
                border: 1px solid #edf2f7;
                box-shadow: 0 10px 18px rgba(15,23,42,0.05);
            }
            .timeline-title {
                font-size: 1rem;
                font-weight: 800;
                color: #0f172a;
                margin: 6px 0 4px 0;
            }
            .timeline-meta {
                font-size: 0.79rem;
                color: #475569;
                line-height: 1.45;
            }
            .timeline-memo {
                font-size: 0.86rem;
                color: #334155;
                line-height: 1.55;
                margin-top: 8px;
            }
            .calendar-grid {
                display: grid;
                grid-template-columns: repeat(7, minmax(0, 1fr));
                gap: 6px;
            }
            .weekday {
                text-align: center;
                font-size: 0.72rem;
                font-weight: 700;
                color: #64748b;
                padding: 4px 0 6px 0;
            }
            .cal-cell {
                min-height: 98px;
                background: #fff;
                border: 1px solid #eef2f7;
                border-radius: 18px;
                padding: 7px;
            }
            .cal-date {
                font-size: 0.83rem;
                font-weight: 800;
                color: #111827;
                margin-bottom: 6px;
            }
            .cal-badge {
                border-radius: 10px;
                padding: 4px 6px;
                font-size: 0.66rem;
                margin-bottom: 4px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .album-card {
                background: white;
                border: 1px solid #eef2f7;
                border-radius: 22px;
                padding: 10px;
                box-shadow: 0 8px 20px rgba(15,23,42,0.05);
                margin-bottom: 10px;
            }
            .family-item {
                border: 1px solid #e8eef6;
                border-radius: 18px;
                padding: 12px;
                margin-bottom: 8px;
                background: #fafcff;
            }
            .bottom-note {
                font-size: 0.76rem;
                color: #64748b;
                line-height: 1.55;
                margin-top: 10px;
            }
            .stButton > button, .stDownloadButton > button {
                border-radius: 14px;
                font-weight: 700;
                width: 100%;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DB
# =========================================================
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


# =========================================================
# 유틸 / CRUD
# =========================================================
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
        {"twin": "첫째", "title": "소아과 정기검진", "category": "병원", "event_date": str(date.today()), "event_time": "10:30", "memo": "예방접종 수첩 챙기기", "status": "예정", "repeat_rule": "없음", "remind_days_before": 1, "photo_path": None},
        {"twin": "둘째", "title": "수영 수업", "category": "학습", "event_date": str(date.today() + timedelta(days=1)), "event_time": "16:20", "memo": "수영복, 수건 준비", "status": "예정", "repeat_rule": "매주", "remind_days_before": 1, "photo_path": None},
        {"twin": "공통", "title": "가족 나들이", "category": "가족", "event_date": str(date.today() + timedelta(days=2)), "event_time": "11:00", "memo": "간식과 물 챙기기", "status": "예정", "repeat_rule": "없음", "remind_days_before": 1, "photo_path": None},
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
    return x[["id", "twin", "title", "category", "날짜", "event_time", "status", "repeat_rule", "remind_days_before", "memo"]].rename(
        columns={
            "id": "ID", "twin": "대상", "title": "일정", "category": "분류", "event_time": "시간",
            "status": "상태", "repeat_rule": "반복", "remind_days_before": "알림", "memo": "메모"
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


# =========================================================
# UI
# =========================================================
def render_header(stats):
    st.markdown(
        f"""
        <div class='hero'>
            <div class='hero-title'>📱 쌍둥이 일정관리 앱 2.0</div>
            <div class='hero-sub'>달력 UI · 가족 공유 · 사진 앨범 · 카카오 알림용 메시지 · 안드로이드 웹앱 전환을 고려한 구조입니다.</div>
            <div class='hero-stats'>
                <div class='hero-stat'><div class='hero-stat-label'>전체 일정</div><div class='hero-stat-value'>{stats['total']}</div></div>
                <div class='hero-stat'><div class='hero-stat-label'>오늘 일정</div><div class='hero-stat-value'>{stats['today']}</div></div>
                <div class='hero-stat'><div class='hero-stat-label'>예정</div><div class='hero-stat-value'>{stats['open']}</div></div>
                <div class='hero-stat'><div class='hero-stat-label'>완료</div><div class='hero-stat-value'>{stats['done']}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_quick_add():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>빠른 일정 등록</div>", unsafe_allow_html=True)
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
        memo = st.text_area("메모", height=70, placeholder="준비물, 장소, 주의사항")
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
                add_schedule({
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
                })
                st.success("일정이 저장되었습니다.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)



def render_filters():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>보기 필터</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.3])
    with c1:
        twin_filter = st.selectbox("대상", ["전체"] + TWIN_OPTIONS, label_visibility="collapsed")
    with c2:
        category_filter = st.selectbox("분류", ["전체"] + CATEGORY_OPTIONS, label_visibility="collapsed")
    with c3:
        status_filter = st.selectbox("상태", ["전체"] + STATUS_OPTIONS, label_visibility="collapsed")
    with c4:
        keyword = st.text_input("검색", placeholder="일정명 / 메모", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return twin_filter, category_filter, status_filter, keyword



def render_timeline(df):
    if df.empty:
        st.info("조건에 맞는 일정이 없습니다.")
        return
    grouped = list(df.groupby(df["display_date"].dt.strftime("%Y-%m-%d")))
    for day, group in grouped:
        dt = pd.to_datetime(day)
        weekday = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
        st.markdown(f"<div class='timeline-day'>{dt.month}.{dt.day} ({weekday})</div>", unsafe_allow_html=True)
        for _, row in group.iterrows():
            c = COLOR_MAP.get(row["twin"], COLOR_MAP["공통"])
            st.markdown(
                f"""
                <div class='timeline-item' style='background:{c['bg']}; border-left:7px solid {c['line']};'>
                    <span class='pill' style='background:{c['chip']}; color:{c['text']};'>{row['twin']}</span>
                    <span class='pill' style='background:#f1f5f9; color:#334155;'>{row['category'] or '일정'}</span>
                    <span class='pill' style='background:#f8fafc; color:#475569;'>{row['status'] or '예정'}</span>
                    <div class='timeline-title'>{row['title']}</div>
                    <div class='timeline-meta'>🕒 {row['event_time']} · 반복 {row.get('repeat_rule', '없음')} · 알림 {row.get('remind_days_before', 0)}일 전</div>
                    <div class='timeline-memo'>{row['memo'] or '메모 없음'}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2, b3 = st.columns(3)
            with b1:
                if row.get("status", "예정") != "완료" and st.button("완료", key=f"done_{row['id']}_{day}"):
                    update_schedule_status(row["id"], "완료")
                    st.rerun()
            with b2:
                if row.get("status", "예정") != "보류" and st.button("보류", key=f"hold_{row['id']}_{day}"):
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



def render_calendar(df, month_date):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>월간 달력</div>", unsafe_allow_html=True)
    year = month_date.year
    month = month_date.month
    cal = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)

    items = {}
    if not df.empty:
        for _, row in df.iterrows():
            d = row["display_date"].date()
            if d.year == year and d.month == month:
                items.setdefault(d, []).append(row)

    week_labels = ["월", "화", "수", "목", "금", "토", "일"]
    st.markdown("<div class='calendar-grid'>" + "".join([f"<div class='weekday'>{w}</div>" for w in week_labels]) + "</div>", unsafe_allow_html=True)

    for week in cal:
        html = []
        for d in week:
            parts = [f"<div class='cal-cell'><div class='cal-date'>{d.day}</div>"]
            day_items = items.get(d, [])
            for row in day_items[:3]:
                c = COLOR_MAP.get(row['twin'], COLOR_MAP['공통'])
                parts.append(f"<div class='cal-badge' style='background:{c['chip']}; color:{c['text']};'>{row['event_time']} {row['title']}</div>")
            if len(day_items) > 3:
                parts.append(f"<div style='font-size:0.66rem;color:#64748b;'>+{len(day_items)-3}건</div>")
            parts.append("</div>")
            html.append("".join(parts))
        st.markdown(f"<div class='calendar-grid'>{''.join(html)}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)



def render_album(df):
    photo_df = df[df["photo_path"].fillna("").astype(str).str.len() > 0].copy() if not df.empty else pd.DataFrame()
    if photo_df.empty:
        st.info("등록된 사진 앨범이 없습니다.")
        return
    cols = st.columns(2)
    for i, (_, row) in enumerate(photo_df.iterrows()):
        with cols[i % 2]:
            st.markdown("<div class='album-card'>", unsafe_allow_html=True)
            st.markdown(f"**{row['title']}**")
            st.caption(f"{row['twin']} · {row['display_date'].strftime('%Y-%m-%d')} · {row['event_time']}")
            p = Path(row["photo_path"])
            if p.exists():
                st.image(str(p), use_container_width=True)
            if row.get("memo"):
                st.caption(row["memo"])
            st.markdown("</div>", unsafe_allow_html=True)



def render_family():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>가족 공유</div>", unsafe_allow_html=True)
    with st.expander("가족 구성원 등록"):
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
            st.markdown("<div class='family-item'>", unsafe_allow_html=True)
            st.write(f"**{row['name']}** · {row['role'] or '-'}")
            st.caption(f"연락처: {row['phone'] or '-'}")
            st.caption(f"메모: {row['note'] or '-'}")
            if st.button(f"구성원 삭제 #{row['id']}", key=f"family_del_{row['id']}"):
                delete_family_member(row["id"])
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)



def render_kakao_alert_preview(df):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>카카오 알림용 메시지</div>", unsafe_allow_html=True)
    msg = build_kakao_message_preview(df)
    st.text_area("오늘 발송 메시지 미리보기", value=msg, height=180)
    st.caption("현재 버전은 카카오 알림톡 실제 전송이 아니라 메시지 포맷과 대상 선별까지 구현한 단계입니다. 실제 발송은 카카오 비즈메시지 API 또는 연동 서비스 설정이 추가로 필요합니다.")
    st.markdown("</div>", unsafe_allow_html=True)



def render_export(df):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>내보내기 / 백업</div>", unsafe_allow_html=True)
    export_df = build_export_df(df)
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
    st.markdown("<div class='bottom-note'>Android 앱 변환은 현재 Streamlit 웹앱을 WebView 래퍼(Flutter/React Native/Android Studio)로 감싸는 방식이 가장 현실적입니다. 장기 운영은 외부 DB와 스토리지로 전환하는 것이 적합합니다.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# 앱 실행
# =========================================================
inject_css()
init_db()
seed_if_empty()

base_df = load_schedules()
window_start = date.today() - timedelta(days=14)
window_end = date.today() + timedelta(days=60)
occ_df = expand_repeating_events(base_df, window_start, window_end)
stats = get_stats(occ_df)

render_header(stats)
render_quick_add()

twin_filter, category_filter, status_filter, keyword = render_filters()
filtered_df = filter_occurrences(occ_df, twin_filter, category_filter, status_filter, keyword, window_start, window_end)

selected_tab = st.segmented_control(
    "화면 선택",
    ["홈", "달력", "사진 앨범", "가족 공유", "카카오 알림", "백업"],
    default="홈",
    label_visibility="collapsed",
)

if selected_tab == "홈":
    render_timeline(filtered_df)
elif selected_tab == "달력":
    month_pick = st.date_input("기준월", value=date.today().replace(day=1), label_visibility="collapsed")
    render_calendar(filtered_df, month_pick)
elif selected_tab == "사진 앨범":
    render_album(filtered_df)
elif selected_tab == "가족 공유":
    render_family()
elif selected_tab == "카카오 알림":
    render_kakao_alert_preview(filtered_df)
elif selected_tab == "백업":
    render_export(filtered_df)

st.caption("※ 현재 2.0 버전은 모바일 앱 수준 UI에 맞춰 카드형 화면과 기능 분리를 적용했습니다. 카카오 실제 발송, 다중 사용자 인증, 안드로이드 APK 배포는 다음 단계에서 외부 서비스 연동이 필요합니다.")
