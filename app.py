import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & STİL ---
st.set_page_config(
    page_title="ProTrade V14 - Hunter Mode",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card { background-color: #1e1e1e; border: 1px solid #333; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #0e1117; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #262730; color: #4CAF50; border-bottom: 2px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- 2. GELİŞMİŞ FORMASYON AVCISI ---
def formasyon_avcisi(df):
    bulgular = []
    cizgiler = [] # Grafiğe çizilecek yatay çizgiler (Fiyat, Renk)
    
    try:
        son = df.iloc[-1]
        
        # A. İKİLİ TEPE / DİP (Esnek Toleranslı)
        # Son 90 güne bak, yerel tepeleri bul
        n = 5 # Kaç günün tepesi?
        df['Yerel_Max'] = df.iloc[argrelextrema(df['High'].values, np.greater_equal, order=n)[0]]['High']
        df['Yerel_Min'] = df.iloc[argrelextrema(df['Low'].values, np.less_equal, order=n)[0]]['Low']
        
        # Son 2 tepeyi al
        son_tepeler = df['Yerel_Max'].dropna().tail(2)
        # Son 2 dibi al
        son_dipler = df['Yerel_Min'].dropna().tail(2)

        # İkili Tepe Kontrolü
        if len(son_tepeler) >= 2:
            tepe1 = son_tepeler.iloc[-2]
            tepe2 = son_tepeler.iloc[-1]
            fark_yuzde = abs(tepe1 - tepe2) / tepe1
            
            # %4'e kadar farkı kabul et (Eskiden %1'di)
            if fark_yuzde < 0.04 and tepe2 > (son['Close'] * 0.95): # Fiyat hala tepeye yakınsa
                bulgular.append({"tur": "⛰️ İKİLİ TEPE", "mesaj": f"Yaklaşık {tepe2:.2f} seviyesinde direnç oluştu. Düşüş riski var."})
                cizgiler.append((tepe2, 'red')) # Kırmızı Çizgi

        # İkili Dip Kontrolü
        if len(son_dipler) >= 2:
            dip1 = son_dipler.iloc[-2]
            dip2 = son_dipler.iloc[-1]
            fark_yuzde = abs(dip1 - dip2) / dip1
            
            if fark_yuzde < 0.04 and dip2 < (son['Close'] * 1.05):
                bulgular.append({"tur": "✅ İKİLİ DİP", "mesaj": f"Yaklaşık {dip2:.2f} seviyesinde taban oluştu. Yükseliş desteği."})
                cizgiler.append((dip2, 'green')) # Yeşil Çizgi

        # B. ÜÇGEN / SIKIŞMA (Daha Hassas)
        bb_width = (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER']
        if bb_width < 0.12: # Toleransı %8'den %12'ye çıkardık, daha çok yakalar
            bulgular.append({"tur": "⚠️ SIKIŞMA (ÜÇGEN)", "mesaj": "Fiyat gittikçe sıkışıyor. Bir yöne sert kırılım (Patlama) çok yakın."})

        # C. MUM FORMASYONLARI
        onceki = df.iloc[-2]
        # Yutan Boğa
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
           (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append({"tur": "🐂 YUTAN BOĞA", "mesaj": "Satıcılar tükendi, alıcılar kontrolü ele aldı."})
            
        # Çekiç
        govde = abs(son['Close'] - son['Open'])
        alt_golge = son['Open'] - son['Low'] if son['Close'] > son['Open'] else son['Close'] - son['Low']
        if alt_golge > (2 * govde) and (son['High'] - son['Close']) < (0.5 * govde):
             bulgular.append({"tur": "🔨 ÇEKİÇ", "mesaj": "Dipte güçlü alım geldi."})

    except: pass
    return bulgular, cizgiler

# --- 3. DİĞER FONKSİYONLAR ---
def pivot_hesapla(df):
    try:
        last = df.iloc[-1]
        P = (last['High'] + last['Low'] + last['Close']) / 3
        R1 = 2*P - last['Low']
        S1 = 2*P - last['High']
        R2 = P + (last['High'] - last['Low'])
        S2 = P - (last['High'] - last['Low'])
        return P, R1, R2, S1, S2
    except: return 0,0,0,0,0

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        # Ema, RSI, MACD, BB, SuperTrend
        rows = len(df)
        for ema in [21, 50, 144, 200, 610]:
            if rows > ema: df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema)
            else: df[f'EMA_{ema}'] = np.nan

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

# --- 4. ARAYÜZ ---
st.sidebar.title("🎛️ Kontrol Paneli")
with st.sidebar.form(key='analiz_form'):
    piyasa = st.radio("Piyasa", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    if piyasa == "🇹🇷 BIST (TL)":
        kod_giris = st.text_input("Hisse Kodu", "THYAO")
    else:
        kod_giris = st.text_input("Hisse Kodu", "NVDA")
    periyot = st.select_slider("Geçmiş Veri", options=["6mo", "1y", "2y", "5y"], value="1y")
    submit_button = st.form_submit_button(label='ANALİZİ BAŞLAT 🚀')

if submit_button:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if piyasa == "🇹🇷 BIST (TL)" else ham_kod
    para_birimi = "TL" if piyasa == "🇹🇷 BIST (TL)" else "$"

    with st.spinner('Formasyonlar taranıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error(f"❌ {sembol} bulunamadı.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
            # BURADA HEM FORMASYONU HEM ÇİZGİLERİ ALIYORUZ
            formasyonlar, cizgiler = formasyon_avcisi(df) 
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # ÜST BİLGİ
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Fiyat", f"{son['Close']:.2f} {para_birimi}", f"{son['Close']-onceki['Close']:.2f}")
            k2.metric("Puan", f"{puan}/100", "Güçlü" if puan>70 else "Zayıf")
            k3.metric("Trend", "YÜKSELİŞ 🔼" if son.get('TrendYon')==1 else "DÜŞÜŞ 🔻")
            k4.metric("Para", "Giriş Var 💰" if son.get('CMF', 0)>0 else "Çıkış Var 💸")
            
            st.divider()

            # SEKMELER
            tab_genel, tab_indikator, tab_formasyon = st.tabs(["📊 GENEL BAKIŞ", "📈 İNDİKATÖRLER", "🕵️‍♂️ FORMASYONLAR"])

            # 1. SEKME: GENEL
            with tab_genel:
                col_g1, col_g2 = st.columns([3, 1])
                with col_g1:
                    st.subheader("Fiyat Grafiği & Formasyon Çizgileri")
                    
                    plot_df = df.iloc[-150:]
                    add_plots = []
                    
                    # EMA'lar
                    if 'EMA_144' in plot_df.columns and not plot_df['EMA_144'].isnull().all():
                        add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2))
                    if 'EMA_610' in plot_df.columns and not plot_df['EMA_610'].isnull().all():
                        add_plots.append(mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5))
                    
                    # SuperTrend
                    if 'SuperTrend' in plot_df.columns:
                        colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                    
                    # MACD
                    if 'MACD' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['MACD'], color='fuchsia', panel=2, ylabel='MACD'))
                        add_plots.append(mpf.make_addplot(plot_df['SIGNAL'], color='orange', panel=2))
                        add_plots.append(mpf.make_addplot(plot_df['MACD_HIST'], type='bar', color='dimgray', panel=2))

                    # FORMASYON ÇİZGİLERİNİ EKLE (Yatay Çizgiler)
                    # Eğer İkili Tepe/Dip bulunduysa hlines ile çiz
                    h_lines_dict = None
                    if cizgiler:
                        seviyeler = [x[0] for x in cizgiler]
                        renkler = [x[1] for x in cizgiler]
                        h_lines_dict = dict(hlines=seviyeler, colors=renkler, linewidths=2, linestyle='-.')

                    # Grafiği Çiz (hlines parametresi eklendi)
                    if h_lines_dict:
                        fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                          addplot=add_plots, volume=True, 
                                          hlines=h_lines_dict, # <-- İŞTE BU ÇİZİYOR
                                          panel_ratios=(3, 1, 1), returnfig=True, figsize=(10, 8))
                    else:
                        fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                          addplot=add_plots, volume=True, 
                                          panel_ratios=(3, 1, 1), returnfig=True, figsize=(10, 8))
                        
                    st.pyplot(fig)
                    if cizgiler:
                        st.caption("ℹ️ GRAFİK ÜZERİNDEKİ KESİKLİ ÇİZGİLER BULUNAN FORMASYON SEVİYELERİDİR (Kırmızı: Tepe, Yeşil: Dip).")

                with col_g2:
                    st.subheader("Pivot Seviyeleri")
                    st.table(pd.DataFrame({
                        "Seviye": ["Direnç 2", "Direnç 1", "PIVOT", "Destek 1", "Destek 2"],
                        "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                    }))
                    
                    if puan >= 70: st.success(f"**PUAN: {puan} (GÜÇLÜ)**")
                    elif puan >= 40: st.warning(f"**PUAN: {puan} (ORTA)**")
                    else: st.error(f"**PUAN: {puan} (ZAYIF)**")

            # 2. SEKME: İNDİKATÖRLER
            with tab_indikator:
                c_i1, c_i2 = st.columns(2)
                with c_i1:
                    st.markdown("#### 🌊 MACD")
                    st.write(f"Değer: {son.get('MACD',0):.2f}")
                    if son.get('MACD',0) > son.get('SIGNAL',0): st.success("DURUM: POZİTİF (AL)")
                    else: st.error("DURUM: NEGATİF (SAT)")
                    
                    st.markdown("#### ⚡ RSI")
                    st.write(f"Değer: {son.get('RSI',0):.2f}")
                with c_i2:
                    st.markdown("#### 💰 Para Akışı (CMF)")
                    st.write(f"Değer: {son.get('CMF',0):.2f}")
                    if son.get('CMF',0) > 0: st.success("Para Girişi Var")
                    else: st.error("Para Çıkışı Var")
                    
                    st.markdown("#### 🏆 Altın Oran (EMA 144)")
                    if son['Close'] > son.get('EMA_144', 999999): st.success("Güvenli Bölge (Üstünde)")
                    else: st.error("Riskli Bölge (Altında)")

            # 3. SEKME: FORMASYONLAR
            with tab_formasyon:
                st.subheader("🕵️‍♂️ Gelişmiş Formasyon Avcısı")
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⛰️" in f['tur']: st.error(f"### {f['tur']}\n{f['mesaj']}")
                        elif "✅" in f['tur']: st.success(f"### {f['tur']}\n{f['mesaj']}")
                        elif "⚠️" in f['tur']: st.warning(f"### {f['tur']}\n{f['mesaj']}")
                        else: st.info(f"### {f['tur']}\n{f['mesaj']}")
                else:
                    st.info("🔍 Şu an çok belirgin bir formasyon yok. (Toleranslar genişletilmesine rağmen temiz bir yapı bulunamadı).")

else:
    st.info("👈 Sol menüden ayarları yapın ve 'ANALİZİ BAŞLAT' butonuna basın.")
