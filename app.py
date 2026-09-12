import os
import json
import re
import time
import io
from datetime import datetime
import streamlit as st

# PIL (Pillow) の読み込みチェック
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Google GenAI / Generative AI SDK の読み込みチェック
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# ReportLab (PDF出力) の読み込みチェック
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

st.set_page_config(
    page_title="StarLog - AI手書き添削 & 学習アシスタント",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSSの適用
st.markdown("""
<style>
    /* メインヘッダー */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .sub-text {
        font-size: 0.98rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    
    /* カードコンテナ */
    .stCard {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    }
    
    /* スコア表示バッジ */
    .score-badge {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        color: white;
        padding: 12px 24px;
        border-radius: 10px;
        font-size: 1.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 15px;
    }

    /* 本棚カードスタイル */
    .book-card {
        background: linear-gradient(135deg, #1E40AF, #3B82F6);
        color: white;
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .book-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 4px;
    }

    /* ノートブック連携通知バナー */
    .linked-banner {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 20px;
        color: #1E40AF;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

query_params = st.query_params
from_app = query_params.get("from", "")

if from_app == "notebook":
    # 初回アクセス時のみパラメータを保持し、画面上に連携通知を表示
    if "notebook_linked" not in st.session_state:
        st.session_state["notebook_linked"] = True
        st.session_state["default_subject"] = query_params.get("subject", "数学")
        st.session_state["default_unit"] = query_params.get("unit", "二次関数とグラフ")
        
        # 数値型変換エラーの防止
        try:
            st.session_state["default_pts"] = int(query_params.get("pts", 0))
        except (ValueError, TypeError):
            st.session_state["default_pts"] = 0

        st.toast(
            f"📓 Notebookから連携されました！\n"
            f"（教科: {st.session_state['default_subject']} / 単元: {st.session_state['default_unit']} / 獲得pt: {st.session_state['default_pts']}）",
            icon="🚀"
        )

USERS_FILE = "users_db.json"
HISTORY_FILE = "quiz_history.json"

def load_registered_users():
    """ユーザー一覧をローカルJSONから読み込み"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return ["ゲストユーザー", "山田太郎", "佐藤花子"]

def save_registered_users(users_list):
    """ユーザー一覧をローカルJSONへ保存"""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"ユーザー情報の保存に失敗しました: {e}")

def load_history():
    """過去問・作成テスト履歴をローカルJSONから読み込み"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {
            "id": "quiz_001",
            "created_at": "2026-09-10 14:00",
            "created_by": "ゲストユーザー",
            "school_type": "中学生",
            "subject": "数学",
            "topic": "二次関数とグラフ",
            "difficulty": "標準",
            "quiz_text": "【問題1】y = x^2 - 4x + 3 の頂点を求めよ。\n【問題2】この放物線とx軸の交点の座標を求めよ。",
            "answers": "【解答1】頂点 (2, -1)\n【解答2】(1, 0), (3, 0)"
        },
        {
            "id": "quiz_002",
            "created_at": "2026-09-11 10:30",
            "created_by": "ゲストユーザー",
            "school_type": "中学生",
            "subject": "英語",
            "topic": "関係代名詞の理解",
            "difficulty": "標準",
            "quiz_text": "【問題1】以下の2文を関係代名詞を用いて1文にしなさい。\nThis is the book. I bought it yesterday.",
            "answers": "【解答1】This is the book which [that] I bought yesterday."
        }
    ]

def save_history(history_data):
    """作成テスト履歴をローカルJSONへ保存"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"履歴の保存に失敗しました: {e}")

def delete_history_item(item_id: str) -> bool:
    """指定されたIDの履歴アイテムを削除"""
    history = load_history()
    new_history = [x for x in history if x.get("id") != item_id]
    if len(new_history) < len(history):
        save_history(new_history)
        return True
    return False

def sanitize_text(text: str) -> str:
    """LaTeX表記や数式コマンドを一般的なプレーンテキストに整形"""
    if not text:
        return ""
    # 分数 \frac{分子}{分母} の変換
    clean = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 / \2', text)
    # \text{...} の除去
    clean = re.sub(r'\\text\{([^}]+)\}', r'\1', clean)
    # LaTeXインライン数式 $...$ の除去
    clean = re.sub(r'\$([^\$]+)\$', r'\1', clean)
    # 演算記号の置換
    clean = (
        clean.replace(r'\times', '×')
        .replace(r'\div', '÷')
        .replace(r'\pm', '±')
    )
    clean = re.sub(r'\\(left|right)', '', clean)
    return clean

def extract_json_from_text(text: str) -> dict:
    """Gemini APIからの返答からJSON構文を抽出・パースする補助関数"""
    if not text:
        return {}
    if isinstance(text, dict):
        return text

    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(1)
        else:
            json_str = text

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        st.warning("⚠️ AIレスポンスを完全なJSONとして解釈できませんでした。テキスト形式で表示します。")
        return {
            "total_score": 0,
            "max_score": 100,
            "questions": [],
            "overall_feedback": text
        }

def create_quiz_pdf(subject, topic, difficulty, print_type, quiz_text):
    """ReportLabを用いた日本語PDF出力関数（数式整形つき）"""
    if not HAS_REPORTLAB:
        raise Exception("reportlab がインストールされていません。`pip install reportlab` を実行してください。")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()

    clean_text = sanitize_text(quiz_text)

    title_style = ParagraphStyle(
        'PdfTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=22,
        spaceAfter=12
    )
    body_style = ParagraphStyle(
        'PdfBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=15,
        spaceAfter=8
    )

    story = []
    header = f"<b>【 StarLog 学習プリント 】</b><br/>教科: {subject} | 単元: {topic} | 難易度: {difficulty}"
    story.append(Paragraph(header, title_style))
    story.append(Spacer(1, 12))

    for line in clean_text.split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), body_style))
        else:
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def parse_quiz_to_questions(quiz_text: str) -> list:
    """テストテキストから個別設問（問題・解答）を抽出・パース"""
    if not quiz_text:
        return []
    questions = []
    raw_blocks = re.split(r'(?=\n(?:【問題\d+】|【問\d+】|問\d+[:：\s]|問題\d+[:：\s]|\d+[\.．]))', quiz_text)

    parent_ctx = ""
    for block in raw_blocks:
        block_str = block.strip()
        if not block_str:
            continue

        m = re.match(r'^(【問題\d+】|【問\d+】|問\d+[:：\s]|問題\d+[:：\s]|\d+[\.．])\s*(.*)', block_str, re.DOTALL)
        if m:
            q_num = m.group(1).strip()
            q_rest = m.group(2).strip()

            if "【模範解答】" in q_rest or "【解答】" in q_rest or "解説:" in q_rest:
                parts = re.split(r'【(?:模範解答|解答)】|解説[:：]', q_rest, maxsplit=1)
                body = parts[0].strip()
                explanation = parts[1].strip() if len(parts) > 1 else "模範解答は問題全体を参照してください。"
            else:
                body = q_rest
                explanation = "正解・解説の詳細は全体解答を参照してください。"

            questions.append({
                "display_num": q_num,
                "body": body,
                "explanation": explanation,
                "parent_context": parent_ctx
            })
        else:
            if len(block_str) < 200:
                parent_ctx = block_str
            else:
                questions.append({
                    "display_num": f"問題 {len(questions)+1}",
                    "body": block_str,
                    "explanation": "正解・解説の詳細は問題全体を参照してください。",
                    "parent_context": ""
                })

    if not questions and quiz_text.strip():
        questions.append({
            "display_num": "問題 1",
            "body": quiz_text.strip(),
            "explanation": "問題全体の模範解答を参照してください。",
            "parent_context": ""
        })

    return questions

users_list = load_registered_users()

if "current_user" not in st.session_state:
    st.session_state["current_user"] = users_list[0] if users_list else "ゲストユーザー"

current_api_key = os.environ.get("GEMINI_API_KEY", "")
if not current_api_key and "GEMINI_API_KEY" in st.secrets:
    current_api_key = st.secrets["GEMINI_API_KEY"]

def call_gemini_api(contents, model_name="gemini-2.5-flash"):
    """Gemini APIを呼び出す汎用関数"""
    if not HAS_GEMINI:
        return "エラー: google-generativeai パッケージがインストールされていません。"
    
    api_key_to_use = st.session_state.get("user_api_key", current_api_key)
    if not api_key_to_use:
        return "エラー: Gemini APIキーが設定されていません。"

    try:
        genai.configure(api_key=api_key_to_use)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        return f"APIエラーが発生しました: {str(e)}"

st.sidebar.title("🎓 AI テスト & 添削 Navi")

selected_user = st.sidebar.selectbox(
    "👤 アカウント切替",
    users_list,
    index=users_list.index(st.session_state["current_user"]) if st.session_state["current_user"] in users_list else 0
)
st.session_state["current_user"] = selected_user

test_mode = st.sidebar.checkbox("🧪 テストモード (API消費なし)", value=False, help="チェックを入れるとダミーデータで動作検証できます。")

st.sidebar.divider()

app_mode = st.sidebar.radio(
    "メインメニュー",
    ["📝 テスト作成", "📖 My参考書", "🌐 WEB一問一答", "📷 AI手書き添削", "📈 学習アナリティクス", "👤 マイページ"]
)

st.sidebar.divider()

custom_key_input = st.sidebar.text_input("🔑 APIキー手動設定", type="password", help="secrets未設定時の個別指定用")
if custom_key_input:
    st.session_state["user_api_key"] = custom_key_input

if current_api_key or st.session_state.get("user_api_key"):
    st.sidebar.success("🔑 APIキー動作準備完了")
else:
    st.sidebar.warning("⚠️ APIキー未設定")

if app_mode == "📝 テスト作成":
    st.markdown("<div class='main-header'>📝 AI自動テスト作成</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-text'>指定した教科・単元に基づき、AIが最適なテスト問題と模範解答を即座に生成します。</div>", unsafe_allow_html=True)

    if st.session_state.get("notebook_linked"):
        st.markdown(
            f"<div class='linked-banner'>📓 Notebookから連携中: "
            f"教科「<b>{st.session_state.get('default_subject', '')}</b>」/ "
            f"単元「<b>{st.session_state.get('default_unit', '')}</b>」が自動入力されています。</div>",
            unsafe_allow_html=True
        )

    subject_options = ["数学", "英語", "国語", "理科", "社会"]
    unit_dict = {
        "数学": ["二次関数とグラフ", "図形の証明", "確率と統計", "微分・積分基礎", "ベクトルの応用"],
        "英語": ["関係代名詞の理解", "仮定法過去", "不定詞と動名詞", "長文読解・段落構成"],
        "国語": ["現代文・主張の把握", "古文・文法基礎", "漢文・訓読の基本"],
        "理科": ["化学結合と反応速度", "力学の法則", "細胞分裂と遺伝", "地層と古生物"],
        "社会": ["歴史・近現代史", "地理・気候帯と産業", "公民・日本国憲法"]
    }

    notebook_sub = st.session_state.get("default_subject", "数学")
    notebook_unit = st.session_state.get("default_unit", "二次関数とグラフ")

    sub_index = subject_options.index(notebook_sub) if notebook_sub in subject_options else 0

    col1, col2 = st.columns(2)
    with col1:
        subject = st.selectbox("📚 教科・科目", subject_options, index=sub_index)
    
    current_units = unit_dict.get(subject, [notebook_unit])
    unit_index = current_units.index(notebook_unit) if notebook_unit in current_units else 0

    with col2:
        topic = st.selectbox("📖 単元・テーマ", current_units, index=unit_index)

    col3, col4, col5 = st.columns(3)
    with col3:
        difficulty = st.selectbox("🎯 難易度", ["標準", "基礎", "応用・発展"])
    with col4:
        q_count = st.slider("🔢 問題数", 1, 5, 2)
    with col5:
        q_type = st.multiselect("📝 問題形式", ["記述式", "計算問題", "選択式"], default=["記述式", "計算問題"])

    custom_instructions = st.text_area("💡 AIへの追加指示・キーワード（任意）", placeholder="例: 途中式を必ず記述させる問題を含めてください。")

    if st.button("🚀 テスト問題を生成する", type="primary", use_container_width=True):
        if not test_mode and not (current_api_key or st.session_state.get("user_api_key")):
            st.error("APIキーが設定されていません。サイドバーまたはSecretsに設定してください。")
        else:
            with st.spinner("AIが難易度と単元に合わせて問題を構成中..."):
                if test_mode:
                    time.sleep(1.2)
                    quiz_content = (
                        f"【{subject} - {topic} 小テスト】（難易度: {difficulty}）\n\n"
                        f"問1: {topic}における基本概念について説明しなさい。（20点）\n\n"
                        f"問2: {topic}に関する実践計算を行い、答えを求めなさい。（30点）"
                    )
                    answer_content = (
                        "【模範解答と解説】\n"
                        "問1: 定義に従って正しく記述されていること。\n"
                        "問2: 途中計算を含めて X = 42 となれば正解。"
                    )
                else:
                    prompt = (
                        f"教科: {subject}\n単元: {topic}\n難易度: {difficulty}\n問題数: {q_count}\n問題形式: {', '.join(q_type)}\n"
                        f"追加指定: {custom_instructions}\n\n"
                        f"上記仕様に基づき、学生向けの小テスト問題(quiz_text)と模範解答・解説(answers)を作成してください。\n"
                        f"明確に【問題】セクションと【模範解答】セクションに分けて出力してください。"
                    )
                    res_text = call_gemini_api(prompt)
                    
                    if "【模範解答】" in res_text:
                        parts = res_text.split("【模範解答】")
                        quiz_content = parts[0]
                        answer_content = "【模範解答】" + parts[1]
                    else:
                        quiz_content = res_text
                        answer_content = "回答欄・解説テキスト内に記載"

                new_quiz = {
                    "id": f"quiz_{int(time.time())}",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "created_by": st.session_state["current_user"],
                    "school_type": "中学生",
                    "subject": f"{subject}",
                    "topic": f"{topic}",
                    "difficulty": difficulty,
                    "quiz_text": quiz_content,
                    "answers": answer_content
                }
                
                history = load_history()
                history.insert(0, new_quiz)
                save_history(history)

                st.success("✅ テスト問題が生成され、過去問履歴に保存されました！")
                
                st.markdown("---")
                col_q, col_a = st.columns(2)
                with col_q:
                    st.markdown("### 📋 生成された問題")
                    st.info(quiz_content)
                with col_a:
                    st.markdown("### 💡 模範解答・解説")
                    st.success(answer_content)

                export_text = f"{quiz_content}\n\n{'='*30}\n\n{answer_content}"
                st.download_button(
                    label="📥 このテストをテキストで保存",
                    data=export_text,
                    file_name=f"test_{subject}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )

elif app_mode == "📖 My参考書":
    st.markdown("<div class='main-header'>📖 My参考書</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-text'><b>{st.session_state['current_user']}</b> さんのオリジナルデジタル本棚です。作成したプリントをいつでも復習できます。</div>", unsafe_allow_html=True)

    history_list = load_history()
    filter_mode = st.radio("👤 表示対象", ["自分のみ", "全員"], horizontal=True)
    if filter_mode == "自分のみ":
        history_list = [x for x in history_list if x.get("created_by") == st.session_state["current_user"]]

    sel_school = st.radio("🏫 校種を選択", ["小学生", "中学生", "高校生"], horizontal=True)
    filtered_h = [x for x in history_list if x.get("school_type", "小学生") == sel_school]

    if "selected_book_subject" not in st.session_state:
        st.session_state["selected_book_subject"] = None

    if st.session_state["selected_book_subject"] is None:
        st.divider()
        st.markdown(f"### 📚 {sel_school} の本棚")

        subjects = (
            ["国語", "算数", "理科", "社会", "英語", "音楽", "図工", "体育", "家庭", "道徳", "総合"] if sel_school == "小学生" else
            (["国語", "数学", "理科", "社会", "英語", "音楽", "美術", "保健体育", "技術", "家庭", "道徳"] if sel_school == "中学生" else
             ["数学", "英語", "理科", "国語", "地歴公民"])
        )

        cols = st.columns(4)
        for idx, subj in enumerate(subjects):
            subj_items = [x for x in filtered_h if subj in x.get("subject", "")]
            count = len(subj_items)

            with cols[idx % 4]:
                st.markdown(f"""
                <div class="book-card">
                    <div class="book-title">{subj}</div>
                    <div style="font-size: 12px; opacity: 0.9;">収録プリント: {count}冊</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"📘 『{subj}』を開く", key=f"btn_book_{subj}", use_container_width=True):
                    st.session_state["selected_book_subject"] = subj
                    st.session_state["book_page"] = 0
                    st.rerun()

    else:
        current_subj = st.session_state["selected_book_subject"]
        book_items = [x for x in filtered_h if current_subj in x.get("subject", "")]

        c_back, c_title = st.columns([1, 4])
        with c_back:
            if st.button("◀ 本棚に戻る", use_container_width=True):
                st.session_state["selected_book_subject"] = None
                st.rerun()
        with c_title:
            st.markdown(f"### 📘 {sel_school}『{current_subj}』My参考書")

        st.divider()

        if not book_items:
            st.info(f"『{current_subj}』のプリントはまだありません。「📝 テスト作成」で作成してみましょう！")
        else:
            cp = st.session_state.get("book_page", 0)
            tp = len(book_items)

            n1, n2, n3 = st.columns([1, 2, 1])
            with n1:
                if st.button("◀ 前のプリント", disabled=(cp == 0), use_container_width=True):
                    st.session_state["book_page"] -= 1
                    st.rerun()
            with n2:
                st.markdown(f"<h4 style='text-align: center;'>- {cp + 1} / {tp} 冊 -</h4>", unsafe_allow_html=True)
            with n3:
                if st.button("次のプリント ▶", disabled=(cp >= tp - 1), use_container_width=True):
                    st.session_state["book_page"] += 1
                    st.rerun()

            item = book_items[cp]
            author = item.get('created_by', '学習者')

            st.markdown(f"""
            <div style="background-color: #ffffff; color: #2c3e50; padding: 25px; border-radius: 8px; border: 1px solid #dcdde1; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 15px;">
                <h3 style="color: #1E40AF; margin-top:0;">📄 {item.get('subject','')} - {item.get('topic','')}</h3>
                <p style="font-size: 12px; color: #6B7280;">作成者: <b>{author}</b> | 作成日時: {item.get('created_at','')} | 難易度: {item.get('difficulty','')}</p>
                <hr style="border: 0.5px solid #eee;">
            </div>
            """, unsafe_allow_html=True)

            st.text_area("本文プレビュー", value=sanitize_text(item.get("quiz_text", "")), height=320)

            col_pdf, col_txt, col_del = st.columns([1.5, 1.5, 1])
            try:
                pdf_data = create_quiz_pdf(
                    item.get("subject", "テスト"),
                    item.get("topic", ""),
                    item.get("difficulty", ""),
                    item.get("print_type", ""),
                    item.get("quiz_text", "")
                )
                with col_pdf:
                    st.download_button(
                        label="📥 日本語 PDF をダウンロード",
                        data=pdf_data,
                        file_name=f"StarLog_{item.get('id', 'file')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
            except Exception as e:
                with col_pdf:
                    st.warning(f"PDF準備中: {e}")

            with col_txt:
                st.download_button(
                    label="📝 テキスト保存",
                    data=sanitize_text(item.get("quiz_text", "")),
                    file_name=f"StarLog_{item.get('id', 'file')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with col_del:
                if st.button("🗑️ 削除", type="secondary", use_container_width=True):
                    if delete_history_item(item.get("id")):
                        st.session_state["book_page"] = max(0, cp - 1)
                        st.rerun()

elif app_mode == "🌐 WEB一問一答":
    st.markdown("<div class='main-header'>🌐 WEB一問一答</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-text'><b>{st.session_state['current_user']}</b> さんの演習モード。作成した問題からカード形式で一問一答トレーニングができます。</div>", unsafe_allow_html=True)

    history_list = load_history()
    filter_mode = st.radio("👤 表示対象", ["自分のみ", "全員"], horizontal=True)
    if filter_mode == "自分のみ":
        history_list = [x for x in history_list if x.get("created_by") == st.session_state["current_user"]]

    if not history_list:
        st.info("演習可能なプリントがありません。「📝 テスト作成」で問題を作成してください。")
    else:
        quiz_opts = {f"[{x.get('created_at','')}] ({x.get('created_by','学習者')}) {x.get('subject','')} - {x.get('topic','')[:10]}...": x for x in history_list}
        selected_label = st.selectbox("🎯 挑戦するプリントを選択", list(quiz_opts.keys()))
        selected_quiz = quiz_opts[selected_label]

        questions = parse_quiz_to_questions(selected_quiz.get("quiz_text", ""))

        if not questions:
            st.warning("問題形式を自動解析できませんでした。テキスト内容をご確認ください。")
        else:
            if "card_idx" not in st.session_state:
                st.session_state["card_idx"] = 0
            if "card_scores" not in st.session_state:
                st.session_state["card_scores"] = {}
            if "show_answer" not in st.session_state:
                st.session_state["show_answer"] = False

            c_idx = st.session_state["card_idx"]
            total_cards = len(questions)

            if c_idx >= total_cards:
                st.balloons()
                st.success("🎉 全問演習完了！おつかれさまでした！")
                correct_count = sum(1 for v in st.session_state["card_scores"].values() if v == "⭕️")
                st.metric("🏆 得点結果", f"{correct_count} / {total_cards} 問正解 ({int(correct_count/total_cards*100) if total_cards > 0 else 0}%)")

                if st.button("🔄 もう一度挑戦する", type="primary"):
                    st.session_state["card_idx"] = 0
                    st.session_state["card_scores"] = {}
                    st.session_state["show_answer"] = False
                    st.rerun()
            else:
                q = questions[c_idx]
                st.progress((c_idx) / total_cards, text=f"カード {c_idx + 1} / {total_cards}")

                parent_html = f"<p style='font-size: 13px; color: #6B7280; margin-bottom: 8px;'>📌 {q['parent_context']}</p><hr style='border:0.5px solid #E5E7EB; margin-bottom:12px;'>" if q.get('parent_context') else ""

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #F3F4F6 0%, #E5E7EB 100%); padding: 25px; border-radius: 15px; border: 2px solid #D1D5DB; color: #1F2937; margin-bottom: 20px;">
                    {parent_html}
                    <h4 style="color: #1D4ED8; margin-top:0;">{q['display_num']}</h4>
                    <p style="font-size: 17px; font-weight: bold; white-space: pre-wrap; margin:0;">{q['body']}</p>
                </div>
                """, unsafe_allow_html=True)

                if not st.session_state["show_answer"]:
                    user_ans = st.text_input("あなたの解答を入力", key=f"card_input_{c_idx}")
                    if st.button("🔍 答えを見る ➔", type="primary", use_container_width=True):
                        st.session_state["user_ans_temp"] = user_ans
                        st.session_state["show_answer"] = True
                        st.rerun()
                else:
                    st.markdown(f"""
                    <div style="background-color: #ECFDF5; padding: 20px; border-radius: 10px; border: 2px solid #10B981; margin-bottom: 15px; color: #065F46;">
                        <p style="color: #047857; font-weight: bold; margin:0;">💡 模範解答・解説:</p>
                        <p style="font-size: 16px; white-space: pre-wrap;">{q['explanation']}</p>
                        <hr>
                        <p style="font-size: 14px; color: #4B5563;">あなたの入力: <b>{st.session_state.get('user_ans_temp','(未入力)')}</b></p>
                    </div>
                    """, unsafe_allow_html=True)

                    col_ok, col_ng = st.columns(2)
                    with col_ok:
                        if st.button("⭕️ 正解！", type="primary", use_container_width=True):
                            st.session_state["card_scores"][c_idx] = "⭕️"
                            st.session_state["card_idx"] += 1
                            st.session_state["show_answer"] = False
                            st.rerun()
                    with col_ng:
                        if st.button("❌ 不正解", use_container_width=True):
                            st.session_state["card_scores"][c_idx] = "❌"
                            st.session_state["card_idx"] += 1
                            st.session_state["show_answer"] = False
                            st.rerun()

elif app_mode == "📷 AI手書き添削":
    st.markdown("<div class='main-header'>📷 AI手書き添削</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-text'>手書きノートや解答用紙の写真をアップロードすると、AIが思考プロセスや計算を添削・採点します。</div>", unsafe_allow_html=True)

    history_list = load_history()
    selected_quiz = {"quiz_text": "標準テスト問題"}

    if history_list:
        quiz_opts = {f"[{x.get('created_at','')}] {x.get('subject','')} ({x.get('topic','')})": x for x in history_list}
        sel_label = st.selectbox("🎯 採点対象の過去問題を選択", list(quiz_opts.keys()))
        selected_quiz = quiz_opts[sel_label]

    uploaded_file = st.file_uploader("📸 ノート写真をアップロード (PNG / JPG / JPEG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None and HAS_PIL:
        image = Image.open(uploaded_file)
        c_img, c_res = st.columns([1, 1.2])

        with c_img:
            st.image(image, caption="アップロードされた手書き画像", use_container_width=True)

        with c_res:
            if st.button("🔍 AI自動添削を実行", type="primary", use_container_width=True):
                if not test_mode and not (current_api_key or st.session_state.get("user_api_key")):
                    st.error("APIキーが設定されていません。サイドバーまたは.streamlit/secrets.tomlをご確認ください。")
                else:
                    with st.spinner("AI Visionが筆跡・途中の計算式・回答論理を解析中..."):
                        if test_mode:
                            time.sleep(1.5)
                            grading_res = {
                                "total_score": 85,
                                "max_score": 100,
                                "questions": [
                                    {"num": "問1", "status": "⭕️", "score": "40/40", "comment": "公式の適用と論理の展開が完璧です！"},
                                    {"num": "問2", "status": "🔺", "score": "45/60", "comment": "途中式は合っていますが、移項時の符号ミスがあります。"}
                                ],
                                "overall_feedback": "基礎理解は非常に高いです！問2のような計算ミスを防ぐための検算習慣をつけましょう。"
                            }
                        else:
                            vision_prompt = (
                                f"画像は生徒が手書きしたテストの解答用紙です。\n"
                                f"元問題:\n{selected_quiz.get('quiz_text','')}\n"
                                f"模範解答:\n{selected_quiz.get('answers','')}\n\n"
                                f"手書き画像を読み取り、設問ごとの採点結果とフィードバックを出力してください。\n"
                                f"必ず以下のJSONフォーマットのみで返答してください:\n"
                                f"{{\"total_score\": 85, \"max_score\": 100, \"questions\": [{{\"num\": \"問1\", \"status\": \"⭕️\", \"score\": \"40/40\", \"comment\": \"詳細解説\"}}], \"overall_feedback\": \"総評アドバイス\"}}"
                            )
                            raw_res = call_gemini_api([image, vision_prompt])
                            grading_res = extract_json_from_text(raw_res)

                        st.session_state["grading_res"] = grading_res

    if "grading_res" in st.session_state:
        res = st.session_state["grading_res"]
        st.divider()
        st.markdown("### 🏆 採点・添削結果シート")

        st.markdown(
            f"<div class='score-badge'>総合得点: {res.get('total_score', 0)} / {res.get('max_score', 100)} 点</div>",
            unsafe_allow_html=True
        )

        for q in res.get("questions", []):
            status_icon = q.get("status", "・")
            with st.expander(f"{status_icon} {q.get('num', '')} - 獲得点数: {q.get('score', '')}", expanded=True):
                st.write(f"**AI添削コメント:** {q.get('comment', '')}")

        st.info(f"💬 **講師AIからのアドバイス:**\n\n{res.get('overall_feedback', '')}")

elif app_mode == "📈 学習アナリティクス":
    st.markdown("<div class='main-header'>📈 学習アナリティクス</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-text'>Notebook連携データおよび添削結果から、学習の進捗と達成度を可視化します。</div>", unsafe_allow_html=True)

    nb_pts = st.session_state.get("default_pts", 0)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("🎓 現在のアカウント", st.session_state["current_user"])
    with col_b:
        st.metric("⭐ Notebook獲得ポイント", f"{nb_pts} pt")
    with col_c:
        st.metric("📝 過去作成テスト数", f"{len(load_history())} 件")

    st.divider()
    st.markdown("### 📊 単元別理解度チェック")
    st.progress(0.85, text="数学 - 二次関数とグラフ (85%)")
    st.progress(0.60, text="英語 - 関係代名詞の理解 (60%)")
    st.progress(0.40, text="理科 - 化学結合 (40%)")

elif app_mode == "👤 マイページ":
    st.markdown("<div class='main-header'>👤 マイページ</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-text'>ログインアカウントの切替およびユーザーデータの管理を行います。</div>", unsafe_allow_html=True)

    st.info(f"現在アクティブなアカウント: **{st.session_state['current_user']}**")

    st.markdown("### ➕ 新規アカウント追加")
    c_in, c_btn = st.columns([3, 1])
    with c_in:
        new_name = st.text_input("新しいユーザー名を入力", placeholder="例: 鈴木一郎")
    with c_btn:
        st.write("")
        st.write("")
        if st.button("追加", type="primary"):
            if new_name and new_name not in users_list:
                users_list.append(new_name)
                save_registered_users(users_list)
                st.success(f"ユーザー「{new_name}」を追加しました。")
                time.sleep(0.5)
                st.rerun()
            elif new_name in users_list:
                st.warning("すでに登録されている名前です。")

    st.divider()
    st.markdown("### 📋 登録アカウント一覧")
    for user in users_list:
        col_u, col_d = st.columns([3, 1])
        with col_u:
            st.write(f"👤 **{user}**" + (" *(ログイン中)*" if user == st.session_state["current_user"] else ""))
        with col_d:
            if len(users_list) > 1 and user != st.session_state["current_user"]:
                if st.button("削除", key=f"del_user_{user}"):
                    users_list.remove(user)
                    save_registered_users(users_list)
                    st.success(f"「{user}」さんを削除しました。")
                    time.sleep(0.5)
                    st.rerun()
