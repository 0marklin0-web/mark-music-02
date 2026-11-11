import base64
import io
import locale
import os
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# 設定繁體中文語系以支援精確的中文筆劃與字典排序
try:
    locale.setlocale(locale.LC_COLLATE, "zh_TW.UTF-8")
except Exception:
    try:
        locale.setlocale(locale.LC_COLLATE, "zh_TW")
    except Exception:
        pass


def stroke_sort_key(item):
    """回傳排序鍵：英文在前，其次依第一個字繁體中文筆劃順序排序"""
    s = str(item).strip()
    if not s:
        return (2, 0, "")

    first_char = s[0]

    # 1. 英文 / ASCII 字母排在最前面 (Group 0)
    if first_char.isascii() and first_char.isalpha():
        return (0, 0, s.lower(), s)
    elif first_char.isascii():
        return (0, 1, s.lower(), s)

    # 常用字筆劃字典（針對名稱第一個字進行極速筆劃對應）
    stroke_dict = {
        "一": 1, "乙": 1,
        "丁": 2, "七": 2, "乃": 2, "九": 2, "了": 2, "二": 2, "人": 2, "入": 2, "八": 2,
        "三": 3, "下": 3, "丈": 3, "上": 3, "丸": 3, "凡": 3, "久": 3, "也": 3, "大": 3, "女": 3, "子": 3, "小": 3, "山": 3, "川": 3, "己": 3, "干": 3, "弓": 3,
        "王": 4, "五": 4, "中": 4, "公": 4, "六": 4, "切": 4, "天": 4, "太": 4, "少": 4, "巴": 4, "方": 4, "日": 4, "月": 4, "木": 4, "水": 4, "火": 4, "牛": 4, "心": 4, "文": 4,
        "古": 5, "出": 5, "包": 5, "半": 5, "平": 5, "正": 5, "母": 5, "民": 5, "生": 5, "白": 5, "目": 5, "立": 5, "示": 5, "石": 5, "禾": 5, "四": 5,
        "光": 6, "再": 6, "同": 6, "名": 6, "后": 6, "好": 6, "字": 6, "安": 6, "朱": 6, "江": 6, "百": 6, "竹": 6, "米": 6, "老": 6, "西": 6,
        "告": 7, "宋": 7, "李": 7, "吳": 7, "林": 7, "何": 7, "余": 7, "沈": 7, "汪": 7, "初": 7, "吹": 7, "我": 7,
        "周": 8, "披": 8, "雨": 8, "夜": 8, "突": 9, "倒": 10, "國": 11, "晴": 12, "經": 13, "蔡": 14, "樂": 15, "獨": 16, "隱": 17
    }

    # 取得第一個字的筆劃數，若未在預設集中則備用比對
    stroke = stroke_dict.get(first_char, 99)

    try:
        collate_key = locale.strxfrm(s)
    except Exception:
        collate_key = s

    return (1, stroke, collate_key)


# --- 雲端自動同步與永久保存機制（全自動，無需手動設定任何 Key/Token） ---
REMOTE_SONGS_URL = "https://kvdb.io/StreetBuskerSongBook2026TW/my_songs_csv"
REMOTE_PWD_URL = "https://kvdb.io/StreetBuskerSongBook2026TW/admin_password_txt"


def sync_from_cloud():
    """當主機重啟或休眠喚醒時，自動向雲端讀取最後一次發佈的歌單與密碼"""
    try:
        res = requests.get(REMOTE_SONGS_URL, timeout=3)
        if res.status_code == 200 and res.text.strip():
            with open("my_songs.csv", "w", encoding="utf-8") as f:
                f.write(res.text)
    except Exception:
        pass

    try:
        res_pwd = requests.get(REMOTE_PWD_URL, timeout=3)
        if res_pwd.status_code == 200 and res_pwd.text.strip():
            with open("admin_password.txt", "w", encoding="utf-8") as f:
                f.write(res_pwd.text.strip())
    except Exception:
        pass


def save_persistently(songs_csv=None, pwd=None):
    """寫入本地硬碟，並自動同步傳至雲端空間永久保存"""
    if songs_csv is not None:
        with open("my_songs.csv", "w", encoding="utf-8") as f:
            f.write(songs_csv)
        try:
            requests.post(REMOTE_SONGS_URL, data=songs_csv.encode("utf-8"), timeout=4)
        except Exception:
            pass

    if pwd is not None:
        with open("admin_password.txt", "w", encoding="utf-8") as f:
            f.write(str(pwd).strip())
        try:
            requests.post(REMOTE_PWD_URL, data=str(pwd).strip().encode("utf-8"), timeout=4)
        except Exception:
            pass


# 程式開啟或伺服器重啟時，自動下載最新的歌單資料
if "cloud_synced" not in st.session_state:
    sync_from_cloud()
    st.session_state.cloud_synced = True


# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# --- 管理員密碼檔案寫入與讀取核心 ---
PWD_FILE = "admin_password.txt"
if not os.path.exists(PWD_FILE):
    save_persistently(pwd="123456")


def get_admin_password():
    if os.path.exists(PWD_FILE):
        with open(PWD_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "123456"


def set_admin_password(new_pwd):
    save_persistently(pwd=str(new_pwd).strip())


# 🎯 核心樣式修正：打造活潑視覺風格，優化按鈕互動與行動端表現，縮小選單與元件間隔
st.markdown(
    """
    <style>
    /* 1. 隱藏 Streamlit 右上角選單中可能暴露 / 原始碼檢視按鈕 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 背景視覺漸層與主題優化 */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    /* 2. 選單大標題與字體微調 */
    h1 {
        font-weight: 800 !important;
        color: #0f172a !important;
    }

    h2 {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #1e293b !important;
        margin-top: 8px !important;
        margin-bottom: 4px !important;
    }

    /* 歌詞文字 (h3 標籤) 強制設為高對比深色 */
    h3 {
        font-size: 20px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        line-height: 1.6 !important;
    }

    /* 強制指定所有內文 Markdown 段落文字顏色 */
    .stMarkdown p, div[data-testid="stMarkdownContainer"] p {
        color: #0f172a !important;
    }

    /* 專門修正 st.success 提示框：改用寶藍/靛藍漸層搭配純白清晰文字 */
    div[data-testid="stAlert"] {
        background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3) !important;
    }
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] div, 
    div[data-testid="stAlert"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* 3. 按鈕內部文字與極致縮小間隔樣式 */
    div.stButton > button p {
        font-size: 17px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* 4. Radio 選項容器與字體活潑化 */
    div.stRadio label p {
        font-size: 18px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
    }
    
    div.stRadio > div {
        background-color: #ffffff;
        padding: 6px 12px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }

    /* 縮小 Streamlit 元件容器上下間距與 Vertical Block 行距 */
    div[data-testid="element-container"] {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.2rem !important;
    }
    
    /* 5. 核心按鈕動態與高度/間隔極致緊湊化修正 */
    div.stButton > button {
        min-height: 38px !important;
        height: 38px !important;
        margin-top: 1px !important;
        margin-bottom: 1px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        border-radius: 10px !important;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
        color: #1e293b !important;
        border: 1.5px solid #cbd5e1 !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.2s ease-in-out !important;
    }

    div.stButton > button:hover {
        transform: translateY(-1px) scale(1.01) !important;
        border-color: #6366f1 !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25) !important;
        background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%) !important;
    }

    div.stButton > button:active {
        transform: translateY(1px) !important;
    }

    /* 主要按鈕 (如返回鍵) 的特色視覺 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        border: none !important;
        color: #ffffff !important;
        box-shadow: 0 3px 10px rgba(79, 70, 229, 0.35) !important;
    }
    div.stButton > button[kind="primary"] p {
        color: #ffffff !important;
    }

    /* 6. 折疊卡片樣式 */
    .stExpander {
        border-radius: 14px !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
        border: 1px solid #e2e8f0 !important;
    }
    .stExpander details summary p {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #4338ca !important;
    }
    
    /* 7. 強制手機版與電腦版皆維持 2 欄並列排版，並緊密欄間距 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 0.3rem !important;
    }
    [data-testid="column"] {
        flex: 1 1 50% !important;
        width: 50% !important;
        min-width: 50% !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 2. 實體檔案同步核心 ---
DATA_FILE = "my_songs.csv"

# 初始化：如果雲端還沒有這個檔案，先建立一份預設資料檔案
if not os.path.exists(DATA_FILE):
    default_data = {
        "歌手名稱": ["周杰倫", "周杰倫", "五月天", "蔡依林", "告五人"],
        "歌曲名稱": [
            "晴天",
            "告白氣球",
            "突然好想你",
            "倒帶",
            "披星戴月的想你",
        ],
        "分類": [
            "國語流行",
            "國語流行",
            "經典樂團",
            "國語流行",
            "獨立樂團",
        ],
        "歌詞": [
            "故事的小黃花 從出生那年就飄著\n童年的蕩秋千 隨記憶一直晃到現在\n吹著前奏望著天空 我想起花瓣試著掉落",
            "親愛的 愛上你 從那天起\n甜蜜的很輕易\n親愛的 別任性 你的眼睛\n在說我願意",
            "突然好想你 你會在哪裡\n過得快樂或委屈\n突然好想你 突然鋒利的回憶\n突然模糊的眼睛",
            "你總是要我乖 張開雙手帶到未來\n如果你善解人意 怎麼不明白\n我們的愛太無奈 總是承載著太多期盼",
            "我會披星戴月的想你\n我會奮不顧身地前進\n遠方煙火點燃你的心\n照亮我的一線生機",
        ],
    }
    init_df = pd.DataFrame(default_data)
    save_persistently(songs_csv=init_df.to_csv(index=False, encoding="utf-8"))

# 讀取實體檔案
df = pd.read_csv(DATA_FILE, encoding="utf-8").fillna("").astype(str)

# --- 3. 側邊欄：模式切換 ---
st.sidebar.title("⚙️ 模式切換面板")
mode = st.sidebar.radio(
    "請選擇當前模式：",
    ["觀眾模式 📱 (粉絲看歌詞)", "管理員模式 🔑 (後台上傳)"],
)

# --- 4. 管理員模式 🔑 ---
if "管理員" in mode:
    st.title("👨‍💼 管理員後台管理 (實體檔案全站同步版)")
    st.markdown("---")

    current_admin_pwd = get_admin_password()

    password = st.text_input(
        "🔑 請輸入管理員登入密碼：", type="password", key="admin_password"
    )

    if password == current_admin_pwd:
        st.success("🔓 認證成功！您現在可以更新歌單與修改管理員密碼。")

        # 🔐 新增修改密碼功能選單
        with st.expander("🔐 變更管理員登入密碼", expanded=False):
            new_pwd = st.text_input("請輸入新密碼：", type="password", key="new_pwd_input")
            confirm_pwd = st.text_input("再次確認新密碼：", type="password", key="confirm_pwd_input")
            if st.button("💾 儲存新密碼", key="save_pwd_btn"):
                if not new_pwd.strip():
                    st.warning("⚠️ 密碼不可為空！")
                elif new_pwd != confirm_pwd:
                    st.error("❌ 兩次輸入的密碼不一致！")
                else:
                    set_admin_password(new_pwd)
                    st.success("🎉 管理員密碼已成功更新！後續登入請使用新密碼。")
                    st.balloons()

        st.markdown("### 📋 方式一：複製貼上更新（💯 實體寫入，手機 100% 絕對同步）")
        paste_data = st.text_area(
            "📥 請在此處貼上您從 Excel 複製的全部歌單內容：",
            height=200,
            key="paste_data_area",
        )

        if st.button("🔥 發佈最新歌單", key="publish_btn"):
            if paste_data.strip():
                try:
                    # 使用自動偵測分隔符號 (支援 Tab 或逗號)
                    new_df = pd.read_csv(
                        io.StringIO(paste_data), sep=None, engine="python"
                    )
                    new_df.dropna(how="all", inplace=True)
                    new_df.columns = [str(col).strip() for col in new_df.columns]

                    required_cols = ["歌手名稱", "歌曲名稱", "歌詞", "分類"]
                    if all(col in new_df.columns for col in required_cols):
                        for col in required_cols:
                            new_df[col] = new_df[col].fillna("").astype(str).str.strip()
                        csv_output = new_df[required_cols].to_csv(index=False, encoding="utf-8")
                        save_persistently(songs_csv=csv_output)
                        st.success("🎉 歌單寫入檔案與雲端備份！隔天重啟也不會消失！")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ 欄位不符！請確認包含：歌手名稱、歌曲名稱、歌詞、分類")
                except Exception as e:
                    st.error(f"❌ 解析失敗: {e}")
        st.table(df)
    elif password != "":
        st.error("🔒 密碼錯誤！")

# --- 5. 觀眾模式 📱 ---
else:
    st.title("🎸 現場 Live 點歌與動態歌詞本")
    st.caption("✨ 歡迎現場的朋友！點選下方大按鈕看歌詞
