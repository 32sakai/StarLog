import io
import os
import re
import json
import time
from datetime import datetime
import streamlit as st

# PIL (Pillow) 読み込みチェック
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Google GenAI ライブラリ安全読み込み
GENAI_CLIENT_AVAILABLE = False
GENAI_LEGACY_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_CLIENT_AVAILABLE = True
except ImportError:
    pass

try:
    import google.generativeai as g_legacy
    GENAI_LEGACY_AVAILABLE = True
except ImportError:
    pass

# ------------------------------------------------------------------------------
# 1. ページ基本設定 & カスタムCSS
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="StarLog AI 学習ナビ Ver.4.2.4",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 10px 14px;
        margin-bottom: 6px;
        border-radius: 8px;
        background-color: rgba(255, 255, 255, 0.05);
        transition: background-color 0.2s ease, transform 0.1s ease;
        cursor: pointer;
        width: 100%;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.15);
        transform: translateX(2px);
    }
    .book-card {
        border: 2px solid #3498db;
        border-radius: 10px;
        padding: 20px 10px;
        text-align: center;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.15);
        margin-bottom: 15px;
    }
    .book-title {
        font-size: 20px;
        font-weight: bold;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .user-welcome-box {
        background: rgba(52, 152, 219, 0.15);
        border-left: 4px solid #3498db;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

HISTORY_FILE = "quiz_history.json"
USERS_FILE = "registered_users.json"
DEFAULT_MODEL = "gemini-3.6-flash"

# ------------------------------------------------------------------------------
# 2. 永続化データ（JSON）操作関数
# ------------------------------------------------------------------------------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list): return data
        except Exception: pass
    return []

def save_history_item(item):
    history = load_history()
    history.insert(0, item)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存失敗: {e}")

def delete_history_item(item_id):
    history = load_history()
    updated = [h for h in history if h.get("id") != item_id]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(updated, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"削除失敗: {e}")
        return False

def load_registered_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data: return data
        except Exception: pass
    return ["学習者"]

def save_registered_users(users_list):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"ユーザー一覧保存失敗: {e}")

# ------------------------------------------------------------------------------
# 3. ユーティリティ & 完全強化版パースエンジン
# ------------------------------------------------------------------------------
def sanitize_text(text):
    if not text: return ""
    t = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1 ÷ \2', text)
    t = re.sub(r'```[a-zA-Z]*', '', t)
    t = t.replace('```', '')
    return t

def extract_json_from_text(text):
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = re.sub(r',\s*([}\]])', r'\1', match.group(0))
            return json.loads(json_str)
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"JSON解析エラー: {e}\nテキスト:\n{text}")

def parse_quiz_to_questions(quiz_text):
    clean_text = sanitize_text(quiz_text)
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]

    prob_lines = []
    ans_lines = []
    in_answer_mode = False

    for line in lines:
        if any(k in line for k in ["=== 模範解答", "=== 解答", "【模範解答", "【解答", "模範解答・解説", "解答・解説"]):
            in_answer_mode = True
            continue
        if not in_answer_mode:
            prob_lines.append(line)
        else:
            ans_lines.append(line)

    cards = []
    curr_parent_num = "問1"
    curr_parent_lead = ""
    curr_parent_lines = []

    is_parent = lambda l: bool(re.match(r'^(問\d+|問題\d+|Q\d+)', l))
    is_sub = lambda l: bool(re.match(r'^(（\d+）|\(\d+\)|①|②|③|④|⑤|[1-9]\))', l))

    for line in prob_lines:
        if any(h in line for h in ["確認テスト", "制限時間", "配点", "【問題編】", "【解答欄】", "単元名："]):
            continue

        if is_parent(line):
            m = re.match(r'^(問\d+|問題\d+|Q\d+)', line)
            curr_parent_num = m.group(0) if m else "問1"
            lead = line[len(curr_parent_num):].strip()
            curr_parent_lines = [lead] if lead else []
        elif is_sub(line):
            sub_m = re.match(r'^(（\d+）|\(\d+\)|①|②|③|④|⑤|[1-9]\))', line)
            sub_num = sub_m.group(0) if sub_m else ""
            
            body_clean = re.sub(r'^(（\d+）|\(\d+\)|①|②|③|④|⑤|[1-9]\))\s*', '', line).strip()
            body_clean = re.sub(r'【解答欄】.*', '', body_clean).strip()
            body_clean = re.sub(r'_+', '', body_clean).strip()

            disp_label = f"{curr_parent_num} {sub_num}".strip() if sub_num else curr_parent_num
            p_lead_text = " ".join(curr_parent_lines).strip()
            p_context = f"{curr_parent_num}: {p_lead_text}" if p_lead_text else curr_parent_num

            cards.append({
                "parent_num": curr_parent_num,
                "sub_num": sub_num,
                "display_num": disp_label,
                "parent_context": p_context,
                "body": body_clean,
                "explanation": ""
            })
        else:
            if not cards or cards[-1]["parent_num"] != curr_parent_num:
                curr_parent_lines.append(line)
            else:
                if not re.match(r'^[_＿\s]+$', line) and "【解答欄】" not in line:
                    cards[-1]["body"] += "\n" + line

    ans_by_parent = {}
    curr_p = "問1"
    
    for line in ans_lines:
        if is_parent(line):
            m = re.match(r'^(問\d+|問題\d+|Q\d+)', line)
            curr_p = m.group(0) if m else "問1"
            if curr_p not in ans_by_parent:
                ans_by_parent[curr_p] = []
        else:
            if curr_p not in ans_by_parent:
                ans_by_parent[curr_p] = []
            ans_by_parent[curr_p].append(line)

    for card in cards:
        p_num = card["parent_num"]
        s_num = card["sub_num"]
        
        matched_text = []
        if p_num in ans_by_parent:
            parent_answers = ans_by_parent[p_num]
            recording = False
            for a_line in parent_answers:
                if s_num and s_num in a_line:
                    matched_text.append(a_line)
                    recording = True
                elif recording:
                    if is_sub(a_line) or is_parent(a_line):
                        break
                    matched_text.append(a_line)

            if not matched_text and parent_answers:
                matched_text = parent_answers

        if matched_text:
            card["explanation"] = "\n".join(matched_text)
        else:
            card["explanation"] = "（模範解答はMy参考書のテキストまたはPDFからご確認ください）"

    return cards

# ------------------------------------------------------------------------------
# 4. PDF生成
# ------------------------------------------------------------------------------
def create_quiz_pdf(title_subject, topic, diff, print_mode, quiz_text):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise Exception("reportlab がインストールされていません ('pip install reportlab')")

    font_name = "Helvetica"
    font_paths = [
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("JFont", p, subfontIndex=0))
                font_name = "JFont"
                break
            except Exception: pass

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()

    t_style = ParagraphStyle('T', parent=styles['Heading1'], fontName=font_name, fontSize=13, leading=16, textColor=colors.HexColor('#1a5276'))
    b_style = ParagraphStyle('B', parent=styles['Normal'], fontName=font_name, fontSize=9.5, leading=14, textColor=colors.HexColor('#2c3e50'))
    q_style = ParagraphStyle('Q', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=14, textColor=colors.HexColor('#111111'), spaceBefore=8, spaceAfter=2)
    ans_box_style = ParagraphStyle('A', parent=styles['Normal'], fontName=font_name, fontSize=9.5, leading=16, textColor=colors.HexColor('#333333'), spaceBefore=4, spaceAfter=6)

    elems = [
        Paragraph(f"✏️ StarLog 学習確認プリント: {title_subject}", t_style),
        Paragraph(f"範囲: {topic} | 難易度: {diff}", b_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#3498db'), spaceAfter=10)
    ]

    clean_text = sanitize_text(quiz_text)
    lines = clean_text.split('\n')
    
    for line in lines:
        cl = line.strip()
        cl = re.sub(r'^[#\*\-\s]+', '', cl)
        if not cl or cl == "【解答欄】": continue

        if any(k in cl for k in ["=== 解答", "=== 模範解答"]):
            elems.append(PageBreak())
            elems.append(Paragraph(f"<b>{cl}</b>", t_style))
            elems.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e74c3c'), spaceAfter=10))
        elif re.match(r'^(問\d+|問題\d+|Q\d+)', cl):
            elems.append(Paragraph(f"<b>{cl}</b>", q_style))
        elif re.match(r'^(（\d+）|\(\d+\)|①|②|③|④|⑤)', cl):
            elems.append(Paragraph(cl, b_style))
            sub_m = re.match(r'^(（\d+）|\(\d+\)|①|②|③|④|⑤)', cl)
            s_num = sub_m.group(0) if sub_m else "（答）"
            ans_fmt = f"{s_num} __________________________________________________"
            elems.append(Paragraph(f"<font color='#555555'>{ans_fmt}</font>", ans_box_style))
        else:
            if "【解答欄】" in cl: cl = cl.replace("【解答欄】", "").strip()
            if cl: elems.append(Paragraph(cl.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'), b_style))

    doc.build(elems)
    return buf.getvalue()

# ------------------------------------------------------------------------------
# 5. Gemini API 安全呼び出し関数
# ------------------------------------------------------------------------------
def get_effective_api_key():
    key = ""
    if "GEMINI_API_KEY" in st.secrets:
        key = st.secrets["GEMINI_API_KEY"]
    elif os.environ.get("GEMINI_API_KEY"):
        key = os.environ.get("GEMINI_API_KEY")
    return re.sub(r'[^\x00-\x7F]+', '', key).strip() if key else ""

def call_gemini_api(contents, sys_inst=None, retries=3):
    api_key = get_effective_api_key()
    if not api_key:
        raise ValueError("APIキーが設定されていません。.streamlit/secrets.toml を確認してください。")

    for attempt in range(retries):
        try:
            if GENAI_CLIENT_AVAILABLE:
                client = genai.Client(api_key=api_key)
                cfg = types.GenerateContentConfig(system_instruction=sys_inst) if sys_inst else None
                return client.models.generate_content(model=DEFAULT_MODEL, contents=contents, config=cfg).text
            elif GENAI_LEGACY_AVAILABLE:
                g_legacy.configure(api_key=api_key)
                return g_legacy.GenerativeModel(DEFAULT_MODEL, system_instruction=sys_inst).generate_content(contents).text
            else:
                raise ImportError("Google GenAI ライブラリがインストールされていません。")
        except Exception as e:
            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise e

# ------------------------------------------------------------------------------
# 6. アプリケーション本体 / UI
# ------------------------------------------------------------------------------
st.title("✏️ StarLog AI 学習ナビ Ver.4.2.4")

users_list = load_registered_users()
if "current_user" not in st.session_state:
    st.session_state["current_user"] = users_list[0]

current_api_key = get_effective_api_key()

with st.sidebar:
    st.markdown(f"""
    <div class="user-welcome-box">
        <span style="font-size: 11px; color: #7f8c8d;">現在のログイン</span><br>
        <span style="font-size: 16px; font-weight: bold; color: #2c3e50;">👋 ようこそ、{st.session_state['current_user']} さん！</span>
    </div>
    """, unsafe_allow_html=True)

    st.header("👤 アカウント切り替え")
    user_options = users_list + ["➕ 新しいユーザーを登録"]
    curr_idx = users_list.index(st.session_state["current_user"]) if st.session_state["current_user"] in users_list else 0
    selected_account = st.selectbox("ログインユーザーを選択", user_options, index=curr_idx)

    if selected_account == "➕ 新しいユーザーを登録":
        new_nickname = st.text_input("ニックネームを入力", placeholder="例：タロウ")
        if st.button("✨ 登録してログイン", type="primary", use_container_width=True):
            cleaned_name = new_nickname.strip()
            if cleaned_name and cleaned_name not in users_list:
                users_list.append(cleaned_name)
                save_registered_users(users_list)
                st.session_state["current_user"] = cleaned_name
                st.success(f"「{cleaned_name}」さんを登録しました！")
                time.sleep(0.5)
                st.rerun()
            elif cleaned_name in users_list:
                st.warning("すでに登録されている名前です。")
            else:
                st.warning("ニックネームを入力してください。")
    else:
        if selected_account != st.session_state["current_user"]:
            st.session_state["current_user"] = selected_account
            st.rerun()

    st.divider()
    test_mode = st.checkbox("🧪 API節約/テストモード", value=False)
    st.divider()
    app_mode = st.radio("📂 メニューナビゲーション", ["📝 問題作成", "📖 My参考書", "🌐 WEB一問一答", "📷 AI手書き添削", "👤 マイページ"])

# ==============================================================================
# 📝 問題作成
# ==============================================================================
if app_mode == "📝 問題作成":
    st.subheader(f"💡 新しいプリント・問題を生成する ({st.session_state['current_user']} さん)")
    
    school_type = st.selectbox("🏫 学校区分 (校種)", ["小学生", "中学生", "高校生"], index=0)
    if school_type == "小学生":
        grade_options = ["小1", "小2", "小3", "小4", "小5", "小6"]
        subject_options = ["国語", "算数", "理科", "社会", "英語", "音楽", "図工", "体育", "家庭", "道徳", "総合"]
    elif school_type == "中学生":
        grade_options = ["中1", "中2", "中3"]
        subject_options = ["国語", "数学", "理科", "社会", "英語", "音楽", "美術", "保健体育", "技術", "家庭", "道徳"]
    else:
        grade_options = ["高1", "高2", "高3", "既卒・高卒認定"]
        subject_options = ["数学I・A", "数学II・B", "数学III・C", "英語コミュニケーション", "論理・表現", "物理", "化学", "生物", "地学", "現代の国語", "言語文化", "歴史総合", "日本史探究", "世界史探究", "地理総合"]

    col_g, col_s = st.columns(2)
    with col_g: selected_grade = st.selectbox("🎒 学年", grade_options, index=0)
    with col_s: selected_subject = st.selectbox("📚 教科・科目", subject_options, index=0)

    full_subject_label = f"{selected_grade} {selected_subject}"

    col1, col2 = st.columns(2)
    with col1: difficulty = st.selectbox("🎯 難易度", ["基礎・基本（確認テスト）", "標準（定期テストレベル）", "応用・発展（受験対策レベル）"])
    with col2: print_mode = st.selectbox("📝 プリント形式", ["プリントモード（2枚構成：問題＋解説）", "テストプリントモード（3枚構成：問題＋解答用紙＋解説）"])

    num_questions = st.number_input("🔢 問題数", min_value=1, max_value=20, value=10)
    topic_range = st.text_area("📖 出題範囲・テーマ", placeholder="例：ヨーロッパの生活・特徴、一次関数など")

    if st.button("🚀 StarLog AIで問題を生成する", type="primary", use_container_width=True):
        if not test_mode and not current_api_key:
            st.error("APIキーが設定されていません！.streamlit/secrets.toml を確認してください。")
        elif not topic_range:
            st.warning("出題範囲を入力してください！")
        else:
            with st.spinner("AIが100点満点プリントを作成中..."):
                if test_mode:
                    q_text = "【問題編】\n問1 次の文章を読んで、あとの問いに答えなさい。\n（1）北大西洋を流れる暖流の名前を答えなさい。\n（2）ヨーロッパに温暖な空気を運ぶ風の名前を答えなさい。\n\n=== 模範解答・解説編 ===\n問1\n（1）北大西洋海流（解説）強い暖流です。\n（2）偏西風（解説）一年中吹く風です。"
                else:
                    prompt = f"""
配点合計100点のプリント（{num_questions}問）を作成してください。

【基本情報】
対象: {full_subject_label} ({school_type})
出題範囲: {topic_range}
難易度: {difficulty}
形式: {print_mode}

【必須ルール】
1. タイトル見出しや「【解答欄】」という独立行は作らないでください。
2. 大問の見出し行は、必ず「問1 次の文章を読み、あとの問いに答えなさい。」のように【問1】などの記号のすぐ後ろに全体指示文を書いてください。
3. 小問は必ず「（1）」の形式で記述してください。
4. 模範解答編でも「問1」「（1）」と大問・小問番号を正しく対応させて出力してください。

【構成例】
【問題編】
問1 次の問いに答えなさい。
（1）問題文1
（2）問題文2

=== 模範解答・解説編 ===
問1
（1）解答1（解説）解説文1
（2）解答2（解説）解説文2
"""
                    q_text = sanitize_text(call_gemini_api(prompt))

                item = {
                    "id": str(int(datetime.now().timestamp())),
                    "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "created_by": st.session_state["current_user"],
                    "subject": full_subject_label,
                    "school_type": school_type,
                    "raw_subject": selected_subject,
                    "topic": topic_range,
                    "difficulty": difficulty,
                    "print_type": print_mode,
                    "quiz_text": q_text
                }
                save_history_item(item)
                st.success("問題を生成し、My参考書に保存しました！")

# ==============================================================================
# 📖 My参考書
# ==============================================================================
elif app_mode == "📖 My参考書":
    st.subheader(f"📖 My参考書（{st.session_state['current_user']} さんの本棚）")
    
    history_list = load_history()
    filter_mode = st.radio("👤 表示対象", ["自分のみ", "全員"], horizontal=True)
    if filter_mode == "自分のみ":
        history_list = [x for x in history_list if x.get("created_by") == st.session_state["current_user"]]

    sel_school = st.radio("🏫 校種を選択", ["小学生", "中学生", "高校生"], horizontal=True)
    filtered_h = [x for x in history_list if x.get("school_type", "小学生") == sel_school]
    
    if "selected_book_subject" not in st.session_state:
        st.session_state["selected_book_subject"] = None

    if st.session_state["selected_book_subject"] is None:
        st.markdown("---")
        st.markdown(f"### 📚 {sel_school} の本棚")
        
        subjects = ["国語", "算数", "理科", "社会", "英語", "音楽", "図工", "体育", "家庭", "道徳", "総合"] if sel_school == "小学生" else (["国語", "数学", "理科", "社会", "英語", "音楽", "美術", "保健体育", "技術", "家庭", "道徳"] if sel_school == "中学生" else ["数学", "英語", "理科", "国語", "地歴公民"])

        cols = st.columns(4)
        for idx, subj in enumerate(subjects):
            subj_items = [x for x in filtered_h if subj in x.get("subject", "")]
            count = len(subj_items)
            
            with cols[idx % 4]:
                st.markdown(f"""
                <div class="book-card">
                    <div class="book-title">{subj}</div>
                    <div style="font-size: 12px; opacity: 0.8;">収録プリント: {count}冊</div>
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
            st.info(f"『{current_subj}』のプリントはまだありません。「📝 問題作成」で作成してみましょう！")
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
            <div style="background-color: #ffffff; color: #2c3e50; padding: 25px; border-radius: 8px; border: 1px solid #dcdde1; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h3 style="color: #2980b9; margin-top:0;">📄 {item.get('subject','')} - {item.get('topic','')}</h3>
                <p style="font-size: 12px; color: #7f8c8d;">作成者: <b>{author}</b> | 作成日時: {item.get('created_at','')} | 難易度: {item.get('difficulty','')}</p>
                <hr style="border: 0.5px solid #eee;">
            </div>
            """, unsafe_allow_html=True)
            
            st.text_area("本文プレビュー", value=sanitize_text(item.get("quiz_text", "")), height=350)

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
                with col_pdf: st.warning(f"PDF準備中: {e}")

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

# ==============================================================================
# 🌐 WEB一問一答
# ==============================================================================
elif app_mode == "🌐 WEB一問一答":
    st.subheader(f"🌐 WEB一問一答 ({st.session_state['current_user']} さんの演習)")
    
    history_list = load_history()
    filter_mode = st.radio("👤 表示対象", ["自分のみ", "全員"], horizontal=True)
    if filter_mode == "自分のみ":
        history_list = [x for x in history_list if x.get("created_by") == st.session_state["current_user"]]

    if not history_list:
        st.info("演習可能なプリントがありません。「📝 問題作成」で問題を作成してください。")
    else:
        quiz_opts = {f"[{x.get('created_at','')}] ({x.get('created_by','学習者')}) {x.get('subject','')} - {x.get('topic','')[:10]}...": x for x in history_list}
        selected_label = st.selectbox("🎯 挑戦するプリントを選択", list(quiz_opts.keys()))
        selected_quiz = quiz_opts[selected_label]
        
        questions = parse_quiz_to_questions(selected_quiz.get("quiz_text", ""))
        
        if not questions:
            st.warning("問題形式を自動解析できませんでした。テキスト内容をご確認ください。")
        else:
            if "card_idx" not in st.session_state: st.session_state["card_idx"] = 0
            if "card_scores" not in st.session_state: st.session_state["card_scores"] = {}
            if "show_answer" not in st.session_state: st.session_state["show_answer"] = False

            c_idx = st.session_state["card_idx"]
            total_cards = len(questions)

            if c_idx >= total_cards:
                st.balloons()
                st.success("🎉 全問演習完了！おつかれさまでした！")
                correct_count = sum(1 for v in st.session_state["card_scores"].values() if v == "⭕️")
                st.metric("🏆 得点結果", f"{correct_count} / {total_cards} 問正解 ({int(correct_count/total_cards*100)}%)")
                
                if st.button("🔄 もう一度挑戦する", type="primary"):
                    st.session_state["card_idx"] = 0
                    st.session_state["card_scores"] = {}
                    st.session_state["show_answer"] = False
                    st.rerun()
            else:
                q = questions[c_idx]
                st.progress((c_idx) / total_cards, text=f"カード {c_idx + 1} / {total_cards}")

                parent_html = f"<p style='font-size: 13px; color: #7f8c8d; margin-bottom: 8px;'>📌 {q['parent_context']}</p><hr style='border:0.5px solid #bdc3c7; margin-bottom:12px;'>" if q.get('parent_context') else ""

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 25px; border-radius: 15px; border: 2px solid #bdc3c7; color: #2c3e50; margin-bottom: 20px;">
                    {parent_html}
                    <h4 style="color: #2980b9; margin-top:0;">{q['display_num']}</h4>
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
                    <div style="background-color: #e8f8f5; padding: 20px; border-radius: 10px; border: 2px solid #2ecc71; margin-bottom: 15px; color: #2c3e50;">
                        <p style="color: #27ae60; font-weight: bold; margin:0;">💡 模範解答・解説:</p>
                        <p style="font-size: 16px; white-space: pre-wrap;">{q['explanation']}</p>
                        <hr>
                        <p style="font-size: 14px; color: #7f8c8d;">あなたの入力: <b>{st.session_state.get('user_ans_temp','(未入力)')}</b></p>
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

# ==============================================================================
# 📷 AI手書き添削
# ==============================================================================
elif app_mode == "📷 AI手書き添削":
    st.subheader("📷 手書きノート・解答AI自動添削")
    st.caption("ノートやテスト用紙の写真をアップロードすると、AIが手書き文字や計算過程を自動採点します。")
    
    history_list = load_history()
    selected_quiz = {"quiz_text": "標準テスト"}
    if history_list:
        quiz_opts = {f"[{x.get('created_at','')}] {x.get('subject','')}" : x for x in history_list}
        sel_label = st.selectbox("🎯 添削対象の過去問を選択", list(quiz_opts.keys()))
        selected_quiz = quiz_opts[sel_label]

    uploaded_file = st.file_uploader("📸 ノート写真をアップロード (PNG / JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None and HAS_PIL:
        image = Image.open(uploaded_file)
        c_img, c_res = st.columns([1, 1.2])
        
        with c_img:
            st.image(image, caption="アップロード画像", use_container_width=True)

        with c_res:
            if st.button("🔍 AI自動添削を実行", type="primary", use_container_width=True):
                if not test_mode and not current_api_key:
                    st.error("APIキーが設定されていません！.streamlit/secrets.toml を確認してください。")
                else:
                    with st.spinner("AIが手書き文字と論理を解析中..."):
                        if test_mode:
                            grading_res = {
                                "total_score": 85,
                                "max_score": 100,
                                "questions": [
                                    {"num": "問1", "status": "⭕️", "score": "40/40", "comment": "立式も正確で素晴らしいです！"},
                                    {"num": "問2", "status": "🔺", "score": "45/60", "comment": "途中の計算ミスがあります。"}
                                ],
                                "overall_feedback": "全体的にとても良く書けています！問2の見直しをしましょう。"
                            }
                        else:
                            vision_prompt = f"生徒の手書きノート画像を解析し、元問題({selected_quiz.get('quiz_text','')})と比較して採点してください。\n出力: JSONのみ({{\"total_score\":85,\"max_score\":100,\"questions\":[{{\"num\":\"問1\",\"status\":\"⭕️\",\"score\":\"40/40\",\"comment\":\"解説\"}}],\"overall_feedback\":\"総評\"}})"
                            grading_res = extract_json_from_text(call_gemini_api([image, vision_prompt]))

                        st.session_state["grading_res"] = grading_res

    if "grading_res" in st.session_state:
        res = st.session_state["grading_res"]
        st.divider()
        st.metric("🏆 採点結果", f"{res.get('total_score', 0)} / {res.get('max_score', 100)} 点")
        for q in res.get("questions", []):
            with st.expander(f"{q.get('status','・')} {q.get('num','')} ({q.get('score','')}点)", expanded=True):
                st.write(q.get('comment',''))
        st.info(f"💬 **AIからのアドバイス:**\n{res.get('overall_feedback','')}")

# ==============================================================================
# 👤 マイページ
# ==============================================================================
elif app_mode == "👤 マイページ":
    st.subheader("👤 マイページ（登録アカウント管理）")
    st.info(f"現在のログインアカウント: **{st.session_state['current_user']}**")
    
    st.markdown("### 📋 登録済みユーザー一覧")
    for u in users_list:
        col_u, col_d = st.columns([3, 1])
        with col_u:
            st.write(f"👤 **{u}**" + (" (現在のユーザー)" if u == st.session_state["current_user"] else ""))
        with col_d:
            if len(users_list) > 1 and u != st.session_state["current_user"]:
                if st.button(f"削除", key=f"del_user_{u}"):
                    users_list.remove(u)
                    save_registered_users(users_list)
                    st.success(f"「{u}」さんを削除しました。")
                    time.sleep(0.5)
                    st.rerun()