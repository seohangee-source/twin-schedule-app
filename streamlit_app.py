import sqlite3
from pathlib import Path
from datetime import datetime, date, time
import pandas as pd
import streamlit as st

# ---------------------------------
# 기본 설정
# ---------------------------------
st.set_page_config(
    page_title="서현우 ❤️ 서지후 일정관리",
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

TARGET_OPTIONS = [
    "첫째",
    "둘째",
    "가족",
    "부모",
    "전체",
    "기타"
]

STATUS_OPTIONS = ["예정", "완료"]


# ---------------------------------
# DB 함수
# ---------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target TEXT,
            category TEXT,
            schedule_dt TEXT,
            status TEXT DEFAULT '예정',
            memo TEXT
        )
    """)
    conn.commit()
    conn.close()


def load_data():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM schedule ORDER BY schedule_dt ASC, id DESC",
        conn
    )
    conn.close()
    return df


def insert_schedule(title, target, category, schedule_dt, status, memo):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO schedule (title, target, category, schedule_dt, status, memo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, target, category, schedule_dt, status, memo))
    conn.commit()
    conn.close()


def mark_done(row_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE schedule SET status='완료' WHERE id=?", (row_id,))
    conn.commit()
    conn.close()


def delete_row(row_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM schedule WHERE id=?", (row_id,))
    conn.commit()
    conn.close()


def update_row(row_id, title, target, category, schedule_dt, status, memo):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE schedule
        SET title=?, target=?, category=?, schedule_dt=?, status=?, memo=?
        WHERE id=?
    """, (title, target, category, schedule_dt, status, memo, row_id))
    conn.commit()
    conn.close()


def insert_sample_if_empty():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schedule")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute("""
            INSERT INTO schedule (title, target, category, schedule_dt, status, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "소아과 검진",
            "첫째",
            "병원",
            "2026-03-08 10:30",
            "예정",
            "예방접종 수첩 챙기기"
        ))
        conn.commit()

    conn.close()


# ---------------------------------
# 유틸
# ---------------------------------
def split_schedule_dt(schedule_dt_str):
    """
    'YYYY-MM-DD HH:MM' 형식을 date, time 객체로 분리
    실패 시 오늘 날짜 / 현재 시간 기본값 사용
    """
    try:
        dt = datetime.strptime(schedule_dt_str, "%Y-%m-%d %H:%M")
        return dt.date(), dt.time().replace(second=0, microsecond=0)
    except Exception:
        now = datetime.now()
        return now.date(), now.time().replace(second=0, microsecond=0)


def format_schedule_dt(d: date, t: time):
    return f"{d.strftime('%Y-%m-%d')} {t.strftime('%H:%M')}"


# ---------------------------------
# 초기화
# ---------------------------------
init_db()
insert_sample_if_empty()

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None


# ---------------------------------
# 스타일
# ---------------------------------
st.markdown("""
<style>
/* 전체 여백 */
.block-container {
    padding-top: 0.9rem !important;
    padding-bottom: 1.2rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    max-width: 100% !important;
}

/* 타이틀 */
.app-title {
    font-size: 2.05rem;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 0.55rem;
    color: #1f1f1f;
}

/* 섹션 제목 */
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.65rem;
    color: #222;
}

/* 카드 텍스트 */
.card-title {
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.4;
    margin-bottom: 0.55rem;
    color: #222;
}

.card-line {
    font-size: 0.96rem;
    line-height: 1.58;
    margin-bottom: 0.18rem;
    color: #333;
    word-break: keep-all;
}

.card-memo {
    font-size: 0.88rem;
    line-height: 1.42;
    color: #777;
    margin-top: 0.4rem;
    margin-bottom: 0.55rem;
    word-break: keep-all;
}

/* 버튼 */
.stButton > button {
    width: 100% !important;
    min-height: 40px !important;
    border-radius: 10px !important;
    font-size: 0.90rem !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
    padding: 0.18rem 0.20rem !important;
}

/* 열 간격 */
[data-testid="stHorizontalBlock"] {
    gap: 0.32rem !important;
}

/* 입력 UI */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea {
    border-radius: 12px !important;
}

/* 모바일 */
@media (max-width: 768px) {
    .block-container {
        padding-top: 0.7rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.55rem !important;
        padding-right: 0.55rem !important;
    }

    .app-title {
        font-size: 1.72rem;
        margin-bottom: 0.45rem;
    }

    .section-title {
        font-size: 0.98rem;
        margin-bottom: 0.55rem;
    }

    .card-title {
        font-size: 0.98rem;
        margin-bottom: 0.42rem;
    }

    .card-line {
        font-size: 0.88rem;
        line-height: 1.48;
        margin-bottom: 0.14rem;
    }

    .card-memo {
        font-size: 0.80rem;
        line-height: 1.35;
        margin-top: 0.28rem;
        margin-bottom: 0.42rem;
    }

    .stButton > button {
        min-height: 34px !important;
        border-radius: 9px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        padding: 0.05rem 0.08rem !important;
        letter-spacing: -0.02em !important;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 0.18rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------
# 타이틀
# ---------------------------------
st.markdown('<div class="app-title">서현우 ❤️ 서지후 일정관리</div>', unsafe_allow_html=True)


# ---------------------------------
# 탭
# ---------------------------------
tab1, tab2, tab3 = st.tabs(["홈", "달력", "백업"])


# ---------------------------------
# 홈 탭
# ---------------------------------
with tab1:
    # 일정 추가
    with st.container(border=True):
        st.markdown('<div class="section-title">일정 추가</div>', unsafe_allow_html=True)

        add_title = st.text_input(
            "일정명",
            placeholder="예: 소아과 검진",
            key="add_title"
        )

        add_col1, add_col2 = st.columns(2)
        with add_col1:
            add_target = st.selectbox(
                "대상",
                TARGET_OPTIONS,
                index=0,
                key="add_target"
            )
        with add_col2:
            add_category = st.selectbox(
                "분류",
                CATEGORY_OPTIONS,
                index=0,
                key="add_category"
            )

        add_col3, add_col4 = st.columns(2)
        with add_col3:
            add_date = st.date_input("날짜", key="add_date")
        with add_col4:
            add_time = st.time_input("시간", key="add_time")

        add_memo = st.text_area(
            "메모",
            placeholder="예: 예방접종 수첩 챙기기",
            key="add_memo"
        )

        if st.button("일정 추가", use_container_width=True, key="add_submit"):
            title = add_title.strip()
            memo = add_memo.strip()

            if not title:
                st.warning("일정명을 입력하세요.")
            else:
                schedule_dt = format_schedule_dt(add_date, add_time)
                insert_schedule(
                    title=title,
                    target=add_target,
                    category=add_category,
                    schedule_dt=schedule_dt,
                    status="예정",
                    memo=memo
                )
                st.success("일정을 추가했습니다.")
                st.rerun()

    # 필터
    status_filter = st.selectbox(
        "상태",
        ["전체"] + STATUS_OPTIONS,
        index=0,
        key="status_filter"
    )
    search_text = st.text_input(
        "검색",
        placeholder="일정명 / 메모",
        key="search_text"
    )

    # 데이터 로드 및 필터
    df = load_data()

    if not df.empty:
        if status_filter != "전체":
            df = df[df["status"] == status_filter]

        if search_text.strip():
            keyword = search_text.strip()
            df = df[
                df["title"].fillna("").str.contains(keyword, case=False, na=False) |
                df["memo"].fillna("").str.contains(keyword, case=False, na=False)
            ]

    # 카드 출력
    if df.empty:
        st.info("표시할 일정이 없습니다.")
    else:
        for _, row in df.iterrows():
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="card-title">일정 : {row['title']}</div>
                    <div class="card-line"><b>대상 :</b> {row['target'] if pd.notna(row['target']) else ''}</div>
                    <div class="card-line"><b>분류 :</b> {row['category'] if pd.notna(row['category']) else ''}</div>
                    <div class="card-line"><b>날짜 :</b> {row['schedule_dt'] if pd.notna(row['schedule_dt']) else ''}</div>
                    <div class="card-line"><b>상태 :</b> {row['status'] if pd.notna(row['status']) else ''}</div>
                    <div class="card-memo">{row['memo'] if pd.notna(row['memo']) else ''}</div>
                    """,
                    unsafe_allow_html=True
                )

                # 카드 내부 하단 버튼 1줄
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1], gap="small")

                with btn_col1:
                    if st.button("완료", key=f"done_{row['id']}", use_container_width=True):
                        mark_done(row["id"])
                        st.rerun()

                with btn_col2:
                    if st.button("삭제", key=f"delete_{row['id']}", use_container_width=True):
                        delete_row(row["id"])
                        if st.session_state.edit_id == row["id"]:
                            st.session_state.edit_id = None
                        st.rerun()

                with btn_col3:
                    if st.button("수정", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state.edit_id = row["id"]
                        st.rerun()

            # 수정 영역
            if st.session_state.edit_id == row["id"]:
                with st.container(border=True):
                    st.markdown('<div class="section-title">일정 수정</div>', unsafe_allow_html=True)

                    current_title = row["title"] if pd.notna(row["title"]) else ""
                    current_target = row["target"] if pd.notna(row["target"]) else TARGET_OPTIONS[0]
                    current_category = row["category"] if pd.notna(row["category"]) else CATEGORY_OPTIONS[0]
                    current_status = row["status"] if pd.notna(row["status"]) else "예정"
                    current_memo = row["memo"] if pd.notna(row["memo"]) else ""
                    current_date, current_time = split_schedule_dt(
                        row["schedule_dt"] if pd.notna(row["schedule_dt"]) else ""
                    )

                    edit_title = st.text_input(
                        "일정",
                        value=current_title,
                        key=f"title_{row['id']}"
                    )

                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        edit_target = st.selectbox(
                            "대상",
                            TARGET_OPTIONS,
                            index=TARGET_OPTIONS.index(current_target) if current_target in TARGET_OPTIONS else 0,
                            key=f"target_{row['id']}"
                        )
                    with edit_col2:
                        edit_category = st.selectbox(
                            "분류",
                            CATEGORY_OPTIONS,
                            index=CATEGORY_OPTIONS.index(current_category) if current_category in CATEGORY_OPTIONS else 0,
                            key=f"category_{row['id']}"
                        )

                    edit_col3, edit_col4 = st.columns(2)
                    with edit_col3:
                        edit_date = st.date_input(
                            "날짜",
                            value=current_date,
                            key=f"date_{row['id']}"
                        )
                    with edit_col4:
                        edit_time = st.time_input(
                            "시간",
                            value=current_time,
                            key=f"time_{row['id']}"
                        )

                    edit_status = st.selectbox(
                        "상태",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0,
                        key=f"status_{row['id']}"
                    )

                    edit_memo = st.text_area(
                        "메모",
                        value=current_memo,
                        key=f"memo_{row['id']}"
                    )

                    save_col1, save_col2 = st.columns(2, gap="small")

                    with save_col1:
                        if st.button("저장", key=f"save_{row['id']}", use_container_width=True):
                            if not edit_title.strip():
                                st.warning("일정명을 입력하세요.")
                            else:
                                update_row(
                                    row["id"],
                                    edit_title.strip(),
                                    edit_target,
                                    edit_category,
                                    format_schedule_dt(edit_date, edit_time),
                                    edit_status,
                                    edit_memo.strip()
                                )
                                st.session_state.edit_id = None
                                st.rerun()

                    with save_col2:
                        if st.button("취소", key=f"cancel_{row['id']}", use_container_width=True):
                            st.session_state.edit_id = None
                            st.rerun()


# ---------------------------------
# 달력 탭
# ---------------------------------
with tab2:
    st.markdown('<div class="section-title">달력</div>', unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.info("일정이 없습니다.")
    else:
        show_df = df.copy().rename(columns={
            "title": "일정",
            "target": "대상",
            "category": "분류",
            "schedule_dt": "날짜",
            "status": "상태",
            "memo": "메모"
        })
        st.dataframe(show_df, use_container_width=True, hide_index=True)


# ---------------------------------
# 백업 탭
# ---------------------------------
with tab3:
    st.markdown('<div class="section-title">백업</div>', unsafe_allow_html=True)

    df = load_data()
    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name="twin_schedule_backup.csv",
        mime="text/csv",
        use_container_width=True
    )