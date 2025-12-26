import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 1. AYARLAR ---
st.set_page_config(
    page_title="ProTrade BIST Scanner",
    layout="wide",
    page_icon="🇹🇷"
)

# CSS STİLİ (Modern & Türk Bayrağı Temalı)
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    
    .header-style {
        font-size: 2.2rem; font-weight: 800; color: #ef4444;
        text-align: center; margin-bottom: 25px;
        text-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
    }
    
    .success-box {
        padding: 15px; background-color: rgba(6, 182, 212, 0.15); 
        border: 1px solid #06b6d4; border-radius: 10px; color: #cffafe;
        transition: transform 0.2s;
    }
    .success-box:hover { transform: scale(1.02); }
    
    .stButton>button {
        background: linear-gradient(90deg, #ef4444, #b91c1c);
        color: white; font-weight: bold; padding: 12px; border-radius: 8px; border:none;
        font-size: 1.1rem;
    }
    .stButton>button:hover { opacity: 0.9; }
    
    /* Tablo */
    div[data-testid="stDataFrame"] { background-color: #1e293b; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. LİSTELER (BIST ÖZEL) ---

# BIST 30 (En Büyükler)
bist30 = [
    "AKBNK.IS", "ALARK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRSAN.IS", "DOAS.IS", "EKGYO.IS", "ENKAI.IS",
    "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "KRDMD.IS",
    "ODAS.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS",
    "TUPRS.IS", "YKBNK.IS"
]

# BIST 50 (30 + 20 Ek)
bist50_ek = [
    "AEFES.IS", "AGHOL.IS", "AKCNS.IS", "AKSA.IS", "AKSEN.IS", "ALBRK.IS", "ASUZU.IS", "AYDEM.IS", "BIOEN.IS", "CCOLA.IS",
    "CIMSA.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS", "ENJSA.IS", "EUREN.IS", "GESAN.IS", "GLYHO.IS", "GWIND.IS", "HALKB.IS",
    "ISGYO.IS", "ISMEN.IS", "KARSN.IS", "KMPUR.IS", "KORDS.IS", "KOZAA.IS", "MGROS.IS", "OTKAR.IS", "QUAGR.IS", "SKBNK.IS",
    "SOKM.IS", "TAVHL.IS", "TKFEN.IS", "TTKOM.IS", "TTRAK.IS", "ULKER.IS", "VAKBN.IS", "VESTL.IS"
]
bist50 = list(set(bist30 + bist50_ek)) # Birleştir ve kopyaları sil

# BIST 100 (50 + 50 Ek)
bist100_ek = [
    "AKFGY.IS", "AKFYE.IS", "ALFAS.IS", "BAGFS.IS", "BERA.IS", "BFREN.IS", "BIENY.IS", "BOBET.IS", "BRYAT.IS", "BUCIM.IS",
    "CANTE.IS", "CWENE.IS", "ECZYT.IS", "EUPWR.IS", "GENIL.IS", "GOKNR.IS", "IMASM.IS", "IPEKE.IS", "ISDMR.IS", "IZMDC.IS",
    "KCAER.IS", "KONYA.IS", "KZBGY.IS", "MAVI.IS", "MIATK.IS", "PENTA.IS", "PSGYO.IS", "REEDR.IS", "SDTTR.IS", "SMRTG.IS",
    "TABGD.IS", "TSKB.IS", "TUKAS.IS", "VESBE.IS", "YEOTK.IS", "YYLGD.IS", "ZOREN.IS", "ADGYO.IS", "AHLGY.IS", "ANSGR.IS"
]
bist100 = list(set(bist50 + bist100_ek))

# BIST TÜMÜ (Genişletilmiş - Popüler Yan Tahtalar Dahil)
# BIST 100'e ek olarak piyasada çok işlem gören diğer hisseler
yan_tahtalar = [
    "FONET.IS", "VBTYZ.IS", "ONCSM.IS", "CVKMD.IS", "TARKM.IS", "EBEBK.IS", "KBORU.IS", "MEKAG.IS", "HATSN.IS", "MARBL.IS",
    "MHRGY.IS", "BORLS.IS", "GIPTA.IS", "KZGYO.IS", "BYDNR.IS", "ENERY.IS", "BAYRK.IS", "IZENR.IS", "TATEN.IS", "OFSYM.IS",
    "KALES.IS", "FZLGY.IS", "ATAKP.IS", "KTLEV.IS", "FORTE.IS", "PASEU.IS", "A1CAP.IS", "CVENR.IS", "GRTRK.IS", "EKSUN.IS",
    "PLTUR.IS", "SOKE.IS", "TEZOL.IS", "YUNSA.IS", "VKGYO.IS", "TURSG.IS", "TRGYO.IS", "TMPOL.IS", "TIRE.IS", "SNGYO.IS",
    "SELEC.IS", "RYGYO.IS", "PRKME.IS", "PARSN.IS", "OZKGY.IS", "NTHOL.IS", "NETAS.IS", "LOGO.IS", "LINK.IS", "KRVGD.IS",
    "KLGYO.IS", "KAREL.IS", "JANTS.IS", "HUNER.IS", "HLGYO.IS", "GEDIK.IS", "GENTS.IS", "EMKEL.IS", "DGATE.IS", "DERIM.IS"
]
bist_tumu = list(set(bist100 + yan_tahtalar))

# --- 3. TARAMA MOTORU ---

def verileri_analiz_et(semboller, strateji):
    sonuclar = []
    
    # İlerleme Çubuğu
    durum_kutusu = st.empty()
    bar = st.progress(0)
    toplam = len(semboller)
    
    start_time = time.time()
    
    for i, sembol in enumerate(semboller):
        durum_kutusu.info(f"🔎 Taranıyor: **{sembol.replace('.IS', '')}** ({i+1}/{toplam})")
        
        try:
            ticker = yf.Ticker(sembol)
            df = ticker.history(period="6mo")
            
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
                if rsi > 50 and macd_val > 0 and trend_yon == 1:
                    uygun = True
                    neden = f"RSI Güçlü ({rsi:.1f}) + MACD Al"

            elif strateji == "Golden Cross 🏆":
                if ema200 > 0 and ema50 > ema200 and fiyat > ema50:
                    uygun = True
                    neden = "Altın Kesişim (50 > 200)"

            elif strateji == "Dip Avcısı 🎣":
                if rsi < 30:
                    uygun = True
                    neden = f"Aşırı Ucuz (RSI: {rsi:.1f})"

            elif strateji == "Güvenli Liman 🛡️":
                if trend_yon == 1 and fiyat > ema50:
                    uygun = True
                    neden = "Trend Yukarı + Fiyat EMA Üstü"

            if uygun:
                sonuclar.append({
                    "Hisse": sembol.replace(".IS", ""),
                    "Fiyat": f"{fiyat:.2f} ₺",
                    "RSI": f"{rsi:.1f}",
                    "Sinyal": neden
                })
                
        except: pass
        bar.progress(min((i + 1) / toplam, 1.0))
    
    elapsed = time.time() - start_time
    durum_kutusu.empty()
    bar.empty()
    return pd.DataFrame(sonuclar), elapsed

# --- 4. YAN MENÜ ---
with st.sidebar:
    st.header("🇹🇷 PROTRADE BIST")
    st.markdown("---")
    
    # Borsa Filtresi
    kategori = st.radio("Hisse Grubu Seç:", [
        "BIST 30 (Devler)",
        "BIST 50 (Büyükler)",
        "BIST 100 (Ana Pazar)",
        "BIST TÜMÜ (Genişletilmiş)"
    ])
    
    if "30" in kategori:
        secili_liste = bist30
        bilgi = "En büyük 30 şirket taranacak."
    elif "50" in kategori:
        secili_liste = bist50
        bilgi = "En büyük 50 şirket taranacak."
    elif "100" in kategori:
        secili_liste = bist100
        bilgi = "BIST 100 endeksinin tamamı taranacak."
    else:
        secili_liste = bist_tumu
        bilgi = f"BIST 100 + Popüler Yan Tahtalar ({len(bist_tumu)} Hisse) taranacak."
    
    st.info(f"ℹ️ {bilgi}")
    
    # Özel Ekleme
    ekstra = st.text_input("Listeye Özel Ekle (Örn: BFREN)", "")
    if ekstra:
        s = f"{ekstra.upper()}.IS"
        if s not in secili_liste: secili_liste.append(s)
    
    st.markdown("---")
    
    # Strateji
    st.markdown("### 🧠 Strateji")
    strateji = st.radio("Sinyal Tipi:", [
        "Momentum Canavarı 🚀",
        "Güvenli Liman 🛡️",
        "Dip Avcısı 🎣",
        "Golden Cross 🏆"
    ])
    
    st.markdown("---")
    baslat = st.button("TARAMAYI BAŞLAT 🔥", use_container_width=True)

# --- 5. ANA EKRAN ---
st.markdown('<div class="header-style">BORSA İSTANBUL TARAMA MERKEZİ</div>', unsafe_allow_html=True)

if baslat:
    st.success(f"🚀 **{kategori}** analizi başladı! Toplam **{len(secili_liste)}** hisse inceleniyor...")
    
    df_sonuc, sure = verileri_analiz_et(secili_liste, strateji)
    
    if not df_sonuc.empty:
        st.balloons()
        st.markdown(f"### 🎉 Tarama Bitti! ({sure:.1f} saniye sürdü)")
        st.success(f"Toplam **{len(df_sonuc)}** adet fırsat bulundu.")
        
        # Sonuç Tablosu
        st.dataframe(df_sonuc, use_container_width=True, hide_index=True)
        
        # Kartlar
        st.markdown("### 💡 Fırsat Kartları")
        cols = st.columns(3)
        for idx, row in df_sonuc.iterrows():
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
        st.warning("😔 Aradığınız kriterlere uygun hisse bulunamadı. Stratejiyi değiştirmeyi deneyin.")
        
else:
    c1, c2 = st.columns([1, 2])
    with c2:
        st.info("👈 Başlamak için sol menüden Hisse Grubunu ve Stratejini seç.")
