import sqlite3
from pathlib import Path
from datetime import datetime
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

STATUS_OPTIONS = ["예정", "완료"]


# ---------------------------------
# DB
# ---------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
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


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_data():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM schedule ORDER BY schedule_dt ASC", conn)
    conn.close()
    return df


def insert_sample_if_empty():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schedule")
    cnt = cur.fetchone()[0]

    if cnt == 0:
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


init_db()
insert_sample_if_empty()


# ---------------------------------
# 세션 상태
# ---------------------------------
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None


# ---------------------------------
# CSS
# ---------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 0.55rem !important;
    padding-bottom: 2rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    max-width: 100% !important;
}

h1, h2, h3 {
    margin-top: 0 !important;
}

div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stHorizontalBlock"]) {
    width: 100%;
}

div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label {
    font-size: 0.95rem !important;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea {
    border-radius: 12px !important;
}

.card-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.6rem;
    line-height: 1.4;
}

.card-line {
    font-size: 1.02rem;
    line-height: 1.65;
    margin-bottom: 0.2rem;
    word-break: keep-all;
}

.card-memo {
    font-size: 0.95rem;
    color: #666;
    margin-top: 0.4rem;
    margin-bottom: 0.7rem;
    line-height: 1.5;
    word-break: keep-all;
}

.stButton > button {
    width: 100% !important;
    min-height: 42px !important;
    border-radius: 12px !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    padding: 0.3rem 0.4rem !important;
}

[data-testid="stHorizontalBlock"] {
    gap: 0.4rem !important;
}

@media (max-width: 768px) {
    .block-container {
        padding-top: 0.45rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-bottom: 1.2rem !important;
    }

    .card-title {
        font-size: 1.02rem;
        margin-bottom: 0.45rem;
    }

    .card-line {
        font-size: 0.92rem;
        line-height: 1.55;
    }

    .card-memo {
        font-size: 0.86rem;
        margin-top: 0.3rem;
        margin-bottom: 0.55rem;
        line-height: 1.42;
    }

    .stButton > button {
        min-height: 36px !important;
        border-radius: 10px !important;
        font-size: 0.8rem !important;
        padding: 0.15rem 0.2rem !important;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 0.25rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------
# 상단 필터
# ---------------------------------
status_filter = st.selectbox("상태", ["전체"] + STATUS_OPTIONS, index=0)
search_text = st.text_input("검색", placeholder="일정명 / 메모")

tab1, tab2, tab3 = st.tabs(["홈", "달력", "백업"])


# ---------------------------------
# 홈
# ---------------------------------
with tab1:
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

                b1, b2, b3 = st.columns(3, gap="small")

                with b1:
                    if st.button("완료", key=f"done_{row['id']}", use_container_width=True):
                        mark_done(row["id"])
                        st.rerun()

                with b2:
                    if st.button("삭제", key=f"delete_{row['id']}", use_container_width=True):
                        delete_row(row["id"])
                        if st.session_state.edit_id == row["id"]:
                            st.session_state.edit_id = None
                        st.rerun()

                with b3:
                    if st.button("수정", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state.edit_id = row["id"]
                        st.rerun()

            if st.session_state.edit_id == row["id"]:
                with st.container(border=True):
                    st.subheader("일정 수정")

                    current_title = row["title"] if pd.notna(row["title"]) else ""
                    current_target = row["target"] if pd.notna(row["target"]) else ""
                    current_category = row["category"] if pd.notna(row["category"]) else CATEGORY_OPTIONS[0]
                    current_dt = row["schedule_dt"] if pd.notna(row["schedule_dt"]) else ""
                    current_status = row["status"] if pd.notna(row["status"]) else "예정"
                    current_memo = row["memo"] if pd.notna(row["memo"]) else ""

                    title_val = st.text_input("일정", value=current_title, key=f"title_{row['id']}")
                    target_val = st.text_input("대상", value=current_target, key=f"target_{row['id']}")

                    if current_category not in CATEGORY_OPTIONS:
                        current_category = CATEGORY_OPTIONS[0]

                    category_val = st.selectbox(
                        "분류",
                        CATEGORY_OPTIONS,
                        index=CATEGORY_OPTIONS.index(current_category),
                        key=f"category_{row['id']}"
                    )

                    dt_val = st.text_input(
                        "날짜",
                        value=current_dt,
                        key=f"dt_{row['id']}",
                        placeholder="예: 2026-03-08 10:30"
                    )

                    status_val = st.selectbox(
                        "상태",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0,
                        key=f"status_{row['id']}"
                    )

                    memo_val = st.text_area("메모", value=current_memo, key=f"memo_{row['id']}")

                    s1, s2 = st.columns(2)

                    with s1:
                        if st.button("저장", key=f"save_{row['id']}", use_container_width=True):
                            update_row(
                                row["id"],
                                title_val.strip(),
                                target_val.strip(),
                                category_val,
                                dt_val.strip(),
                                status_val,
                                memo_val.strip()
                            )
                            st.session_state.edit_id = None
                            st.rerun()

                    with s2:
                        if st.button("취소", key=f"cancel_{row['id']}", use_container_width=True):
                            st.session_state.edit_id = None
                            st.rerun()

            st.write("")


# ---------------------------------
# 달력
# ---------------------------------
with tab2:
    st.subheader("달력")

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
# 백업
# ---------------------------------
with tab3:
    st.subheader("백업")

    df = load_data()
    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name="twin_schedule_backup.csv",
        mime="text/csv",
        use_container_width=True
    )