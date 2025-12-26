import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf

# --- 1. MODERN SAYFA AYARLARI ---
st.set_page_config(
    page_title="ProTrade AI Terminal",
    layout="wide", # Ekranın tamamını kullan
    initial_sidebar_state="expanded"
)

# Özel CSS ile Modern Görünüm (Kartlar, Gölgeler)
st.markdown("""
<style>
    .metric-card {
        background-color: #0e1117;
        border: 1px solid #303030;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR (BEYİN KISMI) ---
def pivot_hesapla(df):
    # Klasik Pivot Noktaları
    last = df.iloc[-1]
    P = (last['High'] + last['Low'] + last['Close']) / 3
    R1 = 2*P - last['Low']
    S1 = 2*P - last['High']
    R2 = P + (last['High'] - last['Low'])
    S2 = P - (last['High'] - last['Low'])
    return P, R1, R2, S1, S2

def verileri_getir(symbol, period):
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 50: return None

        # İndikatörler
        df['RSI'] = df.ta.rsi(length=14)
        df['EMA_50'] = df.ta.ema(length=50)
        df['EMA_200'] = df.ta.ema(length=200)
        
        # MACD
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            df.rename(columns={df.columns[-3]: 'MACD', df.columns[-1]: 'SIGNAL'}, inplace=True)

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

def puanlama_motoru(df):
    puan = 0
    son = df.iloc[-1]
    
    # Kriterler
    if son['Close'] > son['EMA_200']: puan += 20
    if son.get('TrendYon', 0) == 1: puan += 20
    if 30 < son['RSI'] < 70: puan += 10
    if son['RSI'] < 30: puan += 15 # Dip tepkisi şansı
    if son['MACD'] > son['SIGNAL']: puan += 20
    if son.get('CMF', 0) > 0: puan += 15
    
    # Bollinger alt banda yakınsa ek puan
    bb_konum = (son['Close'] - son['BB_LOWER']) / (son['BB_UPPER'] - son['BB_LOWER'])
    if bb_konum < 0.2: puan += 15
    
    return min(puan, 100) # Maks 100

# --- 3. YAN MENÜ (SIDEBAR) ---
st.sidebar.title("🎛️ ProTrade AI")
piyasa = st.sidebar.selectbox("Piyasa Seç", ["🇹🇷 BIST (Türkiye)", "🇺🇸 ABD (Global)", "₿ Kripto"])

if piyasa == "🇹🇷 BIST (Türkiye)":
    sembol = st.sidebar.text_input("Sembol", "THYAO").upper() + ".IS"
elif piyasa == "🇺🇸 ABD (Global)":
    sembol = st.sidebar.text_input("Sembol", "AAPL").upper()
else:
    sembol = st.sidebar.text_input("Sembol", "BTC").upper() + "-USD"

periyot = st.sidebar.select_slider("Analiz Derinliği", options=["3mo", "6mo", "1y", "2y", "5y"], value="1y")

if st.sidebar.button("ANALİZİ BAŞLAT 🔥", use_container_width=True):
    with st.spinner('Yapay zeka verileri işliyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("Veri bulunamadı! Kodu kontrol et.")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puanlama_motoru(df)
            P, R1, R2, S1, S2 = pivot_hesapla(df)

            # --- 4. ANA EKRAN (DASHBOARD) ---
            
            # ÜST BİLGİ ŞERİDİ
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f}", f"{son['Close'] - onceki['Close']:.2f}")
            
            trend_renk = "YÜKSELİŞ 🟢" if son.get('TrendYon') == 1 else "DÜŞÜŞ 🔴"
            c2.metric("Trend", trend_renk)
            
            c3.metric("RSI (Güç)", f"{son['RSI']:.1f}")
            
            # MODERN PUAN BAR'I
            c4.write(f"**Yapay Zeka Skoru: {puan}/100**")
            renk_bar = "green" if puan > 70 else ("orange" if puan > 40 else "red")
            c4.progress(puan/100)

            st.divider()

            # ANA İÇERİK: 2 Sütunlu Yapı
            # Sol taraf: Grafik (Geniş), Sağ taraf: Özet Rapor (Dar)
            col_main, col_side = st.columns([3, 1])

            with col_main:
                # SEKMELER (TABS) - İŞTE MODERNLİK BURADA
                tab1, tab2, tab3 = st.tabs(["📊 Teknik Grafik", "🧠 AI Sinyal Dedektörü", "🔢 Pivot & Destekler"])
                
                with tab1:
                    # GRAFİK
                    plot_df = df.iloc[-120:]
                    add_plots = [
                        mpf.make_addplot(plot_df['EMA_200'], color='purple', width=2),
                    ]
                    if 'SuperTrend' in plot_df.columns:
                        renkler = ['green' if x == 1 else 'red' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=8, color=renkler))

                    fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                      addplot=add_plots, volume=True, 
                                      returnfig=True, title=f"{sembol} - Günlük", figsize=(10,6))
                    st.pyplot(fig)

                with tab2:
                    st.subheader("Yapay Zeka Ne Görüyor?")
                    # Madde madde sinyaller
                    if son['Close'] > son['EMA_200']:
                        st.success("✅ Fiyat 200 günlük ortalamanın üzerinde (Uzun vade POZİTİF)")
                    else:
                        st.error("🔻 Fiyat 200 günlük ortalamanın altında (Uzun vade NEGATİF)")
                    
                    if son['MACD'] > son['SIGNAL']:
                        st.success("✅ MACD Al sinyali üretiyor.")
                    
                    bb_width = (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER']
                    if bb_width < 0.10:
                        st.warning("⚠️ BOLLINGER SIKIŞMASI: Çok sert bir patlama hazırlığı var!")
                    
                    if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and (son['Close'] > onceki['Open']):
                        st.info("🐂 Yutan Boğa formasyonu tespit edildi.")

                with tab3:
                    st.subheader("Kritik Destek & Dirençler")
                    st.markdown("Fiyatın dönebileceği matematiksel seviyeler:")
                    
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.info(f"**Direnç 2 (R2):** {R2:.2f}")
                        st.warning(f"**Direnç 1 (R1):** {R1:.2f}")
                    with col_p2:
                        st.success(f"**Destek 1 (S1):** {S1:.2f}")
                        st.error(f"**Destek 2 (S2):** {S2:.2f}")
                    
                    st.caption(f"Pivot Noktası (Denge): {P:.2f}")

            with col_side:
                # SAĞ TARAFTA HIZLI BAKIŞ KARTI
                st.markdown("### 🚦 Hızlı Bakış")
                
                if puan >= 75:
                    st.success("# AL 🔥")
                    st.write("Momentum çok güçlü.")
                elif puan >= 45:
                    st.warning("# TUT ⚖️")
                    st.write("Yön kararsız.")
                else:
                    st.error("# SAT 🔻")
                    st.write("Trend negatif.")
                
                st.markdown("---")
                st.write("**Para Girişi (CMF):**")
                if son.get('CMF', 0) > 0:
                    st.write("💰 Pozitif")
                else:
                    st.write("💸 Negatif")
                    
                st.write("**Volatilite:**")
                st.write(f"%{bb_width*100:.1f} (Bant Genişliği)")

else:
    # Karşılama Ekranı
    st.info("👈 Sol menüden bir piyasa seç ve 'ANALİZİ BAŞLAT' butonuna bas.")
    st.markdown("""
    ### 🚀 Neler Yeni?
    * **Sekmeli Yapı:** Grafiği ve sinyalleri ayrı sekmelerde gör.
    * **Pivot Analizi:** Yarın fiyatın nereye çarpıp döneceğini gör.
    * **Modern Skor:** Puanını ilerleme çubuğuyla takip et.
    """)
