import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import io
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# 🎯 核心樣式：強制讓拉霸選單（Selectbox）的文字與提示在手機上絕對放大且適應深淺色模式
st.markdown(
    """
    <style>
    /* 強力放大拉霸選單上方的標題文字 */
    div[data-testid="stWidgetLabel"] p {
        font-size: 26px !important;
        font-weight: bold !important;
        line-height: 1.6 !important;
    }
    
    /* 強力放大拉霸框框內顯示的選中字體 */
    div[data-baseweb="select"] div p {
        font-size: 24px !important;
        font-weight: bold !important;
    }
    
    /* 強力放大拉霸點開後的下拉清單字體 */
    ul[role="listbox"] li div {
        font-size: 24px !important;
        font-weight: bold !important;
    }
    
    /* 微調拉霸選單的高度，方便手指點選 */
    div[data-baseweb="select"] > div {
        min-height: 60px !important;
    }
    
    /* 歌詞內文大字體優化 */
    div[data-testid="stText"] {
        font-size: 24px !important;
        line-height: 2 !important;
        font-weight: bold !important;
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
    
    password = st.text_input("🔑 請輸入管理員登入密碼：", type="password")
    
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
    st.caption("✨ 歡迎現場的朋友！請使用下方拉霸選單看歌詞！")
    st.markdown("---")
    
    with st.expander("📱 點我展開現場專用 QR Code"):
        # 🎯 網址精準固定鎖定：您的專屬完整真實網域
        current_url = "https://mark-music-02-xyl3ruztpvq6bwxlkgjxcy.streamlit.app/"
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(current_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf)
        st.image(buf.getvalue(), caption="現場觀眾掃描此碼即可進入此點歌本", width=180)

    # 🎤 第一層拉霸：選擇歌手
    singers = sorted(list(df["歌手名稱"].unique()))
    selected_singer = st.selectbox("🎤 1. 請選擇歌手名稱：", ["--- 請展開選擇歌手 ---"] + singers)
    
    # 🎶 第二層拉霸：選擇歌曲
    if selected_singer != "--- 請展開選擇歌手 ---":
        songs_of_singer = df[df["歌手名稱"] == selected_singer]
        selected_song = st.selectbox("🎶 2. 請選擇歌曲名稱：", ["--- 請展開選擇歌曲 ---"] + list(songs_of_singer["歌曲名稱"]))
        
        # 📄 第三層：顯示完整歌詞
        if selected_song != "--- 請展開選擇歌曲 ---":
            song_info = songs_of_singer[songs_of_singer["歌曲名稱"] == selected_song]
            
            lyrics_text = "\n".join(song_info["歌詞"].astype(str).tolist())
            song_cat = "/".join(song_info["分類"].astype(str).tolist())
            
            st.markdown("---")
            st.markdown(f"## 🎤 {selected_singer}  • 《 {selected_song} 》")
            if song_cat.strip():
                st.caption(f"📁 歌曲分類：{song_cat}")
            
            st.info("🎵 完整歌詞內容：")
            st.text(lyrics_text)
            st.markdown("---")
