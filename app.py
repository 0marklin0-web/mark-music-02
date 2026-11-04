import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import io
import os
import streamlit.components.v1 as components

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# 🎯 核心樣式修正：將大按鈕、radio選項字體放大，並將外距極致縮小讓排版更緊湊，同時隱藏右上角的 GitHub 原始碼連結
st.markdown(
    """
    <style>
    /* 1. 隱藏 Streamlit 右上角選單中可能暴露 / 原始碼檢視按鈕 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 2. 將選單的導引大標題微調 */
    h2 {
        font-size: 24px !important;
        font-weight: bold !important;
        color: inherit !important;
        margin-top: 10px !important;
        margin-bottom: 8px !important;
    }
    
    /* 3. 大按鈕內部的字體大小維持舒適度 */
    div.stButton > button p {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    
    /* 4. 🎯 放大「按歌手查找 / 按風格分類查找」的 radio 選項字體 */
    div.stRadio label p {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    
    /* 5. 🎯 核心修正：將按鈕的高度與間距縮小，讓排版更緊湊、更好塞 */
    div.stButton > button {
        min-height: 45px !important;    /* 高度縮小，減少佔用空間 */
        height: 45px !important;
        margin-top: 2px !important;     /* 上間距縮到最小 */
        margin-bottom: 2px !important;  /* 下間距縮到最小 */
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        border-radius: 8px !important;
    }
    
    /* 6. 折疊按鈕字體 */
    .stExpander details summary p {
        font-size: 18px !important;
        font-weight: 500 !important;
    }
    
    /* 7. 🎯 強制手機版與電腦版皆維持 2 欄並列排版 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
    }
    [data-testid="column"] {
        flex: 1 1 50% !important;
        width: 50% !important;
        min-width: 50% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 2. 實體檔案同步核心 ---
DATA_FILE = "my_songs.csv"

# 初始化：如果雲端還沒有這個檔案，先建立一份預設資料檔案
if not os.path.exists(DATA_FILE):
    default_data = {
        "歌手名稱": ["周杰倫", "周杰倫", "五月天", "蔡依林", "告五人"],
        "歌曲名稱": ["晴天", "告白氣球", "突然好想記", "倒帶", "披星戴月的想你"],
        "分類": ["國語流行", "國語流行", "經典樂團", "國語流行", "獨立樂團"],
        "歌詞": [
            "故事的小黃花 從出生那年就飄著\n童年的蕩秋千 隨記憶一直晃到現在\n吹著前奏望著天空 我想起花瓣試著掉落",
            "親愛的 愛上你 從那天起\n甜蜜的很輕易\n親愛的 別任性 你的眼睛\n在說我願意",
            "突然好想你 你會在哪裡\n過得快樂或委屈\n突然好想你 突然鋒利的回憶\n突然模糊的眼睛",
            "你總是要我乖 張開雙手帶到未來\n如果你善解人意 怎麼不明白\n我們的愛太無奈 總是承載著太多期盼",
            "我會披星戴月的想你\n我會奮不顧身地前進\n遠方煙火點燃你的心\n照亮我的一線生機"
        ]
    }
    pd.DataFrame(default_data).to_csv(DATA_FILE, index=False, encoding='utf-8')

# 讀取實體檔案
df = pd.read_csv(DATA_FILE, encoding='utf-8').fillna("").astype(str)

# --- 3. 側邊欄：模式切換 ---
st.sidebar.title("⚙️ 模式切換面板")
mode = st.sidebar.radio("請選擇當前模式：", ["觀眾模式 📱 (粉絲看歌詞)", "管理員模式 🔑 (後台上傳)"])

# --- 4. 管理員模式 🔑 ---
if "管理員" in mode:
    st.title("👨‍💼 管理員後台管理 (實體檔案全站同步版)")
    st.markdown("---")
    
    password = st.text_input("🔑 請輸入管理員登入密碼：", type="password", key="admin_password")
    
    if password == "Chiho888":
        st.success("🔓 認證成功！您現在可以更新歌單資料。")
        st.markdown("### 📋 方式一：複製貼上更新（💯 實體寫入，手機 100% 絕對同步）")
        paste_data = st.text_area("📥 請在此處貼上您從 Excel 複製的全部歌單內容：", height=200, key="paste_data_area")
        
        if st.button("🔥 發佈最新歌單", key="publish_btn"):
            if paste_data.strip():
                try:
                    new_df = pd.read_csv(io.StringIO(paste_data), sep='\t')
                    if len(new_df.columns) <= 1:
                        new_df = pd.read_csv(io.StringIO(paste_data), sep=',')
                    
                    new_df.dropna(how='all', inplace=True)
                    new_df.columns = [str(col).strip() for col in new_df.columns]
                    
                    required_cols = ["歌手名稱", "歌曲名稱", "歌詞", "分類"]
                    if all(col in new_df.columns for col in required_cols):
                        for col in required_cols:
                            new_df[col] = new_df[col].fillna("").astype(str).str.strip()
                        new_df[required_cols].to_csv(DATA_FILE, index=False, encoding='utf-8')
                        st.success("🎉 歌單永久寫入雲端硬碟檔案！")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ 欄位不符！")
                except Exception as e:
                    st.error(f"❌ 解析失敗: {e}")
        st.table(df)
    elif password != "":
        st.error("🔒 密碼錯誤！")

# --- 5. 觀眾模式 📱 ---
else:
    st.title("🎸 現場 Live 點歌與動態歌詞本")
    st.caption("✨ 歡迎現場的朋友！點選下方大按鈕看歌詞！")
    st.markdown("---")
    
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

    # 第一層：1. 請選擇點歌方式 (歌手 vs 分類)
    st.markdown('<div id="section_top"></div>', unsafe_allow_html=True)
    st.markdown("## 🎤 1. 請選擇瀏覽與點歌方式：")
    
    search_by = st.radio(
        "請選擇分類依據：",
        ["👤 按歌手查找", "📁 按風格分類查找"],
        horizontal=True,
        label_visibility="collapsed",
        key="search_by_radio"
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

    # 設定按鈕區塊的定位點
    st.markdown('<div id="section_filter_buttons"></div>', unsafe_allow_html=True)

    if current_mode == "singer":
        singers = sorted([s for s in df["歌手名稱"].unique() if s.strip()])
        # 2 欄並列排版
        for i in range(0, len(singers), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(singers):
                    singer = singers[i + j]
                    with cols[j]:
                        is_active = (st.session_state.filter_type == "singer") and (st.session_state.chosen_filter_val == singer)
                        label_text = f"👉 【 {singer} 】 👈" if is_active else f"👤 {singer}"
                        if st.button(label_text, key=f"btn_singer_{singer}", use_container_width=True):
                            st.session_state.filter_type = "singer"
                            st.session_state.chosen_filter_val = singer
                            st.session_state.chosen_song = None
                            st.session_state.scroll_target = "section_songs"  # 🎯 點擊時自動跳轉至歌曲清單
                            st.rerun()

    else:
        categories = sorted([c for c in df["分類"].unique() if c.strip()])
        # 2 欄並列排版
        for i in range(0, len(categories), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(categories):
                    cat = categories[i + j]
                    with cols[j]:
                        is_active = (st.session_state.filter_type == "category") and (st.session_state.chosen_filter_val == cat)
                        label_text = f"👉 【 {cat} 】 👈" if is_active else f"📁 {cat}"
                        if st.button(label_text, key=f"btn_cat_{cat}", use_container_width=True):
                            st.session_state.filter_type = "category"
                            st.session_state.chosen_filter_val = cat
                            st.session_state.chosen_song = None
                            st.session_state.scroll_target = "section_songs"  # 🎯 點擊時自動跳轉至歌曲清單
                            st.rerun()

    # 第二層：如果選了歌手或分類，顯示對應的歌曲清單
    if st.session_state.chosen_filter_val:
        st.markdown('<div id="section_songs"></div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # ⬅️ 返回上一頁按鈕：回到原本在選單所選擇的內容位置
        if st.button("⬅️ 返回上一頁（選擇歌手/分類）", key="back_to_top_btn", use_container_width=True, type="primary"):
            st.session_state.chosen_filter_val = None
            st.session_state.chosen_song = None
            st.session_state.scroll_target = "section_filter_buttons"  # 🎯 返回時準確回到選單按鈕區塊
            st.rerun()

        filter_label = "歌手" if st.session_state.filter_type == "singer" else "分類"
        st.markdown(f"## 🎶 2. 【{st.session_state.chosen_filter_val}】({filter_label}) 的歌曲清單：")
        
        if st.session_state.filter_type == "singer":
            filtered_df = df[df["歌手名稱"] == st.session_state.chosen_filter_val]
        else:
            filtered_df = df[df["分類"] == st.session_state.chosen_filter_val]
        
        for idx, row in filtered_df.iterrows():
            song = row["歌曲名稱"]
            singer_name = row["歌手名稱"]
            is_selected = st.session_state.chosen_song == song
            
            display_title = f"《 {song} 》 - {singer_name}" if st.session_state.filter_type == "category" else f"《 {song} 》"
            label_song = f"🔥 正在播放：{display_title}" if is_selected else f"🎵 {display_title}"
            
            if st.button(label_song, key=f"btn_song_{idx}_{song}", use_container_width=True):
                st.session_state.chosen_song = song
                st.session_state.chosen_singer_for_song = singer_name
                st.session_state.scroll_target = "section_lyrics"  # 🎯 點擊歌曲自動跳轉至歌詞
                st.rerun()

    # 第三層：如果選了歌曲，設定錨點並顯示歌詞
    if st.session_state.chosen_song:
        st.markdown('<div id="section_lyrics"></div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # ⬅️ 返回上一頁按鈕（歌曲清單）
        if st.button("⬅️ 返回上一頁（歌曲清單）", key="back_to_songs_btn", use_container_width=True, type="primary"):
            st.session_state.chosen_song = None
            st.session_state.scroll_target = "section_songs"  # 🎯 從歌詞返回時自動回到歌曲清單
            st.rerun()
        
        target_singer = getattr(st.session_state, "chosen_singer_for_song", st.session_state.chosen_filter_val)
        song_info = df[(df["歌曲名稱"] == st.session_state.chosen_song) & (df["歌手名稱"] == target_singer)]
        
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
            
            for line in str(lyrics_text).split('\n'):
                if line.strip():
                    st.markdown(f"### {line}")
                else:
                    st.write("") # 空行
            st.markdown("---")

    # 執行自動平滑滾動的邏輯
    if st.session_state.scroll_target:
        target_id = st.session_state.scroll_target
        st.session_state.scroll_target = None  # 清除狀態避免重複觸發
        components.html(f"""
            <script>
                setTimeout(function() {{
                    const el = window.parent.document.getElementById('{target_id}');
                    if (el) {{
                        el.scrollIntoView({{ behavior: 'smooth' }});
                    }}
                }}, 200);
            </script>
        """, height=0)
