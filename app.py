import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR ---
st.set_page_config(
    page_title="ProTrade V10.1 Fix",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>
    .metric-card { background-color: #0e1117; border: 1px solid #333; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. HESAPLAMA MOTORU ---
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
    
    # Sıkışma
    if (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER'] < 0.08:
        bulgular.append("⚠️ SIKIŞMA: Sert Hareket Bekleniyor")

    # Mumlar
    if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
       (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
        bulgular.append("🐂 YUTAN BOĞA: Yükseliş Sinyali")
        
    return bulgular

def verileri_getir(symbol, period):
    try:
        # YÖNTEM DEĞİŞİKLİĞİ: Ticker().history daha kararlıdır
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        # Eğer boş gelirse None döndür
        if df.empty: return None

        # Sütun isimlerini temizle (TimeZone vb. sorunları için)
        df.index = df.index.tz_localize(None)

        # İNDİKATÖRLER (FIBONACCI & EMA)
        fibo_emas = [21, 55, 144, 233, 610]
        for ema in fibo_emas:
            df[f'EMA_{ema}'] = df.ta.ema(length=ema)
        
        df['RSI'] = df.ta.rsi(length=14)
        
        # MACD
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            # Sütun isimlerini güvenli şekilde yeniden adlandır
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)

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

        df['CMF'] = df.ta.cmf(length=20)
        return df
    
    except Exception as e:
        st.error(f"Teknik Hata: {e}")
        return None

def puan_hesapla(df):
    puan = 0
    son = df.iloc[-1]
    if son['Close'] > son.get('EMA_144', 0): puan += 25
    if son.get('TrendYon') == 1: puan += 25
    if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
    if 30 < son.get('RSI', 50) < 70: puan += 15
    if son.get('CMF', 0) > 0: puan += 20
    return min(puan, 100)

# --- 3. ARAYÜZ ---
st.sidebar.title("🎛️ Piyasa Ayarları")

# RADYO BUTONLARI (DİKKAT EDİLMESİ GEREKEN YER)
piyasa = st.sidebar.radio("Hangi Borsa?", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])

if piyasa == "🇹🇷 BIST (TL)":
    user_input = st.sidebar.text_input("Hisse Kodu Girin", "THYAO").upper()
    # Kullanıcı yanlışlıkla .IS yazarsa kodu bozmayalım, temizleyelim
    temiz_kod = user_input.replace(".IS", "").strip()
    sembol = f"{temiz_kod}.IS"
    para_birimi = "TL"
    st.sidebar.info(f"Sistemde aranacak kod: **{sembol}**")
else:
    user_input = st.sidebar.text_input("Hisse Kodu Girin", "NVDA").upper()
    sembol = user_input.strip()
    para_birimi = "$"
    st.sidebar.info(f"Sistemde aranacak kod: **{sembol}**")

periyot = st.sidebar.select_slider("Zaman", options=["6mo", "1y", "2y", "5y"], value="1y")

# --- 4. ÇALIŞTIRMA ---
if st.sidebar.button("ANALİZ ET 🚀", use_container_width=True):
    with st.spinner('Veriler çekiliyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("❌ VERİ BULUNAMADI!")
            st.warning(f"**Aranan Sembol:** `{sembol}`")
            st.markdown("""
            **Olası Çözümler:**
            1. Sol menüde **Borsa Seçimi** (BIST / ABD) doğru mu?
            2. Hisse kodunu doğru yazdınız mı? (Örn: THYAO)
            3. Sayfayı yenileyip tekrar deneyin.
            """)
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar = formasyon_tara(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # ÜST BİLGİ
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f} {para_birimi}", f"{son['Close']-onceki['Close']:.2f}")
            c2.metric("Altın Puan", f"{puan}", "İyi" if puan>70 else "Riskli")
            c3.metric("Trend", "YÜKSELİŞ 🔼" if son.get('TrendYon')==1 else "DÜŞÜŞ 🔻")
            c4.metric("Para Akışı", "Giriş 💰" if son.get('CMF', 0)>0 else "Çıkış 💸")
            
            st.divider()

            # GRAFİK & VERİ
            col_g, col_d = st.columns([3, 1])
            
            with col_g:
                st.subheader("🕯️ Fibonacci & EMA Analizi")
                plot_df = df.iloc[-150:]
                add_plots = [
                    mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2, panel=0),
                    mpf.make_addplot(plot_df['EMA_233'], color='darkblue', width=2, panel=0),
                    mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5, panel=0),
                ]
                if 'SuperTrend' in plot_df.columns:
                    colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                    add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))

                fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                  addplot=add_plots, volume=True, 
                                  returnfig=True, figsize=(10,6))
                st.pyplot(fig)
                st.caption("Mavi Çizgi: EMA 144 (Altın Destek) | Mor Çizgi: EMA 610 (Ana Trend)")

            with col_d:
                st.subheader("Hedefler (Pivot)")
                st.table(pd.DataFrame({
                    "Seviye": ["R2 (Direnç)", "R1", "Pivot", "S1", "S2 (Destek)"],
                    "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                }))
                
                st.subheader("Sinyaller")
                for f in formasyonlar: st.info(f)
                
                if son['Close'] > son['EMA_144']:
                    st.success("✅ Fiyat 144 Ortalamanın Üzerinde (Pozitif)")
                else:
                    st.error("🔻 Fiyat 144 Ortalamanın Altında (Negatif)")

else:
    st.info("👈 Sol menüden Borsa seçin ve 'ANALİZ ET' butonuna basın.")
