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
    history_df["出題数"] = ss.get("num_questions", "")
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
    ss["num_questions"] = None   # 初期化
    ss.initialized = True

# ==== 問題数オプション ====
if ss.get("num_questions") is None:  # まだ選択されていないとき
    st.subheader("出題数を選んでください")

    option = st.radio(
        "問題数を選んでください",
        ["10題", "20題", "好きな数"],
        horizontal=True
    )

    if option == "10題":
        chosen_num = 10
    elif option == "20題":
        chosen_num = 20
    else:
        chosen_num = st.number_input(
            "出題数を入力してください",
            min_value=1, max_value=len(df),
            value=min(10, len(df)), step=1
        )

    if st.button("開始"):
        if chosen_num >= len(df):
            ss.remaining = df.to_dict("records")
        else:
            ss.remaining = df.sample(chosen_num).to_dict("records")

        ss["num_questions"] = chosen_num
        ss.current = None
        ss.history = []
        ss.phase = "quiz"
        ss.last_outcome = None
        ss.start_time = time.time()
        next_question()
        st.rerun()

    st.stop()  # 出題数を決めるまではここで停止

# ==== 全問終了 ====
if ss.phase == "done":
    st.success("全問終了！お疲れさまでした🎉")
    elapsed = int(time.time() - ss.start_time)
    st.info(f"所要時間: {elapsed//60}分 {elapsed%60}秒")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("もう一回"):
            ss["num_questions"] = None   # 出題数をリセット
            ss.phase = "menu"            # 出題数選択フェーズに戻す
            ss.current = None
            ss.history = []
            ss.last_outcome = None
            st.rerun()
    with col2:
        if st.button("終了"):
            ss.show_save_ui = True
            ss.phase = "finished"
            st.rerun()
    st.stop()

# ==== 終了後の保存UI ====
if ss.phase == "finished" and ss.show_save_ui:
    st.subheader("学習履歴の保存")
    ss.user_name = st.text_input("氏名を入力してください", value=ss.user_name)
    if ss.user_name:
        filename, csv_data = prepare_csv()
        if st.download_button("📥 保存（ダウンロード）", data=csv_data, file_name=filename, mime="text/csv"):
            reset_all()
            st.success("保存しました。新しい学習を始められます。")
            st.rerun()

# ==== 出題 ====
if ss.phase == "quiz" and ss.current:
    current = ss.current
    question_text = current["問題"]

    if ss.question is None:
        correct, options = make_choices(current, df)
        ss.question = {
            "correct": correct,
            "options": options,
            "field": current["分野"],
            "question": question_text
        }

    st.subheader(f"{current['分野']}：{question_text}")
    st.markdown("<p class='choice-header'>選択肢から答えを選んでください</p>", unsafe_allow_html=True)

    for opt in ss.question["options"]:
        if st.button(opt, key=f"opt_{len(ss.history)}_{opt}"):
            elapsed_q = int(time.time() - ss.q_start_time)
            if opt == ss.question["correct"]:
                ss.last_outcome = ("正解", ss.question, elapsed_q)
                ss.remaining = [q for q in ss.remaining if q != current]
            else:
                ss.last_outcome = ("不正解", ss.question, elapsed_q)
            ss.phase = "feedback"
            st.rerun()

# ==== フィードバック ====
if ss.phase == "feedback" and ss.last_outcome:
    status, qinfo, elapsed_q = ss.last_outcome
    if status == "正解":
        st.success(f"正解！ {qinfo['correct']}")
    else:
        st.error(f"不正解… 正解は {qinfo['correct']}")
    ss.history.append({
        "分野": qinfo["field"],
        "問題": qinfo["question"],
        "結果": status,
        "経過秒": elapsed_q
    })
    time.sleep(1)
    next_question()
    st.rerun()
