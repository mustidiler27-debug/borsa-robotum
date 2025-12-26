import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema
import datetime

# --- 1. MODERN AYARLAR & CSS STİL (FİNAL TASARIM) ---
st.set_page_config(
    page_title="ProTrade Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📈"
)

# Özel CSS ile Arayüzü Güzelleştirme
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Yan Menü (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }
    
    /* Özel Başlık Stili */
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        text-align: center;
        margin-bottom: 20px;
        text-shadow: 0px 0px 20px rgba(0, 201, 255, 0.5);
    }
    
    /* Metrik Kartları (Dashboard) */
    .dashboard-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    .dashboard-card:hover {
        transform: translateY(-5px);
        border-color: #38bdf8;
    }
    .card-title {
        color: #94a3b8;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .card-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: bold;
    }
    .card-sub {
        font-size: 0.8rem;
        margin-top: 5px;
    }
    
    /* Buton Tasarımı */
    .stButton>button {
        background: linear-gradient(45deg, #2563eb, #3b82f6);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 15px 20px;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(45deg, #1d4ed8, #2563eb);
        box-shadow: 0 0 15px rgba(37, 99, 235, 0.5);
    }

    /* Tablo ve Tablar */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #1e293b;
        border-radius: 10px;
        color: white;
        border: 1px solid #334155;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR (MOTOR) ---
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
        df['EMA_144'] = df.ta.ema(close=df['Close'], length=144)
        
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

# --- 3. YAN MENÜ TASARIMI ---
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: white; font-size: 24px; margin:0;">🚀 PROTRADE</h1>
        <p style="color: #64748b; font-size: 12px;">Next Gen Analiz Terminali</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("### ⚙️ Parametreler")
        piyasa = st.selectbox("Borsa Seçin", ["🇹🇷 Borsa İstanbul (BIST)", "🇺🇸 NASDAQ / NYSE (ABD)"])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            varsayilan = "THYAO" if "BIST" in piyasa else "NVDA"
            kod_giris = st.text_input("Hisse Sembolü", varsayilan)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True) 
        
        st.markdown("### ⏱️ Zaman Dilimi")
        secilen_etiket = st.pills("Periyot", ["3 Ay", "6 Ay", "YTD", "1 Yıl"], default="1 Yıl")
        zaman_map = {"3 Ay": "3mo", "6 Ay": "6mo", "YTD": "ytd", "1 Yıl": "1y"}
        periyot = zaman_map.get(secilen_etiket, "1y")
        
        st.markdown("---")
        analiz_butonu = st.button("ANALİZİ BAŞLAT 🔥", use_container_width=True)
        
        st.markdown("""
        <div style="position: fixed; bottom: 20px; left: 20px; font-size: 11px; color: #475569;">
            v26.0 Stable • No AI Core
        </div>
        """, unsafe_allow_html=True)

# --- 4. ANA SAYFA MANTIĞI ---

if not analiz_butonu:
    # --- KARŞILAMA EKRANI (Landing Page) ---
    st.markdown('<div class="main-header">PROTRADE TERMINAL</div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style="text-align: center; color: #94a3b8; font-size: 18px; margin-bottom: 40px;">
            Profesyonel Teknik Analiz, Formasyon Avcısı ve Trend Takibi.<br>
            Başlamak için sol menüden bir hisse seçin.
        </div>
        """, unsafe_allow_html=True)

    # Örnek Gösterge Kartları (Statik)
    k1, k2, k3 = st.columns(3)
    k1.markdown("""
    <div class="dashboard-card">
        <div class="card-title">SİSTEM DURUMU</div>
        <div class="card-value" style="color: #4ade80;">AKTİF 🟢</div>
        <div class="card-sub">Veri Akışı Sağlanıyor</div>
    </div>
    """, unsafe_allow_html=True)
    
    k2.markdown("""
    <div class="dashboard-card">
        <div class="card-title">BIST 100</div>
        <div class="card-value">GÜÇLÜ</div>
        <div class="card-sub">Genel Piyasa Yönü</div>
    </div>
    """, unsafe_allow_html=True)
    
    k3.markdown("""
    <div class="dashboard-card">
        <div class="card-title">MOTOR</div>
        <div class="card-value" style="color: #38bdf8;">V26</div>
        <div class="card-sub">Saf Teknik Analiz</div>
    </div>
    """, unsafe_allow_html=True)

else:
    # --- ANALİZ SONUÇ EKRANI ---
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if "BIST" in piyasa else ham_kod
    para_birimi = "₺" if "BIST" in piyasa else "$"

    with st.spinner('Piyasa verileri işleniyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("⚠️ Veri alınamadı. Hisse kodunu kontrol edin.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            degisim = ((son['Close'] - onceki['Close']) / onceki['Close']) * 100
            degisim_renk = "#4ade80" if degisim > 0 else "#f87171"
            
            formasyonlar, cizgiler = formasyon_avcisi(df)
            
            # Ana Başlık
            st.markdown(f'<div class="main-header">{ham_kod} ANALİZİ</div>', unsafe_allow_html=True)

            # --- MODERN METRİK KARTLARI ---
            m1, m2, m3, m4 = st.columns(4)
            
            # Fiyat Kartı
            m1.markdown(f"""
            <div class="dashboard-card">
                <div class="card-title">SON FİYAT</div>
                <div class="card-value">{son['Close']:.2f} {para_birimi}</div>
                <div class="card-sub" style="color: {degisim_renk};">%{degisim:.2f} Değişim</div>
            </div>
            """, unsafe_allow_html=True)
            
            # RSI Kartı
            rsi_val = son.get('RSI', 50)
            rsi_renk = "#f87171" if rsi_val > 70 else "#4ade80" if rsi_val < 30 else "#facc15"
            m2.markdown(f"""
            <div class="dashboard-card">
                <div class="card-title">RSI (GÜÇ)</div>
                <div class="card-value" style="color: {rsi_renk}">{rsi_val:.1f}</div>
                <div class="card-sub">Momentum Durumu</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Trend Kartı
            trend_yon = son.get('TrendYon')
            trend_text = "YÜKSELİŞ 🚀" if trend_yon == 1 else "DÜŞÜŞ 🔻"
            trend_color = "#4ade80" if trend_yon == 1 else "#f87171"
            m3.markdown(f"""
            <div class="dashboard-card">
                <div class="card-title">TREND (SuperTrend)</div>
                <div class="card-value" style="color: {trend_color}">{trend_text}</div>
                <div class="card-sub">Ana Yön</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Sinyal Kartı
            macd = son.get('MACD', 0)
            signal = son.get('SIGNAL', 0)
            macd_durum = "AL ✅" if macd > signal else "SAT ❌"
            m4.markdown(f"""
            <div class="dashboard-card">
                <div class="card-title">MACD SİNYALİ</div>
                <div class="card-value">{macd_durum}</div>
                <div class="card-sub">{macd:.2f} / {signal:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

            # --- GRAFİK SEKMELERİ ---
            tab1, tab2 = st.tabs(["📊 PROFESYONEL GRAFİK", "🔍 DETAYLI FORMASYONLAR"])
            
            with tab1:
                plot_len = min(len(df), 150)
                plot_df = df.iloc[-plot_len:]
                add_plots = []
                
                # İndikatör Çizgileri
                if 'EMA_21' in plot_df.columns: 
                    add_plots.append(mpf.make_addplot(plot_df['EMA_21'], color='#f59e0b', width=1.5)) # Turuncu
                if 'EMA_55' in plot_df.columns: 
                    add_plots.append(mpf.make_addplot(plot_df['EMA_55'], color='#3b82f6', width=2))   # Mavi
                
                # Bollinger
                if 'BB_UPPER' in plot_df.columns:
                    add_plots.append(mpf.make_addplot(plot_df['BB_UPPER'], color='gray', linestyle='--', alpha=0.5))
                    add_plots.append(mpf.make_addplot(plot_df['BB_LOWER'], color='gray', linestyle='--', alpha=0.5))
                
                # SuperTrend
                if 'SuperTrend' in plot_df.columns:
                    colors = ['#4ade80' if x==1 else '#f87171' for x in plot_df['TrendYon']]
                    add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=30, color=colors))
                
                # Formasyonlar
                if cizgiler:
                    for s, r in cizgiler:
                        add_plots.append(mpf.make_addplot([s]*len(plot_df), color=r, linestyle='-.', width=2))
                
                # Alt Paneller
                if 'RSI' in plot_df.columns:
                    add_plots.append(mpf.make_addplot(plot_df['RSI'], panel=2, color='#a855f7', ylabel='RSI', ylim=(0,100)))
                    # RSI 30-70 çizgileri (Manuel çizgi yerine panel ayarı daha temiz durur ama şimdilik sade kalsın)

                # Modern Grafik Teması
                fig, _ = mpf.plot(plot_df, type='candle', style='nightclouds', 
                                  addplot=add_plots, volume=True, 
                                  panel_ratios=(4, 1, 1), 
                                  returnfig=True, figsize=(12, 8),
                                  tight_layout=True)
                
                st.pyplot(fig)
                st.caption("🔵 Mavi: EMA 55 (Ana Trend) | 🟠 Turuncu: EMA 21 (Hızlı Trend)")

            with tab2:
                if formasyonlar:
                    for f in formasyonlar:
                        if "✅" in f['tur']:
                            st.success(f"### {f['tur']}\n{f['mesaj']}")
                        else:
                            st.error(f"### {f['tur']}\n{f['mesaj']}")
                else:
                    st.info("Bu periyotta belirgin bir 'İkili Tepe' veya 'İkili Dip' formasyonu tespit edilmedi.")
