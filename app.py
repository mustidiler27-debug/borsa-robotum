import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & CSS STİL ---
st.set_page_config(
    page_title="ProTrade V19 - Lab Mode",
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
        margin-bottom: 10px;
    }
    .metric-title { font-size: 13px; color: #aaa; margin: 0; }
    .metric-value { font-size: 20px; font-weight: bold; color: #fff; margin: 5px 0; }
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #FF512F, #DD2476);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        font-size: 26px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 35px; background-color: #161b22; border: 1px solid #30363d; color: white; font-size: 14px;
    }
    .stTabs [aria-selected="true"] { background-color: #DD2476 !important; border-color: #DD2476 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. YAPAY ZEKA YORUM MOTORU ---
def yapay_zeka_ozet_yaz(df):
    try:
        son = df.iloc[-1]
        yorum = ""
        
        # 1. Bollinger Yorumu (YENİ)
        bb_upper = son['BB_UPPER']
        bb_lower = son['BB_LOWER']
        close = son['Close']
        if close > bb_upper:
            yorum += "⚠️ **Bollinger Uyarısı:** Fiyat üst bandı delip geçti. Bu çok güçlü bir yükseliş iştahı demek ama aynı zamanda 'Aşırı Alım' bölgesindeyiz. Kısa vadeli bir düzeltme (içeri dönüş) yaşanabilir. "
        elif close < bb_lower:
            yorum += "⚠️ **Bollinger Uyarısı:** Fiyat alt bandın dışına sarktı. Piyasa aşırı satılmış durumda, buradan tepki yükselişi gelme ihtimali yüksek. "
        else:
            # Bant Genişliği (Sıkışma)
            width = (bb_upper - bb_lower) / bb_upper
            if width < 0.10:
                yorum += "⚡ **Sıkışma Var:** Bollinger bantları iyice daraldı. Fiyat enerji topluyor, yakında sert bir patlama (yönü belirsiz) olabilir. "

        # 2. EMA Yorumu (5-13-21-55-89)
        if son['EMA_5'] > son['EMA_21']:
            yorum += "✅ **Kısa Vade:** EMA 5, EMA 21'in üzerinde. Kısa vadeli trend yukarı. "
        else:
            yorum += "🔻 **Kısa Vade:** EMA 5, EMA 21'in altına indi. Kısa vadede güç kaybı var. "
            
        if close > son['EMA_89']:
            yorum += "🏆 **Ana Trend:** Fiyat EMA 89 (Ana Trend) üzerinde, uzun vade görünüm pozitif. "
        else:
            yorum += "⛔ **Ana Trend:** Fiyat EMA 89'un altında, ana trend negatif baskı altında. "

        # 3. MFI Yorumu (ACMF Yerine)
        mfi = son.get('MFI', 50)
        if mfi > 80:
            yorum += "💰 **MFI (Para Akışı):** Para girişi aşırı seviyede (80+). Zirve görülebilir. "
        elif mfi < 20:
            yorum += "💸 **MFI (Para Akışı):** Para çıkışı durma noktasına geldi (20-). Dip görülebilir. "
        elif mfi > 50:
            yorum += "💰 **MFI:** Para girişi pozitif yönde devam ediyor. "
            
        return yorum
    except: return "Veri yetersiz."

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
                bulgular.append({"tur": "⛰️ İKİLİ TEPE", "mesaj": f"Direnç ({t2:.2f}) oluştu."})
                cizgiler.append((float(t2), 'red'))

        if len(son_dipler) >= 2:
            d1, d2 = son_dipler.iloc[-2], son_dipler.iloc[-1]
            if abs(d1 - d2) / d1 < 0.05 and d2 < (son['Close'] * 1.05):
                bulgular.append({"tur": "✅ İKİLİ DİP", "mesaj": f"Destek ({d2:.2f}) oluştu."})
                cizgiler.append((float(d2), 'green'))

        onceki = df.iloc[-2]
        if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
           (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
            bulgular.append({"tur": "🐂 YUTAN BOĞA", "mesaj": "Dönüş sinyali."})
            
    except: pass
    return bulgular, cizgiler

def pivot_hesapla(df):
    try:
        last = df.iloc[-1]
        P = (last['High'] + last['Low'] + last['Close']) / 3
        R1, S1 = 2*P - last['Low'], 2*P - last['High']
        R2, S2 = P + (last['High'] - last['Low']), P - (last['High'] - last['Low'])
        return P, R1, R2, S1, S2
    except: return 0,0,0,0,0

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        rows = len(df)
        # 1. EMA'lar (5, 13, 21, 55, 89)
        for ema in [5, 13, 21, 55, 89]:
            df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema) if rows > ema else np.nan

        # 2. Bollinger Bantları (20, 2)
        bbands = df.ta.bbands(close=df['Close'], length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER', df.columns[-2]: 'BB_MID'}, inplace=True)

        # 3. İndikatörler
        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        
        # MACD
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)
            
        # SuperTrend
        st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'], length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        # 4. MFI (Money Flow Index - ACMF yerine en iyi alternatif)
        df['MFI'] = df.ta.mfi(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], length=14)
        
        return df
    except: return None

def puan_hesapla(df):
    puan = 0
    try:
        son = df.iloc[-1]
        # EMA 89 (Ana Trend)
        if not pd.isna(son.get('EMA_89')) and son['Close'] > son['EMA_89']: puan += 20
        # Bollinger Orta Bant
        if not pd.isna(son.get('BB_MID')) and son['Close'] > son['BB_MID']: puan += 10
        # Trend
        if son.get('TrendYon') == 1: puan += 20
        # MACD
        if son.get('MACD', 0) > son.get('SIGNAL', 0): puan += 15
        # RSI
        if 30 < son.get('RSI', 50) < 70: puan += 15
        # MFI
        if son.get('MFI', 50) > 50: puan += 20
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

    with st.spinner('Laboratuvar sonuçları işleniyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error(f"❌ {sembol} verisi çekilemedi.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2] if len(df)>1 else son
            puan = puan_hesapla(df)
            formasyonlar, cizgiler = formasyon_avcisi(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)
            genel_yorum = yapay_zeka_ozet_yaz(df)

            # METRİKLER
            k1, k2, k3, k4 = st.columns(4)
            degisim = son['Close'] - onceki['Close']
            k1.markdown(f"""<div class="metric-card"><p class="metric-title">Fiyat</p><p class="metric-value">{son['Close']:.2f} {para_birimi}</p></div>""", unsafe_allow_html=True)
            puan_renk = "#4CAF50" if puan > 70 else "#FF9800"
            k2.markdown(f"""<div class="metric-card"><p class="metric-title">AI Puanı</p><p class="metric-value" style="color:{puan_renk}">{puan}/100</p></div>""", unsafe_allow_html=True)
            trend_icon = "🟢 YÜKSELİŞ" if son.get('TrendYon')==1 else "🔴 DÜŞÜŞ"
            k3.markdown(f"""<div class="metric-card"><p class="metric-title">Trend</p><p class="metric-value">{trend_icon}</p></div>""", unsafe_allow_html=True)
            mfi_val = son.get('MFI', 50)
            para_icon = "💰 GİRİŞ" if mfi_val > 50 else "💸 ÇIKIŞ"
            k4.markdown(f"""<div class="metric-card"><p class="metric-title">Para Akışı (MFI)</p><p class="metric-value">{para_icon}</p></div>""", unsafe_allow_html=True)
            
            st.write("")
            tab_genel, tab_indikator, tab_formasyon = st.tabs(["📊 TEKNİK LABORATUVAR", "📈 DETAY VERİLER", "🕵️‍♂️ FORMASYONLAR"])

            with tab_genel:
                col_g1, col_g2 = st.columns([3, 1])
                with col_g1:
                    plot_len = min(len(df), 150)
                    plot_df = df.iloc[-plot_len:]
                    
                    add_plots = []
                    # 1. EMA'lar (İnce ve Kalın Ayarlı)
                    if 'EMA_5' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_5'], color='yellow', width=0.8))
                    if 'EMA_13' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_13'], color='orange', width=0.8))
                    if 'EMA_21' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_21'], color='red', width=1))
                    if 'EMA_55' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_55'], color='cyan', width=1.5))
                    if 'EMA_89' in plot_df.columns: add_plots.append(mpf.make_addplot(plot_df['EMA_89'], color='blue', width=2))
                    
                    # 2. Bollinger Bantları
                    if 'BB_UPPER' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['BB_UPPER'], color='gray', linestyle='--', width=0.8))
                        add_plots.append(mpf.make_addplot(plot_df['BB_LOWER'], color='gray', linestyle='--', width=0.8))

                    # 3. SuperTrend
                    if 'SuperTrend' in plot_df.columns:
                        colors = ['green' if x==1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', color=colors))
                    
                    # 4. Paneller (RSI, MACD, MFI)
                    if 'RSI' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['RSI'], panel=2, color='white', ylabel='RSI', ylim=(0,100)))
                    
                    if 'MACD' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['MACD'], panel=3, color='fuchsia', ylabel='MACD'))
                        add_plots.append(mpf.make_addplot(plot_df['SIGNAL'], panel=3, color='orange'))
                    
                    if 'MFI' in plot_df.columns:
                        add_plots.append(mpf.make_addplot(plot_df['MFI'], panel=4, color='lime', ylabel='MFI', ylim=(0,100)))

                    # Formasyon Çizgileri (Güvenli Yöntem)
                    if cizgiler:
                        for seviye, renk in cizgiler:
                            line_data = [seviye] * len(plot_df)
                            add_plots.append(mpf.make_addplot(line_data, color=renk, linestyle='--'))

                    # GRAFİK ÇİZİMİ (4 Panelli)
                    fig, _ = mpf.plot(plot_df, type='candle', style='nightclouds', 
                                      addplot=add_plots, volume=True, 
                                      panel_ratios=(4, 1, 1, 1, 1), # Fiyat, Vol, RSI, MACD, MFI
                                      returnfig=True, figsize=(10, 10))
                    st.pyplot(fig)
                    st.info(f"🤖 **Yapay Zeka Yorumu:**\n\n{genel_yorum}")

                with col_g2:
                    st.markdown("### 🎯 Pivot Seviyeleri")
                    st.table(pd.DataFrame({"Seviye": ["R2", "R1", "PIVOT", "S1", "S2"], "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]}))
                    
                    st.markdown("### 🧬 EMA Rehberi")
                    st.caption("🟡 EMA 5-13: Çok Kısa Vade (Al-Sat)")
                    st.caption("🔴 EMA 21: Kısa Vade Trend")
                    st.caption("🔵 EMA 55-89: Ana Trend (Omurga)")
                    
                    st.markdown("### 🌊 İndikatörler")
                    st.caption("⚪ **RSI:** 70 üstü pahalı, 30 altı ucuz.")
                    st.caption("🟣 **MACD:** Kesişimleri takip et.")
                    st.caption("🟢 **MFI:** Para giriş/çıkışı (ACMF Alternatifi).")

            with tab_indikator:
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**MACD:** {son.get('MACD',0):.2f}")
                    st.info(f"**RSI (14):** {son.get('RSI',0):.2f}")
                with c2:
                    st.success(f"**MFI (Para Akışı):** {son.get('MFI',0):.2f}")
                    st.warning(f"**Bollinger Üst:** {son.get('BB_UPPER',0):.2f}")
                    st.warning(f"**Bollinger Alt:** {son.get('BB_LOWER',0):.2f}")

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
