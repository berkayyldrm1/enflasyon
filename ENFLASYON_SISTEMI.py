import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from bs4 import BeautifulSoup
import re
import calendar
from datetime import datetime, timedelta
import time
import json
import hashlib
from github import Github
from io import BytesIO
import zipfile
import base64
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai
import PIL.Image
import requests
from prophet import Prophet
import feedparser
from fpdf import FPDF
import shutil
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. AYARLAR VE TEMA YÖNETİMİ ---
st.set_page_config(
    page_title="Enflasyon Monitörü",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="expanded"
)

# --- Session State ile Tema Hafızası ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'  # Varsayılan açılış modu

# --- SIDEBAR AYARLARI ---
with st.sidebar:
    st.title("Ayarlar")
    # Toggle değeri session_state'den gelir
    is_dark = st.toggle("🌙 Karanlık Mod", value=(st.session_state.theme == 'dark'))

    # Eğer kullanıcı butona basarsa state güncellenir ve sayfa yenilenir
    if is_dark and st.session_state.theme == 'light':
        st.session_state.theme = 'dark'
        st.rerun()
    elif not is_dark and st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
        st.rerun()


# --- CSS MOTORU (KESİN ÇÖZÜM V3: RENK ZORLAMA) ---
def apply_theme():
    # --- TEMA RENK AYARLARI (Sadece Arka Plan ve Menüler İçin) ---
    if st.session_state.theme == 'dark':
        colors = {
            "bg": "#0E1117",
            "sidebar": "#262730",
            "text": "#FAFAFA",
            "input_bg": "#1A1C24",
            "input_border": "#4A4A4A",
            "card_bg": "#1A1C24",
            "border_color": "#414141"
        }
        st.session_state.plotly_template = "plotly_dark"
    else:
        colors = {
            "bg": "#FFFFFF",
            "sidebar": "#F0F2F6",
            "text": "#31333F",
            "input_bg": "#FFFFFF",
            "input_border": "#D1D5DB",
            "card_bg": "#FFFFFF",
            "border_color": "#e2e8f0"
        }
        st.session_state.plotly_template = "plotly_white"

    # --- CSS MOTORU ---
    final_css = f"""
    <style>
        /* GİZLEMELER */
        header[data-testid="stHeader"] {{ display: none !important; }}
        [data-testid="stDecoration"] {{ display: none !important; }}
        [data-testid="collapsedControl"] {{ display: none !important; }}
        .block-container {{ padding-top: 1rem !important; }}
        footer {{ visibility: hidden; }}
        .stDeployButton {{ display: none; }}

        /* GENEL SAYFA YAPISI (Temaya Göre Değişir) */
        .stApp {{ background-color: {colors['bg']}; color: {colors['text']}; }}
        section[data-testid="stSidebar"] {{ background-color: {colors['sidebar']}; border-right: 1px solid {colors['border_color']}; }}
        h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .stRadio label {{ color: {colors['text']} !important; }}

        /* INPUT VE SELECTBOX (Temaya Göre Değişir) */
        .stTextInput input, .stNumberInput input {{
            background-color: {colors['input_bg']} !important;
            color: {colors['text']} !important;
            border: 1px solid {colors['input_border']} !important;
        }}

        /* DROPDOWN VE TOAST (Temaya Göre Değişir) */
        div[data-baseweb="popover"], div[data-baseweb="toast"] {{ background-color: #FFFFFF !important; border: 1px solid #ccc !important; }}
        div[data-baseweb="popover"] li, div[data-baseweb="toast"] div {{ color: #000000 !important; }}

        /* TABLOLAR (Temaya Göre Değişir) */
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
            background-color: {colors['card_bg']} !important;
            border: 1px solid {colors['border_color']} !important;
        }}
        [data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td {{ color: {colors['text']} !important; }}
        [data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th {{
            color: {colors['text']} !important;
            background-color: {colors['sidebar']} !important;
        }}

        /* ============================================================ */
        /* --- BUTONLARIN HEPSİ (SİYAH ÇERÇEVE, BEYAZ ZEMİN, SİYAH YAZI) --- */
        /* ============================================================ */

        /* 1. Tüm Buton Tipleri İçin Ortak Kural */
        div.stButton > button, 
        div.stFormSubmitButton > button,
        [data-testid="stDownloadButton"] button {{
            background-color: #ffffff !important;   /* Zemin BEYAZ */
            color: #000000 !important;              /* Yazı SİYAH */
            border: 2px solid #000000 !important;   /* Çerçeve SİYAH ve KALIN */
            border-radius: 8px !important;
            font-weight: bold !important;
        }}

        /* 2. Buton İçindeki Yazıları (p etiketlerini) Zorla Siyah Yap */
        div.stButton > button p,
        div.stFormSubmitButton > button p,
        [data-testid="stDownloadButton"] button * {{
            color: #000000 !important;
        }}

        /* 3. Mouse Üzerine Gelince (Hover) */
        div.stButton > button:hover,
        div.stFormSubmitButton > button:hover,
        [data-testid="stDownloadButton"] button:hover {{
            background-color: #f0f0f0 !important;   /* Hafif Griye Çalsın */
            border-color: #000000 !important;
            color: #000000 !important;
        }}

        /* 4. Primary (Kırmızı/Turuncu) Butonları da Zorla Beyaz Yap */
        div.stButton > button[kind="primary"] {{
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 2px solid #000000 !important;
        }}

        /* ============================================================ */

        /* METRİKLER */
        .metric-card {{ background: {colors['card_bg']} !important; border: 1px solid {colors['border_color']} !important; }}
        .metric-val, div[data-testid="stMetricValue"] {{ color: {colors['text']} !important; }}

    </style>
    """
    st.markdown(final_css, unsafe_allow_html=True)

# Temayı Uygula
apply_theme()

# --- ADMIN AYARI ---
ADMIN_USERS = ["fatih", "berkay", "mehmet"]
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])


# --- KUR ÇEKME FONKSİYONU ---
@st.cache_data(ttl=1800)
def get_exchange_rates():
    rates = {"USD": 0.0, "EUR": 0.0, "GA": 0.0}
    try:
        url_tcmb = "https://www.tcmb.gov.tr/kurlar/today.xml"
        res = requests.get(url_tcmb, timeout=5)
        soup = BeautifulSoup(res.content, 'xml')
        rates["USD"] = float(soup.find(attrs={"CurrencyCode": "USD"}).BanknoteSelling.text)
        rates["EUR"] = float(soup.find(attrs={"CurrencyCode": "EUR"}).BanknoteSelling.text)
    except:
        pass

    try:
        url_gold = "https://bigpara.hurriyet.com.tr/altin/gram-altin-fiyati/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res_gold = requests.get(url_gold, headers=headers, timeout=5)
        soup_gold = BeautifulSoup(res_gold.content, 'html.parser')
        fiyat_text = soup_gold.select_one("span.value").text
        temiz_fiyat = fiyat_text.replace(".", "").replace(",", ".").strip()
        rates["GA"] = float(temiz_fiyat)
    except Exception as e:
        if rates["USD"] > 0:
            rates["GA"] = (2700 * rates["USD"]) / 31.10
    return rates


# --- 2. GITHUB & VERİ MOTORU ---
EXCEL_DOSYASI = "TUFE_Konfigurasyon.xlsx"
FIYAT_DOSYASI = "Fiyat_Veritabani.xlsx"
USERS_DOSYASI = "kullanicilar.json"
ACTIVITY_DOSYASI = "user_activity.json"
SEPETLER_DOSYASI = "user_baskets.json"
SAYFA_ADI = "Madde_Sepeti"


# --- PDF RAPOR MOTORU ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'ENFLASYON DURUM RAPORU', 0, 1, 'C')
        self.set_y(10)
        self.set_font('Arial', 'B', 8)
        self.set_text_color(0, 0, 0)
        self.ln(5)
        self.line(10, 25, 200, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Enflasyon Monitoru - Sayfa {self.page_no()}', 0, 0, 'C')


def create_pdf_report(text_content, filename="Rapor.pdf"):
    pdf = PDFReport()
    pdf.add_page()

    def clean_text_for_pdf(text):
        if not text: return ""
        replacements = {
            'ı': 'i', 'İ': 'I', '\u0131': 'i',
            'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U',
            'ş': 's', 'Ş': 'S',
            'ö': 'o', 'Ö': 'O',
            'ç': 'c', 'Ç': 'C',
            'â': 'a', 'î': 'i', 'û': 'u',
            '₺': 'TL', '“': '"', '”': '"', '’': "'", '‘': "'", '–': '-', '—': '-', '…': '...'
        }
        temp_text = text
        for tr, en in replacements.items():
            temp_text = temp_text.replace(tr, en)
        return temp_text.encode('latin-1', 'replace').decode('latin-1')

    final_text = clean_text_for_pdf(text_content)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 7, final_text)
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "Bu rapor piyasa analiz sistemi tarafindan otomatik olarak olusturulmustur.")
    return pdf.output(dest='S').encode('latin-1', 'ignore')


# --- HABER MOTORU ---
def get_market_sentiment():
    rss_url = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
    try:
        feed = feedparser.parse(rss_url)
        headlines = [entry.title for entry in feed.entries[:10]]
        news_text = "\n".join([f"- {h}" for h in headlines])

        prompt = f"""
        Aşağıdaki Türkiye gündemindeki son dakika haber başlıklarını bir Piyasa Stratejisti gibi tara.
        HABERLER:
        {news_text}
        GÖREVİN:
        1. Bu genel gündem maddeleri arasında ekonomiyi, gıda fiyatlarını veya piyasa riskini etkileyebilecek bir olay var mı?
        2. Yoksa genel gündem siyaset/magazin ağırlıklı mı?
        3. "Piyasa Havası"nı tek kelimeyle tanımla (Örn: Nötr, Gergin, İyimser, Belirsiz).
        4. En kritik 1 haberi (varsa ekonomiyle ilgili) seç ve yorumla.
        Çıktıyı kısa, net ve madde madde ver.
        """
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text, headlines
    except Exception as e:
        return f"Haberler alınamadı: {str(e)}", []


# --- GITHUB İŞLEMLERİ ---
def get_github_repo():
    try:
        return Github(st.secrets["github"]["token"]).get_repo(st.secrets["github"]["repo_name"])
    except:
        return None


def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def github_json_oku(dosya_adi):
    repo = get_github_repo()
    if not repo: return {}
    try:
        c = repo.get_contents(dosya_adi, ref=st.secrets["github"]["branch"])
        return json.loads(c.decoded_content.decode("utf-8"))
    except:
        return {}


def github_json_yaz(dosya_adi, data, mesaj="Update JSON"):
    repo = get_github_repo()
    if not repo: return False
    try:
        content = json.dumps(data, indent=4)
        try:
            c = repo.get_contents(dosya_adi, ref=st.secrets["github"]["branch"])
            repo.update_file(c.path, mesaj, content, c.sha, branch=st.secrets["github"]["branch"])
        except:
            repo.create_file(dosya_adi, mesaj, content, branch=st.secrets["github"]["branch"])
        return True
    except:
        return False


# --- HIZLANDIRILMIŞ (CACHED) VERİ OKUMA ---
@st.cache_data(ttl=60, show_spinner=False)
def github_excel_oku(dosya_adi, sayfa_adi=None):
    repo = get_github_repo()
    if not repo: return pd.DataFrame()
    try:
        c = repo.get_contents(dosya_adi, ref=st.secrets["github"]["branch"])
        if sayfa_adi:
            df = pd.read_excel(BytesIO(c.decoded_content), sheet_name=sayfa_adi, dtype=str)
        else:
            df = pd.read_excel(BytesIO(c.decoded_content), dtype=str)
        return df
    except:
        return pd.DataFrame()


def github_excel_guncelle(df_yeni, dosya_adi):
    repo = get_github_repo()
    if not repo: return "Repo Yok"
    try:
        try:
            c = repo.get_contents(dosya_adi, ref=st.secrets["github"]["branch"])
            old = pd.read_excel(BytesIO(c.decoded_content), dtype=str)
            yeni_tarih = str(df_yeni['Tarih'].iloc[0])
            old = old[~((old['Tarih'].astype(str) == yeni_tarih) & (old['Kod'].isin(df_yeni['Kod'])))]
            final = pd.concat([old, df_yeni], ignore_index=True)
        except:
            c = None;
            final = df_yeni
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            final.to_excel(w, index=False, sheet_name='Fiyat_Log')
        msg = f"Data Update"
        if c:
            repo.update_file(c.path, msg, out.getvalue(), c.sha, branch=st.secrets["github"]["branch"])
        else:
            repo.create_file(dosya_adi, msg, out.getvalue(), branch=st.secrets["github"]["branch"])
        return "OK"
    except Exception as e:
        return str(e)


# --- RESMİ ENFLASYON & PROPHET (CACHED) ---
def get_official_inflation():
    api_key = st.secrets.get("evds", {}).get("api_key")
    if not api_key: return None, "API Key Yok"
    start_date = (datetime.now() - timedelta(days=365)).strftime("%d-%m-%Y")
    end_date = datetime.now().strftime("%d-%m-%Y")
    url = f"https://evds2.tcmb.gov.tr/service/evds/series=TP.FG.J0&startDate={start_date}&endDate={end_date}&type=json&key={api_key}"
    try:
        res = requests.get(url)
        data = res.json()
        if "items" in data:
            df_evds = pd.DataFrame(data["items"])
            df_evds = df_evds[['Tarih', 'TP_FG_J0']]
            df_evds.columns = ['Tarih', 'Resmi_TUFE']
            df_evds['Tarih'] = pd.to_datetime(df_evds['Tarih'] + "-01", format="%Y-%m-%d")
            df_evds['Resmi_TUFE'] = pd.to_numeric(df_evds['Resmi_TUFE'], errors='coerce')
            return df_evds, "OK"
        return None, "Veri Yapısı Hatası"
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def predict_inflation_prophet(df_trend):
    try:
        df_p = df_trend.rename(columns={'Tarih': 'ds', 'TÜFE': 'y'})
        m = Prophet(daily_seasonality=True, yearly_seasonality=False)
        m.fit(df_p)
        future = m.make_future_dataframe(periods=90)
        forecast = m.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    except Exception as e:
        st.error(f"Prophet Hatası: {str(e)}")
        return pd.DataFrame()


# --- YARDIMCI FONKSİYONLAR ---
def update_user_status(username):
    try:
        activity = github_json_oku(ACTIVITY_DOSYASI)
        activity[username] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        github_json_yaz(ACTIVITY_DOSYASI, activity, f"Activity: {username}")
    except:
        pass


def send_verification_email(to_email, code):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]

        # Görünen İsim Ayarı
        display_name = "Enflasyon Monitörü"
        from_header = f"{display_name} <{sender_email}>"

        subject = "🔐 Doğrulama Kodun"

        body = f"""
        Merhaba,

        Enflasyon Monitörü'ne kayıt olmak için doğrulama kodun:

        CODE: {code}

        Bu kodu kimseyle paylaşma.
        Sevgiler.
        """

        msg = MIMEMultipart()
        msg['From'] = from_header
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

def send_reset_email(to_email, username):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        app_url = "https://enflasyon-gida.streamlit.app/"
        reset_link = f"{app_url}?reset_user={username}"
        subject = "🔐 Şifre Sıfırlama - Enflasyon Monitörü"
        body = f"Merhaba {username},\n\nŞifreni sıfırlamak için:\n{reset_link}\n\nSevgiler."
        msg = MIMEMultipart()
        msg['From'] = f"Enflasyon Monitörü <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True, "Sıfırlama bağlantısı gönderildi."
    except Exception as e:
        return False, f"Mail Hatası: {str(e)}"


def send_notification_email(to_email, product_name, current_price, target_price):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        subject = f"🔔 FİYAT DÜŞTÜ: {product_name}"

        body = f"""
        Merhaba,

        Takip ettiğin "{product_name}" ürününün fiyatı düştü!

        📉 Şu Anki Fiyat: {current_price:.2f} TL
        🎯 Hedeflediğin Fiyat: {target_price:.2f} TL

        Fırsatı kaçırmamak için sisteme giriş yapabilirsin.
        Sevgiler,
        Enflasyon Monitörü Ekibi
        """

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Mail Hatası: {e}")
        return False

def github_user_islem(action, username=None, password=None, email=None):
    users_db = github_json_oku(USERS_DOSYASI)
    if action == "login":
        if username in users_db:
            stored_data = users_db[username]
            stored_pass = stored_data if isinstance(stored_data, str) else stored_data.get("password")
            if stored_pass == hash_password(password): return True, "Başarılı"
        return False, "Hatalı Kullanıcı Adı veya Şifre"
    elif action == "register":
        if username in users_db: return False, "Kullanıcı adı alınmış."
        users_db[username] = {"password": hash_password(password), "email": email,
                              "created_at": datetime.now().strftime("%Y-%m-%d")}
        github_json_yaz(USERS_DOSYASI, users_db, f"New User: {username}")
        return True, "Kayıt Başarılı"
    elif action == "forgot_password":
        found_user = None
        for u, data in users_db.items():
            if isinstance(data, dict) and data.get("email") == email: found_user = u; break
        if found_user: return send_reset_email(email, found_user)
        return False, "Kayıtlı e-posta bulunamadı."
    elif action == "update_password":
        if username in users_db:
            user_data = users_db[username]
            if isinstance(user_data, str): user_data = {"email": "", "created_at": ""}
            user_data["password"] = hash_password(password)
            users_db[username] = user_data
            if github_json_yaz(USERS_DOSYASI, users_db,
                               f"Password Reset: {username}"): return True, "Şifreniz güncellendi."
        return False, "Kullanıcı bulunamadı."
    return False, "Hata"


# --- SCRAPER (FİYAT ÇEKİCİ) ---
def temizle_fiyat(t):
    if not t: return None
    t = str(t).replace('TL', '').replace('₺', '').strip()
    t = t.replace('.', '').replace(',', '.') if ',' in t and '.' in t else t.replace(',', '.')
    try:
        return float(re.sub(r'[^\d.]', '', t))
    except:
        return None


def kod_standartlastir(k): return str(k).replace('.0', '').strip().zfill(7)


def fiyat_bul_siteye_gore(soup, url):
    fiyat = 0;
    kaynak = "";
    domain = url.lower() if url else ""
    if "migros" in domain:
        garbage = ["sm-list-page-item", ".horizontal-list-page-items-container", "app-product-carousel",
                   ".similar-products", "div.badges-wrapper"]
        for g in garbage:
            for x in soup.select(g): x.decompose()
        main_wrapper = soup.select_one(".name-price-wrapper")
        if main_wrapper:
            for sel, k in [(".price.subtitle-1", "Migros(N)"), (".single-price-amount", "Migros(S)"),
                           ("#sale-price, .sale-price", "Migros(I)")]:
                if el := main_wrapper.select_one(sel):
                    if val := temizle_fiyat(el.get_text()): return val, k
        if fiyat == 0:
            if el := soup.select_one("fe-product-price .subtitle-1, .single-price-amount"):
                if val := temizle_fiyat(el.get_text()): fiyat = val; kaynak = "Migros(G)"
            if fiyat == 0:
                if el := soup.select_one("#sale-price"):
                    if val := temizle_fiyat(el.get_text()): fiyat = val; kaynak = "Migros(GI)"
    elif "cimri" in domain:
        for sel in ["div.rTdMX", ".offer-price", "div.sS0lR", ".min-price-val"]:
            if els := soup.select(sel):
                vals = [v for v in [temizle_fiyat(e.get_text()) for e in els] if v and v > 0]
                if vals:
                    if len(vals) > 4: vals.sort(); vals = vals[1:-1]
                    fiyat = sum(vals) / len(vals);
                    kaynak = f"Cimri({len(vals)})";
                    break
        if fiyat == 0:
            if m := re.findall(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:TL|₺)', soup.get_text()[:10000]):
                ff = sorted([temizle_fiyat(x) for x in m if temizle_fiyat(x)])
                if ff: fiyat = sum(ff[:max(1, len(ff) // 2)]) / max(1, len(ff) // 2); kaynak = "Cimri(Reg)"
    if fiyat == 0 and "migros" not in domain:
        for sel in [".product-price", ".price", ".current-price", "span[itemprop='price']"]:
            if el := soup.select_one(sel):
                if v := temizle_fiyat(el.get_text()): fiyat = v; kaynak = "Genel(CSS)"; break
    if fiyat == 0 and "migros" not in domain and "cimri" not in domain:
        if m := re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:TL|₺)', soup.get_text()[:5000]):
            if v := temizle_fiyat(m.group(1)): fiyat = v; kaynak = "Regex"
    return fiyat, kaynak


def html_isleyici(log_callback):
    repo = get_github_repo()
    if not repo: return "GitHub Bağlantı Hatası"
    log_callback("📂 Konfigürasyon okunuyor...")
    try:
        df_conf = github_excel_oku(EXCEL_DOSYASI, SAYFA_ADI)
        df_conf.columns = df_conf.columns.str.strip()
        kod_col = next((c for c in df_conf.columns if c.lower() == 'kod'), None)
        url_col = next((c for c in df_conf.columns if c.lower() == 'url'), None)
        ad_col = next((c for c in df_conf.columns if 'ad' in c.lower()), 'Madde adı')
        if not kod_col or not url_col: return "Hata: Excel sütunları eksik."
        df_conf['Kod'] = df_conf[kod_col].astype(str).apply(kod_standartlastir)
        url_map = {str(row[url_col]).strip(): row for _, row in df_conf.iterrows() if pd.notna(row[url_col])}
        veriler = [];
        islenen_kodlar = set()
        bugun = datetime.now().strftime("%Y-%m-%d");
        simdi = datetime.now().strftime("%H:%M")

        log_callback("✍️ Manuel fiyatlar kontrol ediliyor...")
        manuel_col = next((c for c in df_conf.columns if 'manuel' in c.lower()), None)
        ms = 0
        if manuel_col:
            for _, row in df_conf.iterrows():
                if pd.notna(row[manuel_col]) and str(row[manuel_col]).strip() != "":
                    try:
                        fiyat_man = float(row[manuel_col])
                        if fiyat_man > 0:
                            veriler.append({"Tarih": bugun, "Zaman": simdi, "Kod": row['Kod'], "Madde_Adi": row[ad_col],
                                            "Fiyat": fiyat_man, "Kaynak": "Manuel", "URL": row[url_col]})
                            islenen_kodlar.add(row['Kod']);
                            ms += 1
                    except:
                        pass
        if ms > 0: log_callback(f"✅ {ms} manuel fiyat alındı.")

        log_callback("📦 ZIP dosyaları taranıyor...")
        contents = repo.get_contents("", ref=st.secrets["github"]["branch"])
        zip_files = [c for c in contents if c.name.endswith(".zip") and c.name.startswith("Bolum")]
        hs = 0
        for zip_file in zip_files:
            log_callback(f"📂 Arşiv okunuyor: {zip_file.name}")
            try:
                blob = repo.get_git_blob(zip_file.sha)
                zip_data = base64.b64decode(blob.content)
                with zipfile.ZipFile(BytesIO(zip_data)) as z:
                    for file_name in z.namelist():
                        if not file_name.endswith(('.html', '.htm')): continue
                        with z.open(file_name) as f:
                            raw = f.read().decode("utf-8", errors="ignore")
                            soup = BeautifulSoup(raw, 'html.parser')
                            found_url = None
                            if c := soup.find("link", rel="canonical"): found_url = c.get("href")
                            if not found_url and (m := soup.find("meta", property="og:url")): found_url = m.get(
                                "content")
                            if found_url and str(found_url).strip() in url_map:
                                target = url_map[str(found_url).strip()]
                                if target['Kod'] in islenen_kodlar: continue
                                fiyat, kaynak = fiyat_bul_siteye_gore(soup, target[url_col])
                                if fiyat > 0:
                                    veriler.append({"Tarih": bugun, "Zaman": simdi, "Kod": target['Kod'],
                                                    "Madde_Adi": target[ad_col], "Fiyat": fiyat, "Kaynak": kaynak,
                                                    "URL": target[url_col]})
                                    islenen_kodlar.add(target['Kod']);
                                    hs += 1
            except Exception as e:
                log_callback(f"⚠️ Hata ({zip_file.name}): {str(e)}")

        if veriler:
            log_callback(f"💾 {len(veriler)} veri kaydediliyor...")
            return github_excel_guncelle(pd.DataFrame(veriler), FIYAT_DOSYASI)
        else:
            return "Veri bulunamadı."
    except Exception as e:
        return f"Hata: {str(e)}"


def check_alarms_and_notify(df_son_fiyatlar):
    alarms_db = github_json_oku("user_alarms.json")
    if not isinstance(alarms_db, list): return "Alarm veritabanı boş."

    updated = False
    sent_count = 0

    # DataFrame'den kod ve fiyat eşleşmesi (Son fiyat sütunu)
    # df_son_fiyatlar, analiz tablosundaki son verileri içermeli

    for alarm in alarms_db:
        # Sadece aktif ve henüz bildirim gitmemiş alarmlara bak
        if alarm.get("durum") == "aktif":
            kod = alarm.get("kod")
            target = float(alarm.get("hedef_fiyat"))

            # Ürünün güncel fiyatını bul
            row = df_son_fiyatlar[df_son_fiyatlar['Kod'] == kod]
            if not row.empty:
                # Son sütunu dinamik buluyoruz (tarih olan sütunların en sonuncusu)
                cols = [c for c in df_son_fiyatlar.columns if
                        c not in ['Kod', 'Ad', 'Grup', 'Madde_Adi', 'URL', 'Grup_Kodu', 'Agirlik_2025']]
                if cols:
                    last_price_col = cols[-1]  # En son tarihli sütun
                    current_price = float(row[last_price_col].values[0])

                    if current_price > 0 and current_price <= target:
                        # BİLDİRİM GÖNDER
                        if send_notification_email(alarm["email"], alarm["urun_adi"], current_price, target):
                            alarm["durum"] = "tamamlandi"  # Tekrar tekrar mail atmasın diye durumu değiştiriyoruz
                            updated = True
                            sent_count += 1

    if updated:
        github_json_yaz("user_alarms.json", alarms_db, "Alarm Notifications Sent")

    return f"{sent_count} adet alarm bildirimi gönderildi."

# --- DASHBOARD MODU ---
def dashboard_modu():
    bugun = datetime.now().strftime("%Y-%m-%d")
    df_f = github_excel_oku(FIYAT_DOSYASI)
    df_s = github_excel_oku(EXCEL_DOSYASI, SAYFA_ADI)

    # --- SIDEBAR ---
    with st.sidebar:
        user_upper = st.session_state['username'].upper()
        is_admin = st.session_state['username'] in ADMIN_USERS
        role_title = "SYSTEM ADMIN" if is_admin else "VERİ ANALİSTİ"

        # 1. Profil Kartı
        st.markdown(f"""
                <div style="background:white; border:1px solid #e2e8f0; border-radius:12px; padding:15px; text-align:center; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size:32px; margin-bottom:5px;">👤</div>
                    <div style="font-family:'Poppins'; font-weight:700; font-size:18px; color:#1e293b;">{user_upper}</div>
                    <div style="font-size:11px; text-transform:uppercase; color:#64748b; margin-top:4px;">{role_title}</div>
                </div>
            """, unsafe_allow_html=True)

        # 2. PİYASA GÖSTERGELERİ
        try:
            rates = get_exchange_rates()
            st.markdown(
                "<h3 style='color:#1e293b; font-size:14px; margin-bottom:10px; padding-left:5px;'>💱 PİYASA GÖSTERGELERİ</h3>",
                unsafe_allow_html=True)

            st.markdown(f"""
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-bottom:8px;">
                    <div style="background:white; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-size:10px; color:#64748b; font-weight:700;">USD/TRY</div>
                        <div style="font-size:15px; color:#0f172a; font-weight:800;">{rates['USD']:.2f} ₺</div>
                    </div>
                    <div style="background:white; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-size:10px; color:#64748b; font-weight:700;">EUR/TRY</div>
                        <div style="font-size:15px; color:#0f172a; font-weight:800;">{rates['EUR']:.2f} ₺</div>
                    </div>
                </div>
                <div style="background:white; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:center;">
                    <div style="font-size:10px; color:#64748b; font-weight:700;">GRAM ALTIN </div>
                    <div style="font-size:15px; color:#f59e0b; font-weight:800;">{rates['GA']:.2f} ₺</div>
                </div>
                <div style="text-align:right; font-size:9px; color:#94a3b8; margin-top:5px; margin-bottom:20px;">Veriler: TCMB</div>
                <div style="border-bottom:1px solid #e2e8f0; margin-bottom:20px;"></div>
                """, unsafe_allow_html=True)
        except:
            pass

        # 3. ADMIN PANEL
        if is_admin:
            st.markdown("<h3 style='color:#1e293b; font-size:16px;'>⚙️ Kontrol Paneli</h3>", unsafe_allow_html=True)
            st.markdown(
                "<div style='margin-bottom:10px; color:#64748b; font-size:12px; font-weight:bold;'>🟢 ÇEVRİMİÇİ EKİP</div>",
                unsafe_allow_html=True)

            users_db = github_json_oku(USERS_DOSYASI)
            activity_db = github_json_oku(ACTIVITY_DOSYASI)
            update_user_status(st.session_state['username'])

            user_list = []
            for u in users_db.keys():
                last_seen_str = activity_db.get(u, "2000-01-01 00:00:00")
                try:
                    last_seen = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
                except:
                    last_seen = datetime(2000, 1, 1)
                is_online = (datetime.now() - last_seen).total_seconds() < 300
                user_list.append({"name": u, "online": is_online})

            for u in sorted(user_list, key=lambda x: (not x['online'], x['name'] not in ADMIN_USERS, x['name'])):
                role_icon = "🛡️" if u['name'] in ADMIN_USERS else ""
                st.markdown(f"""
                        <div style="background:white; border:1px solid #e2e8f0; padding:8px; margin-bottom:4px; border-radius:6px; display:flex; justify-content:space-between; align-items:center;">
                            <span style="display:flex; align-items:center; color:#334155; font-size:12px; font-weight:600;">
                                <span style="height:6px; width:6px; border-radius:50%; display:inline-block; margin-right:8px; background-color:{'#22c55e' if u['online'] else '#cbd5e1'}; box-shadow:{'0 0 4px #22c55e' if u['online'] else 'none'};"></span>
                                {u['name']} {role_icon}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
            st.divider()

        # 4. Çıkış Butonu
        if st.button("Güvenli Çıkış", use_container_width=True):
            st.session_state['logged_in'] = False
            st.query_params.clear()
            st.rerun()

    # --- CSS: Global Styles (Aydınlık modda düzgün görünmesi için) ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Poppins:wght@400;600;800&family=JetBrains+Mono:wght@400&display=swap');
        .header-container { display: flex; justify-content: space-between; align-items: center; padding: 20px 30px; background: white; border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border-bottom: 4px solid #3b82f6; }
        .app-title { font-family: 'Poppins', sans-serif; font-size: 32px; font-weight: 800; letter-spacing: -1px; background: linear-gradient(90deg, #0f172a 0%, #3b82f6 50%, #0f172a 100%); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: shine 5s linear infinite; }
        @keyframes shine { to { background-position: 200% center; } }
        .update-btn-container button { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important; color: white !important; font-weight: 700 !important; font-size: 16px !important; border-radius: 12px !important; height: 60px !important; border: none !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3); transition: all 0.3s ease !important; animation: pulse 2s infinite; }
        .update-btn-container button:hover { transform: scale(1.02); box-shadow: 0 10px 25px rgba(37, 99, 235, 0.5); animation: none; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(37, 99, 235, 0); } 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); } }
        .ticker-wrap { width: 100%; overflow: hidden; background: linear-gradient(90deg, #0f172a, #1e293b); color: white; padding: 12px 0; margin-bottom: 25px; border-radius: 12px; }
        .ticker { display: inline-block; animation: ticker 45s linear infinite; white-space: nowrap; }
        .ticker-item { display: inline-block; padding: 0 2rem; font-weight: 500; font-size: 14px; font-family: 'JetBrains Mono', monospace; }
        @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
        .bot-bubble { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 0 8px 8px 8px; margin-top: 15px; color: #1e3a8a; font-size: 14px; line-height: 1.5; }
        .bot-log { background: #1e293b; color: #4ade80; font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 15px; border-radius: 12px; height: 180px; overflow-y: auto; }
        #live_clock_js { font-family: 'JetBrains Mono', monospace; color: #2563eb; }

        /* Metric Card Styles */
        .metric-card { padding: 24px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.03); position: relative; overflow: hidden; transition: all 0.3s ease; }
        .metric-card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(59, 130, 246, 0.15); border-color: #3b82f6; }
        .metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 6px; height: 100%; }
        .card-blue::before { background: #3b82f6; } .card-purple::before { background: #8b5cf6; } .card-emerald::before { background: #10b981; } .card-orange::before { background: #f59e0b; }
        .metric-label { color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
        .metric-val { color: #1e293b; font-size: 36px; font-weight: 800; font-family: 'Poppins', sans-serif; letter-spacing: -1px; }
        .metric-val.long-text { font-size: 24px !important; line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER & LIVE CLOCK ---
    tr_time_start = datetime.now() + timedelta(hours=3)
    header_html = f"""
    <div class="header-container">
        <div class="app-title">Enflasyon Monitörü</div>
        <div style="text-align:right;">
            <div style="color:#64748b; font-size:12px; font-weight:600; margin-bottom:4px;">İSTANBUL, TR</div>
            <div id="live_clock_js" style="color:#0f172a; font-size:16px; font-weight:800; font-family:'JetBrains Mono', monospace;">{tr_time_start.strftime('%d %B %Y, %H:%M:%S')}</div>
        </div>
    </div>
    <script>
    function startClock() {{
        var clockElement = document.getElementById('live_clock_js');
        function update() {{
            var now = new Date();
            var options = {{ timeZone: 'Europe/Istanbul', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }};
            if (clockElement) {{ clockElement.innerHTML = now.toLocaleTimeString('tr-TR', options); }}
        }}
        setInterval(update, 1000); update(); 
    }}
    startClock();
    </script>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    if 'toast_shown' not in st.session_state:
        st.toast('Sistem Başarıyla Yüklendi! 🚀', icon='✅')
        st.session_state['toast_shown'] = True

    if is_admin:
        st.markdown('<div class="update-btn-container">', unsafe_allow_html=True)
        # --- MEVCUT KOD BLOKUNU BUL VE BUNUNLA DEĞİŞTİR ---
        if st.button("🚀 SİSTEMİ GÜNCELLE VE ANALİZ ET", type="primary", use_container_width=True):
            with st.status("Veri Tabanı Güncelleniyor...", expanded=True) as status:
                st.write("📡 GitHub bağlantısı kuruluyor...")
                time.sleep(0.5)
                st.write("📦 ZIP dosyaları taranıyor...")
                log_ph = st.empty()
                log_msgs = []

                def logger(m):
                    log_msgs.append(f"> {m}")
                    log_ph.markdown(f'<div class="bot-log">{"<br>".join(log_msgs)}</div>', unsafe_allow_html=True)

                res = html_isleyici(logger)
                status.update(label="İşlem Tamamlandı!", state="complete", expanded=False)

            if "OK" in res:
                # KRİTİK EKLEME: CACHE TEMİZLEME
                st.cache_data.clear()  # <--- BU SATIRI EKLE
                with st.spinner("🔔 Alarmlar kontrol ediliyor..."):
                    try:
                        # 1. Veriyi Taze Oku
                        df_f_new = github_excel_oku(FIYAT_DOSYASI)

                        # 2. TARİH FORMATLAMA (Eksik olan kısım burasıydı)
                        df_f_new['Tarih_DT'] = pd.to_datetime(df_f_new['Tarih'], errors='coerce')
                        df_f_new = df_f_new.dropna(subset=['Tarih_DT']).sort_values('Tarih_DT')
                        df_f_new['Tarih_Str'] = df_f_new['Tarih_DT'].dt.strftime('%Y-%m-%d')

                        # 3. Fiyatı Sayıya Çevir
                        df_f_new['Fiyat'] = pd.to_numeric(df_f_new['Fiyat'], errors='coerce')

                        # 4. Pivot İşlemi (Artık Tarih_Str var, hata vermez)
                        pivot_new = df_f_new.pivot_table(index='Kod', columns='Tarih_Str', values='Fiyat',
                                                         aggfunc='last').ffill(axis=1).reset_index()

                        # 5. Alarm Fonksiyonunu Çağır
                        alarm_sonuc = check_alarms_and_notify(pivot_new)
                        st.success(alarm_sonuc)

                    except Exception as e:
                        st.warning(f"Alarm kontrolü sırasında hata: {e}")
                st.toast('Veritabanı Güncellendi!', icon='🎉')
                st.success("✅ Sistem Başarıyla Senkronize Edildi!")
                time.sleep(2)
                st.rerun()
            elif "Veri bulunamadı" in res:
                st.warning("⚠️ Yeni fiyat verisi bulunamadı. ZIP dosyalarını kontrol et.")
            else:
                st.error(res)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("👋 Hoşgeldiniz. Veriler otomatik olarak sunulmaktadır.")
        st.markdown("<br>", unsafe_allow_html=True)

    if not df_f.empty and not df_s.empty:
        try:
            df_s.columns = df_s.columns.str.strip()
            kod_col = next((c for c in df_s.columns if c.lower() == 'kod'), 'Kod')
            ad_col = next((c for c in df_s.columns if 'ad' in c.lower()), 'Madde adı')
            agirlik_col = next((c for c in df_s.columns if 'agirlik' in c.lower().replace('ğ', 'g').replace('ı', 'i')),
                               'Agirlik_2025')

            df_f['Kod'] = df_f['Kod'].astype(str).apply(kod_standartlastir)
            df_s['Kod'] = df_s[kod_col].astype(str).apply(kod_standartlastir)
            df_f['Tarih_DT'] = pd.to_datetime(df_f['Tarih'], errors='coerce')
            df_f = df_f.dropna(subset=['Tarih_DT']).sort_values('Tarih_DT')
            df_f['Tarih_Str'] = df_f['Tarih_DT'].dt.strftime('%Y-%m-%d')
            df_f['Fiyat'] = pd.to_numeric(df_f['Fiyat'], errors='coerce')
            df_f = df_f[df_f['Fiyat'] > 0]

            pivot = df_f.pivot_table(index='Kod', columns='Tarih_Str', values='Fiyat', aggfunc='last').ffill(
                axis=1).bfill(axis=1).reset_index()
            # --- OTOMATİK ALARM KONTROLÜ (BAŞLANGIÇ) ---
            # Sayfa her yenilendiğinde sadece 1 kez çalışır
            if 'alarm_auto_check' not in st.session_state:
                st.session_state['alarm_auto_check'] = True  # İşaretle ki tekrar tekrar çalışmasın

                # Kullanıcıyı yormadan arka planda kontrol et
                try:
                    # check_alarms_and_notify fonksiyonunu çağırıyoruz (önceki adımda eklediğini varsayıyorum)
                    # Not: pivot tablosunu doğrudan kullanıyoruz, tekrar dosya okumuyoruz.
                    sonuc_msg = check_alarms_and_notify(pivot)

                    # Sadece mail gönderildiyse bildirim göster
                    if "0 adet" not in sonuc_msg:
                        st.toast(f"Otomatik Kontrol: {sonuc_msg}", icon="📧")
                    else:
                        print("Otomatik kontrol yapıldı: Mail atılacak durum yok.")

                except Exception as e:
                    print(f"Otomatik alarm hatası: {e}")
            # --- OTOMATİK ALARM KONTROLÜ (BİTİŞ) ---
            if not pivot.empty:
                if 'Grup' not in df_s.columns:
                    grup_map = {"01": "Gıda", "02": "Alkol", "03": "Giyim", "04": "Konut", "05": "Ev", "06": "Sağlık",
                                "07": "Ulaşım", "08": "İletişim", "09": "Eğlence", "10": "Eğitim", "11": "Lokanta",
                                "12": "Çeşitli"}
                    df_s['Grup'] = df_s['Kod'].str[:2].map(grup_map).fillna("Diğer")
                df_analiz = pd.merge(df_s, pivot, on='Kod', how='left')
                if agirlik_col in df_analiz.columns:
                    df_analiz[agirlik_col] = pd.to_numeric(df_analiz[agirlik_col], errors='coerce').fillna(1)
                else:
                    df_analiz['Agirlik_2025'] = 1;
                    agirlik_col = 'Agirlik_2025'

                gunler = [c for c in pivot.columns if c != 'Kod']
                if len(gunler) < 1: st.warning("Yeterli tarih verisi yok."); return
                baz, son = gunler[0], gunler[-1]

                endeks_genel = (df_analiz.dropna(subset=[son, baz])[agirlik_col] * (
                        df_analiz[son] / df_analiz[baz])).sum() / df_analiz.dropna(subset=[son, baz])[
                                   agirlik_col].sum() * 100
                enf_genel = (endeks_genel / 100 - 1) * 100
                df_analiz['Fark'] = (df_analiz[son] / df_analiz[baz]) - 1
                top = df_analiz.sort_values('Fark', ascending=False).iloc[0]
                gida = df_analiz[df_analiz['Kod'].str.startswith("01")].copy()
                enf_gida = ((gida[son] / gida[baz] * gida[agirlik_col]).sum() / gida[
                    agirlik_col].sum() - 1) * 100 if not gida.empty else 0

                dt_son = datetime.strptime(son, '%Y-%m-%d')
                dt_baz = datetime.strptime(baz, '%Y-%m-%d')
                days_left = calendar.monthrange(dt_son.year, dt_son.month)[1] - dt_son.day
                month_end_forecast = enf_genel + ((enf_genel / max(dt_son.day, 1)) * days_left)
                gun_farki = (dt_son - dt_baz).days

                # --- KAYAN YAZI (TICKER) GÜNCELLEMESİ: GÜNLÜK DEĞİŞİM ---

                # 1. Günlük Fark Hesabı (Eğer en az 2 gün veri varsa)
                if len(gunler) >= 2:
                    dunku_tarih = gunler[-2]
                    bugunku_tarih = gunler[-1]
                    # Yeni bir sütun açıyoruz, mevcut 'Fark' sütununu bozmuyoruz (o genel enflasyon için lazım)
                    df_analiz['Gunluk_Degisim'] = (df_analiz[bugunku_tarih] / df_analiz[dunku_tarih]) - 1
                else:
                    # Yeterli veri yoksa 0 kabul et
                    df_analiz['Gunluk_Degisim'] = 0

                # 2. Sıralamayı artık 'Gunluk_Degisim'e göre yapıyoruz
                inc = df_analiz.sort_values('Gunluk_Degisim', ascending=False).head(5)
                dec = df_analiz.sort_values('Gunluk_Degisim', ascending=True).head(5)

                # 3. Yazıyı oluştururken günlük değişim oranını yazdırıyoruz
                items = []

                # En çok artanlar (Kırmızı)
                for _, r in inc.iterrows():
                    if r['Gunluk_Degisim'] > 0:
                        items.append(
                            f"<span style='color:#f87171'>▲ {r[ad_col]} %{r['Gunluk_Degisim'] * 100:.1f}</span>")

                # En çok düşenler (Yeşil)
                for _, r in dec.iterrows():
                    if r['Gunluk_Degisim'] < 0:
                        items.append(
                            f"<span style='color:#4ade80'>▼ {r[ad_col]} %{r['Gunluk_Degisim'] * 100:.1f}</span>")

                # Eğer hiç değişim yoksa boş kalmasın
                if not items:
                    items.append("Piyasada son 24 saatte önemli bir fiyat değişimi olmadı.")

                st.markdown(
                    f'<div class="ticker-wrap"><div class="ticker"><div class="ticker-item">{" &nbsp;&nbsp; • &nbsp;&nbsp; ".join(items)}</div></div></div>',
                    unsafe_allow_html=True)

                def kpi_card(title, val, sub, sub_color, color_class, is_long_text=False):
                    val_class = "metric-val long-text" if is_long_text else "metric-val"
                    st.markdown(f"""
                        <div class="metric-card {color_class}">
                            <div class="metric-label">{title}</div>
                            <div class="{val_class}">{val}</div>
                            <div class="metric-sub" style="color:{sub_color}">{sub}</div>
                        </div>
                    """, unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    kpi_card("Genel Enflasyon", f"%{enf_genel:.2f}", f"{gun_farki} Günlük Değişim", "#ef4444",
                             "card-blue")
                with c2:
                    kpi_card("Gıda Enflasyonu", f"%{enf_gida:.2f}", "Mutfak Sepeti", "#ef4444", "card-emerald")
                with c3:
                    kpi_card("Ay Sonu Beklentisi", f"%{month_end_forecast:.2f}", f"🗓️ {days_left} gün kaldı", "#8b5cf6",
                             "card-purple")
                with c4:
                    kpi_card("En Yüksek Risk", f"{top[ad_col][:15]}", f"%{top['Fark'] * 100:.1f} Artış", "#f59e0b",
                             "card-orange", is_long_text=True)
                st.markdown("<br>", unsafe_allow_html=True)

                # --- SEKMELER ---
                t_analiz, t_istatistik, t_sepet, t_harita, t_firsat, t_liste, t_haber, t_rapor, t_alarm = st.tabs(
                    ["📊 ANALİZ", "📈 İSTATİSTİK", "🛒 SEPET", "🗺️ HARİTA", "📉 PİYASA VERİLERİ", "📋 LİSTE", "📰 HABERLER",
                     "📝 RAPOR", "🔔 FİYAT ALARMI"])

                with t_analiz:
                    st.markdown("### 📈 Enflasyon Momentum Analizi ve Gelecek Tahmini")
                    trend_data = [{"Tarih": g, "TÜFE": (df_analiz.dropna(subset=[g, baz])[agirlik_col] * (
                            df_analiz[g] / df_analiz[baz])).sum() / df_analiz.dropna(subset=[g, baz])[
                                                           agirlik_col].sum() * 100} for g in gunler]
                    df_trend = pd.DataFrame(trend_data)
                    df_trend['Tarih'] = pd.to_datetime(df_trend['Tarih'])
                    df_resmi, msg = get_official_inflation()

                    with st.spinner("Gelecek tahmini yapıyor..."):
                        df_forecast = predict_inflation_prophet(df_trend)

                    current_year = df_trend['Tarih'].dt.year.max()
                    start_date = df_trend['Tarih'].min()
                    end_date_fixed = f"{current_year}-12-31"

                    fig_main = go.Figure()
                    fig_main.add_trace(go.Scatter(x=df_trend['Tarih'], y=df_trend['TÜFE'], mode='lines+markers',
                                                  name='Enflasyon Monitörü', line=dict(color='#2563eb', width=3)))
                    if not df_forecast.empty:
                        future_only = df_forecast[df_forecast['ds'] > df_trend['Tarih'].max()]
                        fig_main.add_trace(
                            go.Scatter(x=future_only['ds'], y=future_only['yhat'], mode='lines', name='AI Tahmini',
                                       line=dict(color='#f59e0b', dash='dot')))
                        fig_main.add_trace(go.Scatter(x=future_only['ds'].tolist() + future_only['ds'].tolist()[::-1],
                                                      y=future_only['yhat_upper'].tolist() + future_only[
                                                          'yhat_lower'].tolist()[
                                                          ::-1], fill='toself',
                                                      fillcolor='rgba(245, 158, 11, 0.2)',
                                                      line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip",
                                                      showlegend=False))
                    if df_resmi is not None and not df_resmi.empty:
                        fig_main.add_trace(
                            go.Scatter(x=df_resmi['Tarih'], y=df_resmi['Resmi_TUFE'], mode='lines+markers',
                                       name='Resmi TÜİK', line=dict(color='#ef4444', width=2),
                                       marker=dict(symbol='square')))

                    # --- DÜZELTİLDİ: BURADA VIRGUL EKSIKTI ---
                    fig_main.update_layout(
                        template=st.session_state.plotly_template,
                        title="Enflasyon: Geçmiş, Şimdi ve Gelecek",
                        title_font=dict(color='white', size=22),
                        legend=dict(orientation="h", y=1.1, font=dict(color="white")),
                        yaxis=dict(title="TÜFE Endeksi", range=[95, 105]),
                        xaxis=dict(range=[start_date, end_date_fixed]),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_main, use_container_width=True)

                with t_istatistik:
                    st.markdown("### 📊 İstatistiksel Risk ve Dağılım Analizi")
                    col_hist, col_vol = st.columns(2)

                    # 1. Histogram
                    df_analiz['Fark_Yuzde'] = df_analiz['Fark'] * 100
                    fig_hist = px.histogram(df_analiz, x="Fark_Yuzde", nbins=40, title="📊 Zam Dağılımı Frekansı",
                                            color_discrete_sequence=['#8b5cf6'])
                    fig_hist.update_layout(
                        template=st.session_state.plotly_template,
                        title_font=dict(color='white', size=22),
                        xaxis_title="Artış Oranı (%)",
                        yaxis_title="Ürün Adedi",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    col_hist.plotly_chart(fig_hist, use_container_width=True)

                    # 2. Volatilite Analizi
                    try:
                        fiyat_sutunlari = [c for c in pivot.columns if c != 'Kod']
                        pivot['Std'] = pivot[fiyat_sutunlari].std(axis=1)
                        pivot['Mean'] = pivot[fiyat_sutunlari].mean(axis=1)
                        pivot['Volatilite'] = (pivot['Std'] / pivot['Mean']) * 100

                        df_vol = pd.merge(df_analiz, pivot[['Kod', 'Volatilite']], on='Kod', how='left')

                        fig_vol = px.scatter(df_vol, x="Fark_Yuzde", y="Volatilite", color="Grup",
                                             hover_data=[ad_col],
                                             title="⚡ Risk Analizi: Fiyat Hareketliliği vs Değişim",
                                             labels={"Fark_Yuzde": "Fiyat Değişimi (%)",
                                                     "Volatilite": "Hareketlilik Endeksi (Risk)"})

                        fig_vol.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
                        fig_vol.add_hline(y=df_vol['Volatilite'].mean(), line_dash="dash", line_color="red",
                                          annotation_text="Ortalama Risk")

                        fig_vol.update_layout(
                            template=st.session_state.plotly_template,
                            title_font=dict(color='white', size=22),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            legend=dict(
                                font=dict(color='white')  # ← KATEGORİLERİ BEYAZ YAPAN KISIM
                            )
                        )

                        col_vol.plotly_chart(fig_vol, use_container_width=True)
                        riskli_urunler = df_vol.sort_values("Volatilite", ascending=False).head(3)
                        st.info(f"⚠️ **En Dengesiz Fiyatlar:** " + ", ".join(
                            [f"{r[ad_col]} (Risk: {r['Volatilite']:.1f})" for _, r in riskli_urunler.iterrows()]))
                    except Exception as e:
                        col_vol.error(f"Volatilite hesaplanamadı: {e}")

                with t_sepet:
                    st.markdown("### 🛒 Kişisel Enflasyon Sepeti")
                    st.info(
                        "💡 **Nasıl Çalışır?** Aşağıdan ürünleri seçip **aylık tüketim miktarını (adet/kg)** girdiğinde, sistem senin gerçek enflasyonunu hesaplar.")

                    baskets = github_json_oku(SEPETLER_DOSYASI)
                    user_codes = baskets.get(st.session_state['username'], [])
                    all_products = df_analiz[ad_col].unique()
                    default_names = df_analiz[df_analiz['Kod'].isin(user_codes)][ad_col].tolist()

                    selected_names = st.multiselect("Takip Ettiğin Ürünleri Seç:", all_products, default=default_names)

                    if selected_names:
                        my_df = df_analiz[df_analiz[ad_col].isin(selected_names)].copy()
                        if 'Kullanici_Agirlik' not in st.session_state:
                            st.session_state['Kullanici_Agirlik'] = {row['Kod']: 1.0 for _, row in my_df.iterrows()}
                        my_df['Miktar'] = my_df['Kod'].map(st.session_state['Kullanici_Agirlik']).fillna(1.0)

                        col_editor, col_result = st.columns([2, 1])

                        with col_editor:
                            st.caption("👇 Miktarları buradan değiştirebilirsin:")
                            edited_df = st.data_editor(
                                my_df[[ad_col, 'Miktar', baz, son, 'Kod']],
                                column_config={
                                    ad_col: "Ürün Adı",
                                    "Miktar": st.column_config.NumberColumn("Tüketim (Adet/Kg)", min_value=0.1,
                                                                            max_value=1000.0, step=0.5, format="%.1f"),
                                    baz: st.column_config.NumberColumn(f"Eski Fiyat ({baz})", format="%.2f TL"),
                                    son: st.column_config.NumberColumn(f"Yeni Fiyat ({son})", format="%.2f TL"),
                                    "Kod": None
                                },
                                disabled=[ad_col, baz, son],
                                use_container_width=True,
                                key="sepet_editor"
                            )

                        with col_result:
                            try:
                                toplam_eski_masraf = (edited_df[baz] * edited_df['Miktar']).sum()
                                toplam_yeni_masraf = (edited_df[son] * edited_df['Miktar']).sum()

                                if toplam_eski_masraf > 0:
                                    kisisel_enf = ((toplam_yeni_masraf / toplam_eski_masraf) - 1) * 100
                                    fark_tl = toplam_yeni_masraf - toplam_eski_masraf
                                    st.markdown("#### 🧾 Sepet Özeti")
                                    st.metric("Senin Enflasyonun", f"%{kisisel_enf:.2f}", f"{fark_tl:+.2f} TL Fark",
                                              delta_color="inverse")
                                    st.divider()
                                    st.write(f"📉 **Genel Enflasyon:** %{enf_genel:.2f}")

                                    if kisisel_enf > enf_genel:
                                        st.error("Senin sepetin piyasadan daha hızlı pahalanıyor!")
                                    else:
                                        st.success("Tüketim alışkanlıkların seni enflasyondan kısmen koruyor.")
                                else:
                                    st.warning("Hesaplama için miktar giriniz.")
                            except Exception as e:
                                st.error(f"Hesaplama Hatası: {e}")

                        if st.button("💾 Sepet Listesini Kaydet"):
                            new_codes = edited_df['Kod'].tolist()
                            baskets[st.session_state['username']] = new_codes
                            if github_json_yaz(SEPETLER_DOSYASI, baskets, "Basket Update"):
                                st.toast("Sepet başarıyla kaydedildi!", icon='✅')
                            else:
                                st.error("Kaydetme başarısız.")
                    else:
                        st.warning("Henüz sepete ürün eklemedin.")

                with t_harita:
                    # GÜNCELLEME: Sadece Isı Haritası (Treemap) kaldı, tek sütun olarak genişledi.
                    fig_tree = px.treemap(df_analiz, path=[px.Constant("Piyasa"), 'Grup', ad_col], values=agirlik_col,
                                          color='Fark', color_continuous_scale='RdYlGn_r', title="🔥 Isı Haritası")

                    fig_tree.update_traces(marker=dict(line=dict(color='black', width=1)))

                    fig_tree.update_layout(
                        template=st.session_state.plotly_template,
                        title_font=dict(color='white', size=22),
                        margin=dict(t=40, l=0, r=0, b=0),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_tree, use_container_width=True)

                with t_firsat:
                    st.markdown("### 🛍️ Piyasadaki Benzer Ürünler")
                    st.info("Piyasadaki Benzer ürün fiyatlarını anlık tarar.")
                    product_list = sorted(df_analiz[ad_col].unique())
                    selected_product = st.selectbox("Hangi ürünü tarayalım?", product_list)
                    if st.button(f"Piyasa Fiyatlarını Çek", type="primary"):
                        try:
                            my_record = df_analiz[df_analiz[ad_col] == selected_product].iloc[0]
                            my_price = my_record[son]
                        except:
                            my_price = 0
                        st.metric("Senin Fiyatın", f"{my_price:.2f} TL")
                        results_data = []
                        target_url = f"https://www.google.com/search?q={selected_product}&tbm=shop&hl=tr&gl=TR"
                        with st.spinner("Google Taranıyor..."):
                            try:
                                chrome_options = Options()
                                chrome_options.add_argument("--headless")
                                chrome_options.add_argument("--no-sandbox")
                                chrome_options.add_argument("--disable-dev-shm-usage")
                                chrome_options.add_argument("--disable-gpu")
                                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                                chrome_options.add_experimental_option('useAutomationExtension', False)
                                chrome_options.add_argument(
                                    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

                                chrome_path = shutil.which("chromium") or shutil.which(
                                    "chromium-browser") or shutil.which("google-chrome")
                                if chrome_path: chrome_options.binary_location = chrome_path

                                driver_path = shutil.which("chromedriver") or shutil.which(
                                    "chromium-driver") or "/usr/bin/chromedriver"
                                if not driver_path:
                                    st.error("⚠️ Sürücü bulunamadı. packages.txt dosyasını kontrol et.")
                                else:
                                    service = Service(executable_path=driver_path)
                                    driver = webdriver.Chrome(service=service, options=chrome_options)
                                    driver.get(target_url)
                                    try:
                                        wait = WebDriverWait(driver, 5)
                                        consent_buttons = driver.find_elements(By.XPATH,
                                                                               "//button[contains(., 'Kabul') or contains(., 'Accept') or contains(., 'Agree')]")
                                        if consent_buttons: consent_buttons[0].click(); time.sleep(2)
                                    except:
                                        pass
                                    time.sleep(3)
                                    page_source = driver.page_source
                                    driver.quit()
                                    soup = BeautifulSoup(page_source, "html.parser")

                                    cards = soup.find_all(attrs={"aria-label": re.compile(r"Şu Anki Fiyat:")})
                                    if not cards: price_elements = soup.find_all(string=re.compile(r"(₺|TL)\s*\d+"))

                                    for card in cards:
                                        raw_text = card['aria-label']
                                        raw_text = raw_text.replace(u'\xa0', ' ').strip()
                                        price_pattern = r"(?:₺\s?)?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})(?:\s?TL)?"
                                        matches = list(re.finditer(price_pattern, raw_text))

                                        if matches:
                                            best_match = matches[0]
                                            p_price_str = best_match.group(1)
                                            try:
                                                clean_price = float(p_price_str.replace('.', '').replace(',', '.'))
                                            except:
                                                clean_price = 0
                                            if clean_price < 5 and len(matches) > 1:
                                                best_match = matches[1]
                                                p_price_str = best_match.group(1)
                                                try:
                                                    clean_price = float(p_price_str.replace('.', '').replace(',', '.'))
                                                except:
                                                    pass
                                            start, end = best_match.span()
                                            p_name = raw_text[:start].strip().rstrip('.').rstrip(':').replace(
                                                "Şu Anki Fiyat", "").strip()
                                            p_vendor_raw = raw_text[end:].strip()
                                            p_vendor = re.sub(r'^(TL|₺|\.|,)\s*', '', p_vendor_raw)
                                            p_vendor = p_vendor.replace("ve daha fazlası", "").replace(
                                                "ve diğer satıcılar", "").strip()
                                            if len(p_vendor) > 30: p_vendor = p_vendor.split('.')[0]
                                            if not p_name or len(p_name) < 2: continue
                                            if not p_vendor or len(p_vendor) < 2: continue
                                            if p_name.replace('.', '').replace(',', '').isdigit(): continue

                                            results_data.append({
                                                "Ürün": p_name,
                                                "Fiyat_Etiketi": p_price_str + " TL",
                                                "Fiyat_Sayi": clean_price,
                                                "Satıcı": p_vendor
                                            })

                                    if results_data:
                                        df_res = pd.DataFrame(results_data).sort_values("Fiyat_Sayi")
                                        for _, row in df_res.iterrows():
                                            is_cheaper = row['Fiyat_Sayi'] < my_price and row['Fiyat_Sayi'] > 0
                                            card_bg = "#ecfdf5" if is_cheaper else "#ffffff"
                                            border_col = "#10b981" if is_cheaper else "#e2e8f0"
                                            st.markdown(f"""
                                            <div style="background:{card_bg}; border:1px solid {border_col}; padding:15px; border-radius:10px; margin-bottom:10px;">
                                                <div style="font-weight:bold; color:#1e293b;">{row['Ürün']}</div>
                                                <div style="display:flex; justify-content:space-between; margin-top:5px;">
                                                    <div style="color:#64748b;">🏪 {row['Satıcı']}</div>
                                                    <div style="font-weight:800; color:#0f172a;">{row['Fiyat_Etiketi']}</div>
                                                </div>
                                            </div>""", unsafe_allow_html=True)
                                    else:
                                        st.warning("Veri okunamadı.")
                            except Exception as e:
                                st.error(f"Sistem Hatası: {e}")

                with t_liste:
                    st.data_editor(
                        df_analiz[['Grup', ad_col, 'Fark', baz, son]],
                        column_config={
                            "Fark": st.column_config.ProgressColumn("Değişim Oranı", format="%.2f", min_value=-0.5,
                                                                    max_value=0.5), ad_col: "Ürün Adı",
                            "Grup": "Kategori"},
                        hide_index=True, use_container_width=True
                    )
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer: df_analiz.to_excel(writer, index=False,
                                                                                                 sheet_name='Analiz')
                    st.download_button("📥 Excel Raporunu İndir", data=output.getvalue(),
                                       file_name=f"Enflasyon_Raporu_{son}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                with t_haber:
                    st.markdown("### 🌍 Piyasa Gündemi")
                    if st.button("Haberleri Tara ve Analiz Et", key="btn_news"):
                        with st.spinner("İnternet taranıyor, yorumlanıyor..."):
                            analysis_text, headlines = get_market_sentiment()
                            c_news1, c_news2 = st.columns([2, 1])
                            with c_news1:
                                st.markdown("#### 🧠 Piyasa Yorumu")
                                st.success(analysis_text)
                            with c_news2:
                                st.markdown("#### 🗞️ Son Başlıklar")
                                for h in headlines:
                                    st.caption(f"• {h}")

                with t_rapor:
                    st.markdown("### 📝 Profesyonel Yönetici Raporu")
                    col_gen, col_download = st.columns(2)
                    if 'report_text' not in st.session_state: st.session_state['report_text'] = ""
                    with col_gen:
                        if st.button("✍️ Raporu Yazdır", type="primary"):
                            with st.spinner("Veriler derleniyor, rapor yazılıyor..."):
                                sepet_dagilimi = df_analiz.groupby('Grup')['Fark'].mean().sort_values(ascending=False)
                                kategori_metni = ""
                                for kat, oran in sepet_dagilimi.items(): durum = "YÜKSELİŞ" if oran > 0 else "DÜŞÜŞ"; kategori_metni += f"- {kat}: %{oran * 100:.2f} ({durum})\n"
                                report_summary = f"Tarih: {datetime.now().strftime('%d-%m-%Y')}\nGenel Enflasyon: %{enf_genel:.2f}\nGıda Enflasyonu: %{enf_gida:.2f}\nEn Çok Artan: {top[ad_col]} (%{top['Fark'] * 100:.2f})\nTahmin: %{month_end_forecast:.2f}"
                                prompt_report = f"Sen kıdemli bir analistsin. Şu verilere göre PROFESYONEL bir rapor yaz:\nVERİLER:\n{report_summary}\nSEKTÖREL:\n{kategori_metni}\nŞABLON: 1.GİRİŞ 2.DETAYLAR 3.ÖNGÖRÜ. İmza: Enflasyon Monitörü Ekibi"
                                model_rep = genai.GenerativeModel('gemini-2.5-flash')
                                st.session_state['report_text'] = model_rep.generate_content(prompt_report).text
                                st.success("Rapor oluşturuldu!")
                    if st.session_state['report_text']:
                        st.markdown("---");
                        st.markdown(st.session_state['report_text'])
                        pdf_bytes = create_pdf_report(st.session_state['report_text'])
                        with col_download: st.download_button(label="📥 PDF Olarak İndir", data=pdf_bytes,
                                                              file_name=f"Enflasyon_Raporu_{bugun}.pdf",
                                                              mime="application/pdf")
                with t_alarm:
                    st.markdown("### 🔔 Akıllı Fiyat Alarmı Kur")
                    st.info(
                        "Takip ettiğin ürün belirlediğin fiyatın **altına** düşerse sana otomatik e-posta atarız.")
                    ALARMS_DOSYASI = "user_alarms.json"
                    alarms_db = github_json_oku(ALARMS_DOSYASI)
                    if not isinstance(alarms_db, list): alarms_db = []
                    product_list = sorted(df_analiz[ad_col].unique())
                    secilen_urun = st.selectbox("Hangi ürün için alarm kurulsun?", product_list,
                                                key="alarm_product")
                    curr_price = df_analiz[df_analiz[ad_col] == secilen_urun][son].values[0]

                    c_al1, c_al2, c_al3 = st.columns(3)
                    with c_al1:
                        st.metric("Şu Anki Fiyat", f"{curr_price:.2f} TL")
                    with c_al2:
                        target_price = st.number_input("Hedef Fiyat (TL)", min_value=1.0,
                                                       value=float(curr_price) * 0.9, step=1.0,
                                                       help="Fiyat bu seviyenin altına inerse mail atılır.")
                    with c_al3:
                        user_email = ""
                        users_db = github_json_oku(USERS_DOSYASI)
                        if st.session_state['username'] in users_db:
                            user_data = users_db[st.session_state['username']]
                            if isinstance(user_data, dict): user_email = user_data.get("email", "")
                        target_email = st.text_input("Bildirim E-Postası", value=user_email)

                    if st.button("🔔 Alarmı Kur", type="primary"):
                        if target_price < curr_price:
                            new_alarm = {
                                "user": st.session_state['username'],
                                "email": target_email,
                                "kod": df_analiz[df_analiz[ad_col] == secilen_urun]['Kod'].values[0],
                                "urun_adi": secilen_urun,
                                "hedef_fiyat": target_price,
                                "durum": "aktif",
                                "olusturma_tarihi": datetime.now().strftime("%Y-%m-%d")
                            }
                            alarms_db.append(new_alarm)
                            if github_json_yaz(ALARMS_DOSYASI, alarms_db, "New Alarm"):
                                st.success(
                                    f"✅ Alarm kuruldu! {secilen_urun} fiyatı {target_price} TL altına düşerse mail gelecek.")
                            else:
                                st.error("Kayıt hatası.")
                        else:
                            st.warning("Hedef fiyat, şu anki fiyattan düşük olmalıdır.")

                    st.divider()
                    st.markdown("#### 📋 Aktif Alarmların")
                    my_alarms = [a for a in alarms_db if a.get('user') == st.session_state['username']]
                    if my_alarms:
                        st.dataframe(
                            pd.DataFrame(my_alarms)[['urun_adi', 'hedef_fiyat', 'durum', 'olusturma_tarihi']],
                            use_container_width=True)
                        if st.button("🗑️ Tüm Alarmlarımı Temizle"):
                            alarms_db = [a for a in alarms_db if a.get('user') != st.session_state['username']]
                            github_json_yaz(ALARMS_DOSYASI, alarms_db, "Clear Alarms")
                            st.rerun()
                    else:
                        st.info("Henüz kurulu bir alarmın yok.")
        except Exception as e:
            st.error(f"Kritik Hata: {e}")
    st.markdown(
        '<div style="text-align:center; color:#94a3b8; font-size:11px; margin-top:50px;">DESIGNED BY FATIH ARSLAN © 2025</div>',
        unsafe_allow_html=True)


# --- 5. ANA GİRİŞ SİSTEMİ (MAIN) ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    params = st.query_params
    if "session_user" in params and not st.session_state['logged_in']:
        auto_user = params["session_user"]
        users_db = github_json_oku(USERS_DOSYASI)
        if auto_user in users_db:
            st.session_state['logged_in'] = True
            st.session_state['username'] = auto_user
            st.toast(f"Tekrar Hoşgeldin, {auto_user} 👋", icon="🔓")
            time.sleep(1)
            st.rerun()

    if "reset_user" in params and not st.session_state['logged_in']:
        reset_user = params["reset_user"]
        st.markdown("""
        <style>
            .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); }
            [data-testid="stForm"] { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 40px; }
            h1, h2, h3, p, label, .stMarkdown { color: white !important; }
            .stTextInput input { color: #0f172a !important; }
        </style>
        """, unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center;'>🔐 ŞİFRE SIFIRLAMA</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.form("reset_form"):
                st.info(f"Kullanıcı: {reset_user}")
                new_p = st.text_input("Yeni Şifre", type="password")
                conf_p = st.text_input("Şifreyi Onayla", type="password")
                if st.form_submit_button("ŞİFREYİ GÜNCELLE", use_container_width=True):
                    if new_p and new_p == conf_p:
                        ok, msg = github_user_islem("update_password", username=reset_user, password=new_p)
                        if ok:
                            st.success(msg)
                            time.sleep(2)
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Şifreler uyuşmuyor.")
        return

    if not st.session_state['logged_in']:
        st.markdown("""
        <style>
            .stApp {
                background-color: #0f172a;
                background-image: radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
                font-family: 'Inter', sans-serif;
            }
            [data-testid="stForm"] {
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(12px);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                padding: 40px;
            }
            h1 { color: white !important; font-weight: 800 !important; letter-spacing: -1px; }
            p, label, span { color: #e2e8f0 !important; }
            .stTabs [data-baseweb="tab-list"] {
                background-color: rgba(255,255,255,0.05);
                border-radius: 10px;
                padding: 5px;
                gap: 5px;
            }
            .stTabs [data-baseweb="tab-list"] button {
                color: #94a3b8;
                border-radius: 8px;
                border: none;
                font-weight: 600;
            }
            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
                background-color: #3b82f6 !important;
                color: white !important;
            }
            .stTextInput input {
                background-color: #1e293b !important;
                color: white !important;
                border: 1px solid #334155 !important;
            }
            .stTextInput input:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
            }
            button[kind="secondaryFormSubmit"] {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                border: none;
                color: white !important;
                font-weight: bold;
                transition: all 0.3s;
            }
            button[kind="secondaryFormSubmit"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
            }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(
            "<div style='text-align: center; margin-top:60px; margin-bottom:20px;'><h1 style='font-size:42px;'>ENFLASYON MONİTÖRÜ</h1><p style='font-size:14px; color:#94a3b8 !important;'>PİYASA ANALİZ SİSTEMİ</p></div>",
            unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            t_log, t_reg, t_forgot = st.tabs(["🔒 GİRİŞ YAP", "📝 KAYIT OL", "🔑 ŞİFREMİ UNUTTUM"])
            with t_log:
                with st.form("login_f"):
                    l_u = st.text_input("Kullanıcı Adı")
                    l_p = st.text_input("Şifre", type="password")
                    beni_hatirla = st.checkbox("Beni Hatırla")
                    if st.form_submit_button("SİSTEME GİRİŞ", use_container_width=True):
                        ok, msg = github_user_islem("login", l_u, l_p)
                        if ok:
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = l_u
                            if beni_hatirla:
                                st.query_params["session_user"] = l_u
                            else:
                                st.query_params.clear()
                            st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
            with t_reg:
                # --- KAYIT SÜRECİ STATE YÖNETİMİ ---
                if 'reg_stage' not in st.session_state:
                    st.session_state.reg_stage = 1  # 1: Bilgi Girişi, 2: Kod Doğrulama
                if 'reg_temp_data' not in st.session_state:
                    st.session_state.reg_temp_data = {}  # Bilgileri geçici tutacağımız yer

                # --- AŞAMA 1: BİLGİ GİRİŞİ ---
                if st.session_state.reg_stage == 1:
                    st.markdown("### 📝 Hesap Oluştur")
                    with st.form("reg_step1_form"):
                        r_u = st.text_input("Kullanıcı Adı Belirle")
                        r_e = st.text_input("E-Posta Adresi")
                        r_p = st.text_input("Şifre Belirle", type="password")

                        # Butona basınca kodu gönderip 2. aşamaya geçeceğiz
                        if st.form_submit_button("DOĞRULAMA KODU GÖNDER", use_container_width=True):
                            if r_u and r_p and r_e:
                                # Kullanıcı adı zaten var mı kontrol et (GitHub'a sormadan önce basit kontrol)
                                users_check = github_json_oku(USERS_DOSYASI)
                                if r_u in users_check:
                                    st.error("Bu kullanıcı adı zaten alınmış.")
                                else:
                                    # 1. Kodu Üret (100000 ile 999999 arası)
                                    code = str(random.randint(100000, 999999))

                                    # 2. Mail Gönder
                                    with st.spinner("Kod gönderiliyor..."):
                                        if send_verification_email(r_e, code):
                                            # 3. Bilgileri State'e Kaydet
                                            st.session_state.reg_temp_data = {
                                                "username": r_u,
                                                "email": r_e,
                                                "password": r_p,
                                                "code": code
                                            }
                                            st.session_state.reg_stage = 2  # Diğer ekrana geç
                                            st.rerun()
                                        else:
                                            st.error("Mail gönderilemedi. E-posta adresini kontrol et.")
                            else:
                                st.warning("Lütfen tüm alanları doldurunuz.")

                # --- AŞAMA 2: KOD DOĞRULAMA ---
                elif st.session_state.reg_stage == 2:
                    st.markdown(f"### 🔐 Kodu Gir")
                    st.info(f"**{st.session_state.reg_temp_data['email']}** adresine 6 haneli bir kod gönderdik.")

                    with st.form("reg_step2_form"):
                        entered_code = st.text_input("Doğrulama Kodu", max_chars=6)

                        col_verify, col_back = st.columns(2)
                        with col_verify:
                            btn_verify = st.form_submit_button("✅ ONAYLA VE KAYDOL", use_container_width=True)
                        with col_back:
                            # Geri dön butonu (Form içinde buton zor olduğu için logic ile yapıyoruz)
                            pass

                            # Form dışı butonlar (Daha düzgün hizalama için)
                    if st.button("⬅️ Geri Dön / E-postayı Düzenle"):
                        st.session_state.reg_stage = 1
                        st.rerun()

                    if btn_verify:
                        real_code = st.session_state.reg_temp_data.get("code")
                        if entered_code == real_code:
                            # KOD DOĞRU! ŞİMDİ KAYIT İŞLEMİNİ YAP.
                            data = st.session_state.reg_temp_data
                            ok, msg = github_user_islem("register", data["username"], data["password"], data["email"])

                            if ok:
                                st.success("✅ Doğrulama Başarılı! Hesap oluşturuldu.")
                                st.session_state['logged_in'] = True
                                st.session_state['username'] = data["username"]
                                # Temizlik
                                st.session_state.reg_stage = 1
                                st.session_state.reg_temp_data = {}
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.error("❌ Hatalı Kod! Lütfen tekrar kontrol et.")
            with t_forgot:
                with st.form("forgot_f"):
                    f_email = st.text_input("Kayıtlı E-Posta Adresi")
                    if st.form_submit_button("SIFIRLAMA LİNKİ GÖNDER", use_container_width=True):
                        if f_email:
                            ok, msg = github_user_islem("forgot_password", email=f_email)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                        else:
                            st.warning("Lütfen e-posta adresinizi girin.")
    else:
        dashboard_modu()


if __name__ == "__main__":
    main()