import random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import time
import difflib
import re
from datetime import datetime

st.title("4択クイズ（歴史・地理・公民）")

# ==== 生徒名入力 ====
student_name = st.text_input("生徒名を入力してください", key="student_name")
if not student_name:
    st.stop()

# ==== 問題セット選択 ====
dataset = st.selectbox("問題セットを選んでください", ["歴史", "地理", "公民"])

if dataset == "歴史":
    df = pd.read_csv("rekishi.csv", encoding="utf-8")
elif dataset == "地理":
    df = pd.read_csv("chiri.csv", encoding="utf-8")
else:
    df = pd.read_csv("koumin.csv", encoding="utf-8")

if not {"問題", "答え"}.issubset(df.columns):
    st.error("CSVには『問題』『答え』列が必要です。")
    st.stop()

# ==== カテゴリ自動判定 ====
def guess_category(answer: str) -> str:
    if pd.isna(answer):
        return "その他"
    ans = str(answer)
    if ans.isdigit():
        return "年号"
    if any(word in ans for word in ["戦争","乱","一揆","革命","事変","変"]):
        return "戦争・事件"
    if any(word in ans for word in ["条約","憲法","法","令","詔","布告","改正"]):
        return "条約・法令"
    if re.match(r'^[一-龥]{2,4}$', ans):
        return "人物"
    if re.match(r'^[ァ-ヶー]+$', ans):
        return "人物"
    if re.match(r'^[A-Za-z .-]+$', ans):
        return "人物"
    if any(word in ans for word in ["県","都","道","府","市","村","山","川","湖","湾","島","平野","高原"]):
        return "地理"
    if any(word in ans for word in ["内閣","議会","大統領","選挙","権","自由","民主","市場","経済","GDP","憲政"]):
        return "政治・経済"
    return "その他"

df["カテゴリ"] = df["答え"].apply(guess_category)

# ==== 出題数設定 ====
preset = st.radio("問題数を選択してください", ["10題", "15題", "20題", "手動入力"])
if preset == "手動入力":
    num_questions = st.number_input("問題数を入力してください", min_value=1, step=1, value=10)
else:
    num_questions = int(preset.replace("題", ""))

# ==== セッション初期化 ====
ss = st.session_state

def init_quiz():
    ss.remaining = random.sample(df.to_dict("records"), min(num_questions, len(df)))
    ss.current = None
    ss.choices = None
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.start_time = time.time()
    ss.score = 0
    ss.total = 0
    ss.limit = num_questions
    ss.history = []

if "initialized" not in ss or dataset != ss.get("current_dataset"):
    init_quiz()
    ss.current_dataset = dataset
    ss.initialized = True

def next_question():
    if not ss.remaining or ss.total >= ss.limit:
        ss.current = None
        ss.phase = "done"
        return
    ss.current = random.choice(ss.remaining)
    ss.phase = "quiz"
    ss.last_outcome = None
    ss.choices = None

def reset_quiz():
    init_quiz()

# ==== 紛らわしい選択肢生成 ====
def generate_distractors(correct_answer, current, df):
    other_records = [r for r in df.to_dict("records") if r != current]
    correct_cat = current["カテゴリ"]
    same_category = [r["答え"] for r in other_records if r.get("カテゴリ") == correct_cat]
    scored = [(r["答え"], difflib.SequenceMatcher(None, correct_answer, r["答え"]).ratio()) for r in other_records]
    scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
    similar = [s[0] for s in scored_sorted[:10]]
    distractors = []
    distractors.extend(same_category[:5])
    distractors.extend(similar)
    distractors = list(dict.fromkeys(distractors))
    if correct_answer in distractors:
        distractors.remove(correct_answer)
    if len(distractors) >= 3:
        distractors = random.sample(distractors, 3)
    else:
        need = 3 - len(distractors)
        extra = random.sample([r["答え"] for r in other_records if r["答え"] not in distractors], need)
        distractors.extend(extra)
    return distractors

# ==== 全問終了 ====
if ss.phase == "done":
    st.success("全問終了！お疲れさまでした🎉")
    elapsed = int(time.time() - ss.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    st.info(f"所要時間: {minutes}分 {seconds}秒")
    correct_rate = round((ss.score / ss.total) * 100, 1) if ss.total > 0 else 0
    st.write(f"正解数: {ss.score}/{ss.total}（正解率 {correct_rate}%）")
    today = datetime.now().strftime("%Y-%m-%d")
    result_file = f"results_{today}.csv"
    results_df = pd.DataFrame(ss.history)
    results_df["名前"] = student_name
    results_df["分野"] = dataset
    results_df["日時"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # ✅ Excel用に UTF-8-SIG で保存
    csv = results_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="成績ファイルをダウンロード",
        data=csv,
        file_name=result_file,
        mime="text/csv",
    )
    if st.button("もう一回"):
        reset_quiz()
        st.rerun()
    st.stop()

# ==== 新しい問題 ====
if ss.current is None and ss.phase == "quiz":
    next_question()

# ==== 出題 ====
if ss.phase == "quiz" and ss.current:
    current = ss.current
    st.subheader(f"問題: {current['問題']}")
    correct_answer = current["答え"]

    if ss.choices is None:
        distractors = generate_distractors(correct_answer, current, df)
        choices = distractors + [correct_answer]
        random.shuffle(choices)
        ss.choices = choices

    choice_map = {str(i+1): ans for i, ans in enumerate(ss.choices)}
    for num, ans in choice_map.items():
        st.write(f"{num}. {ans}")

    with st.form("answer_form", clear_on_submit=True):
        ans = st.text_input("番号を入力（1〜4）", max_chars=1, key="answer_box", label_visibility="collapsed")
        submitted = st.form_submit_button("解答")

    # ✅ 解答欄にフォーカス
    components.html(
        """
        <script>
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if (inputs.length > 0) {
            inputs[inputs.length - 1].focus();
            inputs[inputs.length - 1].select();
        }
        </script>
        """,
        height=0,
    )

    if submitted and ans in choice_map:
        ss.total += 1
        correct_flag = (choice_map[ans] == correct_answer)
        if correct_flag:
            ss.remaining = [q for q in ss.remaining if q != current]
            ss.last_outcome = ("correct", correct_answer)
            ss.score += 1
        else:
            ss.last_outcome = ("wrong", correct_answer)
        ss.history.append({
            "問題": current["問題"],
            "答え": correct_answer,
            "選択肢": ";".join(ss.choices),
            "解答": choice_map[ans],
            "正解か": "○" if correct_flag else "×"
        })
        ss.phase = "feedback"
        st.rerun()

# ==== フィードバック ====
if ss.phase == "feedback" and ss.last_outcome:
    status, answer = ss.last_outcome
    if status == "correct":
        st.success(f"正解！ {answer} 🎉")
    else:
        st.error(f"不正解！ 正解は {answer}")
    if st.button("次の問題へ"):
        next_question()
        st.rerun()
