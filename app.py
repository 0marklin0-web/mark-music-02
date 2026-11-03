import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import io
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# 🎯 強力修正：使用全域與屬性選擇器進行強力覆蓋，不論新舊版 Streamlit 結構，紅框字體全部強制極大化！
st.markdown(
    """
    <style>
    /* 1. 紅框：強力放大「1. 請選擇歌手名稱：」與「2. 請選擇歌曲名稱：」的標題字體 */
    div[data-testid="stWidgetLabel"] * {
        font-size: 34px !important;
        font-weight: bold !important;
        line-height: 1.6 !important;
    }
    
    #tabs-b Bukhara-tab-0 * { font-size: 34px !important; }
    
    /* 1. 紅框：強力放大選單框框內顯示的選中文字與提示文字（如：周杰倫、--- 請展開選擇歌曲 ---） */
    div[data-baseweb="select"] * {
        font-size: 30px !important;
        font-weight: bold !important;
    }
    
    /* 1. 紅框：強力放大點開下拉選單後彈出來的清單項目文字 */
    ul[role="listbox"] * {
        font-size: 30px !important;
        font-weight: bold !important;
    }
    
    /* 2. 藍框保持精緻大小：維持在 18px */
    .stExpander details summary p, .stExpander details summary * {
        font-size: 18px !important;
        font-weight: 500 !important;
    }
    
    /* 加大選單觸控高度，方便大字體呈現與手指點擊 */
    div[data-baseweb="select"] > div {
        min-height: 75px !important;
    }
    
    /* 歌詞內文大字體優化 */
    div[data-testid="stText"] {
        font-size: 26px !important;
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
        st.info("💡 說明：打開您的 Excel 或 CSV 歌單，直接**全選（Ctrl+A）並複製（Ctrl+C）**，然後把內容直接貼在下方的大框框中即可！")
        
        paste_data = st.text_area("📥 請在此處貼上您從 Excel 複製的全部歌單內容：", height=200, placeholder="歌手名稱\t歌曲名稱\t分類\t歌詞\n周杰倫\t晴天\t國語流行\t故事的小黃花...")
        
        if st.button("🔥 點我發佈並同步更新至全站觀眾手機"):
            if paste_data.strip():
                try:
                    new_df = pd.read_csv(io.StringIO(paste_data), sep='\t')
                    if len(new_df.columns) <= 1:
                        new_df = pd.read_csv(io.StringIO(paste_data), sep=',')
                    
                    new_df.dropna(how='all', inplace=True)
                    new_df.columns = [str(col).strip() for col in new_df.columns]
                    
                    required_cols = ["歌手名稱", "歌曲名稱", "歌詞", "分類"]
                    missing_cols = [col for col in required_cols if col not in new_df.columns]
                    
                    if not missing_cols:
                        for col in required_cols:
                            new_df[col] = new_df[col].fillna("").astype(str).str.strip()
                        
                        # 直接把新資料複寫覆蓋掉雲端硬碟的 CSV 檔案
                        new_df[required_cols].to_csv(DATA_FILE, index=False, encoding='utf-8')
                        st.success("🎉 歌單已永久寫入雲端檔案！現場所有粉絲的手機只要重新整理，就能立刻看到全新歌單！")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ 欄位不符！貼上的內容必須包含這四個標題：歌手名稱、歌曲名稱、歌詞、分類。目前缺少：{', '.join(missing_cols)}")
                except Exception as e:
                    st.error(f"❌ 解析失敗，請確保您是從 Excel 中完整複製包含標頭的表格。錯誤訊息: {e}")
            else:
                st.warning("⚠️ 框框內目前沒有內容，請先貼上資料。")
                
        st.markdown("---")
        st.write("📊 **目前雲端實體檔案中的歌單總覽 (共 {} 首)：**".format(len(df)))
        st.dataframe(df, use_container_width=True)
        
    elif password != "":
        st.error("🔒 密碼錯誤！請重新輸入。")

# --- 5. 觀眾模式 📱 ---
else:
    st.title("🎸 現場 Live 點歌與動態歌詞本")
    st.caption("✨ 歡迎現場的朋友！用手機點選你想看的歌曲與歌詞吧！")
    st.markdown("---")
    
    with st.expander("📱 點我展開現場專用 QR Code (可供台下粉絲掃描)"):
        # 🎯 網址精準固定鎖定：您的專屬完整真實網域
        current_url = "https://mark-music-02-xyl3ruztpvq6bwxlkgjxcy.streamlit.app/"
            
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(current_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf)
        st.image(buf.getvalue(), caption="現場觀眾掃描此碼即可進入此點歌本", width=180)

    # 選擇歌手
    singers = sorted(list(df["歌手名稱"].unique()))
    selected_singer = st.selectbox("🎤 1. 請選擇歌手名稱：", ["--- 請展開選擇歌手 ---"] + singers)
    
    # 選擇歌曲
    if selected_singer != "--- 請展開選擇歌手 ---":
        songs_of_singer = df[df["歌手名稱"] == selected_singer]
        selected_song = st.selectbox("🎶 2. 請選擇歌曲名稱：", ["--- 請展開選擇歌曲 ---"] + list(songs_of_singer["歌曲名稱"]))
        
        # 秀出歌詞
        if selected_song != "--- 請展開選擇歌曲 ---":
            song_info = songs_of_singer[songs_of_singer["歌曲名稱"] == selected_song]
            
            # 使用官方安全格式提取純文字
            lyrics_text = "\n".join(song_info["歌詞"].astype(str).tolist())
            song_cat = "/".join(song_info["分類"].astype(str).tolist())
            
            st.markdown("---")
            st.markdown(f"## 🎤 {selected_singer}  • 《 {selected_song} 》")
            if song_cat.strip():
                st.caption(f"📁 歌曲分類：{song_cat}")
            
            st.info("🎵 完整歌詞內容：")
            st.text(lyrics_text)
            st.markdown("---")
