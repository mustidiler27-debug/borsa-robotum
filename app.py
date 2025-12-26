import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf

# --- 1. MODERN SAYFA AYARLARI ---
st.set_page_config(
    page_title="ProTrade V8 - Kontrol Merkezi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tablo ve Kart Stilleri
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stDataFrame { width: 100%; }
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

def verileri_getir(symbol, period):
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 50: return None

        # Temel İndikatörler
        df['RSI'] = df.ta.rsi(length=14)
        df['EMA_200'] = df.ta.ema(length=200)
        df['EMA_50'] = df.ta.ema(length=50)

        # MACD (Grafik için gerekli)
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            # Sütun isimlerini sabitleyelim
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
    with st.spinner('Veriler işleniyor...'):
        df = verileri_getir(sembol, periyot)
        
        if df is None:
            st.error("Veri bulunamadı!")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]
            puan = puan_hesapla(df)
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
            col_grafik, col_veri = st.columns([3, 1]) # Grafik 3 birim, Veriler 1 birim genişlikte

            with col_grafik:
                st.subheader("📊 Teknik Grafik (Fiyat + MACD)")
                
                # GRAFİK AYARLARI
                plot_df = df.iloc[-120:]
                add_plots = [
                    mpf.make_addplot(plot_df['EMA_200'], color='purple', width=2, panel=0),
                    # MACD Paneli (Panel 1)
                    mpf.make_addplot(plot_df['MACD'], color='blue', panel=1, ylabel='MACD'),
                    mpf.make_addplot(plot_df['SIGNAL'], color='orange', panel=1),
                    mpf.make_addplot(plot_df['MACD_HIST'], type='bar', color='dimgray', panel=1),
                ]
                
                # SuperTrend varsa ekle
                if 'SuperTrend' in plot_df.columns:
                    renkler = ['green' if x == 1 else 'red' for x in plot_df['TrendYon']]
                    add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=5, color=renkler, panel=0))

                # Grafiği Çiz
                fig, _ = mpf.plot(plot_df, type='candle', style='yahoo', 
                                  addplot=add_plots, volume=False, # Hacmi kapattım MACD net görünsün
                                  panel_ratios=(3, 1), # Fiyat büyük, MACD küçük
                                  returnfig=True, title=f"{sembol}", figsize=(10,7))
                st.pyplot(fig)

            with col_veri:
                st.subheader("🔢 Kritik Seviyeler")
                
                # 1. PIVOT TABLOSU (Destek Direnç)
                st.markdown("##### 🎯 Hedef & Stoplar")
                pivot_data = {
                    "Seviye": ["Direnç 2 (R2)", "Direnç 1 (R1)", "PIVOT (Denge)", "Destek 1 (S1)", "Destek 2 (S2)"],
                    "Fiyat": [f"{R2:.2f}", f"{R1:.2f}", f"{P:.2f}", f"{S1:.2f}", f"{S2:.2f}"]
                }
                st.table(pd.DataFrame(pivot_data))

                # 2. CANLI İNDİKATÖR DEĞERLERİ
                st.markdown("##### 📟 İndikatör Değerleri")
                
                # MACD Durumu
                macd_durum = "AL ✅" if son['MACD'] > son['SIGNAL'] else "SAT ❌"
                st.write(f"**MACD:** {son['MACD']:.2f}")
                st.write(f"**Sinyal:** {son['SIGNAL']:.2f}")
                st.caption(f"Durum: {macd_durum}")
                
                st.divider()
                
                # RSI Durumu
                rsi_durum = "Nötr 😐"
                if son['RSI'] > 70: rsi_durum = "Pahalı 🔴"
                elif son['RSI'] < 30: rsi_durum = "Ucuz 🟢"
                st.write(f"**RSI (14):** {son['RSI']:.2f}")
                st.caption(f"Durum: {rsi_durum}")

                st.divider()
                st.markdown("##### 🤖 Sinyal Özeti")
                if son['Close'] > son['EMA_200']:
                    st.success("Uzun Vade: YÜKSELİŞ")
                else:
                    st.error("Uzun Vade: DÜŞÜŞ")

else:
    st.info("👈 Sol menüden hisse seçip butona basın.")
