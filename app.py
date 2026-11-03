import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# 初始化 Session State (確保歌單資料在切換模式時不會消失)
if "song_df" not in st.session_state:
    # 預設建立幾筆範例資料，方便你現在直接測試觀眾模式
    default_data = {
        "歌手名稱": ["周杰倫", "周杰倫", "五月天", "蔡依林", "告五人"],
        "歌曲名稱": ["晴天", "告白氣球", "突然好想你", "倒帶", "披星戴月的想你"],
        "分類": ["國語流行", "國語流行", "經典樂團", "國語流行", "獨立樂團"],
        "歌詞": [
            "故事的小黃花 從出生那年就飄著\n童年的蕩秋千 隨記憶一直晃到現在\n吹著前奏望著天空 我想起花瓣試著掉落",
            "親愛的 愛上你 從那天起\n甜蜜的很輕易\n親愛的 別任性 你的眼睛\n在說我願意",
            "突然好想你 你會在哪裡\n過得快樂或委屈\n突然好想你 突然鋒利的回憶\n突然模糊的眼睛",
            "你總是要我乖 張開雙手帶我到未來\n如果你善解人意 怎麼不明白\n我們的愛太無奈 總是承載著太多期盼",
            "我會披星戴月的想你\n我會奮不顧身地前進\n遠方煙火點燃你的心\n照亮我的一線生機"
        ]
    }
    st.session_state.song_df = pd.DataFrame(default_data)

# --- 2. 側邊欄：模式切換 ---
st.sidebar.title("⚙️ 模式切換面板")
mode = st.sidebar.radio("請選擇當前模式：", ["觀眾模式 📱 (粉絲看歌詞)", "管理員模式 🔑 (後台上傳)"])

# --- 3. 管理員模式 🔑 ---
if mode == "管理員模式 🔑 (後台上傳)":
    st.title("👨‍💼 管理員後台管理")
    st.markdown("---")
    
    # 安全密碼驗證
    password = st.text_input("🔑 請輸入管理員登入密碼：", type="password", help="預設測試密碼請輸入：1234")
    
    if password == "1234":
        st.success("🔓 認證成功！您現在可以更新歌單資料。")
        
        # 檔案上傳器
        uploaded_file = st.file_uploader("📥 請上傳您的 Excel 歌單檔案 (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                # 讀取 Excel
                new_df = pd.read_excel(uploaded_file)
                
                # 檢查欄位
                required_cols = ["歌手名稱", "歌曲名稱", "歌詞", "分類"]
                if all(col in new_df.columns for col in required_cols):
                    st.session_state.song_df = new_df
                    st.success("🎉 歌單全數更新成功！切換回觀眾模式即可看到新歌單。")
                    st.balloons()
                else:
                    st.error(f"❌ 錯誤：Excel 欄位名稱不符！必須完全包含這四個欄位：{', '.join(required_cols)}")
            except Exception as e:
                st.error(f"❌ 讀取檔案時發生錯誤: {e}")
                
        # 顯示當前系統內的資料表
        st.write("📊 **目前系統內的歌單總覽 (共 {} 首)：**".format(len(st.session_state.song_df)))
        st.dataframe(st.session_state.song_df, use_container_width=True)
        
    elif password != "":
        st.error("🔒 密碼錯誤！請重新輸入。（提示：測試密碼為 1234）")

# --- 4. 觀眾模式 📱 ---
else:
    st.title("🎸 現場 Live 點歌與動態歌詞本")
    st.caption("✨ 歡迎現場的朋友！用手機點選你想看的歌曲與歌詞吧！")
    st.markdown("---")
    
    df = st.session_state.song_df
    
    # QR Code 區塊
    with st.expander("📱 點我展開現場專用 QR Code (可供台下粉絲掃描)"):
        # 這裡會自動產生一個範例網址的 QR code
        demo_url = https://mark-music-02-xyl3ruztpvq6bwxlkgjxcy.streamlit.app/
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(demo_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf)
        st.image(buf.getvalue(), caption="現場觀眾掃描此碼即可進入此點歌本", width=180)

    # 第一層：選擇分類 (輔助篩選)
    categories = ["全部歌曲"] + list(df["分類"].unique())
    selected_cat = st.selectbox("🎵 1. 先選擇歌曲分類：", categories)
    
    if selected_cat != "全部歌曲":
        filtered_df = df[df["分類"] == selected_cat]
    else:
        filtered_df = df
        
    # 第一層：選擇歌手
    singers = sorted(list(filtered_df["歌手名稱"].unique()))
    selected_singer = st.selectbox("🎤 2. 請選擇歌手名稱：", ["--- 請展開選擇歌手 ---"] + singers)
    
    # 第二層：選擇歌曲
    if selected_singer != "--- 請展開選擇歌手 ---":
        songs_of_singer = filtered_df[filtered_df["歌手名稱"] == selected_singer]
        selected_song = st.selectbox("🎶 3. 請選擇歌曲名稱：", ["--- 請展開選擇歌曲 ---"] + list(songs_of_singer["歌曲名稱"]))
        
        # 第三層：秀出歌詞
        if selected_song != "--- 請展開選擇歌曲 ---":
            song_info = songs_of_singer[songs_of_singer["歌曲名稱"] == selected_song]
            lyrics_text = song_info["歌詞"].values[0]
            song_cat = song_info["分類"].values[0]
            
            st.markdown("---")
            st.markdown(f"### 🎤 {selected_singer}  • 《 {selected_song} 》")
            st.caption(f"📁 歌曲分類：{song_cat}")
            
            # 使用內嵌樣式讓歌詞在手機上大字、置中、好閱讀
            st.markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px;">
                    <p style="font-size: 18px; line-height: 2; white-space: pre-wrap; font-weight: bold; color: #1f2d3d;">
{lyrics_text}
                    </p>
                </div>
                """, 
                unsafe_style_allowed=True
            )
            st.markdown("---")
