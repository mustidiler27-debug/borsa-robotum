import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 1. AYARLAR ---
st.set_page_config(
    page_title="ProTrade Scanner V32",
    layout="wide",
    page_icon="📡"
)

# CSS STİLİ
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    
    .header-style {
        font-size: 2.2rem; font-weight: 800; color: #38bdf8;
        text-align: center; margin-bottom: 25px;
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
    }
    
    .success-box {
        padding: 15px; background-color: rgba(6, 182, 212, 0.15); 
        border: 1px solid #06b6d4; border-radius: 10px; color: #cffafe;
        transition: transform 0.2s;
    }
    .success-box:hover { transform: scale(1.02); }
    
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #06b6d4);
        color: white; font-weight: bold; padding: 12px; border-radius: 8px; border:none;
    }
    
    /* Tablo */
    div[data-testid="stDataFrame"] { background-color: #1e293b; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. TARAMA MOTORU ---

def verileri_analiz_et(semboller, strateji):
    sonuclar = []
    
    # İlerleme Çubuğu ve Bilgi
    durum_kutusu = st.empty()
    bar = st.progress(0)
    toplam = len(semboller)
    
    for i, sembol in enumerate(semboller):
        # Durum Güncelle
        durum_kutusu.caption(f"Taraniyor: {sembol} ({i+1}/{toplam})")
        
        try:
            # Veri Çek
            ticker = yf.Ticker(sembol)
            df = ticker.history(period="6mo") # 6 ay yeterli, daha hızlı olur
            
            if df.empty: continue
            
            # İndikatörler
            close = df['Close']
            rsi = df.ta.rsi(close=close, length=14).iloc[-1]
            
            # MACD
            macd = df.ta.macd(close=close)
            macd_val = macd[macd.columns[0]].iloc[-1]
            
            # EMA
            ema50 = df.ta.ema(close=close, length=50).iloc[-1]
            ema200 = df.ta.ema(close=close, length=200).iloc[-1] if len(df) > 200 else 0
            
            # SuperTrend
            st_ind = df.ta.supertrend(high=df['High'], low=df['Low'], close=close, length=10, multiplier=3)
            trend_yon = st_ind[st_ind.columns[1]].iloc[-1] # 1=Up, -1=Down
            
            fiyat = close.iloc[-1]
            uygun = False
            neden = ""
            
            # --- STRATEJİLER ---
            
            if strateji == "Momentum Canavarı 🚀":
                # RSI > 50 ve MACD Pozitif ve Trend Yukarı
                if rsi > 50 and macd_val > 0 and trend_yon == 1:
                    uygun = True
                    neden = f"RSI Güçlü ({rsi:.1f}) + MACD Al + Trend Yukarı"

            elif strateji == "Golden Cross 🏆":
                # EMA 50 > EMA 200 (Sadece uzun veri varsa)
                if ema200 > 0 and ema50 > ema200 and fiyat > ema50:
                    uygun = True
                    neden = "EMA 50 > EMA 200 (Golden Cross)"

            elif strateji == "Dip Avcısı 🎣":
                # RSI < 30
                if rsi < 30:
                    uygun = True
                    neden = f"Aşırı Satım (RSI: {rsi:.1f})"

            elif strateji == "Trend Takipçisi 🛡️":
                # Sadece SuperTrend AL ve Fiyat > EMA50
                if trend_yon == 1 and fiyat > ema50:
                    uygun = True
                    neden = "SuperTrend AL + Fiyat Ortalamaların Üstünde"

            if uygun:
                sonuclar.append({
                    "Hisse": sembol.replace(".IS", ""),
                    "Fiyat": f"{fiyat:.2f}",
                    "RSI": f"{rsi:.1f}",
                    "Sinyal": neden
                })
                
        except: pass
        
        # Bar İlerle
        bar.progress(min((i + 1) / toplam, 1.0))
        
    durum_kutusu.empty()
    bar.empty()
    return pd.DataFrame(sonuclar)

# --- 3. LİSTELER (GENİŞLETİLMİŞ) ---

# BIST 100 TAM LİSTE (Güncel Bileşenler)
bist100_list = [
    "AEFES.IS", "AGHOL.IS", "AGROT.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS",
    "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ASUZU.IS", "AYDEM.IS", "BAGFS.IS", "BERA.IS", "BFREN.IS",
    "BIENY.IS", "BIMAS.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS",
    "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS",
    "EUPWR.IS", "EUREN.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GOKNR.IS", "GUBRF.IS", "GWIND.IS",
    "HALKB.IS", "HEKTS.IS", "IMASM.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS", "ISMEN.IS", "IZMDC.IS", "KARSN.IS",
    "KCAER.IS", "KCHOL.IS", "KMPUR.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KZBGY.IS",
    "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", "PSGYO.IS",
    "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS",
    "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS",
    "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YYLGD.IS", "ZOREN.IS"
]

# ABD DEVLER LİGİ (S&P 50 Top 50)
usa_top50 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "LLY", "V",
    "TSM", "UNH", "AVGO", "JPM", "XOM", "WMT", "JNJ", "MA", "PG", "HD",
    "MRK", "COST", "ABBV", "CVX", "CRM", "AMD", "PEP", "KO", "BAC", "ACN",
    "NFLX", "LIN", "MCD", "DIS", "ADBE", "NKE", "INTC", "T", "VZ", "PFE",
    "CSCO", "CMCSA", "TMUS", "WFC", "BA", "INTU", "QCOM", "IBM", "GE", "AMGN"
]

# --- 4. YAN MENÜ ---
with st.sidebar:
    st.header("📡 ProTrade Scanner")
    st.markdown("---")
    
    # Pazar Seçimi
    pazar = st.selectbox("PAZAR SEÇİMİ", ["🇹🇷 BIST 100 (Tam Liste)", "🇺🇸 ABD Top 50 (Devler)", "⭐ BIST 30 (Hızlı)"])
    
    # Liste Atama
    if pazar == "🇹🇷 BIST 100 (Tam Liste)":
        sembol_listesi = bist100_list
        mesaj = "BIST 100 Endeksinin tamamı (100 Hisse) taranacak."
    elif pazar == "🇺🇸 ABD Top 50 (Devler)":
        sembol_listesi = usa_top50
        mesaj = "Amerika'nın en büyük 50 şirketi taranacak."
    else:
        sembol_listesi = bist100_list[:30] # İlk 30
        mesaj = "BIST 30 (En Hacimli) hisseler taranacak."
        
    st.caption(f"ℹ️ {mesaj}")
    
    # Özel Hisse Ekleme
    ekstra = st.text_input("Listeye Özel Ekle (Örn: BJKAS)", "")
    if ekstra:
        s = f"{ekstra.upper()}.IS" if "BIST" in pazar else ekstra.upper()
        if s not in sembol_listesi: sembol_listesi.append(s)
    
    st.markdown("---")
    
    # Strateji
    st.markdown("### 🧠 Strateji")
    strateji = st.radio("Sinyal Türü:", [
        "Momentum Canavarı 🚀",
        "Trend Takipçisi 🛡️",
        "Dip Avcısı 🎣",
        "Golden Cross 🏆"
    ])
    
    st.markdown("---")
    baslat = st.button("TARAMAYI BAŞLAT 🔥", use_container_width=True)

# --- 5. ANA EKRAN ---
st.markdown('<div class="header-style">BORSA TARAMA MERKEZİ</div>', unsafe_allow_html=True)

if baslat:
    st.info(f"🚀 Analiz Başladı! {len(sembol_listesi)} hisse için veriler çekiliyor... (Ortalama süre: 1-2 dakika)")
    
    # Analiz Fonksiyonunu Çağır
    sonuc_df = verileri_analiz_et(sembol_listesi, strateji)
    
    if not sonuc_df.empty:
        st.success(f"🎉 SONUÇ: {len(sonuc_df)} adet hisse kriterlere uydu!")
        
        # Tablo
        st.dataframe(sonuc_df, use_container_width=True, hide_index=True)
        
        # Kartlar
        st.markdown("### 💡 Fırsat Kartları")
        cols = st.columns(3)
        for idx, row in sonuc_df.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="success-box">
                    <h3 style="margin:0; color:white;">{row['Hisse']}</h3>
                    <div style="font-size:1.5rem; font-weight:bold; color:#67e8f9;">{row['Fiyat']}</div>
                    <hr style="border-color:#06b6d4; opacity:0.3;">
                    <div style="font-size:0.9rem;">{row['Sinyal']}</div>
                </div>
                <br>
                """, unsafe_allow_html=True)
    else:
        st.warning("😔 Hiçbir hisse bu stratejiye uymadı. Piyasa koşulları zorlu olabilir veya 'Dip Avcısı' gibi farklı bir strateji deneyebilirsin.")

else:
    c1, c2 = st.columns([1, 2])
    with c2:
        st.markdown("""
        ### 👋 Nasıl Çalışır?
        1. **Pazarı Seç:** BIST 100, ABD Devleri veya BIST 30.
        2. **Stratejini Belirle:**
           - **Momentum Canavarı:** Yükseliş gücü yüksek olanlar.
           - **Dip Avcısı:** Çok düşmüş, tepki vermesi muhtemel olanlar.
           - **Trend Takipçisi:** Güvenli liman arayanlar.
        3. **Başlat:** Robot senin yerine yüzlerce grafiğe bakar ve sonuçları getirir.
        """)
