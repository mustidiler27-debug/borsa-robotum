import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. MODERN SAYFA AYARLARI ---
st.set_page_config(
    page_title="ProTrade V10 - Golden Edition",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tablo ve CSS Stilleri
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stDataFrame { width: 100%; }
    .metric-card { background-color: #0e1117; border: 1px solid #333; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. HESAPLAMA FONKSİYONLARI ---
def pivot_hesapla(df):
    last = df.iloc[-1]
    P = (last['High'] + last['Low'] + last['Close']) / 3
    R1 = 2*P - last['Low']
    S1 = 2*P - last['High']
    R2 = P + (last['High'] - last['Low'])
    S2 = P - (last['High'] - last['Low'])
    return P, R1, R2, S1, S2

def formasyon_tara(df):
    bulgular = []
    son = df.iloc[-1]
    onceki = df.iloc[-2]
    
    # SIKIŞMA
    bb_width = (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER']
    if bb_width < 0.08:
        bulgular.append("⚠️ SIKIŞMA ALARMI: Patlama Yakın (Bollinger Daraldı)")

    # İKİLİ TEPE (Basit Kontrol)
    try:
        df['Tepe'] = df.iloc[argrelextrema(df['High'].values, np.greater_equal, order=5)[0]]['High']
        tepeler = df['Tepe'].dropna().tail(3)
        if len(tepeler) >= 2:
            t1 = tepeler.iloc[-1]
            t2 = tepeler.iloc[-2]
            if abs(t1 - t2) / t1 < 0.02:
                bulgular.append("⛰️ İKİLİ TEPE: Direnç Geçilemiyor!")
    except: pass

    # MUM FORMASYONLARI
    if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
       (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
        bulgular.append("🐂 YUTAN BOĞA: Dönüş Sinyali")
    
    govde = abs(son['Close'] - son['Open'])
    mum_boyu = son['High'] - son['Low']
    if mum_boyu > 0 and govde <= mum_boyu * 0.1:
        bulgular.append("🕯️ DOJI: Kararsızlık Mumu")
        
    if (son['Close'] > son['Open']) and \
       ((son['Open'] - son['Low']) > (2 * (son['Close'] - son['Open']))) and \
       ((son['High'] - son['Close']) < (0.2 * (son['Close'] - son['Open']))):
        bulgular.append("🔨 ÇEKİÇ: Dipten Dönüş")

    return bulgular

def verileri_getir(symbol, period):
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 50: return None

        # --- A. FİBONACCİ EMA SERİSİ (ALTIN ORANLAR) ---
        # İsteğin üzerine: 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610
        fibo_emas = [5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]
        for ema in fibo_emas:
            df[f'EMA_{ema}'] = df.ta.ema(length=ema)

        # B. Standart İndikatörler
        df['RSI'] = df.ta.rsi(length=14)
        
        # MACD
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL', cols[-2]: 'MACD_HIST'}, inplace=True)

        # Bollinger
        bbands = df.ta.bbands(length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)

        # SuperTrend
        st_ind = df.ta.supertrend(length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        # Para Akışı
        df['CMF'] = df.ta.cmf(length=20)
        
        return df
    except: return None

def puan_hesapla(df):
    puan = 0
    son = df.iloc[-1]
    
    # 1. Fibonacci 144 (Altın Destek) Kontrolü
    if son['Close'] > son.get('EMA_144', 0): puan += 25
    
    # 2. SuperTrend
    if son.get('TrendYon') == 1: puan += 25
    
    # 3. MACD
    if son['MACD'] > son['SIGNAL']: puan += 15
    
    # 4. RSI
    if 30 < son['RSI'] < 70: puan += 15
    elif son['RSI'] <= 30: puan += 20 # Dip fırsatı primi
    
    # 5. Para Akışı
    if son.get('CMF', 0) > 0: puan += 15
    
    return min(puan, 100)

# --- 3. YAN MENÜ ---
st.sidebar.title("🎛️ Piyasa Seçimi")
# Kripto kaldırıldı, sadece BIST ve ABD
piyasa = st.sidebar.radio("Borsa Seç", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])

if piyasa == "🇹🇷 BIST (TL)":
    kod = st.sidebar.text_input("Hisse Kodu", "THYAO").upper()
    sembol = f"{kod}.IS"
    para_birimi = "TL"
else:
    kod = st.sidebar.text_input("Hisse Kodu", "NVDA").upper()
    sembol = kod # ABD hisselerinde ek yok
    para_birimi = "$"

periyot = st.sidebar.select_slider("Zaman Dilimi", options=["6mo", "1y", "2y", "5y"], value="1y")

# --- 4. ANA EKRAN ---
if st.sidebar.button("ANALİZ ET 🚀", use_container_width=True):
    with st.spinner('Fibonacci seviyeleri hesaplanıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("Veri bulunamadı! Kodu kontrol et.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar = formasyon_tara(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # --- A. ÜST METRİKLER ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f} {para_birimi}", f"{son['Close'] - onceki['Close']:.2f}")
            c2.metric("Altın Puan", f"{puan}/100", "Güçlü" if puan>70 else "Zayıf")
            
            trend_icon = "🔼 YÜKSELİŞ" if son.get('TrendYon')==1 else "🔻 DÜŞÜŞ"
            c3.metric("Trend", trend_icon)
            
            para = "Giriş 💰" if son.get('CMF', 0) > 0 else "Çıkış 💸"
            c4.metric("Para Akışı", para)

            st.markdown("---")

            # --- B. İKİ SÜTUNLU YAPI ---
            col_grafik, col_veri = st.columns([3, 1])

            with col_grafik:
                # GRAFİK SEKMELERİ
                tab_g, tab_m = st.tabs(["🕯️ Fibonacci Grafiği", "🌊 MACD & Momentum"])
                
                with tab_g:
                    # Ana Grafik
                    plot_df = df.iloc[-150:]
                    add_plots = [
                        # Fibonacci Golden Ratios (En önemlileri)
                        mpf.make_addplot(plot_df['EMA_21'], color='yellow', width=1, panel=0),
                        mpf.make_addplot(plot_df['EMA_55'], color='orange', width=1.5, panel=0),
                        mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2, panel=0), # Ana Altın Destek
                        mpf.make_addplot(plot_df['EMA_233'], color='darkblue', width=2, panel=0), # Kale
                        mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5, panel=0), # Uzun Vade Sınır
                    ]
                    if 'SuperTrend' in plot_df.columns:
                        renkler = ['green' if x == 1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=5, color=renkler))

                    fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                      addplot=add_plots, volume=True, 
                                      returnfig=True, title=f"{sembol} - Altın Oran Analizi", figsize=(10,7))
                    st.pyplot(fig)
                    st.caption("Çizgiler: Sarı(21), Turuncu(55), Mavi(144 - Altın Destek), Lacivert(233), Mor(610)")
                
                with tab_m:
                    st.line_chart(df[['MACD', 'SIGNAL']].tail(100))
                    st.caption("Mavi çizgi Turuncuyu yukarı keserse AL sinyalidir.")

            with col_veri:
                # 1. FORMASYON RADARI
                st.subheader("🕵️‍♂️ Formasyon Radarı")
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⚠️" in f or "⛰️" in f: st.error(f)
                        elif "🐂" in f or "🔨" in f: st.success(f)
                        else: st.warning(f)
                else:
                    st.info("Belirgin formasyon yok.")
                
                st.divider()

                # 2. ALTIN ORAN ANALİZİ (YENİ)
                st.subheader("🏆 Altın Oran Analizi")
                ema_144 = son['EMA_144']
                if son['Close'] > ema_144:
                    st.success(f"✅ Fiyat EMA 144'ün Üzerinde ({ema_144:.2f})")
                    st.caption("Uzun vadeli trend POZİTİF.")
                else:
                    st.error(f"🔻 Fiyat EMA 144'ün Altında ({ema_144:.2f})")
                    st.caption("Uzun vadeli trend NEGATİF.")

                st.divider()

                # 3. PIVOT TABLOSU
                st.markdown("##### 🎯 Hedef & Stoplar")
                pivot_data = {
                    "Seviye": ["Direnç 2", "Direnç 1", "PIVOT", "Destek 1", "Destek 2"],
                    "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                }
                st.table(pd.DataFrame(pivot_data))
                
                # İndikatör Değerleri
                st.write(f"**RSI:** {son['RSI']:.2f}")

else:
    st.info("👈 Sol menüden Borsa seçin (ABD/TR) ve hisse kodunu girin.")
