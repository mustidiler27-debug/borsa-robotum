import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Borsa Analiz v4", layout="wide")

st.title("🤖 Borsa Terminatörü V4.0")
st.markdown("""
**Hisse Senedi Yapay Zeka Analiz Terminali**
*İnteraktif Grafikler | Formasyon Taraması | Trend Analizi*
""")

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Kontrol Paneli")
hisse_kodu = st.sidebar.text_input("Hisse Kodu (Örn: THYAO.IS)", "THYAO.IS")
periyot = st.sidebar.selectbox("Veri Periyodu", ["6mo", "1y", "2y", "5y"], index=1)
st.sidebar.info("Not: BIST hisseleri için sonuna .IS eklemeyi unutmayın (Örn: GARAN.IS).")

def verileri_cek(symbol, period):
    try:
        # Veriyi indir
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        
        # MultiIndex düzeltmesi (Yahoo Finance yeni sürüm hatası için)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or len(df) < 50:
            return None

        # --- İNDİKATÖRLER ---
        # 1. RSI & MACD
        df['RSI'] = df.ta.rsi(length=14)
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            # Sütun isimlerini standartlaştıralım
            df.rename(columns={df.columns[-3]: 'MACD', df.columns[-1]: 'SIGNAL'}, inplace=True)

        # 2. Fibonacci EMA'ları
        for sayi in [21, 50, 144, 200]:
            df[f'EMA_{sayi}'] = df.ta.ema(length=sayi)

        # 3. Bollinger & SuperTrend
        bbands = df.ta.bbands(length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)

        st_ind = df.ta.supertrend(length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]] # 1: UP, -1: DOWN

        # 4. Para Akışı (ACMF)
        df['CMF'] = df.ta.cmf(length=20)
        
        return df
    except Exception as e:
        return None

if st.sidebar.button("ANALİZ ET 🚀"):
    with st.spinner(f'{hisse_kodu} verileri işleniyor...'):
        df = verileri_cek(hisse_kodu, periyot)
        
        if df is None:
            st.error("❌ HATA: Veri çekilemedi. Hisse kodunu kontrol edin (Örn: ASELS.IS).")
        else:
            son = df.iloc[-1]
            onceki = df.iloc[-2]

            # --- 1. ÜST BİLGİ KARTLARI ---
            col1, col2, col3, col4 = st.columns(4)
            
            # Fiyat
            fiyat_renk = "normal"
            delta_val = float(son['Close'] - onceki['Close'])
            col1.metric("Son Fiyat", f"{son['Close']:.2f} TL", f"{delta_val:.2f}")

            # Trend
            yon = "YÜKSELİŞ 🔼" if son.get('TrendYon', 0) == 1 else "DÜŞÜŞ 🔻"
            col2.metric("SuperTrend", yon)

            # RSI
            rsi_val = son['RSI']
            durum_rsi = "Nötr 😐"
            if rsi_val > 70: durum_rsi = "Aşırı Alım (Sat!) 🔴"
            elif rsi_val < 30: durum_rsi = "Aşırı Satım (Al!) 🟢"
            col3.metric("RSI (14)", f"{rsi_val:.2f}", durum_rsi)

            # Para Akışı
            cmf_val = son.get('CMF', 0)
            para = "Giriş Var 💰" if cmf_val > 0 else "Çıkış Var 💸"
            col4.metric("Para Akışı", para)

            st.divider()

            # --- 2. GRAFİK BÖLÜMÜ ---
            st.subheader(f"📊 {hisse_kodu} Teknik Grafiği")
            
            # Son 150 günü çizelim
            plot_df = df.iloc[-150:]

            # Grafiğe eklenecek çizgiler
            add_plots = []
            
            # EMA'lar
            if 'EMA_144' in plot_df.columns:
                add_plots.append(mpf.make_addplot(plot_df['EMA_144'], color='blue', width=1.5))
            if 'EMA_200' in plot_df.columns:
                add_plots.append(mpf.make_addplot(plot_df['EMA_200'], color='purple', width=2))
            
            # SuperTrend (Yeşil/Kırmızı Çizgi)
            if 'SuperTrend' in plot_df.columns:
                renkler = ['green' if x == 1 else 'red' for x in plot_df['TrendYon']]
                add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=10, color=renkler))

            # ACMF Paneli (En alt)
            if 'CMF' in plot_df.columns:
                add_plots.append(mpf.make_addplot(plot_df['CMF'], panel=2, color='teal', ylabel='Para Akışı', type='bar'))

            # Grafiği Çiz
            fig, axlist = mpf.plot(plot_df, type='candle', style='yahoo', 
                                   addplot=add_plots, volume=True, 
                                   panel_ratios=(4,1,1), returnfig=True, 
                                   title=f"{hisse_kodu}", figsize=(12,8))
            st.pyplot(fig)

            st.divider()

            # --- 3. DETAYLI KARNE (SİNYALLER) ---
            st.subheader("🕵️‍♂️ Yapay Zeka Tespitleri")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.info("🛠️ Mum & Trend Analizi")
                # Mum Formasyonları
                if (onceki['Close'] < onceki['Open']) and (son['Close'] > son['Open']) and \
                   (son['Open'] < onceki['Close']) and (son['Close'] > onceki['Open']):
                    st.success("🐂 YUTAN BOĞA: Güçlü dönüş sinyali tespit edildi.")
                
                govde = abs(son['Close'] - son['Open'])
                mum_boyu = son['High'] - son['Low']
                if mum_boyu > 0 and govde <= mum_boyu * 0.1:
                    st.warning("🕯️ DOJI: Piyasada kararsızlık hakim.")
                
                # Trend
                if son['Close'] > son.get('EMA_200', 0):
                    st.success("✅ ANA TREND: Pozitif (Fiyat 200 günlüğün üzerinde).")
                else:
                    st.error("🔻 ANA TREND: Negatif (Fiyat 200 günlüğün altında).")

            with c2:
                st.info("📐 Teknik & İndikatör Analizi")
                # Sıkışma
                if 'BB_UPPER' in df.columns:
                    bb_width = (son['BB_UPPER'] - son['BB_LOWER']) / son['BB_UPPER']
                    if bb_width < 0.10:
                        st.warning("⚠️ SIKIŞMA ALARMI: Bollinger bantları çok daraldı. Sert patlama yakındır!")
                
                # MACD
                if 'MACD' in df.columns and son['MACD'] > son['SIGNAL']:
                    st.success("✅ MACD: AL bölgesinde.")
                else:
                    st.error("❌ MACD: SAT bölgesinde.")

else:
    st.write("👈 Lütfen sol menüden hisse kodunu girip butona basın.")
