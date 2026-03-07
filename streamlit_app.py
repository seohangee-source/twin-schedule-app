import json
import sqlite3
from datetime import date, datetime, timedelta, time as dtime
from pathlib import Path

import pandas as pd
import streamlit as st

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="쌍둥이 일정관리",
    page_icon="🗓️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path("twin_schedule.db")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

TWIN_OPTIONS = ["첫째", "둘째", "공통"]
CATEGORY_OPTIONS = ["일정", "병원", "학습", "행사", "가족", "준비물", "사진기록"]
REPEAT_OPTIONS = ["없음", "매일", "매주", "매월"]
STATUS_OPTIONS = ["예정", "완료", "보류"]

COLOR_MAP = {
    "첫째": "#FFE4EC",
    "둘째": "#E3F2FD",
    "공통": "#E8F5E9",
}

ACCENT_MAP = {
    "첫째": "#D81B60",
    "둘째": "#1E88E5",
    "공통": "#43A047",
}


def inject_css():
    st.markdown(
        """
        <style>
            .main > div {padding-top: 1rem;}
            .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
            .app-title {
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 0.2rem;
            }
            .app-subtitle {
                color: #666;
                margin-bottom: 1rem;
            }
            .stat-card {
                border-radius: 18px;
                padding: 18px 18px 16px 18px;
                border: 1px solid #e9e9e9;
                background: white;
                box-shadow: 0 2px 10px rgba(0,0,0,0.03);
                height: 100%;
            }
            .stat-label {
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 6px;
            }
            .stat-value {
                font-size: 1.7rem;
                font-weight: 700;
            }
            .schedule-card {
                border-radius: 18px;
                padding: 14px 16px;
                margin-bottom: 12px;
                border: 1px solid #ececec;
                box-shadow: 0 1px 8px rgba(0,0,0,0.03);
            }
            .section-title {
                font-size: 1.2rem;
                font-weight: 700;
                margin: 0.6rem 0 0.8rem;
            }
            .tiny {
                font-size: 0.84rem;
                color: #666;
            }
            .day-chip {
                display: inline-block;
                padding: 6px 12px;
                border-radius: 999px;
                background: #f3f4f6;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .calendar-cell {
                min-height: 120px;
                border: 1px solid #ececec;
                border-radius: 14px;
                padding: 8px;
                background: white;
            }
            .calendar-date {
                font-weight: 700;
                margin-bottom: 8px;
            }
            .calendar-item {
                font-size: 0.78rem;
                border-radius: 10px;
                padding: 5px 7px;
                margin-bottom: 5px;
                color: #222;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .family-box {
                border: 1px dashed #d8d8d8;
                border-radius: 16px;
                padding: 14px;
                background: #fafafa;
            }
            .footer-note {
                color: #888;
                font-size: 0.82rem;
                margin-top: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# DB
# =========================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            twin TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            memo TEXT,
            status TEXT NOT NULL DEFAULT '예정',
            repeat_rule TEXT NOT NULL DEFAULT '없음',
            remind_days_before INTEGER NOT NULL DEFAULT 0,
            photo_path TEXT,
            created_at TEXT NOT NULL
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
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# =========================
# 유틸
# =========================
def fmt_date(d):
    try:
        return pd.to_datetime(d).strftime("%Y-%m-%d")
    except Exception:
        return ""



def fmt_kor_date(d):
    try:
        dt = pd.to_datetime(d)
        weekday = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
        return f"{dt.year}.{dt.month:02d}.{dt.day:02d} ({weekday})"
    except Exception:
        return str(d)



def fmt_time(t):
    return str(t)[:5] if t else ""



def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = uploaded_file.name.replace(" ", "_")
    file_path = UPLOAD_DIR / f"{timestamp}_{safe_name}"
    file_path.write_bytes(uploaded_file.getbuffer())
    return str(file_path)



def add_schedule(twin, title, category, event_date, event_time, memo, status, repeat_rule, remind_days_before, photo_path):
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
            twin,
            title,
            category,
            fmt_date(event_date),
            fmt_time(event_time),
            memo,
            status,
            repeat_rule,
            int(remind_days_before),
            photo_path,
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
    if df.empty:
        return df
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    return df



def load_family_members():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM family_members ORDER BY id", conn)
    conn.close()
    return df



def create_demo_data_if_empty():
    df = load_schedules()
    if not df.empty:
        return
    demo = [
        ("첫째", "소아과 정기검진", "병원", date.today(), "10:30", "예방접종 수첩 지참", "예정", "없음", 1, None),
        ("둘째", "수영 수업", "학습", date.today() + timedelta(days=1), "16:00", "수영복, 수건 준비", "예정", "매주", 1, None),
        ("공통", "가족 나들이", "가족", date.today() + timedelta(days=2), "11:00", "도시락 챙기기", "예정", "없음", 1, None),
        ("첫째", "성장 사진 촬영", "사진기록", date.today() + timedelta(days=3), "18:30", "같은 배경에서 촬영", "예정", "매월", 2, None),
    ]
    for row in demo:
        add_schedule(*row)

    fam = load_family_members()
    if fam.empty:
        add_family_member("엄마", "보호자", "010-0000-0000", "평일 등원 담당")
        add_family_member("아빠", "보호자", "010-1111-1111", "병원 예약 담당")



def expand_repeating_events(df, window_start, window_end):
    if df.empty:
        return df.copy()

    rows = []
    for _, r in df.iterrows():
        base_date = pd.to_datetime(r["event_date"]).date() if pd.notnull(r["event_date"]) else None
        if not base_date:
            continue

        repeat_rule = r["repeat_rule"]
        if repeat_rule == "없음":
            if window_start <= base_date <= window_end:
                rr = r.copy()
                rr["display_date"] = pd.to_datetime(base_date)
                rows.append(rr)
            continue

        current = base_date
        while current <= window_end:
            if current >= window_start:
                rr = r.copy()
                rr["display_date"] = pd.to_datetime(current)
                rows.append(rr)

            if repeat_rule == "매일":
                current += timedelta(days=1)
            elif repeat_rule == "매주":
                current += timedelta(days=7)
            elif repeat_rule == "매월":
                month = current.month + 1
                year = current.year
                if month == 13:
                    month = 1
                    year += 1
                day = min(current.day, 28)
                current = date(year, month, day)
            else:
                break

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["display_date"] = pd.to_datetime(out["display_date"])
    out = out.sort_values(["display_date", "event_time", "id"]).reset_index(drop=True)
    return out



def get_dashboard_stats(df_occ):
    today = pd.Timestamp(date.today())
    if df_occ.empty:
        return {
            "total": 0,
            "today": 0,
            "upcoming": 0,
            "done": 0,
            "photo": 0,
        }
    total = len(df_occ)
    today_cnt = int((df_occ["display_date"].dt.date == date.today()).sum())
    upcoming = int((df_occ["display_date"] >= today).sum())
    done = int((df_occ["status"] == "완료").sum())
    photo = int(df_occ["photo_path"].fillna("").astype(str).str.len().gt(0).sum())
    return {
        "total": total,
        "today": today_cnt,
        "upcoming": upcoming,
        "done": done,
        "photo": photo,
    }



def build_export_dataframe(df_occ):
    if df_occ.empty:
        return pd.DataFrame(columns=["ID", "대상", "일정", "분류", "날짜", "시간", "상태", "반복", "알림", "메모", "사진"])
    out = df_occ.copy()
    out["날짜"] = out["display_date"].dt.strftime("%Y-%m-%d")
    out["사진"] = out["photo_path"].apply(lambda x: "있음" if pd.notnull(x) and str(x).strip() else "없음")
    return out[["id", "twin", "title", "category", "날짜", "event_time", "status", "repeat_rule", "remind_days_before", "memo", "사진"]].rename(
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



def filter_occurrences(df_occ, target, category, status, keyword, start_date, end_date):
    if df_occ.empty:
        return df_occ
    out = df_occ.copy()
    if target != "전체":
        out = out[out["twin"] == target]
    if category != "전체":
        out = out[out["category"] == category]
    if status != "전체":
        out = out[out["status"] == status]
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
    out = out.sort_values(["display_date", "event_time", "id"]).reset_index(drop=True)
    return out



def render_stat_cards(stats):
    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "전체 일정", stats["total"]),
        (c2, "오늘 일정", stats["today"]),
        (c3, "예정 일정", stats["upcoming"]),
        (c4, "완료 건수", stats["done"]),
        (c5, "사진 기록", stats["photo"]),
    ]
    for col, label, value in cards:
        with col:
            st.markdown(
                f"<div class='stat-card'><div class='stat-label'>{label}</div><div class='stat-value'>{value}</div></div>",
                unsafe_allow_html=True,
            )



def render_alerts(df_occ):
    if df_occ.empty:
        st.info("등록된 일정이 없습니다. 좌측에서 일정을 추가해 주세요.")
        return

    today_dt = date.today()
    alerts = []
    for _, row in df_occ.iterrows():
        remind = int(row.get("remind_days_before", 0) or 0)
        display_date = row["display_date"].date()
        diff = (display_date - today_dt).days
        if row["status"] != "완료" and diff == remind:
            alerts.append((display_date, row["twin"], row["title"], remind))

    if alerts:
        msg = " / ".join([f"{a[0]} {a[1]} - {a[2]}" for a in alerts[:6]])
        st.warning(f"알림 대상 일정: {msg}")
    else:
        st.caption("오늘 기준 알림 대상 일정이 없습니다.")



def render_timeline(df_occ):
    st.markdown("<div class='section-title'>일정 타임라인</div>", unsafe_allow_html=True)
    if df_occ.empty:
        st.info("조건에 맞는 일정이 없습니다.")
        return

    grouped = list(df_occ.groupby(df_occ["display_date"].dt.strftime("%Y-%m-%d")))
    for day_str, group in grouped:
        st.markdown(f"<div class='day-chip'>{fmt_kor_date(day_str)}</div>", unsafe_allow_html=True)
        for _, row in group.iterrows():
            bg = COLOR_MAP.get(row["twin"], "#f7f7f7")
            acc = ACCENT_MAP.get(row["twin"], "#888")
            photo_html = "📷 사진" if pd.notnull(row.get("photo_path")) and str(row.get("photo_path")).strip() else ""
            st.markdown(
                f"""
                <div class='schedule-card' style='background:{bg}; border-left:8px solid {acc};'>
                    <div style='display:flex; justify-content:space-between; gap:12px; align-items:flex-start;'>
                        <div>
                            <div style='font-size:0.82rem; color:#555; margin-bottom:4px;'>
                                {row['twin']} · {row['category']} · {row['event_time']} · {row['status']} · 반복:{row['repeat_rule']}
                            </div>
                            <div style='font-size:1.02rem; font-weight:700; margin-bottom:4px;'>{row['title']}</div>
                            <div style='font-size:0.87rem; color:#444;'>{row['memo'] or '메모 없음'}</div>
                            <div style='font-size:0.8rem; color:#666; margin-top:6px;'>{photo_html}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            b1, b2, b3 = st.columns([1, 1, 1.2])
            with b1:
                if row["status"] != "완료" and st.button(f"완료 #{row['id']}", key=f"done_{row['id']}_{day_str}"):
                    update_schedule_status(row["id"], "완료")
                    st.rerun()
            with b2:
                if row["status"] != "보류" and st.button(f"보류 #{row['id']}", key=f"hold_{row['id']}_{day_str}"):
                    update_schedule_status(row["id"], "보류")
                    st.rerun()
            with b3:
                if st.button(f"삭제 #{row['id']}", key=f"del_{row['id']}_{day_str}"):
                    delete_schedule(row["id"])
                    st.rerun()

            photo_path = row.get("photo_path")
            if pd.notnull(photo_path) and str(photo_path).strip() and Path(photo_path).exists():
                try:
                    st.image(photo_path, width=260)
                except Exception:
                    st.caption("사진 미리보기를 불러오지 못했습니다.")



def render_calendar_month(df_occ, selected_month):
    st.markdown("<div class='section-title'>월간 캘린더</div>", unsafe_allow_html=True)

    month_start = selected_month.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)

    first_weekday = month_start.weekday()  # Mon=0
    days_in_month = (next_month - timedelta(days=1)).day
    total_cells = ((first_weekday + days_in_month + 6) // 7) * 7

    items_by_day = {}
    if not df_occ.empty:
        mm = df_occ[
            (df_occ["display_date"].dt.date >= month_start)
            & (df_occ["display_date"].dt.date < next_month)
        ]
        for _, row in mm.iterrows():
            items_by_day.setdefault(row["display_date"].date(), []).append(row)

    week_labels = ["월", "화", "수", "목", "금", "토", "일"]
    cols = st.columns(7)
    for i, lab in enumerate(week_labels):
        cols[i].markdown(f"**{lab}**")

    cursor = month_start - timedelta(days=first_weekday)
    for _ in range(total_cells // 7):
        week_cols = st.columns(7)
        for j in range(7):
            current = cursor + timedelta(days=j)
            day_items = items_by_day.get(current, [])
            cell_html = [f"<div class='calendar-cell'><div class='calendar-date'>{current.day}</div>"]
            for item in day_items[:4]:
                bg = COLOR_MAP.get(item["twin"], "#f7f7f7")
                cell_html.append(
                    f"<div class='calendar-item' style='background:{bg};'>{item['event_time']} {item['title']}</div>"
                )
            if len(day_items) > 4:
                cell_html.append(f"<div class='tiny'>외 {len(day_items)-4}건</div>")
            cell_html.append("</div>")
            week_cols[j].markdown("".join(cell_html), unsafe_allow_html=True)
        cursor += timedelta(days=7)



def render_growth_gallery(df_occ):
    st.markdown("<div class='section-title'>사진 기록</div>", unsafe_allow_html=True)
    photo_df = df_occ[df_occ["photo_path"].fillna("").astype(str).str.len() > 0].copy() if not df_occ.empty else pd.DataFrame()
    if photo_df.empty:
        st.info("등록된 사진 기록이 없습니다.")
        return

    cols = st.columns(3)
    for idx, (_, row) in enumerate(photo_df.iterrows()):
        col = cols[idx % 3]
        with col:
            st.markdown(f"**{row['title']}**")
            st.caption(f"{row['twin']} · {row['display_date'].strftime('%Y-%m-%d')} · {row['event_time']}")
            try:
                if Path(row["photo_path"]).exists():
                    st.image(row["photo_path"], use_container_width=True)
            except Exception:
                st.caption("이미지 표시 실패")
            if row.get("memo"):
                st.caption(row["memo"])



def render_family_members():
    st.markdown("<div class='section-title'>가족 공유 메모</div>", unsafe_allow_html=True)
    fam = load_family_members()
    with st.expander("보호자/가족 구성원 등록", expanded=False):
        with st.form("family_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("이름")
                role = st.text_input("역할")
            with c2:
                phone = st.text_input("연락처")
                note = st.text_input("메모")
            submitted = st.form_submit_button("가족 구성원 저장")
            if submitted:
                if not name.strip():
                    st.error("이름은 필수입니다.")
                else:
                    add_family_member(name.strip(), role.strip(), phone.strip(), note.strip())
                    st.success("저장되었습니다.")
                    st.rerun()

    if fam.empty:
        st.caption("등록된 가족 구성원이 없습니다.")
        return

    for _, row in fam.iterrows():
        st.markdown("<div class='family-box'>", unsafe_allow_html=True)
        st.write(f"**{row['name']}**  |  {row['role'] or '-'}")
        st.caption(f"연락처: {row['phone'] or '-'}")
        st.caption(f"메모: {row['note'] or '-'}")
        if st.button(f"구성원 삭제 #{row['id']}", key=f"family_del_{row['id']}"):
            delete_family_member(row["id"])
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# =========================
# 앱 시작
# =========================
inject_css()
init_db()
create_demo_data_if_empty()

st.markdown("<div class='app-title'>🗓️ 쌍둥이 일정관리 앱</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='app-subtitle'>달력형 일정 · 알림 · 자동저장(DB) · 가족 공유 · 사진 기록 · 핸드폰 사용까지 고려한 Python(Streamlit) 버전</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("일정 등록")
    with st.form("add_schedule_form", clear_on_submit=True):
        twin = st.selectbox("대상", TWIN_OPTIONS)
        title = st.text_input("일정명")
        category = st.selectbox("분류", CATEGORY_OPTIONS)
        event_date = st.date_input("날짜", value=date.today())
        event_time = st.time_input("시간", value=dtime(9, 0))
        memo = st.text_area("메모", height=80, placeholder="준비물, 병원 위치, 특이사항 등")
        status = st.selectbox("상태", STATUS_OPTIONS, index=0)
        repeat_rule = st.selectbox("반복", REPEAT_OPTIONS, index=0)
        remind_days_before = st.selectbox("사전 알림", [0, 1, 2, 3, 7], index=1, help="0이면 당일 알림")
        photo = st.file_uploader("사진 첨부", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("일정 저장")

        if submitted:
            if not title.strip():
                st.error("일정명은 필수입니다.")
            else:
                photo_path = save_uploaded_file(photo)
                add_schedule(
                    twin=twin,
                    title=title.strip(),
                    category=category,
                    event_date=event_date,
                    event_time=event_time,
                    memo=memo.strip(),
                    status=status,
                    repeat_rule=repeat_rule,
                    remind_days_before=remind_days_before,
                    photo_path=photo_path,
                )
                st.success("일정이 저장되었습니다.")
                st.rerun()

    st.divider()
    st.subheader("조회 조건")
    target_filter = st.selectbox("대상 필터", ["전체"] + TWIN_OPTIONS, index=0)
    category_filter = st.selectbox("분류 필터", ["전체"] + CATEGORY_OPTIONS, index=0)
    status_filter = st.selectbox("상태 필터", ["전체"] + STATUS_OPTIONS, index=0)
    keyword = st.text_input("검색", placeholder="일정명, 메모, 분류")
    start_date = st.date_input("조회 시작일", value=date.today() - timedelta(days=7))
    end_date = st.date_input("조회 종료일", value=date.today() + timedelta(days=31))
    month_picker = st.date_input("캘린더 기준월", value=date.today().replace(day=1))

    st.divider()
    st.subheader("데이터 내보내기")
    base_df = load_schedules()
    occ_for_export = expand_repeating_events(base_df, start_date, end_date)
    filtered_export = filter_occurrences(
        occ_for_export,
        target_filter,
        category_filter,
        status_filter,
        keyword,
        start_date,
        end_date,
    )
    export_df = build_export_dataframe(filtered_export)
    st.download_button(
        "CSV 다운로드",
        data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="twin_schedule_export.csv",
        mime="text/csv",
        use_container_width=True,
    )

    backup_payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "schedules": load_schedules().assign(event_date=lambda x: x["event_date"].astype(str)).to_dict(orient="records"),
        "family_members": load_family_members().to_dict(orient="records"),
    }
    st.download_button(
        "JSON 백업",
        data=json.dumps(backup_payload, ensure_ascii=False, indent=2),
        file_name="twin_schedule_backup.json",
        mime="application/json",
        use_container_width=True,
    )

# 데이터 로드 및 가공
base_df = load_schedules()
occ_df = expand_repeating_events(base_df, start_date, end_date)
filtered_df = filter_occurrences(
    occ_df,
    target_filter,
    category_filter,
    status_filter,
    keyword,
    start_date,
    end_date,
)
stats = get_dashboard_stats(filtered_df)

render_stat_cards(stats)
render_alerts(filtered_df)

# 탭
main_tabs = st.tabs(["타임라인", "월간 캘린더", "표 보기", "사진 기록", "가족 공유"])

with main_tabs[0]:
    render_timeline(filtered_df)

with main_tabs[1]:
    render_calendar_month(filtered_df, month_picker.replace(day=1))

with main_tabs[2]:
    st.markdown("<div class='section-title'>표 형식 조회</div>", unsafe_allow_html=True)
    grid_df = build_export_dataframe(filtered_df)
    st.dataframe(grid_df, use_container_width=True, hide_index=True)

with main_tabs[3]:
    render_growth_gallery(filtered_df)

with main_tabs[4]:
    render_family_members()

st.markdown("<div class='footer-note'>※ 푸시알림은 Streamlit 단독으로는 제한적입니다. 현재 버전은 '오늘 알림 대상 일정'을 화면 상단에 표시하는 방식입니다. 진짜 휴대폰 푸시까지 하려면 카카오 알림/텔레그램/이메일 연동 또는 별도 모바일 앱(Flutter/React Native) 확장이 필요합니다.</div>", unsafe_allow_html=True)

st.markdown("<div class='footer-note'>※ 이 버전은 SQLite 자동저장이라 앱을 껐다 켜도 데이터가 유지됩니다. 같은 폴더에 twin_schedule.db 파일이 생성됩니다.</div>", unsafe_allow_html=True)
