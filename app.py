import base64
import io
import json
import locale
import os
import re
import urllib.error
import urllib.request
import pandas as pd
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


# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# --- 雲端永久儲存同步核心 (GitHub API 自動偵測與同步) ---
PWD_FILE = "admin_password.txt"
DATA_FILE = "my_songs.csv"


def _detect_git_info():
    repo = ""
    branch = ""
    try:
        if os.path.exists(".git/config"):
            with open(".git/config", "r", encoding="utf-8", errors="ignore") as f:
                cfg = f.read()
            m = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?\s*$", cfg, re.MULTILINE)
            if m:
                repo = m.group(1).strip()
        if os.path.exists(".git/HEAD"):
            with open(".git/HEAD", "r", encoding="utf-8", errors="ignore") as f:
                head = f.read().strip()
            if head.startswith("ref: refs/heads/"):
                branch = head.replace("ref: refs/heads/", "").strip()
    except Exception:
        pass
    return repo, branch


def _get_github_config():
    token = ""
    repo = ""
    branch = ""
    try:
        for key in ("GITHUB_TOKEN", "github_token", "TOKEN", "token"):
            if key in st.secrets and str(st.secrets[key]).strip():
                token = str(st.secrets[key]).strip()
                break
        for key in ("GITHUB_REPO", "github_repo", "REPO", "repo"):
            if key in st.secrets and str(st.secrets[key]).strip():
                repo = str(st.secrets[key]).strip()
                break
        for key in ("GITHUB_BRANCH", "github_branch", "BRANCH", "branch"):
            if key in st.secrets and str(st.secrets[key]).strip():
                branch = str(st.secrets[key]).strip()
                break
    except Exception:
        pass

    if not token:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        token = str(st.session_state.get("runtime_github_token", "")).strip()

    auto_repo, auto_branch = _detect_git_info()
    if not repo:
        repo = os.environ.get("GITHUB_REPO", "").strip() or auto_repo
    if not branch:
        branch = os.environ.get("GITHUB_BRANCH", "").strip() or auto_branch

    return token, repo, branch


def _github_request(url, token="", method="GET", data=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Streamlit-Songbook-App",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_branch(token, repo, branch):
    if branch:
        return branch
    try:
        repo_info = _github_request(f"https://api.github.com/repos/{repo}", token)
        return repo_info.get("default_branch", "main")
    except Exception:
        return "main"


def pull_from_github(filepath):
    token, repo, branch = _get_github_config()
    if not repo:
        return False
    try:
        branch = _resolve_branch(token, repo, branch)
        url = f"https://api.github.com/repos/{repo}/contents/{filepath}?ref={branch}"
        res = _github_request(url, token)
        content_b64 = res.get("content", "")
        if content_b64:
            raw_bytes = base64.b64decode(content_b64)
            with open(filepath, "wb") as f:
                f.write(raw_bytes)
            return True
    except Exception:
        try:
            branch = branch or "main"
            raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{filepath}"
            req = urllib.request.Request(raw_url, headers={"User-Agent": "Streamlit-Songbook-App"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_bytes = resp.read()
                if raw_bytes:
                    with open(filepath, "wb") as f:
                        f.write(raw_bytes)
                    return True
        except Exception:
            pass
    return False


def push_to_github(filepath, commit_msg="Sync data"):
    token, repo, branch = _get_github_config()
    if not token:
        return False, "請在上方「☁️ 雲端永久儲存設定」或 Streamlit Secrets 填入 GITHUB_TOKEN"
    if not repo:
        return False, "無法自動偵測 GitHub 倉庫名稱，請在 Streamlit Secrets 設定 GITHUB_REPO"
    if not os.path.exists(filepath):
        return False, f"找不到檔案 {filepath}"
    try:
        branch = _resolve_branch(token, repo, branch)
        url = f"https://api.github.com/repos/{repo}/contents/{filepath}"
        sha = None
        try:
            existing = _github_request(f"{url}?ref={branch}", token)
            sha = existing.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise

        with open(filepath, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "message": commit_msg,
            "content": content_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        _github_request(url, token, method="PUT", data=payload)
        return True, "成功永久同步至 GitHub"
    except Exception as e:
        return False, str(e)


if "github_synced" not in st.session_state:
    pull_from_github(PWD_FILE)
    pull_from_github(DATA_FILE)
    st.session_state.github_synced = True

# --- 管理員密碼檔案寫入與讀取核心 ---
if not os.path.exists(PWD_FILE):
    with open(PWD_FILE, "w", encoding="utf-8") as f:
        f.write("123456")
    push_to_github(PWD_FILE, "Initialize admin password")

def get_admin_password():
    if os.path.exists(PWD_FILE):
        with open(PWD_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "123456"

def set_admin_password(new_pwd):
    with open(PWD_FILE, "w", encoding="utf-8") as f:
        f.write(str(new_pwd).strip())
    return push_to_github(PWD_FILE, "Update admin password")

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
    pd.DataFrame(default_data).to_csv(DATA_FILE, index=False, encoding="utf-8")
    push_to_github(DATA_FILE, "Initialize default songs")

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

        _cfg_token, _cfg_repo, _ = _get_github_config()
        if not _cfg_token:
            with st.expander("☁️ 雲端永久儲存設定（首次設定後重啟永不遺失）", expanded=True):
                st.caption(
                    f"已自動偵測 GitHub 倉庫：`{_cfg_repo or '未偵測到'}`。"
                    "請在 Streamlit Cloud 後台 Secrets 加入 `GITHUB_TOKEN`，或先在此貼上金鑰以立即同步："
                )
                input_token = st.text_input(
                    "GitHub Personal Access Token (ghp_...)：",
                    type="password",
                    value=st.session_state.get("runtime_github_token", ""),
                    key="github_token_ui_input",
                )
                if input_token.strip():
                    st.session_state.runtime_github_token = input_token.strip()
                    if st.button("☁️ 立即將目前歌單與密碼永久同步至 GitHub", key="sync_now_btn"):
                        ok1, msg1 = push_to_github(PWD_FILE, "Sync admin password")
                        ok2, msg2 = push_to_github(DATA_FILE, "Sync song list")
                        if ok1 and ok2:
                            st.success("🎉 已成功永久寫入 GitHub！建議將此 Token 存入 Streamlit Secrets 以免主機重啟後需重填。")
                        else:
                            st.error(f"❌ 同步失敗：{msg2 if not ok2 else msg1}")

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
                    sync_ok, sync_msg = set_admin_password(new_pwd)
                    if sync_ok:
                        st.success("🎉 管理員密碼已成功更新並永久儲存！後續登入請使用新密碼。")
                        st.balloons()
                    else:
                        st.warning(f"⚠️ 本機密碼已更新，但雲端永久同步未完成：{sync_msg}")

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
                        new_df[required_cols].to_csv(
                            DATA_FILE, index=False, encoding="utf-8"
                        )
                        sync_ok, sync_msg = push_to_github(DATA_FILE, "Update song list")
                        if sync_ok:
                            st.success("🎉 歌單已永久寫入雲端與硬碟檔案！")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 本機歌單已更新，但雲端永久同步未完成：{sync_msg}")
                    else:
                        st.error("❌ 欄位不符！請確認包含：歌手名稱、歌曲名稱、歌詞、分類")
                except Exception as e:
                    st.error(f"❌ 解析失敗: {e}")
        st.table(df)
    elif password != "":
        st.error("🔒 密碼錯誤！")

# --- 5. 觀眾模式 📱 ---
else:
    st.title("🎸 「彈唱Mark」點歌單(內含歌詞)")
    st.caption("✨ 歡迎現場的朋友！點選下方大按鈕看歌詞！")
    st.markdown("---")

    st.markdown('<p style="font-size: 125%;">歡迎加入並追蹤「彈唱Mark」IG <a href="https://www.instagram.com/mark.lin.tw?xtok=MXd0OHh4Y2o5MXFxNQ%3D%3D&utm_source=qr" target="_blank">(連結)</a>呦!</p>', unsafe_allow_html=True)

    # 預設展開 QR Code (expanded=True)
    with st.expander("📱 點我展開現場專用 QR Code", expanded=True):
        qr_component_code = """
            <div id="qrcode-container" style="display:flex; flex-direction:column; align-items:center;">
                <p style="font-size:14px; color:#555;">正在產生現場專用 QR Code...</p>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
            <script>
                const currentUrl = window.parent.location.href;
                const container = document.getElementById('qrcode-container');
                container.innerHTML = '';
                
                const qrDiv = document.createElement('div');
                container.appendChild(qrDiv);
                
                new QRCode(qrDiv, {
                    text: currentUrl,
                    width: 180,
                    height: 180,
                    colorDark : "#000000",
                    colorLight : "#ffffff",
                    correctLevel : QRCode.CorrectLevel.H
                });
                
                const caption = document.createElement('p');
                caption.style.cssText = "font-size: 14px; color: #31333F; margin-top: 10px; text-align: center;";
                caption.innerText = "現場觀眾掃描此碼即可進入此點歌本";
                container.appendChild(caption);
            </script>
        """
        components.html(qr_component_code, height=240)

    # 利用 Session State 記錄點選狀態與滾動目標
    if "filter_type" not in st.session_state:
        st.session_state.filter_type = "singer"
    if "chosen_filter_val" not in st.session_state:
        st.session_state.chosen_filter_val = None
    if "chosen_song" not in st.session_state:
        st.session_state.chosen_song = None
    if "scroll_target" not in st.session_state:
        st.session_state.scroll_target = None

    # 第一層：請選擇點歌方式 (歌手 vs 分類)
    st.markdown('<div id="section_top"></div>', unsafe_allow_html=True)
    st.markdown("## 🎤 請選擇瀏覽與點歌方式：")

    search_by = st.radio(
        "請選擇分類依據：",
        ["👤 按歌手查找", "📁 按風格分類查找"],
        horizontal=True,
        label_visibility="collapsed",
        key="search_by_radio",
    )

    # 判斷當前選擇的查找模式
    current_mode = "singer" if "按歌手" in search_by else "category"

    # 如果切換了查找模式，自動清空先前的選項以確保畫面正常顯示對應清單
    if "last_mode" not in st.session_state:
        st.session_state.last_mode = current_mode

    if st.session_state.last_mode != current_mode:
        st.session_state.last_mode = current_mode
        st.session_state.filter_type = current_mode
        st.session_state.chosen_filter_val = None
        st.session_state.chosen_song = None

    if current_mode == "singer":
        # 🎯 新增：歌手名稱文字搜尋輸入框
        singer_search = st.text_input(
            "🔍 搜尋歌手名稱：",
            placeholder="請輸入歌手姓名關鍵字...",
            key="singer_search_input",
        )

        singers = sorted(
            [s for s in df["歌手名稱"].unique() if s.strip()],
            key=stroke_sort_key,
        )

        # 依關鍵字進行過濾
        if singer_search.strip():
            singers = [
                s for s in singers if singer_search.strip().lower() in s.lower()
            ]

        if not singers:
            st.info("🔍 未找到符合關鍵字的歌手。")

        # 2 欄並列排版
        for i in range(0, len(singers), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(singers):
                    singer = singers[i + j]
                    with cols[j]:
                        st.markdown(
                            f'<div id="item_singer_{singer}"></div>',
                            unsafe_allow_html=True,
                        )
                        is_active = (
                            st.session_state.filter_type == "singer"
                        ) and (st.session_state.chosen_filter_val == singer)
                        label_text = (
                            f"👉 【 {singer} 】 👈"
                            if is_active
                            else f"👤 {singer}"
                        )
                        if st.button(
                            label_text,
                            key=f"btn_singer_{singer}",
                            use_container_width=True,
                        ):
                            st.session_state.filter_type = "singer"
                            st.session_state.chosen_filter_val = singer
                            st.session_state.chosen_song = None
                            st.session_state.scroll_target = "section_songs"
                            st.rerun()

    else:
        categories = sorted(
            [c for c in df["分類"].unique() if c.strip()], key=stroke_sort_key
        )
        # 2 欄並列排版
        for i in range(0, len(categories), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(categories):
                    cat = categories[i + j]
                    with cols[j]:
                        st.markdown(
                            f'<div id="item_category_{cat}"></div>',
                            unsafe_allow_html=True,
                        )
                        is_active = (
                            st.session_state.filter_type == "category"
                        ) and (st.session_state.chosen_filter_val == cat)
                        label_text = (
                            f"👉 【 {cat} 】 👈"
                            if is_active
                            else f"📁 {cat}"
                        )
                        if st.button(
                            label_text,
                            key=f"btn_cat_{cat}",
                            use_container_width=True,
                        ):
                            st.session_state.filter_type = "category"
                            st.session_state.chosen_filter_val = cat
                            st.session_state.chosen_song = None
                            st.session_state.scroll_target = "section_songs"
                            st.rerun()

    # 第二層：如果選了歌手或分類，顯示對應的歌曲清單
    if st.session_state.chosen_filter_val:
        st.markdown('<div id="section_songs"></div>', unsafe_allow_html=True)
        st.markdown("---")

        # ⬅️ 返回上一頁按鈕 (傳回原點選的歌手/分類項目位置)
        if st.button(
            "⬅️ 返回上一頁（選擇歌手/分類）",
            key="back_to_top_btn",
            use_container_width=True,
            type="primary",
        ):
            target_val = st.session_state.chosen_filter_val
            target_type = st.session_state.filter_type
            st.session_state.chosen_filter_val = None
            st.session_state.chosen_song = None
            if target_val:
                st.session_state.scroll_target = f"item_{target_type}_{target_val}"
            else:
                st.session_state.scroll_target = "section_top"
            st.rerun()

        filter_label = (
            "歌手" if st.session_state.filter_type == "singer" else "分類"
        )
        st.markdown(
            f"## 🎶 2. 【{st.session_state.chosen_filter_val}】({filter_label}) 的歌曲清單："
        )

        if st.session_state.filter_type == "singer":
            filtered_df = df[
                df["歌手名稱"] == st.session_state.chosen_filter_val
            ].copy()
        else:
            filtered_df = df[
                df["分類"] == st.session_state.chosen_filter_val
            ].copy()

        # 歌曲名稱依筆劃順序排序
        filtered_df["_stroke_key"] = filtered_df["歌曲名稱"].apply(
            stroke_sort_key
        )
        filtered_df = filtered_df.sort_values("_stroke_key").drop(
            columns=["_stroke_key"]
        )

        for idx, row in filtered_df.iterrows():
            song = row["歌曲名稱"]
            singer_name = row["歌手名稱"]
            is_selected = st.session_state.chosen_song == song

            display_title = (
                f"《 {song} 》{singer_name}"
                if st.session_state.filter_type == "category"
                else f"《 {song} 》"
            )
            label_song = (
                f"🔥 正在播放：{display_title}"
                if is_selected
                else f"🎵 {display_title}"
            )

            if st.button(
                label_song,
                key=f"btn_song_{idx}_{song}",
                use_container_width=True,
            ):
                st.session_state.chosen_song = song
                st.session_state.chosen_singer_for_song = singer_name
                st.session_state.scroll_target = "section_lyrics"
                st.rerun()

    # 第三層：如果選了歌曲，設定錨點並顯示歌詞
    if st.session_state.chosen_song:
        st.markdown('<div id="section_lyrics"></div>', unsafe_allow_html=True)
        st.markdown("---")

        # ⬅️ 返回上一頁按鈕
        if st.button(
            "⬅️ 返回上一頁（歌曲清單）",
            key="back_to_songs_btn",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.chosen_song = None
            st.session_state.scroll_target = "section_songs"
            st.rerun()

        target_singer = getattr(
            st.session_state,
            "chosen_singer_for_song",
            st.session_state.chosen_filter_val,
        )
        song_info = df[
            (df["歌曲名稱"] == st.session_state.chosen_song)
            & (df["歌手名稱"] == target_singer)
        ]

        if song_info.empty:
            song_info = df[df["歌曲名稱"] == st.session_state.chosen_song]

        if not song_info.empty:
            actual_singer = song_info.iloc[0]["歌手名稱"]
            lyrics_text = song_info.iloc[0]["歌詞"]
            song_cat = song_info.iloc[0]["分類"]

            st.markdown(f"# 🎤 {actual_singer}")
            st.markdown(f"# 《 {st.session_state.chosen_song} 》")
            if song_cat.strip():
                st.caption(f"📁 歌曲分類：{song_cat}")

            st.markdown("---")
            st.success("🎵 完整歌詞如下（請向下捲動閱讀）：")

            for line in str(lyrics_text).split("\n"):
                if line.strip():
                    st.markdown(f"### {line}")
                else:
                    st.write("")  # 空行
            st.markdown("---")

    # 執行自動平滑滾動的邏輯
    if st.session_state.scroll_target:
        target_id = st.session_state.scroll_target
        st.session_state.scroll_target = None  # 清除狀態避免重複觸發
        components.html(
            f"""
            <script>
                setTimeout(function() {{
                    const el = window.parent.document.getElementById('{target_id}');
                    if (el) {{
                        el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                }}, 200);
            </script>
            """,
            height=0,
        )
