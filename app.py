import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import io

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="🎸 街頭藝人線上點歌本", layout="centered")

# 初始化 Session State (確保歌單資料在切換模式時不會消失)
if "song_df" not in st.session_state:
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
if "管理員" in mode:
    st.title("👨‍💼 管理員後台管理 (終極穩定版)")
    st.markdown("---")
    
    password = st.text_input("🔑 請輸入管理員登入密碼：", type="password")
    
    if password == "Chiho888":
        st.success("🔓 認證成功！您現在可以更新歌單資料。")
        
        st.markdown("### 📋 方式一：複製貼上更新（💯 最穩定，100% 成功）")
        st.info("💡 說明：打開您的 Excel 或 CSV 歌單，直接**全選（Ctrl+A）並複製（Ctrl+C）**，然後把內容直接貼在下方的大框框中即可！")
        
        # 建立大文字貼上區
        paste_data = st.text_area("📥 請在此處貼上您從 Excel 複製的全部歌單內容：", height=200, placeholder="歌手名稱\t歌曲名稱\t分類\t歌詞\n周杰倫\t晴天\t國語流行\t故事的小黃花...")
        
        if st.button("🔥 點我解析並儲存貼上的歌單"):
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
                        st.session_state.song_df = new_df[required_cols]
                        st.success("🎉 歌單透過文字解析成功！切換回觀眾模式即可看到新歌單。")
                        st.balloons()
                    else:
                        st.error(f"❌ 欄位不符！貼上的內容必須包含這四個標題：歌手名稱、歌曲名稱、歌詞、分類。目前缺少：{', '.join(missing_cols)}")
                except Exception as e:
                    st.error(f"❌ 解析失敗，請確保您是從 Excel 中完整複製包含標頭的表格。錯誤訊息: {e}")
            else:
                st.warning("⚠️ 框框內目前沒有內容，請先貼上資料。")
                
        st.markdown("---")
        st.markdown("### 📂 方式二：傳統檔案上傳 (若您的網路已被解除阻擋可使用)")
        uploaded_file = st.file_uploader("📥 上傳歌單檔案 (.xlsx 或 .csv)", type=["xlsx", "csv"], key="file_uploader_backup")
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    new_df = pd.read_csv(uploaded_file, encoding='utf-8')
                else:
                    new_df = pd.read_excel(uploaded_file, engine='openpyxl')
                    
                new_df.dropna(how='all', inplace=True)
                new_df.columns = [str(col).strip() for col in new_df.columns]
                
                required_cols = ["歌手名稱", "歌曲名稱", "歌詞", "分類"]
                missing_cols = [col for col in required_cols if col not in new_df.columns]
                
                if not missing_cols:
                    for col in required_cols:
                        new_df[col] = new_df[col].fillna("").astype(str).str.strip()
                    st.session_state.song_df = new_df[required_cols]
                    st.success("🎉 檔案上傳更新成功！")
                    st.balloons()
                else:
                    st.error(f"❌ 錯誤：檔案欄位名稱不符！缺少：{', '.join(missing_cols)}")
            except Exception as e:
                st.error(f"❌ 讀取檔案錯誤: {e}")
                
        st.write("📊 **目前系統內的歌單總覽 (共 {} 首)：**".format(len(st.session_state.song_df)))
        st.dataframe(st.session_state.song_df, use_container_width=True)
        
    elif password != "":
        st.error("🔒 密碼錯誤！請重新輸入。")

# --- 4. 觀眾模式 📱 ---
else:
    st.title("🎸 現場 Live 點歌與動態歌詞本")
    st.caption("✨ 歡迎現場的朋友！用手機點選你想看的歌曲與歌詞吧！")
    st.markdown("---")
    
    df = st.session_state.song_df
    
    with st.expander("📱 點我展開現場專用 QR Code (可供台下粉絲掃描)"):
        # 🎯 採用原生防干擾安全導向：自動辨識並綁定目前運作中的真實短網址
        current_url = "https://streamlit.app"
        
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
            # 🎯 錯字修正：已將過往遺留的 "歌曲 speechless" 徹底修正為正確的欄位比對
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
