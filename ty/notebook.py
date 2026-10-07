import streamlit as st
import json
import os
from datetime import date, datetime, timedelta

# --- ページ基本設定 ---
st.set_page_config(
    page_title="notebook",
    page_icon="📓",
    layout="wide"
)

# --- 1. データ保存・読み込み処理（JSON） ---
DATA_FILE = "notebook_data.json"

def load_data():
    """保存されたデータを読み込む（無ければ初期値を返す）"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # 初期データ構造
    return {
        "points": 30,
        "plans": [
            {
                "subject": "数学",
                "color": "#1E88E5", # 青
                "title": "2学期中間テスト ワーク",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=12)),
                "total_pages": 30,
                "completed_pages": 6
            }
        ],
        "inventory": {
            "月曜日": ["体操服", "書道セット", "筆記用具"],
            "火曜日": ["リコーダー", "筆記用具"]
        }
    }

def save_data(data):
    """データをJSONファイルに保存する"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# セッション状態の初期化
if "user_data" not in st.session_state:
    st.session_state.user_data = load_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- 2. ログイン画面（パスワード認証） ---
PASSWORD_SECRET = "1234"  # 任意で変更可能

if not st.session_state.authenticated:
    st.markdown("### 🔒 notebook ログイン")
    col1, col2 = st.columns([1, 2])
    with col1:
        input_pass = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if input_pass == PASSWORD_SECRET:
                st.session_state.authenticated = True
                st.success("ログイン成功！")
                st.rerun()
            else:
                st.error("パスワードが違います")
    st.stop()  # ログイン前はここで処理を停止

# --- 3. 追従固定ヘッダー（CSS） ---
st.markdown("""
<style>
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 60px;
        background-color: #ffffff;
        border-bottom: 2px solid #e0e0e0;
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .header-logo {
        font-size: 22px;
        font-weight: bold;
        color: #333333;
    }
    .header-points {
        font-size: 18px;
        font-weight: bold;
        color: #f39c12;
        background-color: #fef5e7;
        padding: 5px 15px;
        border-radius: 20px;
    }
    .main .block-container {
        padding-top: 80px; /* ヘッダーと被らないための余白 */
    }
</style>
""", unsafe_allow_cookies=True)

# ヘッダー画像チェック（logo.pngがあれば表示）
logo_html = "📓 notebook"
if os.path.exists("logo.png"):
    logo_html = '<img src="app/static/logo.png" height="35" alt="notebook">'

pts = st.session_state.user_data.get("points", 0)
st.markdown(f"""
<div class="fixed-header">
    <div class="header-logo">{logo_html}</div>
    <div class="header-points">⭐ 所持 pt: {pts} pt</div>
</div>
""", unsafe_allow_html=True)

# --- 4. サイドバー ナビゲーション ---
st.sidebar.title("メニュー")
menu = st.sidebar.radio(
    "機能選択",
    ["🏠 ダッシュボード", "📅 Myスケジュール", "🎯 マイ・ルート", "⚔️ dailyタスク", "🎒 持ち物リスト", "🚀 StarLog"]
)

# パスワードログアウトボタン
if st.sidebar.button("🔒 ログアウト"):
    st.session_state.authenticated = False
    st.rerun()

# --- 5. 各画面表示 logic ---
data = st.session_state.user_data

if menu == "🏠 ダッシュボード":
    st.title("🏠 ダッシュボード")
    
    # 簡単な情報サマリー
    st.info("👋 おかえりなさい！今日も計画的に進めましょう。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 テストまでのカウントダウン")
        if data["plans"]:
            plan = data["plans"][0]
            end_d = datetime.strptime(plan["end_date"], "%Y-%m-%d").date()
            diff = (end_d - date.today()).days
            st.metric(label=plan["title"], value=f"あと {diff} 日", delta=f"{plan['subject']}")
        else:
            st.write("計画が登録されていません。")

    with col2:
        st.subheader("🚀 StarLog 連携")
        st.write("プリント作成・学習ハブ")
        
        # StarLogバナー画像チェック（starlog_banner.pngがあれば表示）
        if os.path.exists("starlog_banner.png"):
            st.image("starlog_banner.png", use_container_width=True)
            
        st.link_button("StarLog を別タブで開く 🚀", "http://localhost:8501")

elif menu == "🎯 マイ・ルート":
    st.title("🎯 マイ・ルート（逆算学習計画）")
    st.write("教科ごとの目標と期間を設定します。")
    st.json(data["plans"])  # 現在のデータを簡易表示

else:
    st.title(menu)
    st.write("画面構築中...")