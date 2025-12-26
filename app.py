import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

# --- 1. AYARLAR & PREMIUM TASARIM ---
st.set_page_config(
    page_title="ProTrade Premium",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💎"
)

# CSS İLE MODERN VE TEMİZ GÖRÜNÜM
st.markdown("""
<style>
    /* Genel Arka Plan (Daha Yumuşak Lacivert) */
    .stApp { background-color: #0F172A; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    
    /* Premium Başlık */
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.2rem;
        margin-bottom: 25px;
    }
    
    /* Bilgi Kartları (Glass Effect) */
    .info-box {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: transform 0.2s;
    }
    .info-box:hover { transform: translateY(-2px); border-color: #38bdf8; }
    
    .box-label { color: #94A3B8; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .box-value { color: #F8FAFC; font-size: 1.6rem; font-weight: 700; margin: 5px 0; }
    .box-sub { font-size: 0.9rem; font-weight: 500; }
    
    /* Karne Puanı */
    .score-badge {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white; padding: 5px 15px; border-radius: 20px;
        font-weight: bold; font-size: 1.2rem; display: inline-block;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
    }
    
    /* Tablo Tasarımı */
    .perf-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
    .perf-table th { color: #94A3B8; border-bottom: 1px solid #334155; padding: 8px; text-align: center; }
    .perf-table td { color: #E2E8F0; padding: 8px; text-align: center; font-weight: 600; border-bottom: 1px solid #1e293b; }
    
    /* Buton */
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6, #06b6d4);
        color: white; border: none; border-radius: 8px; font-weight: 600;
        padding: 12px 20px; transition: opacity 0.3s;
    }
    .stButton>button:hover { opacity: 0.9; }
    
    /* Tablar */
    .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #334155; }
    .stTabs [aria-selected="true"] { color: #38bdf8 !important; border-bottom: 2px solid #38bdf8 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. HESAPLAMA MOTORU ---

def fibonacci_levels(df):
    max_p = df['High'].max()
    min_p = df['Low'].min()
    diff = max_p - min_p
    return [max_p, max_p - 0.236*diff, max_p - 0.382*diff, max_p - 0.5*diff, max_p - 0.618*diff, min_p]

def karne_hesapla(df):
    puan = 0
    notlar = []
    try:
        son = df.iloc[-1]
        
        # 1. Trend (25 Puan)
        if son['TrendYon'] == 1:
            puan += 25
            notlar.append("✅ Trend Yükselişte (+25)")
        else:
            notlar.append("🔻 Trend Düşüşte (0)")

        # 2. RSI (20 Puan)
        rsi = son.get('RSI', 50)
        if 40 <= rsi <= 70:
            puan += 20
            notlar.append("✅ RSI İdeal Bölgede (+20)")
        elif rsi < 30:
            puan += 10
            notlar.append("⚠️ RSI Ucuz (Tepki Beklentisi) (+10)")
        else:
            notlar.append("🔻 RSI Zayıf/Şişkin (0)")

        # 3. MACD (20 Puan)
        if son['MACD'] > son['SIGNAL']:
            puan += 20
            notlar.append("✅ MACD Pozitif (+20)")
        else:
            notlar.append("🔻 MACD Negatif (0)")

        # 4. Hareketli Ortalamalar (20 Puan)
        if son['Close'] > son.get('EMA_55', 999999):
            puan += 20
            notlar.append("✅ Fiyat EMA 55 Üzerinde (+20)")
        else:
            notlar.append("🔻 Fiyat EMA 55 Altında (0)")

        # 5. Para Akışı (15 Puan)
        if son.get('MFI', 50) > 50:
            puan += 15
            notlar.append("✅ Para Girişi Var (+15)")
        else:
            notlar.append("🔻 Para Çıkışı Var (0)")
            
    except: pass
    return puan, notlar

def verileri_getir(symbol, period):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
        df.index = df.index.tz_localize(None)
        
        # İndikatörler
        df['RSI'] = df.ta.rsi(close=df['Close'], length=14)
        for ema in [8, 13, 21, 55, 200]:
            df[f'EMA_{ema}'] = df.ta.ema(close=df['Close'], length=ema)
            
        st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'], length=10, multiplier=3)
        if st_ind is not None:
            df['SuperTrend'] = st_ind[st_ind.columns[0]]
            df['TrendYon'] = st_ind[st_ind.columns[1]]

        bbands = df.ta.bbands(close=df['Close'], length=20, std=2)
        if bbands is not None:
            df = df.join(bbands)
            df.rename(columns={df.columns[-3]: 'BB_LOWER', df.columns[-1]: 'BB_UPPER'}, inplace=True)
            
        macd = df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = df.join(macd)
            cols = df.columns
            df.rename(columns={cols[-3]: 'MACD', cols[-1]: 'SIGNAL'}, inplace=True)
        
        df['MFI'] = df.ta.mfi(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], length=14)

        return df
    except: return None

# --- 3. YAN MENÜ ---
with st.sidebar:
    st.markdown("<h3 style='color: #38bdf8; text-align: center;'>PROTRADE PREMIUM</h3>", unsafe_allow_html=True)
    st.markdown("---")
    piyasa = st.selectbox("BORSA", ["🇹🇷 BIST (TL)", "🇺🇸 ABD (USD)"])
    varsayilan = "THYAO" if "BIST" in piyasa else "NVDA"
    kod_giris = st.text_input("HİSSE KODU", varsayilan)
    periyot_secimi = st.selectbox("PERİYOT", ["1 Yıllık", "6 Aylık", "3 Aylık"], index=0)
    zaman_map = {"1 Yıllık": "1y", "6 Aylık": "6mo", "3 Aylık": "3mo"}
    st.write("")
    analiz_butonu = st.button("ANALİZ ET 🚀", use_container_width=True)

# --- 4. ANA EKRAN ---
if analiz_butonu:
    ham_kod = kod_giris.upper().strip().replace(".IS", "")
    sembol = f"{ham_kod}.IS" if "BIST" in piyasa else ham_kod
    para_birimi = "₺" if "BIST" in piyasa else "$"

    with st.spinner('Analiz yapılıyor...'):
        df = verileri_getir(sembol, zaman_map[periyot_secimi])
        
        if df is None:
            st.error("❌ Veri bulunamadı. Lütfen hisse kodunu kontrol edin.")
        else:
            son = df.iloc[-1]
            puan, notlar = karne_hesapla(df)
            
            # ÜST BAŞLIK
            st.markdown(f'<div class="main-header">{ham_kod} FİNANSAL RAPOR</div>', unsafe_allow_html=True)
            
            # --- METRİKLER (3 ŞIK KUTU) ---
            c1, c2, c3 = st.columns([1.2, 1, 1])
            
            # KUTU 1: FİYAT VE GEÇMİŞ
            with c1:
                degisim = ((son['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
                renk_degisim = "#4ade80" if degisim > 0 else "#f87171"
                
                st.markdown(f"""
                <div class="info-box">
                    <div class="box-label">SON FİYAT</div>
                    <div class="box-value">{son['Close']:.2f} {para_birimi}</div>
                    <div class="box-sub" style="color:{renk_degisim}">%{degisim:.2f} (Günlük)</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Geçmiş Performans (Tıklayınca Açılır)
                try:
                    p_ret = {}
                    for p_label, days in {'1 Hafta':5, '1 Ay':21, '3 Ay':63}.items():
                        if len(df) > days:
                            ret = ((son['Close'] - df.iloc[-days]['Close']) / df.iloc[-days]['Close']) * 100
                            color = "#4ade80" if ret > 0 else "#f87171"
                            p_ret[p_label] = f"<span style='color:{color}'>%{ret:.1f}</span>"
                        else: p_ret[p_label] = "-"
                    
                    with st.expander("📅 Geçmiş Getiriler"):
                        st.markdown(f"""
                        <table class="perf-table">
                            <tr><th>1 Hafta</th><th>1 Ay</th><th>3 Ay</th></tr>
                            <tr><td>{p_ret['1 Hafta']}</td><td>{p_ret['1 Ay']}</td><td>{p_ret['3 Ay']}</td></tr>
                        </table>
                        """, unsafe_allow_html=True)
                except: pass

            # KUTU 2: KARNE PUANI
            with c2:
                renk_puan = "linear-gradient(90deg, #10b981, #34d399)" if puan >= 70 else "linear-gradient(90deg, #f59e0b, #fbbf24)" if puan >= 50 else "linear-gradient(90deg, #ef4444, #f87171)"
                st.markdown(f"""
                <div class="info-box">
                    <div class="box-label">TEKNİK PUAN</div>
                    <div style="margin: 10px 0;">
                        <span style="background: {renk_puan}; color: white; padding: 5px 15px; border-radius: 15px; font-weight: bold; font-size: 1.5rem;">{puan}/100</span>
                    </div>
                    <div class="box-sub">Yapay Zeka Skoru</div>
                </div>
                """, unsafe_allow_html=True)

            # KUTU 3: TREND
            with c3:
                trend_durum = "YÜKSELİŞ" if son['TrendYon'] == 1 else "DÜŞÜŞ"
                trend_renk = "#4ade80" if son['TrendYon'] == 1 else "#f87171"
                st.markdown(f"""
                <div class="info-box">
                    <div class="box-label">ANA TREND</div>
                    <div class="box-value" style="color: {trend_renk}">{trend_durum}</div>
                    <div class="box-sub">SuperTrend</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")

            # --- SEKMELER ---
            tab_grafik, tab_veri, tab_karne = st.tabs(["📊 GRAFİK & ANALİZ", "🔢 TEKNİK VERİLER", "📝 KARNE DETAYI"])

            with tab_grafik:
                col_ayar, col_cizim = st.columns([1, 4])
                
                with col_ayar:
                    st.markdown("##### 🛠️ Göstergeler")
                    opt_ema = st.checkbox("EMA (8-13-21)", value=True)
                    opt_bb = st.checkbox("Bollinger Bantları", value=False)
                    opt_super = st.checkbox("SuperTrend", value=True)
                    opt_fib = st.checkbox("Fibonacci Seviyeleri", value=False)
                    
                    st.markdown("---")
                    st.caption(f"**Yorum:**\nFiyat EMA ortalamalarının {'üzerinde, trend pozitif.' if son['Close'] > son['EMA_21'] else 'altında, trend baskılanıyor.'}")

                with col_cizim:
                    plot_len = min(len(df), 200)
                    plot_df = df.iloc[-plot_len:]
                    add_plots = []
                    
                    if opt_ema:
                        add_plots.append(mpf.make_addplot(plot_df['EMA_8'], color='#fcd34d', width=1))
                        add_plots.append(mpf.make_addplot(plot_df['EMA_13'], color='#fb923c', width=1))
                        add_plots.append(mpf.make_addplot(plot_df['EMA_21'], color='#f87171', width=1.5))
                    
                    if opt_bb:
                        add_plots.append(mpf.make_addplot(plot_df['BB_UPPER'], color='gray', linestyle='--', width=0.8))
                        add_plots.append(mpf.make_addplot(plot_df['BB_LOWER'], color='gray', linestyle='--', width=0.8))

                    if opt_super:
                        colors = ['#4ade80' if x==1 else '#f87171' for x in plot_df['TrendYon']]
                        add_plots.append(mpf.make_addplot(plot_df['SuperTrend'], type='scatter', markersize=20, color=colors))
                    
                    # FİBONACCİ (HATA ÇIKARMAYAN YENİ YÖNTEM)
                    if opt_fib:
                        fibs = fibonacci_levels(plot_df)
                        for level in fibs:
                            # Hlines yerine addplot kullanıyoruz - BU KESİN ÇÖZÜM
                            add_plots.append(mpf.make_addplot([level]*len(plot_df), color='white', linestyle='-.', width=0.5, alpha=0.5))

                    fig, _ = mpf.plot(plot_df, type='candle', style='nightclouds', 
                                      addplot=add_plots, volume=True, 
                                      panel_ratios=(4, 1), 
                                      returnfig=True, figsize=(12, 7), tight_layout=True)
                    st.pyplot(fig)

            with tab_veri:
                st.dataframe(df.tail(10)[['Close', 'High', 'Low', 'RSI', 'MACD']].style.format("{:.2f}"))

            with tab_karne:
                st.markdown("#### Karne Detayları")
                for n in notlar:
                    if "✅" in n: st.success(n)
                    elif "⚠️" in n: st.warning(n)
                    else: st.error(n)
else:
    st.markdown('<div class="main-header">PROTRADE PREMIUM</div>', unsafe_allow_html=True)
    st.info("👈 Başlamak için sol menüden bir hisse seçin ve 'ANALİZ ET' butonuna basın.")
