import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. MODERN SAYFA AYARLARI ---
st.set_page_config(
    page_title="ProTrade V9 - Full Paket",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tablo ve Kart Stilleri
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stDataFrame { width: 100%; }
    .reportview-container .main .block-container{ padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. HESAPLAMA VE FORMASYON FONKSİYONLARI ---
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
    
    # 1. SIKIŞMA (Üçgen / Flama / Takoz)
    # Bollinger bantları birbirine çok yaklaştıysa patlama (üçgen kırılımı) yakındır.
    bb_width = (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER']
    if bb_width < 0.08: # %8'den az fark varsa
        bulgular.append("⚠️ SIKIŞMA / ÜÇGEN: Fiyat çok sıkıştı, sert patlama yakın.")

    # 2. İKİLİ TEPE / DİP (Matematiksel)
    # Son 30 gündeki yerel tepeleri bul
    try:
        n = 5 # Hassasiyet
        df['Tepe'] = df.iloc[argrelextrema(df['High'].values, np.greater_equal, order=n)[0]]['High']
        tepeler = df['Tepe'].dropna().tail(3) # Son 3 tepe
        
        if len(tepeler) >= 2:
            t1 = tepeler.iloc[-1]
            t2 = tepeler.iloc[-2]
            if abs(t1 - t2) / t1 < 0.02: # Tepeler %2 kadar yakınsa
                bulgular.append("⛰️ İKİLİ TEPE: Direnç geçilemiyor (Düşüş Riski).")
    except:
        pass

    # 3. MUM FORMASYONLARI
    # Yutan Boğa
    if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
       (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
        bulgular.append("🐂 YUTAN BOĞA: Dönüş sinyali.")
    
    # Doji (Kararsızlık)
    govde = abs(son['Close'] - son['Open'])
    mum_boyu = son['High'] - son['Low']
    if mum_boyu > 0 and govde <= mum_boyu * 0.1:
        bulgular.append("🕯️ DOJI: Kararsızlık (Yön değişebilir).")

    # Çekiç (Hammer)
    if (son['Close'] > son['Open']) and \
       ((son['Open'] - son['Low']) > (2 * (son['Close'] - son['Open']))) and \
       ((son['High'] - son['Close']) < (0.2 * (son['Close'] - son['Open']))):
        bulgular.append("🔨 ÇEKİÇ: Dipten dönüş sinyali.")

    return bulgular

def verileri_getir(symbol, period):
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 50: return None

        # İndikatörler
        df['RSI'] = df.ta.rsi(length=14)
        df['EMA_200'] = df.ta.ema(length=200)
        df['EMA_50'] = df.ta.ema(length=50)

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
    if son['Close'] > son['EMA_200']: puan += 25
    if son.get('TrendYon') == 1: puan += 25
    if son['MACD'] > son['SIGNAL']: puan += 20
    if 30 < son['RSI'] < 70: puan += 10
    if son.get('CMF', 0) > 0: puan += 20
    return min(puan, 100)

# --- 3. YAN MENÜ ---
st.sidebar.title("🎛️ Piyasa Seçimi")
piyasa = st.sidebar.selectbox("Piyasa", ["🇹🇷 BIST", "🇺🇸 ABD", "₿ Kripto"])

if piyasa == "🇹🇷 BIST":
    kod = st.sidebar.text_input("Hisse Kodu", "THYAO").upper()
    sembol = f"{kod}.IS"
elif piyasa == "🇺🇸 ABD":
    sembol = st.sidebar.text_input("Hisse Kodu", "NVDA").upper()
else:
    kod = st.sidebar.text_input("Coin Kodu", "BTC").upper()
    sembol = f"{kod}-USD"

periyot = st.sidebar.select_slider("Zaman Dilimi", options=["6mo", "1y", "2y", "5y"], value="1y")

# --- 4. ANA EKRAN ---
if st.sidebar.button("ANALİZ ET 🚀", use_container_width=True):
    with st.spinner('Formasyonlar taranıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("Veri bulunamadı!")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar = formasyon_tara(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # --- A. ÜST METRİKLER ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f}", f"{son['Close'] - onceki['Close']:.2f}")
            c2.metric("Puan", f"{puan}/100", "Güçlü" if puan>70 else "Zayıf")
            
            trend_icon = "🔼 YÜKSELİŞ" if son.get('TrendYon')==1 else "🔻 DÜŞÜŞ"
            c3.metric("Trend", trend_icon)
            
            para = "Giriş 💰" if son.get('CMF', 0) > 0 else "Çıkış 💸"
            c4.metric("Para Akışı", para)

            st.markdown("---")

            # --- B. İKİ SÜTUNLU YAPI ---
            col_grafik, col_veri = st.columns([3, 1])

            with col_grafik:
                # GRAFİK SEKMELERİ
                tab_g, tab_m = st.tabs(["🕯️ Fiyat Grafiği", "🌊 MACD & Trend"])
                
                with tab_g:
                    # Ana Grafik
                    plot_df = df.iloc[-120:]
                    add_plots = [
                        mpf.make_addplot(plot_df['EMA_200'], color='purple', width=2, panel=0),
                        mpf.make_addplot(plot_df['BB_UPPER'], color='gray', linestyle='--', width=0.8),
                        mpf.make_addplot(plot_df['BB_LOWER'], color='gray', linestyle='--', width=0.8),
                    ]
                    if 'SuperTrend' in plot_df.columns:
                        renkler = ['green' if x == 1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=5, color=renkler))

                    fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                      addplot=add_plots, volume=True, 
                                      returnfig=True, title=f"{sembol}", figsize=(10,6))
                    st.pyplot(fig)
                
                with tab_m:
                    # MACD Grafiği (Ayrıntılı)
                    st.line_chart(df[['MACD', 'SIGNAL']].tail(100))
                    st.caption("Mavi: MACD, Turuncu: Sinyal. Mavi üstteyse AL demektir.")

            with col_veri:
                # 1. FORMASYON RADARI (YENİ EKLENDİ)
                st.subheader("🕵️‍♂️ Formasyon Radarı")
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⚠️" in f or "⛰️" in f:
                            st.error(f)
                        elif "🐂" in f or "🔨" in f:
                            st.success(f)
                        else:
                            st.warning(f)
                else:
                    st.info("Şu an belirgin bir formasyon (Üçgen, İkili Tepe vb.) yok.")
                
                st.divider()

                # 2. PIVOT TABLOSU
                st.markdown("##### 🎯 Hedef & Stoplar")
                pivot_data = {
                    "Seviye": ["Direnç 2", "Direnç 1", "PIVOT", "Destek 1", "Destek 2"],
                    "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                }
                st.table(pd.DataFrame(pivot_data))

                # 3. İNDİKATÖR DEĞERLERİ
                st.markdown("##### 📟 Göstergeler")
                macd_renk = "🟢" if son['MACD'] > son['SIGNAL'] else "🔴"
                st.write(f"MACD: {macd_renk}")
                
                rsi_durum = "Nötr"
                if son['RSI'] > 70: rsi_durum = "🔴 Pahalı"
                elif son['RSI'] < 30: rsi_durum = "🟢 Ucuz"
                st.write(f"RSI: {son['RSI']:.0f} ({rsi_durum})")

else:
    st.info("👈 Sol menüden hisse seçip butona basın.")
