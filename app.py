import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema
import datetime

# --- 1. AYARLAR & NAVY BLUE TEMA ---
st.set_page_config(
    page_title="ProTrade V28 Ultimate",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💎"
)

# CSS TASARIMI
st.markdown("""
<style>
    .stApp { background-color: #0a192f; color: #ccd6f6; }
    [data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }
    
    /* Başlık */
    .main-header {
        background: linear-gradient(90deg, #64ffda 0%, #5bc0be 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; text-align: center; margin-bottom: 20px;
    }
    
    /* Kartlar */
    .metric-box {
        background-color: #112240; border: 1px solid #233554; border-radius: 12px;
        padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-label { color: #8892b0; font-size: 0.8rem; text-transform: uppercase; }
    .metric-value { color: #e6f1ff; font-size: 1.8rem; font-weight: bold; }
    
    /* Süper Karne Puanı */
    .score-circle {
        font-size: 2rem; font-weight: bold; padding: 10px; border-radius: 50%;
        border: 4px solid; display: inline-block; width: 80px; height: 80px; line-height: 55px;
    }
    
    /* Performans Tablosu */
    .perf-table { width: 100%; text-align: center; border-collapse: collapse; margin-top: 10px; }
    .perf-table th { color: #64ffda; border-bottom: 1px solid #233554; padding: 5px; }
    .perf-table td { color: #ccd6f6; padding: 5px; font-weight: bold; }
    
    /* Sekmeler */
    .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #233554; }
    .stTabs [aria-selected="true"] { color: #64ffda !important; border-bottom: 2px solid #64ffda !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. HESAPLAMA MOTORU ---

def fibonacci_levels(df):
    max_p = df['High'].max()
    min_p = df['Low'].min()
    diff = max_p - min_p
    levels = {
        0: max_p,
        0.236: max_p - 0.236 * diff,
        0.382: max_p - 0.382 * diff,
        0.5: max_p - 0.5 * diff,
        0.618: max_p - 0.618 * diff,
        1: min_p
    }
    return levels

def karne_hesapla(df):
    puan = 0
    notlar = []
    try:
        son = df.iloc[-1]
        
        # 1. Trend (25 Puan)
        if son['TrendYon'] == 1:
            puan += 25
            notlar.append("✅ SuperTrend Yükselişte (+25)")
        else:
            notlar.append("🔻 SuperTrend Düşüşte (0)")

        # 2. RSI (20 Puan)
        rsi = son.get('RSI', 50)
        if 40 <= rsi <= 70:
            puan += 20
            notlar.append("✅ RSI Sağlıklı Bölgede (+20)")
        elif rsi < 30:
            puan += 10
            notlar.append("⚠️ RSI Aşırı Satımda (Tepki Gelebilir) (+10)")
        else:
            notlar.append("🔻 RSI Aşırı Şişkin/Zayıf (0)")

        # 3. MACD (20 Puan)
        if son['MACD'] > son['SIGNAL']:
            puan += 20
            notlar.append("✅ MACD Al Sinyalinde (+20)")
        else:
            notlar.append("🔻 MACD Sat Konumunda (0)")

        # 4. Hareketli Ortalamalar (20 Puan)
        if son['Close'] > son.get('EMA_55', 999999):
            puan += 20
            notlar.append("✅ Fiyat EMA 55 Üstünde (Ana Trend Pozitif) (+20)")
        else:
            notlar.append("🔻 Fiyat EMA 55 Altında (Ana Trend Negatif) (0)")

        # 5. Hacim/Para Akışı (15 Puan)
        if son.get('MFI', 50) > 50:
            puan += 15
            notlar.append("✅ Para Girişi Pozitif (+15)")
        else:
            notlar.append("🔻 Para Çıkışı Var (0)")
            
    except: pass
    return puan, notlar

def teknik_yorumla(df, secimler):
    yorumlar = []
    son = df.iloc[-1]
    
    yorumlar.append(f"**Genel Durum:** Kapanış fiyatı **{son['Close']:.2f}**. ")
    
    if "EMA (8-13-21)" in secimler:
        if son['EMA_8'] > son['EMA_13']:
            yorumlar.append("⚡ **EMA Analizi:** Kısa vadeli EMA 8, EMA 13'ün üzerinde. Bu, kısa vadeli momentumun **GÜÇLÜ** olduğunu gösterir.")
        else:
            yorumlar.append("⚡ **EMA Analizi:** Kısa vadeli ortalamalarda zayıflama var, kar satışı baskısı olabilir.")
            
    if "Bollinger Bantları" in secimler:
        if son['Close'] > son['BB_UPPER']:
            yorumlar.append("🌊 **Bollinger:** Fiyat üst bandı zorluyor. Volatilite yüksek, aşırı alım bölgesindeyiz.")
        elif son['Close'] < son['BB_LOWER']:
            yorumlar.append("🌊 **Bollinger:** Fiyat alt bandın dışına sarktı, buradan tepki yükselişi gelebilir.")
    
    if "SuperTrend" in secimler:
        if son['TrendYon'] == 1:
            yorumlar.append("🚀 **Trend:** SuperTrend indikatörü **AL** sinyalini koruyor. Yön yukarı.")
        else:
            yorumlar.append("🛑 **Trend:** SuperTrend indikatörü **SAT** baskısında. Yön aşağı.")

    if not yorumlar:
        return "Detaylı yorum için yukarıdan indikatör seçimi yapınız."
        
    return " ".join(yorumlar)

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        # İndikatörler
        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        for ema in [8, 13, 21, 55, 100, 200]:
            df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema)
            
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
        
        df['MFI'] = df.ta.mfi(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], length=14)

        return df
    except: return None

# --- 3. YAN MENÜ ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #64ffda;'>PROTRADE<br>ULTIMATE</h2>", unsafe_allow_html=True)
    piyasa = st.selectbox("📍 PAZAR", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    varsayilan = "THYAO" if "BIST" in piyasa else "NVDA"
    kod_giris = st.text_input("🔍 HİSSE KODU", varsayilan)
    secilen_etiket = st.selectbox("⏱️ PERİYOT", ["1 Yıllık", "2 Yıllık", "YTD", "6 Aylık"], index=0)
    zaman_map = {"1 Yıllık": "1y", "2 Yıllık": "2y", "YTD": "ytd", "6 Aylık": "6mo"}
    analiz_butonu = st.button("ANALİZ ET 🚀", use_container_width=True, type="primary")

# --- 4. ANA EKRAN ---
if analiz_butonu:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if "BIST" in piyasa else ham_kod
    para_birimi = "₺" if "BIST" in piyasa else "$"

    with st.spinner('Analiz motoru çalışıyor...'):
        df = verileri_getir(sembol, zaman_map[secilen_etiket])
        
        if df is None:
            st.error("Veri bulunamadı.")
        else:
            son = df.iloc[-1]
            puan, notlar = karne_hesapla(df)
            
            # --- BAŞLIK ---
            st.markdown(f'<div class="main-header">{ham_kod} ANALİZ RAPORU</div>', unsafe_allow_html=True)
            
            # --- ÜST METRİKLER VE KARNE ---
            k1, k2, k3, k4 = st.columns([1.5, 1.5, 1, 1])
            
            with k1: # Fiyat ve Geçmiş Performans
                degisim = ((son['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
                renk = "#4ade80" if degisim > 0 else "#ff6b6b"
                
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">SON FİYAT</div>
                    <div class="metric-value">{son['Close']:.2f} {para_birimi}</div>
                    <div style="color: {renk}; font-weight: bold;">%{degisim:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Performans Hesaplama (Haftalık, Aylık vs.)
                try:
                    hist_returns = {}
                    periods = {'1H': 5, '1A': 21, '3A': 63, '1Y': 252}
                    for label, days in periods.items():
                        if len(df) > days:
                            past_price = df.iloc[-days]['Close']
                            ret = ((son['Close'] - past_price) / past_price) * 100
                            color_style = "#4ade80" if ret > 0 else "#ff6b6b"
                            hist_returns[label] = f"<span style='color:{color_style}'>%{ret:.1f}</span>"
                        else:
                            hist_returns[label] = "-"
                    
                    with st.expander("📅 Fiyat Geçmişi & Performans (Tıkla)", expanded=False):
                        st.markdown(f"""
                        <table class="perf-table">
                            <tr><th>1 Hafta</th><th>1 Ay</th><th>3 Ay</th><th>1 Yıl</th></tr>
                            <tr>
                                <td>{hist_returns['1H']}</td>
                                <td>{hist_returns['1A']}</td>
                                <td>{hist_returns['3A']}</td>
                                <td>{hist_returns['1Y']}</td>
                            </tr>
                        </table>
                        """, unsafe_allow_html=True)
                except: pass

            with k2: # SÜPER KARNE
                renk_puan = "#4ade80" if puan >= 75 else "#facc15" if puan >= 50 else "#ff6b6b"
                durum_mesaj = "GÜÇLÜ AL 🐂" if puan >= 80 else "AL / TUT ⚖️" if puan >= 50 else "SAT / BEKLE 🐻"
                
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">SÜPER KARNE NOTU</div>
                    <div style="color: {renk_puan}; font-size: 2.2rem; font-weight: bold;">{puan}/100</div>
                    <div style="color: {renk_puan}; font-size: 0.9rem;">{durum_mesaj}</div>
                </div>
                """, unsafe_allow_html=True)

            with k3:
                trend_text = "YÜKSELİŞ" if son['TrendYon'] == 1 else "DÜŞÜŞ"
                trend_color = "#4ade80" if son['TrendYon'] == 1 else "#ff6b6b"
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">ANA TREND</div>
                    <div class="metric-value" style="color: {trend_color}; font-size: 1.4rem;">{trend_text}</div>
                </div>
                """, unsafe_allow_html=True)

            with k4:
                rsi_val = son.get('RSI', 50)
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">RSI GÜCÜ</div>
                    <div class="metric-value" style="font-size: 1.4rem;">{rsi_val:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            
            # --- SEKMELER (GRAFİK - İNDİKATÖR - KARNE DETAY) ---
            tab1, tab2, tab3 = st.tabs(["📊 İNTERAKTİF GRAFİK", "🧮 TEKNİK VERİLER", "📝 KARNE DETAYLARI"])

            with tab1:
                col_sets, col_chart = st.columns([1, 4])
                
                with col_sets:
                    st.markdown("### 🛠️ Araçlar")
                    show_ema = st.checkbox("EMA (8-13-21)", value=True)
                    show_bollinger = st.checkbox("Bollinger Bantları", value=False)
                    show_supertrend = st.checkbox("SuperTrend", value=True)
                    show_fib = st.checkbox("Fibonacci Seviyeleri", value=False)
                    
                    secimler = []
                    if show_ema: secimler.append("EMA (8-13-21)")
                    if show_bollinger: secimler.append("Bollinger Bantları")
                    if show_supertrend: secimler.append("SuperTrend")
                    if show_fib: secimler.append("Fibonacci")

                with col_chart:
                    plot_len = min(len(df), 200)
                    plot_df = df.iloc[-plot_len:]
                    add_plots = []
                    
                    if show_ema:
                        add_plots.append(mpf.make_addplot(plot_df['EMA_8'], color='yellow', width=1))
                        add_plots.append(mpf.make_addplot(plot_df['EMA_13'], color='orange', width=1))
                        add_plots.append(mpf.make_addplot(plot_df['EMA_21'], color='red', width=1.5))
                    
                    if show_bollinger:
                        add_plots.append(mpf.make_addplot(plot_df['BB_UPPER'], color='gray', linestyle='--'))
                        add_plots.append(mpf.make_addplot(plot_df['BB_LOWER'], color='gray', linestyle='--'))

                    if show_supertrend:
                        colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                    
                    hlines_dict = None
                    if show_fib:
                        fibs = fibonacci_levels(plot_df)
                        # Sadece seviye değerlerini liste olarak al
                        fib_values = list(fibs.values())
                        hlines_dict = dict(hlines=fib_values, colors=['#ccd6f6']*len(fib_values), linestyle='-.', linewidths=0.5)

                    fig, _ = mpf.plot(plot_df, type='candle', style='nightclouds', 
                                      addplot=add_plots, volume=True, 
                                      hlines=hlines_dict,
                                      panel_ratios=(4, 1), 
                                      returnfig=True, figsize=(12, 7), tight_layout=True)
                    st.pyplot(fig)
                    
                    # OTOMATİK YORUMCU
                    st.markdown("### 🤖 Teknik Yorum")
                    otomatik_yorum = teknik_yorumla(df, secimler)
                    st.info(otomatik_yorum)

            with tab2:
                # Teknik Veriler Tablosu
                st.markdown("#### Detaylı Gösterge Değerleri")
                gostergeler = pd.DataFrame({
                    "Gösterge": ["RSI", "MACD", "Sinyal", "Para Akışı (MFI)", "EMA 55", "EMA 200"],
                    "Değer": [
                        f"{son.get('RSI',0):.2f}",
                        f"{son.get('MACD',0):.2f}",
                        f"{son.get('SIGNAL',0):.2f}",
                        f"{son.get('MFI',0):.2f}",
                        f"{son.get('EMA_55',0):.2f}",
                        f"{son.get('EMA_200',0):.2f}"
                    ]
                })
                st.table(gostergeler)

            with tab3:
                st.markdown("#### 🏆 Karne Puanlama Detayı")
                for not_ in notlar:
                    if "✅" in not_:
                        st.success(not_)
                    elif "⚠️" in not_:
                        st.warning(not_)
                    else:
                        st.error(not_)
                
                if puan < 50:
                    st.error("SONUÇ: Hisse teknik olarak ZAYIF. Alım için riskli olabilir.")
                elif puan < 80:
                    st.warning("SONUÇ: Hisse NÖTR. Bazı göstergeler olumlu ama teyit lazım.")
                else:
                    st.success("SONUÇ: Hisse GÜÇLÜ. Teknik göstergelerin çoğu alımı destekliyor.")

else:
    # Karşılama
    st.markdown('<div class="main-header">PROTRADE TERMINAL V28</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.info("👈 Başlamak için sol menüden bir hisse seçin.")
