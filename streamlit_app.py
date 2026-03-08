import sqlite3
from pathlib import Path
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


# ---------------------------
# DB
# ---------------------------
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


init_db()
insert_sample_if_empty()

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None


# ---------------------------
# CSS
# ---------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 0.55rem !important;
    padding-bottom: 1.2rem !important;
    padding-left: 0.7rem !important;
    padding-right: 0.7rem !important;
    max-width: 100% !important;
}

/* 카드 전체 */
.card-box {
    border: 1px solid #d9d9d9;
    border-radius: 14px;
    background: #ffffff;
    padding: 14px 12px 10px 12px;
    margin-bottom: 10px;
}

/* 제목/본문 */
.card-title {
    font-size: 1.12rem;
    font-weight: 700;
    line-height: 1.4;
    margin-bottom: 0.5rem;
    color: #222;
}

.card-line {
    font-size: 0.98rem;
    line-height: 1.6;
    margin-bottom: 0.18rem;
    color: #333;
    word-break: keep-all;
}

.card-memo {
    font-size: 0.9rem;
    line-height: 1.45;
    color: #777;
    margin-top: 0.45rem;
    margin-bottom: 0.7rem;
    word-break: keep-all;
}

/* 버튼행 */
.card-button-wrap {
    margin-top: 0.15rem;
}

/* Streamlit 버튼 */
.stButton > button {
    width: 100% !important;
    min-height: 40px !important;
    border-radius: 11px !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    padding: 0.2rem 0.35rem !important;
}

/* 열 간격 */
[data-testid="stHorizontalBlock"] {
    gap: 0.35rem !important;
}

/* 입력 UI */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea {
    border-radius: 12px !important;
}

@media (max-width: 768px) {
    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 0.9rem !important;
        padding-left: 0.55rem !important;
        padding-right: 0.55rem !important;
    }

    .card-box {
        border-radius: 12px;
        padding: 12px 10px 9px 10px;
        margin-bottom: 9px;
    }

    .card-title {
        font-size: 1.0rem;
        margin-bottom: 0.42rem;
    }

    .card-line {
        font-size: 0.9rem;
        line-height: 1.55;
    }

    .card-memo {
        font-size: 0.84rem;
        line-height: 1.4;
        margin-top: 0.32rem;
        margin-bottom: 0.55rem;
    }

    .stButton > button {
        min-height: 36px !important;
        border-radius: 10px !important;
        font-size: 0.78rem !important;
        padding: 0.08rem 0.15rem !important;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 0.22rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------
# 상단 필터
# ---------------------------
status_filter = st.selectbox("상태", ["전체"] + STATUS_OPTIONS, index=0)
search_text = st.text_input("검색", placeholder="일정명 / 메모")

tab1, tab2, tab3 = st.tabs(["홈", "달력", "백업"])


# ---------------------------
# 홈
# ---------------------------
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
            # 카드 시작
            card = st.container()

            with card:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)

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

                st.markdown('<div class="card-button-wrap">', unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3, gap="small")

                with c1:
                    if st.button("완료", key=f"done_{row['id']}", use_container_width=True):
                        mark_done(row["id"])
                        st.rerun()

                with c2:
                    if st.button("삭제", key=f"delete_{row['id']}", use_container_width=True):
                        delete_row(row["id"])
                        if st.session_state.edit_id == row["id"]:
                            st.session_state.edit_id = None
                        st.rerun()

                with c3:
                    if st.button("수정", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state.edit_id = row["id"]
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

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

                    s1, s2 = st.columns(2, gap="small")

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


# ---------------------------
# 달력
# ---------------------------
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


# ---------------------------
# 백업
# ---------------------------
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