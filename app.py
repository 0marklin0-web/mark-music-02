import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import io
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

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
            "突然好想死 你會在哪裡\n過得快樂或委屈\n突然好想你 突然鋒利的回憶\n突然模糊的眼睛",
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
    st.caption("✨ 歡迎現場的朋友！點選下方大按鈕看歌詞！")
    st.markdown("---")
    
    with st.expander("📱 點我展開現場專用 QR Code"):
        # 🎯 網址精準固定鎖定：您的專屬完整真實網域，絕不再漏字、不漏符號
        current_url = "https://mark-music-02-xyl3ruztpvq6bwxlkgjxcy.streamlit.app/"
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(current_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf)
        st.image(buf.getvalue(), caption="現場觀眾掃描此碼即可進入此點歌本", width=180)

    # 利用全新 Session State 來記錄長輩點選了哪位歌手與歌曲
    if "chosen_singer" not in st.session_state:
        st.session_state.chosen_singer = None
    if "chosen_song" not in st.session_state:
        st.session_state.chosen_song = None

    # 第一層：用大標題引導選擇歌手
    st.markdown("## 🎤 1. 請點選歌手選單：")
    
    # 獲取歌手清單
    singers = sorted(list(df["歌手名稱"].unique()))
    
    # 用排版將按鈕變大，一個歌手一條大按鈕
    for singer in singers:
        label_text = f"👉 【 {singer} 】 👈" if st.session_state.chosen_singer == singer else f"👤 {singer}"
        if st.button(label_text, key=f"btn_singer_{singer}", use_container_width=True):
            st.session_state.chosen_singer = singer
            st.session_state.chosen_song = None  # 切換歌手時重設歌曲
            st.rerun()

    # 第二層：如果選了歌手，秀出該歌手的所有歌曲大按鈕
    if st.session_state.chosen_singer:
        st.markdown("---")
        st.markdown(f"## 🎶 2. 歌手【{st.session_state.chosen_singer}】的歌曲清單：")
        
        songs_of_singer = df[df["歌手名稱"] == st.session_state.chosen_singer]
        
        for song in list(songs_of_singer["歌曲名稱"]):
            label_song = f"🔥 正在播放：《 {song} 》" if st.session_state.chosen_song == song else f"🎵 《 {song} 》"
            if st.button(label_song, key=f"btn_song_{song}", use_container_width=True):
                st.session_state.chosen_song = song
                st.rerun()

    # 第三層：如果選了歌曲，秀出極大字體、最適合長輩閱讀的精美歌詞
    if st.session_state.chosen_song and st.session_state.chosen_singer:
        st.markdown("---")
        song_info = df[(df["歌手名稱"] == st.session_state.chosen_singer) & (df["歌曲名稱"] == st.session_state.chosen_song)]
        
        if not song_info.empty:
            lyrics_text = "\n".join(song_info["歌詞"].astype(str).tolist())
            song_cat = "/".join(song_info["分類"].astype(str).tolist())
            
            # 使用官方標題層級，強制輸出最大、最顯眼的文字
            st.markdown(f"# 🎤 {st.session_state.chosen_singer}")
            st.markdown(f"# 《 {st.session_state.chosen_song} 》")
            if song_cat.strip():
                st.caption(f"📁 歌曲分類：{song_cat}")
            
            st.markdown("---")
            st.success("🎵 完整歌詞如下（請向下捲動閱讀）：")
            
            # 歌詞內文直接使用大標題語法呈現，保證長輩不需要放大鏡
            for line in lyrics_text.split('\n'):
                if line.strip():
                    st.markdown(f"### {line}")
                else:
                    st.write("") # 空行
            st.markdown("---")
