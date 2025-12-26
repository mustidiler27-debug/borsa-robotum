import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & NAVY BLUE TEMA ---
st.set_page_config(
    page_title="ProTrade Navy",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💎"
)

# MODERN NAVY CSS
st.markdown("""
<style>
    /* 1. Genel Arka Plan (Derin Lacivert) */
    .stApp {
        background-color: #0a192f;
        color: #ccd6f6;
    }
    
    /* 2. Sol Menü (Daha Açık Lacivert) */
    [data-testid="stSidebar"] {
        background-color: #112240;
        border-right: 1px solid #233554;
    }
    
    /* 3. Başlık Stili */
    .main-header {
        background: linear-gradient(90deg, #64ffda 0%, #5bc0be 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 800;
        font-size: 3rem;
        text-align: center;
        margin-bottom: 25px;
        letter-spacing: 2px;
    }
    
    /* 4. Metrik Kartları (Glassmorphism Navy) */
    .metric-box {
        background-color: #112240;
        border: 1px solid #233554;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 10px 30px -15px rgba(2, 12, 27, 0.7);
        transition: transform 0.3s ease;
    }
    .metric-box:hover {
        transform: translateY(-5px);
        border-color: #64ffda;
    }
    .metric-label {
        color: #8892b0;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #e6f1ff;
        font-size: 1.8rem;
        font-weight: bold;
    }
    .metric-delta {
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    /* 5. Buton Stili (Cyan Neon) */
    .stButton>button {
        background: transparent;
        color: #64ffda;
        border: 1px solid #64ffda;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: rgba(100, 255, 218, 0.1);
        box-shadow: 0 0 15px rgba(100, 255, 218, 0.2);
        border-color: #64ffda;
        color: #64ffda;
    }
    
    /* 6. Tablo ve Sekmeler */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 1px solid #233554;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #8892b0;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        color: #64ffda !important;
        border-bottom: 2px solid #64ffda !important;
    }
    
    /* Input Alanları */
    .stTextInput>div>div>input {
        background-color: #0a192f;
        color: #ccd6f6;
        border: 1px solid #233554;
    }
    .stSelectbox>div>div>div {
        background-color: #0a192f;
        color: #ccd6f6;
        border: 1px solid #233554;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. HESAPLAMA MOTORU ---
def formasyon_avcisi(df):
    bulgular, cizgiler = [], []
    try:
        son = df.iloc[-1]
        n = 5
        df['Yerel_Max'] = df.iloc[argrelextrema(df['High'].values, np.greater_equal, order=n)[0]]['High']
        df['Yerel_Min'] = df.iloc[argrelextrema(df['Low'].values, np.less_equal, order=n)[0]]['Low']
        
        t = df['Yerel_Max'].dropna().tail(2)
        d = df['Yerel_Min'].dropna().tail(2)

        if len(t) >= 2:
            t1, t2 = t.iloc[-2], t.iloc[-1]
            if abs(t1 - t2) / t1 < 0.05 and t2 > (son['Close'] * 0.95):
                bulgular.append({"tur": "⛰️ İKİLİ TEPE", "mesaj": f"Direnç ({t2:.2f}) zorlanıyor."})
                cizgiler.append((float(t2), 'red'))

        if len(d) >= 2:
            d1, d2 = d.iloc[-2], d.iloc[-1]
            if abs(d1 - d2) / d1 < 0.05 and d2 < (son['Close'] * 1.05):
                bulgular.append({"tur": "✅ İKİLİ DİP", "mesaj": f"Destek ({d2:.2f}) çalışıyor."})
                cizgiler.append((float(d2), 'green'))
    except: pass
    return bulgular, cizgiler

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        # İndikatörler
        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        df['EMA_21'] = df.ta.ema(close=df['Close'], length=21)
        df['EMA_55'] = df.ta.ema(close=df['Close'], length=55)
        
        st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'], length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        bbands = df.ta.bbands(close=df['Close'], length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)
            
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)

        return df
    except: return None

# --- 3. YAN MENÜ (Modern Dropdown) ---
with st.sidebar:
    st.markdown("""
    <h2 style='text-align: center; color: #64ffda; font-weight: 300; letter-spacing: 3px;'>NAVY<br><span style='font-weight:800'>TRADER</span></h2>
    <hr style='border-color: #233554;'>
    """, unsafe_allow_html=True)
    
    # 1. Borsa Seçimi
    piyasa = st.selectbox(
        "📍 PAZAR SEÇİMİ",
        ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"],
        index=0
    )
    
    # 2. Hisse Kodu
    varsayilan = "THYAO" if "BIST" in piyasa else "NVDA"
    kod_giris = st.text_input("🔍 HİSSE KODU", varsayilan)
    
    # 3. Zaman Dilimi (İstediğin gibi aşağı açılan menü)
    st.write("") # Boşluk
    secilen_etiket = st.selectbox(
        "⏱️ ANALİZ PERİYODU",
        ["3 Aylık", "6 Aylık", "Yılbaşından Bugüne (YTD)", "1 Yıllık", "2 Yıllık"],
        index=3  # 1 Yıllık varsayılan
    )
    
    zaman_map = {
        "3 Aylık": "3mo", "6 Aylık": "6mo", 
        "Yılbaşından Bugüne (YTD)": "ytd", 
        "1 Yıllık": "1y", "2 Yıllık": "2y"
    }
    periyot = zaman_map[secilen_etiket]
    
    st.markdown("---")
    analiz_butonu = st.button("ANALİZİ BAŞLAT", use_container_width=True)

# --- 4. ANA EKRAN ---

if not analiz_butonu:
    # Karşılama Ekranı
    st.markdown('<div class="main-header">PİYASA KONTROL MERKEZİ</div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("👋 Sol menüden hisse kodunu gir ve 'ANALİZİ BAŞLAT' butonuna bas.")

else:
    # Analiz Ekranı
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if "BIST" in piyasa else ham_kod
    para_birimi = "₺" if "BIST" in piyasa else "$"

    with st.spinner('Veriler sunucudan çekiliyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("⚠️ Veri bulunamadı.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            yuzde = ((son['Close'] - onceki['Close']) / onceki['Close']) * 100
            renk_delta = "#64ffda" if yuzde > 0 else "#ff6b6b"
            
            formasyonlar, cizgiler = formasyon_avcisi(df)
            
            # Başlık
            st.markdown(f'<div class="main-header">{ham_kod} TEKNİK BAKIŞ</div>', unsafe_allow_html=True)
            
            # --- KARTLAR (NAVY STYLE) ---
            k1, k2, k3, k4 = st.columns(4)
            
            # 1. Fiyat
            k1.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Son Fiyat</div>
                <div class="metric-value">{son['Close']:.2f} {para_birimi}</div>
                <div class="metric-delta" style="color: {renk_delta};">%{yuzde:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. RSI
            rsi_val = son.get('RSI', 50)
            rsi_color = "#ff6b6b" if rsi_val > 70 else "#64ffda" if rsi_val < 30 else "#ccd6f6"
            k2.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">RSI Göstergesi</div>
                <div class="metric-value" style="color: {rsi_color}">{rsi_val:.1f}</div>
                <div class="metric-delta">Momentum</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. Trend
            trend_yon = son.get('TrendYon')
            trend_text = "YÜKSELİŞ" if trend_yon == 1 else "DÜŞÜŞ"
            trend_color = "#64ffda" if trend_yon == 1 else "#ff6b6b"
            k3.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Trend Yönü</div>
                <div class="metric-value" style="color: {trend_color}">{trend_text}</div>
                <div class="metric-delta">SuperTrend</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 4. Sinyal
            macd = son.get('MACD', 0)
            sig = son.get('SIGNAL', 0)
            durum = "AL" if macd > sig else "SAT"
            durum_renk = "#64ffda" if macd > sig else "#ff6b6b"
            k4.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">MACD Sinyali</div>
                <div class="metric-value" style="color: {durum_renk}">{durum}</div>
                <div class="metric-delta">Kesişim</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- GRAFİK ---
            tab1, tab2 = st.tabs(["📊 GRAFİK ANALİZİ", "⚡ FORMASYON SİNYALLERİ"])
            
            with tab1:
                plot_len = min(len(df), 150)
                plot_df = df.iloc[-plot_len:]
                add_plots = []
                
                # EMA
                if 'EMA_21' in plot_df.columns: 
                    add_plots.append(mpf.make_addplot(plot_df['EMA_21'], color='#f1c40f', width=1.5))
                if 'EMA_55' in plot_df.columns: 
                    add_plots.append(mpf.make_addplot(plot_df['EMA_55'], color='#3498db', width=2))
                
                # Bollinger
                if 'BB_UPPER' in plot_df.columns:
                    add_plots.append(mpf.make_addplot(plot_df['BB_UPPER'], color='#8892b0', linestyle='--', alpha=0.6))
                    add_plots.append(mpf.make_addplot(plot_df['BB_LOWER'], color='#8892b0', linestyle='--', alpha=0.6))
                
                # SuperTrend
                if 'SuperTrend' in plot_df.columns:
                    colors = ['#64ffda' if x==1 else '#ff6b6b' for x in plot_df['TrendYon']]
                    add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                
                # Formasyonlar
                if cizgiler:
                    for s, r in cizgiler:
                        line_col = '#64ffda' if r=='green' else '#ff6b6b'
                        add_plots.append(mpf.make_addplot([s]*len(plot_df), color=line_col, linestyle='-.', width=2))
                
                # Paneller
                if 'RSI' in plot_df.columns:
                     add_plots.append(mpf.make_addplot(plot_df['RSI'], panel=2, color='#bd93f9', ylabel='RSI'))

                # Grafik Teması
                fig, _ = mpf.plot(plot_df, type='candle', style='nightclouds', 
                                  addplot=add_plots, volume=True, 
                                  panel_ratios=(4, 1, 1), 
                                  returnfig=True, figsize=(12, 8),
                                  tight_layout=True)
                st.pyplot(fig)
            
            with tab2:
                if formasyonlar:
                    for f in formasyonlar:
                        if "✅" in f['tur']:
                            st.success(f"### {f['tur']}\n{f['mesaj']}")
                        else:
                            st.error(f"### {f['tur']}\n{f['mesaj']}")
                else:
                    st.info("Bu periyotta temiz bir formasyon oluşumu yok.")
