import random
import pandas as pd
import streamlit as st
import time
from datetime import datetime, timedelta, timezone
import io

# ==== 利用期限チェック ====
expiry_date = datetime(2025, 11, 30)
today = datetime.now()
if today.date() > expiry_date.date():
    st.error("このアプリの利用期限は 2025-11-30 で終了しました。")
    st.stop()

# ==== 日本時間 ====
try:
    from zoneinfo import ZoneInfo
    JST = ZoneInfo("Asia/Tokyo")
except Exception:
    JST = timezone(timedelta(hours=9))

# ==== スタイル調整 ====
st.markdown("""
<style>
h1, h2, h3, h4, h5, h6 {margin-top: 0.2em; margin-bottom: 0.2em;}
p, div, label {margin-top: 0.05em; margin-bottom: 0.05em; line-height: 1.1;}
button, .stButton>button {
    padding: 0.4em;
    margin: 0.05em 0;
    font-size:20px;
    width:100%;
}
.stTextInput>div>div>input {padding: 0.2em; font-size: 16px;}
.choice-header {margin-top:0.8em;}
</style>
""", unsafe_allow_html=True)

# ==== タイトル ====
st.markdown("<h1 style='font-size:22px;'>社会４択クイズ（CSV版・スマホ対応）</h1>", unsafe_allow_html=True)

# ==== ファイルアップロード ====
uploaded_file = st.file_uploader(
    "社会科問題リスト（CSV, UTF-8推奨）をアップロードしてください  （利用期限25-11-30）",
    type=["csv"],
    key="file_uploader"
)

# ==== 初期化関数 ====
def reset_all():
    for key in list(st.session_state.keys()):
        if key != "file_uploader":
            del st.session_state[key]

if uploaded_file is None:
    reset_all()
    st.info("まずは CSV をアップロードしてください。")
    st.stop()

# ==== CSV読み込み ====
try:
    df = pd.read_csv(uploaded_file, encoding="utf-8")
except UnicodeDecodeError:
    df = pd.read_csv(uploaded_file, encoding="shift-jis")

required_cols = {"分野", "問題", "答え"}
if not required_cols.issubset(df.columns):
    st.error("CSVには『分野』『問題』『答え』列が必要です。")
    st.stop()

# ==== 選択肢生成 ====
def make_choices(correct_item, df):
    correct = correct_item["答え"]
    pool = df[df["答え"] != correct]["答え"].tolist()
    wrongs = random.sample(pool, 3) if len(pool) >= 3 else random.choices(pool, k=3)
    choices = wrongs + [correct]
    random.shuffle(choices)
    return correct, choices

# ==== 次の問題を用意 ====
def next_question():
    ss = st.session_state
    if not ss.remaining:
        ss.current = None
        ss.phase = "done"
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.question = None
    ss.q_start_time = time.time()

# ==== クイズ全体をリセット ====
def reset_quiz():
    ss = st.session_state
    ss.remaining = df.to_dict("records")
    ss.current = None
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.start_time = time.time()
    ss.question = None
    next_question()

# ==== 履歴保存 ====
def prepare_csv():
    ss = st.session_state
    timestamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    filename = f"{ss.user_name}_{timestamp}.csv"
    history_df = pd.DataFrame(ss.history)
    elapsed = int(time.time() - ss.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    history_df["総学習時間"] = f"{minutes}分{seconds}秒"
    history_df["出題数"] = ss.num_questions
    csv_buffer = io.StringIO()
    history_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_data = csv_buffer.getvalue().encode("utf-8-sig")
    return filename, csv_data

# ==== セッション初期化 ====
ss = st.session_state
if "initialized" not in ss:   # 初回だけ実行
    ss.remaining = []
    ss.current = None
    ss.phase = "menu"
    ss.last_outcome = None
    ss.start_time = time.time()
    ss.history = []
    ss.show_save_ui = False
    ss.user_name = ""
    ss.question = None
    ss.num_questions = None   # ← 初期化時にキーを必ず作成
    ss.initialized = True

# ==== 問題数オプション ====
if ss.get("num_questions"_
