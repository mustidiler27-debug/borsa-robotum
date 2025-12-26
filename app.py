import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & STİL ---
st.set_page_config(
    page_title="ProTrade V13 - Professional Tabs",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kartlar ve Sekmeler İçin Özel CSS
st.markdown("""
<style>
    .metric-card { background-color: #1e1e1e; border: 1px solid #333; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #0e1117; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #262730; color: #4CAF50; border-bottom: 2px solid #4CAF50; }
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
        
        # 1. Bollinger Sıkışması
        if (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER'] < 0.08:
            bulgular.append({"tur": "⚠️ SIKIŞMA", "mesaj": "Bollinger bantları çok daraldı. Sert bir kırılım (patlama) gelmek üzere."})

        # 2. Yutan Boğa
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
           (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append({"tur": "🐂 YUTAN BOĞA", "mesaj": "Düşüş trendi bitmiş, alıcılar piyasayı ele geçirmiş. Güçlü dönüş sinyali."})

        # 3. Çekiç
        if (son['Close'] > son['Open']) and \
           ((son['Open'] - son['Low']) > (2 * (son['Close'] - son['Open']))) and \
           ((son['High'] - son['Close']) < (0.2 * (son['Close'] - son['Open']))):
            bulgular.append({"tur": "🔨 ÇEKİÇ", "mesaj": "Fiyat dibi görüp hızla toparlamış. Dip çalışması tamamlanmış olabilir."})

        # 4. Golden Cross
        if (onceki.get('EMA_50', 0) < onceki.get('EMA_200', 0)) and (son.get('EMA_50', 0) > son.get('EMA_200', 0)):
             bulgular.append({"tur": "🌟 GOLDEN CROSS", "mesaj": "50 Günlük ortalama 200 günlüğü yukarı kesti. Efsanevi ralli sinyali."})

    except: pass
    return bulgular

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        
        # Temizlik
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        # İndikatörler
        rows = len(df)
        
        # Altın Oran EMA'ları
        for ema in [21, 50, 144, 200, 610]:
            if rows > ema:
                df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema)
            else:
                df[f'EMA_{ema}'] = np.nan

        # RSI, MACD, Bollinger, SuperTrend, CMF
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
        # Kriterler
        if son['Close'] > son.get('EMA_144', 999999): puan += 25
        if son.get('TrendYon') == 1: puan += 25
        if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
        if 30 < son.get('RSI', 50) < 70: puan += 15
        if son.get('CMF', 0) > 0: puan += 20
    except: pass
    return min(puan, 100)

# --- 3. ARAYÜZ (SIDEBAR) ---
st.sidebar.title("🎛️ Kontrol Paneli")
with st.sidebar.form(key='analiz_form'):
    piyasa = st.radio("Piyasa", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    if piyasa == "🇹🇷 BIST (TL)":
        kod_giris = st.text_input("Hisse Kodu", "THYAO")
    else:
        kod_giris = st.text_input("Hisse Kodu", "NVDA")
    periyot = st.select_slider("Geçmiş Veri", options=["6mo", "1y", "2y", "5y"], value="2y")
    submit_button = st.form_submit_button(label='ANALİZİ BAŞLAT 🚀')

# --- 4. ANA EKRAN MANTIĞI ---
if submit_button:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if piyasa == "🇹🇷 BIST (TL)" else ham_kod
    para_birimi = "TL" if piyasa == "🇹🇷 BIST (TL)" else "$"

    with st.spinner('Yapay zeka analiz yapıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error(f"❌ {sembol} bulunamadı.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            formasyonlar = formasyon_tara(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # --- ÜST BİLGİ ŞERİDİ (HER ZAMAN GÖRÜNÜR) ---
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Fiyat", f"{son['Close']:.2f} {para_birimi}", f"{son['Close']-onceki['Close']:.2f}")
            k2.metric("Genel Puan", f"{puan}/100", "Güçlü" if puan>70 else "Zayıf")
            k3.metric("Ana Trend", "YÜKSELİŞ 🔼" if son.get('TrendYon')==1 else "DÜŞÜŞ 🔻")
            k4.metric("Para Durumu", "Giriş Var 💰" if son.get('CMF', 0)>0 else "Çıkış Var 💸")
            
            st.divider()

            # --- SEKMELİ YAPI (TABS) ---
            tab_genel, tab_indikator, tab_formasyon = st.tabs(["📊 GENEL BAKIŞ", "📈 İNDİKATÖRLER", "🕵️‍♂️ FORMASYONLAR"])

            # ---------------------------
            # 1. SEKME: GENEL BAKIŞ
            # ---------------------------
            with tab_genel:
                col_g1, col_g2 = st.columns([3, 1])
                
                with col_g1:
                    st.subheader("Fiyat Grafiği ve Altın Oranlar")
                    # Grafik Hazırlığı
                    plot_df = df.iloc[-150:]
                    add_plots = []
                    # EMA 144 (Destek) ve 610 (Ana Trend)
                    if 'EMA_144' in plot_df.columns and not plot_df['EMA_144'].isnull().all():
                        add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2, panel=0))
                    if 'EMA_610' in plot_df.columns and not plot_df['EMA_610'].isnull().all():
                        add_plots.append(mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5, panel=0))
                    # SuperTrend
                    if 'SuperTrend' in plot_df.columns:
                        colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors, panel=0))
                    # MACD Paneli (Altta)
                    if 'MACD' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['MACD'], color='fuchsia', panel=2, ylabel='MACD'))
                        add_plots.append(mpf.make_addplot(plot_df['SIGNAL'], color='orange', panel=2))
                        add_plots.append(mpf.make_addplot(plot_df['MACD_HIST'], type='bar', color='dimgray', panel=2))

                    fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                      addplot=add_plots, volume=True, 
                                      panel_ratios=(3, 1, 1), returnfig=True, figsize=(10, 8))
                    st.pyplot(fig)
                    st.info("ℹ️ Mavi Çizgi: EMA 144 (Altın Destek) | Mor Çizgi: EMA 610 | Alt Panel: MACD")

                with col_g2:
                    st.subheader("Hedef Seviyeler (Pivot)")
                    st.write("Yarın için takip edilecek destek ve direnç noktaları:")
                    pivot_df = pd.DataFrame({
                        "Nokta": ["Direnç 2", "Direnç 1", "PIVOT", "Destek 1", "Destek 2"],
                        "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                    })
                    st.table(pivot_df)
                    
                    st.markdown("---")
                    st.subheader("Yapay Zeka Notu")
                    if puan >= 80:
                        st.success(f"**AA - MÜKEMMEL ({puan})**\n\nKağıt teknik olarak çok güçlü. Trend yukarı, para girişi var.")
                    elif puan >= 60:
                        st.info(f"**BA - İYİ ({puan})**\n\nPozitif görünüm devam ediyor. Ufak riskler olsa da yön yukarı.")
                    elif puan >= 40:
                        st.warning(f"**CC - NÖTR ({puan})**\n\nKararsız bölge. İzlemek daha sağlıklı olabilir.")
                    else:
                        st.error(f"**FF - RİSKLİ ({puan})**\n\nTeknik göstergeler negatif. Satış baskısı var.")

            # ---------------------------
            # 2. SEKME: İNDİKATÖRLER
            # ---------------------------
            with tab_indikator:
                st.subheader("Teknik Gösterge Analizi")
                
                col_i1, col_i2 = st.columns(2)
                
                with col_i1:
                    # MACD ANALİZİ
                    macd_val = son.get('MACD', 0)
                    sig_val = son.get('SIGNAL', 0)
                    st.markdown("#### 🌊 MACD (Trend Gücü)")
                    if macd_val > sig_val:
                        st.success(f"**DURUM: POZİTİF (AL)**\n\nMACD çizgisi ({macd_val:.2f}), Sinyal çizgisinin ({sig_val:.2f}) üzerinde. Bu, yükseliş trendinin desteklendiğini gösterir.")
                    else:
                        st.error(f"**DURUM: NEGATİF (SAT)**\n\nMACD çizgisi sinyalin altına inmiş. Yükseliş ivmesi kaybolmuş, düzeltme veya düşüş olabilir.")

                    st.markdown("---")
                    
                    # RSI ANALİZİ
                    rsi_val = son.get('RSI', 50)
                    st.markdown(f"#### ⚡ RSI (Göreceli Güç): {rsi_val:.2f}")
                    if rsi_val > 70:
                        st.error("**AŞIRI ALIM BÖLGESİ (>70)**\n\nHisse çok hızlı yükselmiş ve pahalılanmış olabilir. Kâr satışı gelebilir.")
                    elif rsi_val < 30:
                        st.success("**AŞIRI SATIM BÖLGESİ (<30)**\n\nHisse çok sert düşmüş ve ucuzlamış. Buradan tepki yükselişi gelebilir.")
                    else:
                        st.info("**NÖTR BÖLGE (30-70)**\n\nFiyat normal seyrinde ilerliyor. Aşırı bir şişkinlik veya çöküş yok.")

                with col_i2:
                    # CMF ANALİZİ
                    cmf_val = son.get('CMF', 0)
                    st.markdown("#### 💰 CMF (Para Akışı)")
                    if cmf_val > 0.05:
                        st.success(f"**GÜÇLÜ GİRİŞ ({cmf_val:.2f})**\n\nBüyük oyuncular mal topluyor. Fiyat yükselmese bile para giriyor.")
                    elif cmf_val > 0:
                        st.info(f"**ZAYIF GİRİŞ ({cmf_val:.2f})**\n\nUfak çaplı para girişi var, pozitif.")
                    else:
                        st.error(f"**PARA ÇIKIŞI ({cmf_val:.2f})**\n\nHisseden para çıkıyor. Satıcılar daha baskın.")
                        
                    st.markdown("---")
                    
                    # EMA 144 ANALİZİ
                    ema144 = son.get('EMA_144', 0)
                    st.markdown("#### 🏆 Fibonacci EMA 144")
                    if son['Close'] > ema144:
                        st.success(f"**GÜVENLİ BÖLGE**\n\nFiyat {ema144:.2f} seviyesindeki Altın Destek noktasının üzerinde. Ana trend bozulmamış.")
                    else:
                        st.error(f"**RİSKLİ BÖLGE**\n\nFiyat {ema144:.2f} desteğinin altına sarkmış. Bu seviye direnç olarak çalışabilir.")

            # ---------------------------
            # 3. SEKME: FORMASYONLAR
            # ---------------------------
            with tab_formasyon:
                st.subheader("🕵️‍♂️ Yapay Zeka Formasyon Taraması")
                
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⚠️" in f['tur']:
                            st.error(f"### {f['tur']}\n{f['mesaj']}")
                        elif "🐂" in f['tur'] or "🌟" in f['tur']:
                            st.success(f"### {f['tur']}\n{f['mesaj']}")
                        else:
                            st.info(f"### {f['tur']}\n{f['mesaj']}")
                else:
                    st.info("🔍 Şu an grafik üzerinde belirgin bir mum formasyonu (Doji, Çekiç vb.) veya sıkışma tespit edilemedi.")
                    st.write("Bu her zaman kötü değildir; piyasa stabil bir trendde olabilir.")

else:
    st.info("👈 Sol menüden ayarları yapın ve 'ANALİZİ BAŞLAT' butonuna basın.")
