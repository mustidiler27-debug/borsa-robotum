import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Borsa Karnesi V6", layout="wide")

st.title("🎓 Borsa Terminatörü V6.0: AKILLI KARNE")
st.markdown("""
**Yapay Zeka Destekli Puanlama Sistemi**
Trend, Hacim ve İndikatörleri analiz edip hisseye **100 üzerinden not verir.**
""")

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Kontrol Paneli")
piyasa = st.sidebar.radio(
    "Piyasa Seçimi",
    ("🇹🇷 Türkiye (BIST)", "🇺🇸 ABD (Nasdaq/NYSE)", "₿ Kripto / Altın")
)

if piyasa == "🇹🇷 Türkiye (BIST)":
    sembol_ham = st.sidebar.text_input("Hisse Kodu", "THYAO")
    hisse_kodu = f"{sembol_ham}.IS"
    st.sidebar.caption(f"Aranıyor: {hisse_kodu}")
elif piyasa == "🇺🇸 ABD (Nasdaq/NYSE)":
    hisse_kodu = st.sidebar.text_input("Hisse Kodu", "AAPL")
else:
    sembol_ham = st.sidebar.text_input("Kripto Kodu", "BTC")
    hisse_kodu = f"{sembol_ham}-USD"
    st.sidebar.caption(f"Aranıyor: {hisse_kodu}")

periyot = st.sidebar.selectbox("Veri Periyodu", ["6mo", "1y", "2y", "5y"], index=1)

# --- PUANLAMA MOTORU ---
def puan_hesapla(df):
    puan = 0
    son = df.iloc[-1]
    rapor = []

    # 1. TREND PUANI (Maks 30 Puan)
    if son['Close'] > son['EMA_200']:
        puan += 15
        rapor.append("✅ Fiyat 200 GHO üzerinde (+15)")
    else:
        rapor.append("🔻 Fiyat 200 GHO altında (0)")

    if son.get('TrendYon', 0) == 1: # SuperTrend
        puan += 15
        rapor.append("✅ SuperTrend Yükseliş (+15)")
    else:
        rapor.append("🔻 SuperTrend Düşüş (0)")

    # 2. MOMENTUM & RSI (Maks 20 Puan)
    rsi = son['RSI']
    if 50 < rsi < 70:
        puan += 20
        rapor.append("✅ RSI Güçlü Bölgede (+20)")
    elif 30 <= rsi <= 50:
        puan += 10
        rapor.append("⚠️ RSI Toparlanıyor (+10)")
    elif rsi < 30:
        puan += 15
        rapor.append("🔥 RSI Aşırı Satım - Tepki Beklentisi (+15)")
    else: # > 70
        puan += 0
        rapor.append("⛔ RSI Aşırı Şişmiş - Riskli (0)")

    # 3. MACD SİNYALİ (Maks 20 Puan)
    if son['MACD'] > son['SIGNAL']:
        puan += 20
        rapor.append("✅ MACD Al Sinyalinde (+20)")
    else:
        rapor.append("🔻 MACD Sat Sinyalinde (0)")

    # 4. HACİM / PARA AKIŞI (Maks 20 Puan)
    if son.get('CMF', 0) > 0.05:
        puan += 20
        rapor.append("💰 Güçlü Para Girişi (+20)")
    elif son.get('CMF', 0) > 0:
        puan += 10
        rapor.append("💵 Zayıf Para Girişi (+10)")
    else:
        rapor.append("💸 Para Çıkışı Var (0)")

    # 5. BOLLINGER KONUMU (Maks 10 Puan)
    # Fiyat alt banda yakınsa alım fırsatı olabilir
    bb_konum = (son['Close'] - son['BB_LOWER']) / (son['BB_UPPER'] - son['BB_LOWER'])
    if bb_konum < 0.2:
        puan += 10
        rapor.append("✅ Fiyat Alt Banda Yakın - Destek (+10)")
    elif bb_konum > 0.8:
        rapor.append("⛔ Fiyat Üst Banda Yakın - Direnç (0)")
    else:
        puan += 5
        rapor.append("ℹ️ Fiyat Orta Bantta (+5)")

    return puan, rapor

# --- VERİ ÇEKME ---
def verileri_cek(symbol, period):
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 50: return None

        # İndikatör Hesaplamaları
        df['RSI'] = df.ta.rsi(length=14)
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            df.rename(columns={df.columns[-3]: 'MACD', df.columns[-1]: 'SIGNAL'}, inplace=True)
        
        for sayi in [21, 50, 144, 200]:
            df[f'EMA_{sayi}'] = df.ta.ema(length=sayi)

        bbands = df.ta.bbands(length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)

        st_ind = df.ta.supertrend(length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        df['CMF'] = df.ta.cmf(length=20)
        return df
    except: return None

if st.sidebar.button("KARNEYİ ÇIKAR 🚀"):
    with st.spinner('Yapay zeka sınav kağıdını okuyor...'):
        df = verileri_cek(hisse_kodu, periyot)
        
        if df is None:
            st.error("Veri bulunamadı!")
        else:
            son = df.iloc[-1]
            puan, rapor_detay = puan_hesapla(df)

            # --- KARNE GÖRÜNÜMÜ ---
            st.markdown("### 📝 GENEL DEĞERLENDİRME")
            
            # Puan Renkleri ve Mesajı
            if puan >= 80:
                renk = "green"
                mesaj = "GÜÇLÜ AL 🚀"
                not_harfi = "AA"
            elif puan >= 60:
                renk = "blue"
                mesaj = "AL (Pozitif) 📈"
                not_harfi = "BA"
            elif puan >= 40:
                renk = "orange"
                mesaj = "TUT / NÖTR ⚖️"
                not_harfi = "CC"
            else:
                renk = "red"
                mesaj = "SAT / RİSKLİ 🔻"
                not_harfi = "FF"

            # Büyük Puan Göstergesi
            col_puan, col_detay = st.columns([1, 2])
            
            with col_puan:
                st.markdown(f"""
                <div style="text-align: center; border: 4px solid {renk}; padding: 20px; border-radius: 10px;">
                    <h1 style="color:{renk}; font-size: 60px; margin:0;">{puan}</h1>
                    <h3 style="margin:0;">/ 100</h3>
                    <h2 style="color:{renk};">{mesaj}</h2>
                    <h1>Not: {not_harfi}</h1>
                </div>
                """, unsafe_allow_html=True)
            
            with col_detay:
                st.subheader("Hisse Neden Bu Puanı Aldı?")
                for madde in rapor_detay:
                    st.write(madde)

            st.divider()

            # --- STANDART GRAFİK ---
            st.subheader(f"📊 {hisse_kodu} Grafiği")
            plot_df = df.iloc[-150:]
            add_plots = []
            if 'SuperTrend' in plot_df.columns:
                renkler = ['green' if x == 1 else 'red' for x in plot_df['TrendYon']]
                add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=10, color=renkler))
            
            if 'EMA_200' in plot_df.columns:
                add_plots.append(mpf.make_addplot(plot_df['EMA_200'], color='purple', width=2))

            fig, axlist = mpf.plot(plot_df, type='candle', style='yahoo', 
                                   addplot=add_plots, volume=True, 
                                   panel_ratios=(4,1), returnfig=True, 
                                   title=f"{hisse_kodu} Fiyatı: {son['Close']:.2f}", figsize=(12,6))
            st.pyplot(fig)
