import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & STİL ---
st.set_page_config(
    page_title="ProTrade V18 - Bulletproof",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0e1117; border-right: 1px solid #333; }
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #262626 100%);
        border: 1px solid #444;
        padding: 10px 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }
    .metric-title { font-size: 14px; color: #aaa; margin: 0; }
    .metric-value { font-size: 22px; font-weight: bold; color: #fff; margin: 5px 0; }
    .metric-delta { font-size: 12px; color: #ddd; }
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        font-size: 28px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 35px;
        border-radius: 6px;
        background-color: #161b22;
        border: 1px solid #30363d;
        color: white;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        border-color: #238636 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---
def yapay_zeka_ozet_yaz(df):
    try:
        son = df.iloc[-1]
        yorum = ""
        # Trend
        if not pd.isna(son.get('EMA_144')):
            if son['Close'] > son['EMA_144']:
                yorum += "Teknik görünüm pozitif. Fiyat, uzun vadeli trend desteği olan **EMA 144** seviyesinin üzerinde işlem görüyor. Bu, alıcıların piyasaya hakim olduğunu gösterir. "
            else:
                yorum += "Teknik görünüm zayıfladı. Fiyat kritik **EMA 144** desteğinin altına sarktı. Bu bölge artık direnç görevi görebilir, dikkatli olunmalı. "
        # Momentum
        if son.get('TrendYon') == 1:
            yorum += "SuperTrend indikatörü 'AL' sinyaliyle yükselişi destekliyor. "
        else:
            yorum += "SuperTrend şu an 'SAT' baskısının sürdüğünü işaret ediyor. "
        # Hacim
        if son.get('CMF', 0) > 0:
            yorum += "Hissede **Para Girişi** mevcut, bu da yükseliş ihtimalini güçlendiriyor."
        else:
            yorum += "Ancak **Para Çıkışı** var, yükselişler hacimsiz kalabilir."
        return yorum
    except: return "Veri yetersiz."

def rsi_yorumu_yap(rsi):
    if rsi > 70: return f"RSI **{rsi:.1f}** ile aşırı alım bölgesinde. Düzeltme gelebilir."
    elif rsi < 30: return f"RSI **{rsi:.1f}** ile aşırı satım bölgesinde. Tepki yükselişi beklenebilir."
    else: return f"RSI **{rsi:.1f}** ile nötr bölgede."

def macd_yorumu_yap(macd, signal):
    if macd > signal: return "MACD, Sinyal çizgisini yukarı kesti (AL)."
    else: return "MACD, Sinyal çizgisinin altında (SAT/BEKLE)."

def formasyon_avcisi(df):
    bulgular = []
    cizgiler = [] 
    try:
        son = df.iloc[-1]
        n = 5
        df['Yerel_Max'] = df.iloc[argrelextrema(df['High'].values, np.greater_equal, order=n)[0]]['High']
        df['Yerel_Min'] = df.iloc[argrelextrema(df['Low'].values, np.less_equal, order=n)[0]]['Low']
        
        son_tepeler = df['Yerel_Max'].dropna().tail(2)
        son_dipler = df['Yerel_Min'].dropna().tail(2)

        if len(son_tepeler) >= 2:
            t1, t2 = son_tepeler.iloc[-2], son_tepeler.iloc[-1]
            if abs(t1 - t2) / t1 < 0.05 and t2 > (son['Close'] * 0.95):
                bulgular.append({"tur": "⛰️ İKİLİ TEPE", "mesaj": f"Direnç ({t2:.2f}) aşılamıyor."})
                cizgiler.append((float(t2), 'red')) # Çizgi ekle

        if len(son_dipler) >= 2:
            d1, d2 = son_dipler.iloc[-2], son_dipler.iloc[-1]
            if abs(d1 - d2) / d1 < 0.05 and d2 < (son['Close'] * 1.05):
                bulgular.append({"tur": "✅ İKİLİ DİP", "mesaj": f"Destek ({d2:.2f}) çalışıyor."})
                cizgiler.append((float(d2), 'green')) # Çizgi ekle

        if (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER'] < 0.12:
            bulgular.append({"tur": "⚠️ SIKIŞMA", "mesaj": "Sert kırılım yaklaşıyor."})
        
        onceki = df.iloc[-2]
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
           (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append({"tur": "🐂 YUTAN BOĞA", "mesaj": "Güçlü yükseliş sinyali."})
            
    except: pass
    return bulgular, cizgiler

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
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)
            
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
        if not pd.isna(son.get('EMA_144')) and son['Close'] > son['EMA_144']: puan += 25
        if son.get('TrendYon') == 1: puan += 25
        if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
        if 30 < son.get('RSI', 50) < 70: puan += 15
        if son.get('CMF', 0) > 0: puan += 20
    except: pass
    return min(puan, 100)

# --- 3. ARAYÜZ ---
with st.sidebar:
    st.markdown('<p class="gradient-text">ProTrade AI</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("🛠️ Analiz Ayarları", expanded=True):
        piyasa = st.selectbox("Piyasa", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
        kod_giris = st.text_input("Hisse Kodu", "THYAO" if piyasa == "🇹🇷 BIST (TL)" else "NVDA")
            
        st.write("⏱️ **Periyot:**")
        zaman_secenekleri = ["3 Ay", "6 Ay", "YTD", "1 Yıl", "2 Yıl", "5 Yıl"]
        secilen_etiket = st.pills("Zaman", zaman_secenekleri, default="1 Yıl")
        
        zaman_map = {"3 Ay": "3mo", "6 Ay": "6mo", "YTD": "ytd", "1 Yıl": "1y", "2 Yıl": "2y", "5 Yıl": "5y"}
        periyot = zaman_map.get(secilen_etiket, "1y")

    analiz_butonu = st.button("ANALİZİ BAŞLAT 🚀", use_container_width=True, type="primary")
    st.markdown("---")
    st.caption("🟢 Sistem: **ONLİNE**")

if analiz_butonu:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if piyasa == "🇹🇷 BIST (TL)" else ham_kod
    para_birimi = "TL" if piyasa == "🇹🇷 BIST (TL)" else "$"

    with st.spinner('Analiz yapılıyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error(f"❌ {sembol} verisi çekilemedi.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2] if len(df)>1 else son
            puan = puan_hesapla(df)
            formasyonlar, cizgiler = formasyon_avcisi(df)
            
            # Pivot (Basit)
            P = (son['High'] + son['Low'] + son['Close']) / 3
            R1, S1 = 2*P - son['Low'], 2*P - son['High']
            
            genel_yorum = yapay_zeka_ozet_yaz(df)
            rsi_text = rsi_yorumu_yap(son.get('RSI', 50))
            macd_text = macd_yorumu_yap(son.get('MACD', 0), son.get('SIGNAL', 0))

            # METRİKLER
            k1, k2, k3, k4 = st.columns(4)
            degisim = son['Close'] - onceki['Close']
            k1.markdown(f"""<div class="metric-card"><p class="metric-title">Fiyat</p><p class="metric-value">{son['Close']:.2f} {para_birimi}</p><p class="metric-delta">{degisim:.2f} değişim</p></div>""", unsafe_allow_html=True)
            k2.markdown(f"""<div class="metric-card"><p class="metric-title">AI Puanı</p><p class="metric-value">{puan}/100</p><p class="metric-delta">Teknik Skor</p></div>""", unsafe_allow_html=True)
            trend_icon = "🟢 YÜKSELİŞ" if son.get('TrendYon')==1 else "🔴 DÜŞÜŞ"
            k3.markdown(f"""<div class="metric-card"><p class="metric-title">Trend</p><p class="metric-value">{trend_icon}</p><p class="metric-delta">Yön Durumu</p></div>""", unsafe_allow_html=True)
            para_icon = "💰 GİRİŞ" if son.get('CMF', 0)>0 else "💸 ÇIKIŞ"
            k4.markdown(f"""<div class="metric-card"><p class="metric-title">Para Akışı</p><p class="metric-value">{para_icon}</p><p class="metric-delta">CMF Bazlı</p></div>""", unsafe_allow_html=True)
            
            st.write("")
            tab_genel, tab_indikator, tab_formasyon = st.tabs(["📊 GENEL BAKIŞ", "📈 İNDİKATÖRLER", "🕵️‍♂️ FORMASYONLAR"])

            with tab_genel:
                col_g1, col_g2 = st.columns([3, 1])
                with col_g1:
                    plot_len = min(len(df), 150)
                    plot_df = df.iloc[-plot_len:]
                    
                    add_plots = []
                    # EMA'lar
                    if 'EMA_144' in plot_df.columns and not plot_df['EMA_144'].isnull().all():
                        add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=2))
                    if 'EMA_610' in plot_df.columns and not plot_df['EMA_610'].isnull().all():
                        add_plots.append(mpf.make_addplot(plot_df['EMA_610'], color='purple', width=2.5))
                    if 'SuperTrend' in plot_df.columns:
                        colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                    if 'MACD' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['MACD'], color='fuchsia', panel=2))
                        add_plots.append(mpf.make_addplot(plot_df['SIGNAL'], color='orange', panel=2))

                    # ÇÖZÜM: Formasyon çizgilerini 'hlines' ile değil, 'addplot' ile çiziyoruz (Zırhlı Yöntem)
                    if cizgiler:
                        for seviye, renk in cizgiler:
                            # Grafiğin boyu kadar sabit bir çizgi verisi oluşturuyoruz
                            line_data = [seviye] * len(plot_df)
                            add_plots.append(mpf.make_addplot(line_data, color=renk, linestyle='--'))

                    # hlines parametresini sildik, artık hata veremez
                    fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                      addplot=add_plots, volume=True, 
                                      panel_ratios=(3, 1, 1), returnfig=True, figsize=(10, 8))
                    st.pyplot(fig)
                    st.info(f"🤖 **Yapay Zeka Analisti:**\n\n{genel_yorum}")

                with col_g2:
                    st.markdown("### 🎯 Hedefler")
                    st.table(pd.DataFrame({"Seviye": ["Direnç 1", "PIVOT", "Destek 1"], "Fiyat": [f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}"]}))
                    if puan >= 80: st.success("🚀 GÜÇLÜ AL")
                    elif puan >= 40: st.warning("⚖️ NÖTR")
                    else: st.error("🔻 SAT")

            with tab_indikator:
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**MACD:** {son.get('MACD',0):.2f}\n\n💡 {macd_text}")
                with c2:
                    st.info(f"**RSI:** {son.get('RSI',0):.2f}\n\n💡 {rsi_text}")

            with tab_formasyon:
                if len(formasyonlar) > 0:
                    for f in formasyonlar:
                        if "⛰️" in f['tur']: st.error(f"### {f['tur']}\n{f['mesaj']}")
                        elif "✅" in f['tur']: st.success(f"### {f['tur']}\n{f['mesaj']}")
                        else: st.warning(f"### {f['tur']}\n{f['mesaj']}")
                else:
                    st.info("Temiz grafik. Belirgin formasyon yok.")

else:
    st.info("👈 Analize başlamak için sol menüyü kullanın.")
