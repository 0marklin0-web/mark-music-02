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
        "分類":
