import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR ---
st.set_page_config(
    page_title="ProTrade V11 - Stable",
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
    try:
        last = df.iloc[-1]
        P = (last['High'] + last['Low'] + last['Close']) / 3
        R1 = 2*P - last['Low']
        S1 = 2*P - last['High']
        R2 = P + (last['High'] - last['Low'])
        S2 = P - (last['High'] - last['Low'])
        return P, R1, R2, S1, S2
    except:
        return 0,0,0,0,0

def formasyon_tara(df):
    bulgular = []
    try:
        son = df.iloc[-1]
        onceki = df.iloc[-2]
        
        # Sıkışma
        if (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER'] < 0.08:
            bulgular.append("⚠️ SIKIŞMA: Sert Hareket Bekleniyor")

        # Mumlar
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
        (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append("🐂 YUTAN BOĞA: Yükseliş Sinyali")
    except:
        pass
        
    return bulgular

def verileri_getir(symbol, period):
    try:
        # Ticker modülü daha güvenlidir
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty: return None

        # Sütun İsimlerini Temizle (MultiIndex Hatasını Önler)
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        
        # Tarih formatını düzelt
        df.index = df.index.tz_localize(None)

        # GÜVENLİ EMA HESAPLAMA (HATA ÖNLEYİCİ)
        # Eğer veri sayısı EMA uzunluğundan az ise o EMA'yı hesaplama!
        veri_sayisi = len(df)
        fibo_emas = [21, 55, 144, 233, 610]
        
        for ema in fibo_emas:
            if veri_sayisi > ema:
                # Sadece 'Close' sütununu kullanarak hesapla (Çoklu kolon hatasını engeller)
                df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema)
            else:
                # Veri yetersizse 0 bas, program çökmesin
                df[f'EMA_{ema}'] = np.nan

        # İndikatörler
        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        
        # MACD
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            # Dinamik isimlendirme yakalama
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)

        # Bollinger
        bbands = df.ta.bbands(close=df['Close'], length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)

        # SuperTrend
        st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'], length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        df['CMF'] = df.ta.cmf(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], length=20)
        
        # Nan temizliği (Grafik çizimi için baştaki boşlukları at)
        df.dropna(subset=['EMA_21'], inplace=True)
        
        return df
    
    except Exception as e:
        # Hata olursa ekrana bas ama çökme
        st.error(f"Veri işleme hatası: {e}")
        return None

def puan_hesapla(df):
    puan = 0
    try:
        son = df.iloc[-1]
        # EMA 144 var mı kontrol et (NaN değilse)
        if not pd.isna(son.get('EMA_144')) and son['Close'] > son['EMA_144']: puan += 25
        if son.get('TrendYon') == 1: puan += 25
        if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
        if 30 < son.get('RSI', 50) < 70: puan += 15
        if son.get('CMF', 0) > 0: puan += 20
    except:
        pass
    return min(puan, 100)

# --- 3. ARAYÜZ (FORM YAPISI - ENTER TUŞU İÇİN) ---
st.sidebar.title("🎛️ Piyasa Ayarları")

# Form başlangıcı: Bu sayede Enter tuşu çalışır
with st.sidebar.form(key='analiz_form'):
    piyasa = st.radio("Hangi Borsa?", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    
    if piyasa == "🇹🇷 BIST (TL)":
        kod_giris = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO")
    else:
        kod_giris = st.text_input("Hisse Kodu (Örn: NVDA)", "NVDA")
        
    periyot = st.select_slider("Analiz Geçmişi", options=["6mo", "1y", "2y", "5y", "max"], value="2y")
    
    # Form gönderme butonu
    submit_button = st.form_submit_button(label='ANALİZ ET 🚀')

# --- 4. ÇALIŞTIRMA MANTIĞI ---
if submit_button:
    # Kod Temizliği
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    if piyasa == "🇹🇷 BIST (TL)":
        sembol = f"{ham_kod}.IS"
        para_birimi = "TL"
    else:
        sembol = ham_kod
        para_birimi = "$"

    with st.spinner(f'{sembol} analiz ediliyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None or df.empty:
            st.error("❌ VERİ ALINAMADI")
            st.warning(f"Aranan: {sembol}")
            st.info("Lütfen hisse kodunu kontrol edin veya 'Analiz Geçmişi'ni artırın (EMA 610 için en az 2y veri gerekir).")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar = formasyon_tara(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # EKRAN ÇIKTILARI
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f} {para_birimi}", f"{son['Close']-onceki['Close']:.2f}")
            c2.metric("Puan", f"{puan}", "Güçlü" if puan>70 else "Nötr")
            c3.metric("Trend", "YÜKSELİŞ 🔼" if son.get('TrendYon')==1 else "DÜŞÜŞ 🔻")
            c4.metric("Hacim", "Giriş 💰" if son.get('CMF', 0)>0 else "Çıkış 💸")
            
            st.divider()

            col_g, col_d = st.columns([3, 1])
            
            with col_g:
                st.subheader("🕯️ Altın Oran Grafiği")
                # Grafik verisi (Son 150 gün)
                plot_df = df.iloc[-150:]
                
                add_plots = []
                # Sadece hesaplanabilmiş (NaN olmayan) EMA'ları çiz
                if 'EMA_144' in plot_df.columns and not plot_df['EMA_144'].isnull().all():
                    add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2, panel=0))
                if 'EMA_610' in plot_df.columns and not plot_df['EMA_610'].isnull().all():
                    add_plots.append(mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5, panel=0))
                
                if 'SuperTrend' in plot_df.columns:
                    colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                    add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))

                fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                  addplot=add_plots, volume=True, 
                                  returnfig=True, figsize=(10,6))
                st.pyplot(fig)

            with col_d:
                st.subheader("Pivot Seviyeleri")
                st.table(pd.DataFrame({
                    "Seviye": ["Direnç 2", "Direnç 1", "PIVOT", "Destek 1", "Destek 2"],
                    "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                }))
                
                st.subheader("Sinyaller")
                if len(formasyonlar) > 0:
                    for f in formasyonlar: st.info(f)
                else:
                    st.write("Belirgin formasyon yok.")

else:
    st.info("👈 Sol menüden kodu yazıp ENTER'a basın.")
