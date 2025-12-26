import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 1. AYARLAR ---
st.set_page_config(
    page_title="ProTrade Scanner",
    layout="wide",
    page_icon="📡"
)

# CSS (Modern Tablo Görünümü)
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    
    .header-style {
        font-size: 2rem; font-weight: 800; color: #38bdf8;
        text-align: center; margin-bottom: 20px;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }
    
    /* Tablo Stili */
    div[data-testid="stDataFrame"] {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 10px;
    }
    
    .success-box {
        padding: 15px; background-color: rgba(16, 185, 129, 0.2); 
        border: 1px solid #10b981; border-radius: 8px; color: #d1fae5;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white; border: none; font-weight: bold; padding: 10px 20px;
        border-radius: 8px; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. TARAMA MOTORU ---

def verileri_analiz_et(semboller, strateji):
    sonuclar = []
    
    # İlerleme Çubuğu
    bar = st.progress(0)
    step = 1 / len(semboller)
    
    for i, sembol in enumerate(semboller):
        try:
            # Veri Çek (Son 1 Yıl yeterli)
            ticker = yf.Ticker(sembol)
            df = ticker.history(period="1y")
            
            if df.empty: continue
            
            # --- İNDİKATÖRLERİ HESAPLA ---
            close = df['Close']
            
            # RSI
            rsi = df.ta.rsi(close=close, length=14).iloc[-1]
            
            # MACD
            macd = df.ta.macd(close=close)
            macd_val = macd[macd.columns[0]].iloc[-1]
            macd_signal = macd[macd.columns[2]].iloc[-1] # Hist
            
            # EMA'lar
            ema50 = df.ta.ema(close=close, length=50).iloc[-1]
            ema200 = df.ta.ema(close=close, length=200).iloc[-1]
            
            # SuperTrend
            st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=close, length=10, multiplier=3)
            trend_yon = st_ind[st_ind.columns[1]].iloc[-1] # 1=Up, -1=Down
            
            fiyat = close.iloc[-1]
            
            # --- STRATEJİ SORGULAMA ---
            uygun = False
            neden = ""
            
            # 1. STRATEJİ: SENİN İSTEDİĞİN (RSI > 50 & MACD Pozitif & Trend Yukarı)
            if strateji == "Momentum Canavarı 🚀":
                if rsi > 50 and macd_val > 0 and trend_yon == 1:
                    uygun = True
                    neden = f"RSI Güçlü ({rsi:.1f}) + MACD Pozitif"

            # 2. STRATEJİ: GOLDEN CROSS (EMA 50 > EMA 200)
            elif strateji == "Golden Cross (Altın Kesişim) 🏆":
                if ema50 > ema200 and fiyat > ema50:
                    uygun = True
                    neden = "EMA 50, EMA 200'ün üzerinde (Uzun Vade Ralli)"
            
            # 3. STRATEJİ: DİP AVCISI (RSI < 30)
            elif strateji == "Dip Avcısı 🎣":
                if rsi < 30:
                    uygun = True
                    neden = f"Aşırı Satım Bölgesi (RSI: {rsi:.1f})"

            # 4. STRATEJİ: GÜVENLİ LİMAN (Sadece Trend)
            elif strateji == "Güvenli Trend Takibi 🛡️":
                if trend_yon == 1 and fiyat > ema50:
                    uygun = True
                    neden = "SuperTrend AL + Fiyat Ortalamaların Üstünde"

            # Eğer kriterlere uyuyorsa listeye ekle
            if uygun:
                sonuclar.append({
                    "Hisse": sembol.replace(".IS", ""),
                    "Fiyat": f"{fiyat:.2f}",
                    "RSI": f"{rsi:.1f}",
                    "Sinyal Nedeni": neden,
                    "Durum": "✅ EŞLEŞTİ"
                })
                
        except: pass
        bar.progress(min((i + 1) * step, 1.0))
        
    bar.empty()
    return pd.DataFrame(sonuclar)

# --- 3. ARAYÜZ ---

with st.sidebar:
    st.header("📡 ProTrade Scanner")
    st.info("Burası senin hisse filtreleme merkezin. Grafikler yok, sadece sonuçlar var.")
    
    # 1. Borsa Seçimi
    piyasa = st.selectbox("Pazar Seç", ["🇹🇷 BIST 30 (Özet)", "🇹🇷 BIST 100 (Popüler)", "🇺🇸 ABD Teknoloji"])
    
    # Hisse Listeleri (Otomatik Tanımlı)
    if piyasa == "🇹🇷 BIST 30 (Özet)":
        hisseler = ["AKBNK.IS", "ASELS.IS", "BIMAS.IS", "EKGYO.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KOZAL.IS", "KRDMD.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"]
    elif piyasa == "🇹🇷 BIST 100 (Popüler)":
        # Örnek olarak popülerleri ekledim, liste uzatılabilir
        hisseler = ["THYAO.IS", "ASELS.IS", "SASA.IS", "HEKTS.IS", "EREGL.IS", "TUPRS.IS", "FROTO.IS", "KCHOL.IS", "GARAN.IS", "AKBNK.IS", "ASTOR.IS", "KONTR.IS", "GUBRF.IS", "KOZAL.IS", "ODAS.IS", "PETKM.IS"]
    else:
        hisseler = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC"]
        
    # Kullanıcı Ekstra Hisse Ekleyebilir
    ekstra = st.text_input("Listeye Özel Hisse Ekle (Örn: MGROS)", "")
    if ekstra:
        sembol_ek = f"{ekstra.upper()}.IS" if "BIST" in piyasa else ekstra.upper()
        hisseler.append(sembol_ek)
    
    st.markdown("---")
    
    # 2. Strateji Seçimi
    st.markdown("### 🧠 Strateji Seç")
    strateji = st.radio(
        "Hangi Kriterlere Göre Tarayalım?",
        [
            "Momentum Canavarı 🚀", 
            "Golden Cross (Altın Kesişim) 🏆", 
            "Dip Avcısı 🎣", 
            "Güvenli Trend Takibi 🛡️"
        ]
    )
    
    st.caption(f"**Seçilen Strateji Detayı:**\n{strateji}")
    
    if strateji == "Momentum Canavarı 🚀":
        st.warning("👉 Kriterler: RSI > 50 VE MACD > 0 VE Trend Yukarı")
    elif strateji == "Golden Cross (Altın Kesişim) 🏆":
        st.warning("👉 Kriterler: EMA 50, EMA 200'ü yukarı kesmiş.")
    elif strateji == "Dip Avcısı 🎣":
        st.warning("👉 Kriterler: RSI < 30 (Aşırı Ucuz)")

    st.markdown("---")
    tara_butonu = st.button("TARAMAYI BAŞLAT 🔍")

# --- 4. ANA EKRAN ---
st.markdown('<div class="header-style">BORSA TARAMA VE SİNYAL MERKEZİ</div>', unsafe_allow_html=True)

if tara_butonu:
    st.markdown(f"### 🔎 Analiz Ediliyor: {len(hisseler)} Hisse taranıyor...")
    
    with st.spinner('Yapay zeka stratejileri uyguluyor... Lütfen bekleyin.'):
        sonuc_df = verileri_analiz_et(hisseler, strateji)
        
    if not sonuc_df.empty:
        st.success(f"🎉 TARAMA TAMAMLANDI! Kriterlere uyan **{len(sonuc_df)}** hisse bulundu.")
        
        # Sonuçları Tablo Olarak Göster
        st.dataframe(
            sonuc_df, 
            use_container_width=True,
            hide_index=True
        )
        
        # Detaylı Kart Görünümü (İsteğe Bağlı)
        st.markdown("---")
        st.subheader("💡 Tespit Edilen Fırsatlar")
        
        cols = st.columns(3)
        for idx, row in sonuc_df.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="success-box">
                    <h3 style="margin:0; color:white;">{row['Hisse']}</h3>
                    <div style="font-size:1.5rem; font-weight:bold;">{row['Fiyat']}</div>
                    <hr style="border-color:#10b981;">
                    <div>RSI: {row['RSI']}</div>
                    <div style="font-size:0.8rem; margin-top:5px;">{row['Sinyal Nedeni']}</div>
                </div>
                <br>
                """, unsafe_allow_html=True)
                
    else:
        st.error("😔 Malesef şu anki piyasa koşullarında bu stratejiye uyan hiçbir hisse bulunamadı.")
        st.info("💡 İpucu: Stratejiyi değiştirip tekrar deneyebilirsin (Örn: 'Güvenli Trend Takibi' daha çok sonuç verebilir).")

else:
    # Başlangıç Ekranı
    col1, col2 = st.columns([1, 2])
    with col2:
        st.markdown("""
        ### 👋 Hoş Geldin!
        Burası senin **Sinyal Komuta Merkezin.**
        
        1. Sol taraftan **Pazar** seç (BIST 30 vs.)
        2. Bir **Strateji** belirle (Örn: Momentum Canavarı)
        3. **TARAMAYI BAŞLAT** butonuna bas.
        
        Robot senin yerine tek tek bütün hisselere bakacak ve sadece **kriterlere uyanları** önüne getirecek.
        """)
