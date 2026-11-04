import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import io
import os
import streamlit.components.v1 as components

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# 🎯 核心樣式修正：將大按鈕的上下高度與外距（間距）極致縮小，讓排版更緊湊
st.markdown(
    """
    <style>
    /* 1. 將選單的導引大標題微調 */
    h2 {
        font-size: 24px !important;
        font-weight: bold !important;
        color: inherit !important;
        margin-top: 10px !important;
        margin-bottom: 8px !important;
    }
    
    /* 2. 大按鈕內部的字體大小維持舒適度 */
    div.stButton > button p {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    
    /* 3. 🎯 核心修正：將按鈕的高度與間距縮小，讓排版更緊湊、更好塞 */
    div.stButton > button {
        min-height: 45px !important;    /* 高度縮小，減少佔用空間 */
        height: 45px !important;
        margin-top: 2px !important;     /* 上間距縮到最小 */
        margin-bottom: 2px !important;  /* 下間距縮到最小 */
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        border-radius: 8px !important;
    }
    
    /* 4. 折疊按鈕字體 */
    .stExpander details summary p {
        font-size: 18px !important;
        font-weight: 500 !important;
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
    
    # 🎯 加上 key="admin_password" 確保密碼輸入框狀態穩定、不會莫名消失
    password = st.text_input("🔑 請輸入管理員登入密碼：", type="password", key="admin_password")
    
    if password == "Chiho888":
        st.success("🔓 認證成功！您現在可以更新歌單資料。")
        st.markdown("### 📋 方式一：複製貼上更新（💯 實體寫入，手機 100% 絕對同步）")
        paste_data = st.text_area("📥 請在此處貼上您從 Excel 複製的全部歌單內容：", height=200)
        
        if st.button("🔥 發佈最新歌單"):
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
        st.dataframe(df, use_container_width=True)
    elif password != "":
        st.error("🔒 密碼錯誤！")

# --- 5. 觀眾模式 📱 ---
else:
    st.title("🎸 現場 Live 點歌與動態歌詞本")
    st.caption("✨ 歡迎現場的朋友！點選下方大按鈕看歌詞！")
    st.markdown("---")
    
    with st.expander("📱 點我展開現場專用 QR Code"):
        current_url = "https://mark-music-02-xyl3ruztpvq6bwxlkgjxcy.streamlit.app/"
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(current_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf)
        st.image(buf.getvalue(), caption="現場觀眾掃描此碼即可進入此點歌本", width=180)

    # 利用 Session State 記錄點選狀態與滾動目標
    if "chosen_singer" not in st.session_state:
        st.session_state.chosen_singer = None
    if "chosen_song" not in st.session_state:
        st.session_state.chosen_song = None
    if "scroll_target" not in st.session_state:
        st.session_state.scroll_target = None

    # 第一層：用大標題引導選擇歌手
    st.markdown("## 🎤 1. 請點選歌手選單：")
    
    singers = sorted(list(df["歌手名稱"].unique()))
    
    for singer in singers:
        label_text = f"👉 【 {singer} 】 👈" if st.session_state.chosen_singer == singer else f"👤 {singer}"
        if st.button(label_text, key=f"btn_singer_{singer}", use_container_width=True):
            st.session_state.chosen_singer = singer
            st.session_state.chosen_song = None  # 切換歌手時重設歌曲
            st.session_state.scroll_target = "section_songs"  # 設定自動跳轉目標
            st.rerun()

    # 第二層：如果選了歌手，設定錨點並顯示歌曲清單
    if st.session_state.chosen_singer:
        st.markdown('<div id="section_songs"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"## 🎶 2. 歌手【{st.session_state.chosen_singer}】的歌曲清單：")
        
        songs_of_singer = df[df["歌手名稱"] == st.session_state.chosen_singer]
        
        for song in list(songs_of_singer["歌曲名稱"]):
            label_song = f"🔥 正在播放：《 {song} 》" if st.session_state.chosen_song == song else f"🎵 《 {song} 》"
            if st.button(label_song, key=f"btn_song_{song}", use_container_width=True):
                st.session_state.chosen_song = song
                st.session_state.scroll_target = "section_lyrics"  # 設定自動跳轉目標
                st.rerun()

    # 第三層：如果選了歌曲，設定錨點並顯示歌詞
    if st.session_state.chosen_song and st.session_state.chosen_singer:
        st.markdown('<div id="section_lyrics"></div>', unsafe_allow_html=True)
        st.markdown("---")
        song_info = df[(df["歌手名稱"] == st.session_state.chosen_singer) & (df["歌曲名稱"] == st.session_state.chosen_song)]
        
        if not song_info.empty:
            lyrics_text = "\n".join(song_info["歌詞"].astype(str).tolist())
            song_cat = "/".join(song_info["分類"].astype(str).tolist())
            
            st.markdown(f"# 🎤 {st.session_state.chosen_singer}")
            st.markdown(f"# 《 {st.session_state.chosen_song} 》")
            if song_cat.strip():
                st.caption(f"📁 歌曲分類：{song_cat}")
            
            st.markdown("---")
            st.success("🎵 完整歌詞如下（請向下捲動閱讀）：")
            
            for line in lyrics_text.split('\n'):
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
