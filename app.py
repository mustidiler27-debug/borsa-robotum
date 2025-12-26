import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & CSS STİL (MODERNLEŞTİRME) ---
st.set_page_config(
    page_title="ProTrade V15 - Ultra Modern",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MODERN CSS ENJEKSİYONU
st.markdown("""
<style>
    /* Sol Menü Arka Planı */
    [data-testid="stSidebar"] {
        background-color: #0e1117;
        border-right: 1px solid #333;
    }
    /* Metrik Kartları */
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        border: 1px solid #444;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 10px;
    }
    /* Tab Başlıkları */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        border-radius: 8px;
        background-color: #161b22;
        color: #ffffff;
        border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important; /* Yeşil Seçim */
        color: white !important;
    }
    /* Başlık Gradyanı */
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        font-size: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---
def formasyon_avcisi(df):
    bulgular = []
    cizgiler = [] 
    try:
        son = df.iloc[-1]
        # İkili Tepe/Dip
        n = 5
        df['Yerel_Max'] = df.iloc[argrelextrema(df['High'].values, np.greater_equal, order=n)[0]]['High']
        df['Yerel_Min'] = df.iloc[argrelextrema(df['Low'].values, np.less_equal, order=n)[0]]['Low']
        
        son_tepeler = df['Yerel_Max'].dropna().tail(2)
        son_dipler = df['Yerel_Min'].dropna().tail(2)

        if len(son_tepeler) >= 2:
            tepe1, tepe2 = son_tepeler.iloc[-2], son_tepeler.iloc[-1]
            if abs(tepe1 - tepe2) / tepe1 < 0.04 and tepe2 > (son['Close'] * 0.95):
                bulgular.append({"tur": "⛰️ İKİLİ TEPE", "mesaj": "Direnç oluştu, düşüş riski."})
                cizgiler.append((tepe2, 'red'))

        if len(son_dipler) >= 2:
            dip1, dip2 = son_dipler.iloc[-2], son_dipler.iloc[-1]
            if abs(dip1 - dip2) / dip1 < 0.04 and dip2 < (son['Close'] * 1.05):
                bulgular.append({"tur": "✅ İKİLİ DİP", "mesaj": "Destek oluştu, yükseliş ihtimali."})
                cizgiler.append((dip2, 'green'))

        # Sıkışma
        if (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER'] < 0.12:
            bulgular.append({"tur": "⚠️ SIKIŞMA (ÜÇGEN)", "mesaj": "Sert kırılım yaklaşıyor."})

        # Mumlar
        onceki = df.iloc[-2]
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
           (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append({"tur": "🐂 YUTAN BOĞA", "mesaj": "Güçlü dönüş sinyali."})
            
    except: pass
    return bulgular, cizgiler

def pivot_hesapla(df):
    try:
        last = df.iloc[-1]
        P = (last['High'] + last['Low'] + last['Close']) / 3
        R1, S1 = 2*P - last['Low'], 2*P - last['High']
        R2, S2 = P + (last['High'] - last['Low']), P - (last['High'] - last['Low'])
        return P, R1, R2, S1, S2
    except: return 0,0,0,0,0

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        rows = len(df)
        for ema in [21, 50, 144, 200, 610]:
            df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema) if rows > ema else np.nan

        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL', cols[-2]: 'MACD_HIST'}, inplace=True)
            
        bbands = df.ta.bbands(close=df['Close'], length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)
            
        st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'], length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        df['CMF'] = df.ta.cmf(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], length=20)
        return df
    except: return None

def puan_hesapla(df):
    puan = 0
    try:
        son = df.iloc[-1]
        if son['Close'] > son.get('EMA_144', 999999): puan += 25
        if son.get('TrendYon') == 1: puan += 25
        if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
        if 30 < son.get('RSI', 50) < 70: puan += 15
        if son.get('CMF', 0) > 0: puan += 20
    except: pass
    return min(puan, 100)

# --- 3. MODERN SOL MENÜ ---
with st.sidebar:
    # Logo / Başlık Alanı
    st.markdown('<p class="gradient-text">ProTrade AI</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Modern Ayar Kutusu
    with st.expander("🛠️ Analiz Ayarları", expanded=True):
        piyasa = st.selectbox("Piyasa Seçimi", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
        
        if piyasa == "🇹🇷 BIST (TL)":
            kod_giris = st.text_input("Hisse Kodu", "THYAO", help="BIST kodunu girin (Örn: GARAN)")
        else:
            kod_giris = st.text_input("Hisse Kodu", "NVDA", help="ABD kodunu girin (Örn: AAPL)")
            
        periyot = st.select_slider("Zaman Dilimi", options=["6mo", "1y", "2y", "5y"], value="1y")

    # Büyük Buton
    analiz_butonu = st.button("ANALİZİ BAŞLAT 🚀", use_container_width=True, type="primary")
    
    # Alt Bilgi
    st.markdown("---")
    st.caption("🟢 Sistem: **ONLİNE**")
    st.caption("🤖 Model: **v15.0 Hunter**")

# --- 4. ANA EKRAN ---
if analiz_butonu:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if piyasa == "🇹🇷 BIST (TL)" else ham_kod
    para_birimi = "TL" if piyasa == "🇹🇷 BIST (TL)" else "$"

    with st.spinner('Yapay zeka piyasayı tarıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error(f"❌ {sembol} bulunamadı.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar, cizgiler = formasyon_avcisi(df) 
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # MODERN METRİK KARTLARI
            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f"""<div class="metric-card"><h3>Fiyat</h3><h2>{son['Close']:.2f} {para_birimi}</h2><p>{son['Close']-onceki['Close']:.2f} değişim</p></div>""", unsafe_allow_html=True)
            
            puan_renk = "#4CAF50" if puan > 70 else "#FF9800"
            k2.markdown(f"""<div class="metric-card"><h3>AI Puanı</h3><h2 style="color:{puan_renk}">{puan}/100</h2></div>""", unsafe_allow_html=True)
            
            trend_icon = "🟢 YÜKSELİŞ" if son.get('TrendYon')==1 else "🔴 DÜŞÜŞ"
            k3.markdown(f"""<div class="metric-card"><h3>Trend</h3><h2>{trend_icon}</h2></div>""", unsafe_allow_html=True)
            
            para_icon = "💰 GİRİŞ" if son.get('CMF', 0)>0 else "💸 ÇIKIŞ"
            k4.markdown(f"""<div class="metric-card"><h3>Para Akışı</h3><h2>{para_icon}</h2></div>""", unsafe_allow_html=True)
            
            st.write("") # Boşluk

            # SEKMELER
            tab_genel, tab_indikator, tab_formasyon = st.tabs(["📊 GENEL BAKIŞ", "📈 İNDİKATÖRLER", "🕵️‍♂️ FORMASYONLAR"])

            # 1. SEKME
            with tab_genel:
                col_g1, col_g2 = st.columns([3, 1])
                with col_g1:
                    plot_df = df.iloc[-150:]
                    add_plots = []
                    if 'EMA_144' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2))
                    if 'EMA_610' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5))
                    if 'SuperTrend' in plot_df.columns:
                        colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                    if 'MACD' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['MACD'], color='fuchsia', panel=2))
                        add_plots.append(mpf.make_addplot(plot_df['SIGNAL'], color='orange', panel=2))
                        add_plots.append(mpf.make_addplot(plot_df['MACD_HIST'], type='bar', color='dimgray', panel=2))

                    h_lines_dict = dict(hlines=[x[0] for x in cizgiler], colors=[x[1] for x in cizgiler], linewidths=2, linestyle='-.') if cizgiler else None

                    fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', addplot=add_plots, volume=True, hlines=h_lines_dict, panel_ratios=(3, 1, 1), returnfig=True, figsize=(10, 8))
                    st.pyplot(fig)

                with col_g2:
                    st.markdown("### 🎯 Hedefler")
                    st.table(pd.DataFrame({"Seviye": ["R2", "R1", "PIVOT", "S1", "S2"], "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]}))
                    if puan >= 80: st.success("🚀 GÜÇLÜ AL")
                    elif puan >= 40: st.warning("⚖️ NÖTR / İZLE")
                    else: st.error("🔻 SAT / DÜŞÜŞ")

            # 2. SEKME
            with tab_indikator:
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**MACD:** {son.get('MACD',0):.2f} / Sinyal: {son.get('SIGNAL',0):.2f}")
                    st.info(f"**RSI:** {son.get('RSI',0):.2f}")
                with c2:
                    st.success(f"**Para Akışı (CMF):** {son.get('CMF',0):.2f}")
                    st.warning(f"**Altın Destek (144):** {son.get('EMA_144',0):.2f}")

            # 3. SEKME
            with tab_formasyon:
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⛰️" in f['tur']: st.error(f"### {f['tur']}\n{f['mesaj']}")
                        elif "✅" in f['tur']: st.success(f"### {f['tur']}\n{f['mesaj']}")
                        elif "⚠️" in f['tur']: st.warning(f"### {f['tur']}\n{f['mesaj']}")
                        else: st.info(f"### {f['tur']}\n{f['mesaj']}")
                else:
                    st.info("Temiz grafik. Belirgin formasyon yok.")

else:
    # Boş ekranda karşılama mesajı
    st.info("👈 Analize başlamak için sol menüyü kullanın.")
