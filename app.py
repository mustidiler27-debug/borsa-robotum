import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR ---
st.set_page_config(page_title="ProTrade - Kafa Rahat", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #262626 100%);
        border: 1px solid #444; padding: 10px; border-radius: 8px; margin-bottom: 10px;
    }
    .metric-value { font-size: 20px; font-weight: bold; color: #fff; }
    .metric-title { font-size: 12px; color: #aaa; }
    .stTabs [aria-selected="true"] { background-color: #DD2476 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. TEKNİK ANALİZ MOTORU ---
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
                bulgular.append({"tur": "⛰️ İKİLİ TEPE", "mesaj": f"Direnç ({t2:.2f}) oluştu."})
                cizgiler.append((float(t2), 'red'))

        if len(d) >= 2:
            d1, d2 = d.iloc[-2], d.iloc[-1]
            if abs(d1 - d2) / d1 < 0.05 and d2 < (son['Close'] * 1.05):
                bulgular.append({"tur": "✅ İKİLİ DİP", "mesaj": f"Destek ({d2:.2f}) oluştu."})
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
        
        rows = len(df)
        for ema in [21, 50, 144, 200]:
            df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema) if rows > ema else np.nan

        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)
            
        st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'], length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        df['CMF'] = df.ta.cmf(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], length=20)
        return df
    except: return None

# --- 3. ARAYÜZ (SADE VE NET) ---
with st.sidebar:
    st.header("📈 Borsa Robotum")
    st.info("Sistem Durumu: **MÜKEMMEL** ✨")
    
    piyasa = st.selectbox("Piyasa", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    kod_giris = st.text_input("Hisse Kodu", "THYAO" if piyasa == "🇹🇷 BIST (TL)" else "NVDA")
    
    secilen_etiket = st.pills("Periyot", ["3 Ay", "6 Ay", "YTD", "1 Yıl"], default="1 Yıl")
    zaman_map = {"3 Ay": "3mo", "6 Ay": "6mo", "YTD": "ytd", "1 Yıl": "1y"}
    periyot = zaman_map.get(secilen_etiket, "1y")
    
    analiz_butonu = st.button("ANALİZİ BAŞLAT 🚀", type="primary")

if analiz_butonu:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if piyasa == "🇹🇷 BIST (TL)" else ham_kod
    para_birimi = "TL" if piyasa == "🇹🇷 BIST (TL)" else "$"

    with st.spinner('Grafikler çiziliyor...'):
        df = verileri_getir(sembol, periyot)
        if df is None:
            st.error("Hisse bulunamadı, kodu kontrol et.")
        else:
            son = df.iloc[-1]
            formasyonlar, cizgiler = formasyon_avcisi(df)
            
            rsi = son.get('RSI', 50)
            trend = "Yükseliş 🟢" if son.get('TrendYon') == 1 else "Düşüş 🔴"
            cmf = son.get('CMF', 0)

            # METRİKLER
            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f"""<div class="metric-card"><p class="metric-title">Fiyat</p><p class="metric-value">{son['Close']:.2f} {para_birimi}</p></div>""", unsafe_allow_html=True)
            k2.markdown(f"""<div class="metric-card"><p class="metric-title">RSI (Güç)</p><p class="metric-value">{rsi:.1f}</p></div>""", unsafe_allow_html=True)
            k3.markdown(f"""<div class="metric-card"><p class="metric-title">Trend</p><p class="metric-value">{trend}</p></div>""", unsafe_allow_html=True)
            k4.markdown(f"""<div class="metric-card"><p class="metric-title">Para Akışı</p><p class="metric-value">{cmf:.2f}</p></div>""", unsafe_allow_html=True)

            st.write("")
            
            # GRAFİK SEKMELERİ
            tab1, tab2 = st.tabs(["📊 Büyük Grafik", "🕵️‍♂️ Formasyonlar"])
            with tab1:
                plot_len = min(len(df), 150)
                plot_df = df.iloc[-plot_len:]
                add_plots = []
                
                # İndikatörleri Grafiğe Ekle
                if 'EMA_144' in plot_df.columns: 
                    add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2))
                
                if 'SuperTrend' in plot_df.columns:
                     colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                     add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                
                # Formasyon Çizgilerini Ekle
                if cizgiler:
                     for s, r in cizgiler:
                         add_plots.append(mpf.make_addplot([s]*len(plot_df), color=r, linestyle='--'))
                
                # ÇİZİM
                fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                  addplot=add_plots, volume=True, 
                                  returnfig=True, figsize=(10, 6),
                                  title=f"{sembol} Teknik Analiz")
                st.pyplot(fig)
            
            with tab2:
                if formasyonlar:
                    for f in formasyonlar:
                        st.info(f"**{f['tur']}:** {f['mesaj']}")
                else:
                    st.success("Grafik şu an temiz, belirgin bir formasyon yok.")
