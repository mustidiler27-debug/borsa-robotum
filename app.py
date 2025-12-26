import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR ---
st.set_page_config(
    page_title="ProTrade V12 - Komutan Modu",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Modern Kartlar CSS
st.markdown("""
<style>
    .metric-card { background-color: #0e1117; border: 1px solid #333; padding: 15px; border-radius: 10px; }
    .stAlert { padding: 10px; margin-bottom: 5px; }
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
        
        # 1. BOLLINGER SIKIŞMASI
        if (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER'] < 0.08:
            bulgular.append("⚠️ SIKIŞMA VAR: Sert Patlama Yakın!")

        # 2. YUTAN BOĞA (Dönüş)
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
           (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append("🐂 YUTAN BOĞA: Yükseliş Sinyali")

        # 3. ÇEKİÇ (Dip Dönüşü)
        if (son['Close'] > son['Open']) and \
           ((son['Open'] - son['Low']) > (2 * (son['Close'] - son['Open']))) and \
           ((son['High'] - son['Close']) < (0.2 * (son['Close'] - son['Open']))):
            bulgular.append("🔨 ÇEKİÇ: Dipten Dönüş İhtimali")
            
        # 4. GOLDEN CROSS (50 kesti 200)
        if (onceki['EMA_50'] < onceki['EMA_200']) and (son['EMA_50'] > son['EMA_200']):
            bulgular.append("🌟 GOLDEN CROSS: Büyük Ralli Başlangıcı!")
            
    except:
        pass
    return bulgular

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty: return None

        # Temizlik
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)

        # GÜVENLİ HESAPLAMA (Veri yetersizse hesaplama yapma)
        rows = len(df)
        
        # Altın Oranlar
        for ema in [21, 50, 55, 144, 200, 233, 610]:
            if rows > ema:
                df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema)
            else:
                df[f'EMA_{ema}'] = np.nan

        # İndikatörler
        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        
        # MACD (Kesin Hesapla)
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL', cols[-2]: 'MACD_HIST'}, inplace=True)

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
        
        # Grafik çizerken NaN hatası almamak için temizlik (Opsiyonel)
        # df.dropna(subset=['EMA_21'], inplace=True) 
        
        return df
    except Exception as e:
        return None

def puan_hesapla(df):
    puan = 0
    try:
        son = df.iloc[-1]
        # EMA 144 Altın Kuralı
        if not pd.isna(son.get('EMA_144')) and son['Close'] > son['EMA_144']: puan += 25
        # Trend
        if son.get('TrendYon') == 1: puan += 25
        # MACD
        if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
        # RSI
        rsi = son.get('RSI', 50)
        if 30 < rsi < 70: puan += 15
        elif rsi <= 30: puan += 20 # Dip fırsatı
        # Hacim
        if son.get('CMF', 0) > 0: puan += 20
    except: pass
    return min(puan, 100)

# --- 3. ARAYÜZ (FORM YAPISI) ---
st.sidebar.title("🎛️ Komuta Merkezi")

with st.sidebar.form(key='analiz_form'):
    piyasa = st.radio("Borsa Seçimi", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    
    if piyasa == "🇹🇷 BIST (TL)":
        kod_giris = st.text_input("Hisse Kodu", "THYAO")
    else:
        kod_giris = st.text_input("Hisse Kodu", "NVDA")
        
    periyot = st.select_slider("Analiz Geçmişi", options=["6mo", "1y", "2y", "5y"], value="2y")
    submit_button = st.form_submit_button(label='ANALİZ ET 🚀')

# --- 4. ÇALIŞTIRMA ---
if submit_button:
    # Kod Temizleme
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    if piyasa == "🇹🇷 BIST (TL)":
        sembol = f"{ham_kod}.IS"
        para_birimi = "TL"
    else:
        sembol = ham_kod
        para_birimi = "$"

    with st.spinner(f'{sembol} taranıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None or df.empty:
            st.error(f"❌ '{sembol}' Bulunamadı!")
            st.info("Lütfen Borsa seçimini (ABD/BIST) kontrol edin.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar = formasyon_tara(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # --- A. ÜST METRİKLER ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f} {para_birimi}", f"{son['Close']-onceki['Close']:.2f}")
            c2.metric("Puan", f"{puan}/100", "GÜÇLÜ" if puan>70 else "RİSKLİ")
            
            trend_str = "YÜKSELİŞ 🔼" if son.get('TrendYon')==1 else "DÜŞÜŞ 🔻"
            c3.metric("Trend", trend_str)
            
            hacim_str = "Para Girişi 💰" if son.get('CMF', 0)>0 else "Para Çıkışı 💸"
            c4.metric("Hacim", hacim_str)

            st.divider()

            # --- B. GRAFİK VE VERİ PANELİ ---
            col_chart, col_data = st.columns([3, 1])
            
            with col_chart:
                st.subheader(f"📊 {ham_kod} Analiz Grafiği")
                
                # Grafik Verisi (Son 150 mum)
                plot_df = df.iloc[-150:]
                
                # Çizgiler (AddPlots)
                add_plots = []
                
                # 1. EMA'lar (Altın Oranlar)
                # Hesaplandıysa çiz, yoksa çizme
                if 'EMA_144' in plot_df.columns and not plot_df['EMA_144'].isnull().all():
                    add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2, panel=0))
                if 'EMA_610' in plot_df.columns and not plot_df['EMA_610'].isnull().all():
                    add_plots.append(mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5, panel=0))
                
                # 2. SuperTrend (Noktalar)
                if 'SuperTrend' in plot_df.columns:
                    colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                    add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors, panel=0))
                
                # 3. MACD (Panel 2 - Alt Kısım)
                if 'MACD' in plot_df.columns:
                    add_plots.append(mpf.make_addplot(plot_df['MACD'], color='fuchsia', panel=2, ylabel='MACD'))
                    add_plots.append(mpf.make_addplot(plot_df['SIGNAL'], color='orange', panel=2))
                    add_plots.append(mpf.make_addplot(plot_df['MACD_HIST'], type='bar', color='dimgray', panel=2))

                # Grafiği Çiz (Panel 0: Fiyat, Panel 1: Hacim, Panel 2: MACD)
                fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                  addplot=add_plots, volume=True, 
                                  panel_ratios=(3, 1, 1), # Fiyat büyük, diğerleri küçük
                                  returnfig=True, figsize=(10, 8))
                st.pyplot(fig)
                st.info("ℹ️ Çizgiler: Mavi (EMA 144 - Destek), Mor (EMA 610), Pembe/Turuncu (MACD Alt Panel)")

            with col_data:
                # 1. FORMASYON RADARI
                st.markdown("### 🕵️‍♂️ Formasyon Radarı")
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⚠️" in f: st.error(f)
                        elif "🐂" in f: st.success(f)
                        elif "🌟" in f: st.success(f)
                        else: st.info(f)
                else:
                    st.write("✅ Belirgin bir 'alarm' formasyonu yok.")
                
                st.divider()

                # 2. İNDİKATÖR DEĞERLERİ
                st.markdown("### 📟 Göstergeler")
                
                # MACD Sayısal
                macd_val = son.get('MACD', 0)
                sig_val = son.get('SIGNAL', 0)
                durum = "AL ✅" if macd_val > sig_val else "SAT ❌"
                st.write(f"**MACD:** {durum}")
                st.caption(f"Değer: {macd_val:.2f}")

                # RSI Sayısal
                rsi_val = son.get('RSI', 0)
                rsi_durum = "Nötr"
                if rsi_val > 70: rsi_durum = "Pahalı 🔴"
                elif rsi_val < 30: rsi_durum = "Ucuz 🟢"
                st.write(f"**RSI:** {rsi_val:.1f} ({rsi_durum})")

                st.divider()

                # 3. PIVOTLAR
                st.markdown("### 🎯 Hedefler")
                pivot_data = {
                    "Seviye": ["R2", "R1", "PIVOT", "S1", "S2"],
                    "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                }
                st.table(pd.DataFrame(pivot_data))

else:
    st.info("👈 Sol menüden Borsa Seçimi yapın, Hisse Kodu girin ve ENTER'a basın.")
