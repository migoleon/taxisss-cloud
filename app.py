import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import io
import time
from datetime import datetime

# --- ΡΥΘΜΙΣΕΙΣ ---
st.set_page_config(page_title="Taxis Cloud Live", layout="wide")

def update_preview(page, image_spot, status_text):
    """Βοηθητική συνάρτηση για να δείχνουμε τι βλέπει ο browser"""
    try:
        # Τραβάμε screenshot στη μνήμη
        screenshot = page.screenshot()
        # Το δείχνουμε στο Streamlit
        image_spot.image(screenshot, caption=status_text, use_container_width=True)
    except:
        pass

def run_taxis_scraper(username, password, logs_placeholder, image_spot):
    data = {
        "USERNAME": username, "STATUS": "Processing",
        "ΟΝΟΜΑΤΕΠΩΝΥΜΟ": "", "ΑΦΜ": "", "ΑΜΚΑ": ""
    }
    
    try:
        api_key = st.secrets["BROWSERLESS_API_KEY"]
    except:
        logs_placeholder.error("❌ Λείπει το API Key!")
        return data

    logs_placeholder.info(f"⏳ [{username}] Εκκίνηση...")

    try:
        with sync_playwright() as p:
            # Σύνδεση με Browserless
            # Προσοχή: Εδώ δεν μπορούμε να μπλοκάρουμε εικόνες αν θέλουμε να τις βλέπουμε εμείς!
            browser = p.chromium.connect_over_cdp(f'wss://production-sfo.browserless.io/chromium?token={api_key}')
            context = browser.new_context()
            page = context.new_page()

            logs_placeholder.info(f"🌍 [{username}] Μπαίνω Taxis...")
            page.goto("https://www1.aade.gr/taxisnet/info/protected/displayRegistryInfo.htm")
            
            # --- LIVE PREVIEW 1 ---
            update_preview(page, image_spot, f"[{username}] Φόρτωση Σελίδας")

            # Login
            page.wait_for_selector("#username")
            page.fill("#username", username)
            page.fill("#password", password)
            
            # --- LIVE PREVIEW 2 ---
            update_preview(page, image_spot, f"[{username}] Συμπλήρωση Στοιχείων")
            
            logs_placeholder.info(f"🔑 [{username}] Πατάω είσοδο...")
            page.press("#password", "Enter")
            
            # Περιμένουμε...
            page.wait_for_timeout(3000)
            
            # --- LIVE PREVIEW 3 ---
            update_preview(page, image_spot, f"[{username}] Αποτέλεσμα Εισόδου")

            content = page.content().lower()

            if "login failed" in content or "λανθασμένο όνομα" in content:
                data["STATUS"] = "Wrong Credentials"
                logs_placeholder.warning(f"❌ [{username}] Λάθος κωδικοί")
            elif "αποσύνδεση" in content or "μητρώου" in content:
                data["STATUS"] = "Success"
                logs_placeholder.success(f"✅ [{username}] Επιτυχία!")

                # SCRAPING (Απλοποιημένο για το παράδειγμα)
                try:
                    dfs = pd.read_html(page.content())
                    for df in dfs:
                        df_str = df.to_string()
                        if "ΑΦΜ" in df_str:
                            # Απλή λογική εξαγωγής
                            try:
                                info = dict(zip(df[0], df[1]))
                                data["ΑΦΜ"] = info.get("ΑΦΜ", "")
                                data["ΑΜΚΑ"] = info.get("Α.Μ.Κ.Α.", "")
                                data["ΟΝΟΜΑΤΕΠΩΝΥΜΟ"] = info.get("Επώνυμο / Επώνυμο(β) / Όνομα", "")
                            except: pass
                except: pass
            
            browser.close()
            
    except Exception as e:
        data["STATUS"] = "Error"
        logs_placeholder.error(f"💀 Error: {e}")

    return data

# --- UI ---
st.title("👁️ Taxis Cloud - Live Monitor")
st.markdown("Τώρα βλέπουμε τι βλέπει και το ρομπότ!")

col1, col2, col3 = st.columns([1, 1.5, 1.5])

with col1:
    st.subheader("1. Στοιχεία")
    user_input = st.text_area("User Pass", height=150)
    start_btn = st.button("🚀 Start Live", type="primary", use_container_width=True)

if start_btn and user_input:
    lines = user_input.strip().split('\n')
    creds = [line.split() for line in lines if len(line.split()) >= 2]
    
    # Εδώ φτιάχνουμε τα placeholders για να φαίνονται ωραία
    with col2:
        st.subheader("2. Logs")
        logs = st.empty()
    
    with col3:
        st.subheader("3. Live View")
        # Εδώ θα εμφανίζεται η εικόνα του browser!
        image_spot = st.empty() 

    results = []
    for u, p in creds:
        res = run_taxis_scraper(u, p, logs, image_spot)
        results.append(res)
    
    st.success("Τέλος!")
    st.dataframe(pd.DataFrame(results))