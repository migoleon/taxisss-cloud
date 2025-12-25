import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import io
import time
from datetime import datetime

# --- ΡΥΘΜΙΣΕΙΣ ΣΕΛΙΔΑΣ ---
st.set_page_config(page_title="Taxis Cloud Scraper", layout="wide")

def run_taxis_scraper(username, password, logs_placeholder):
    """
    Συνδέεται στο TaxisNet μέσω Browserless και τραβάει τα στοιχεία.
    """
    data = {
        "USERNAME": username,
        "STATUS": "Processing",
        "ΟΝΟΜΑΤΕΠΩΝΥΜΟ": "",
        "ΑΦΜ": "",
        "ΑΜΚΑ": "",
        "ΔΟΥ": ""
    }
    
    # Παίρνουμε το κλειδί από τα κρυφά secrets του Streamlit
    try:
        api_key = st.secrets["BROWSERLESS_API_KEY"]
    except:
        logs_placeholder.error("❌ Λείπει το API Key από τα Secrets!")
        return data

    logs_placeholder.info(f"⏳ [{username}] Σύνδεση με Cloud Browser...")

    try:
        # Σύνδεση με Browserless μέσω Playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f'wss://production-sfo.browserless.io/chromium?token={api_key}')
            context = browser.new_context()
            page = context.new_page()

            logs_placeholder.info(f"🌍 [{username}] Μπαίνω στο Taxis...")
            page.goto("https://www1.aade.gr/taxisnet/info/protected/displayRegistryInfo.htm", timeout=60000)

            # Login
            page.wait_for_selector("#username")
            page.fill("#username", username)
            page.fill("#password", password)
            
            logs_placeholder.info(f"🔑 [{username}] Πατάω είσοδο...")
            page.press("#password", "Enter") # Πατάμε Enter για σιγουριά

            # Περιμένουμε λίγο να φορτώσει η επόμενη σελίδα
            page.wait_for_timeout(4000)
            
            content = page.content().lower()

            if "login failed" in content or "λανθασμένο όνομα" in content:
                data["STATUS"] = "Wrong Credentials"
                logs_placeholder.warning(f"❌ [{username}] Λάθος κωδικοί")
            elif "αποσύνδεση" in content or "μητρώου" in content:
                data["STATUS"] = "Success"
                logs_placeholder.success(f"✅ [{username}] Επιτυχία! Τραβάω δεδομένα...")

                # --- SCRAPING ΤΟΥ ΠΙΝΑΚΑ ---
                try:
                    # Διαβάζουμε τον πίνακα με Pandas απευθείας από την HTML
                    html = page.content()
                    dfs = pd.read_html(html)
                    
                    # Συνήθως ο πίνακας με τα στοιχεία είναι ο 2ος ή 3ος, ψάχνουμε αυτόν που έχει "ΑΦΜ"
                    found_table = False
                    for df in dfs:
                        # Μετατρέπουμε τον πίνακα σε string για να ψάξουμε λέξεις κλειδιά
                        df_str = df.to_string()
                        if "ΑΦΜ" in df_str or "Α.Φ.Μ." in df_str:
                            # Καθαρισμός και μάζεμα στοιχείων
                            # Εδώ κάνουμε μια απλή λογική: Ψάχνουμε τα κελιά
                            # Προσαρμογή ανάλογα με τη μορφή του πίνακα
                            
                            # Ένας μπακάλικος αλλά αποδοτικός τρόπος για αρχή:
                            # Μετατρέπουμε το dataframe σε dictionary 
                            # (Υποθέτουμε ότι η στήλη 0 είναι οι ετικέτες και η 1 οι τιμές)
                            try:
                                info_dict = dict(zip(df[0], df[1]))
                            except:
                                info_dict = {}

                            # Ψάχνουμε με διάφορα κλειδιά γιατί το Taxis τα αλλάζει
                            data["ΑΦΜ"] = info_dict.get("ΑΦΜ", info_dict.get("Α.Φ.Μ.", ""))
                            data["ΑΜΚΑ"] = info_dict.get("Α.Μ.Κ.Α.", info_dict.get("AMKA", ""))
                            data["ΔΟΥ"] = info_dict.get("Αρμόδια ΔΟΥ", "")
                            
                            # Όνομα
                            eponymo = info_dict.get("Επώνυμο / Επώνυμο(β) / Όνομα", "")
                            data["ΟΝΟΜΑΤΕΠΩΝΥΜΟ"] = eponymo
                            
                            found_table = True
                            break
                    
                    if not found_table:
                        logs_placeholder.warning(f"⚠️ [{username}] Δεν βρέθηκε ο πίνακας στοιχείων.")
                
                except Exception as e:
                    logs_placeholder.error(f"⚠️ [{username}] Σφάλμα ανάγνωσης πίνακα: {e}")

            else:
                data["STATUS"] = "Unknown Error"
                logs_placeholder.error(f"⚠️ [{username}] Άγνωστο σφάλμα σύνδεσης.")

            browser.close()
            
    except Exception as e:
        data["STATUS"] = "System Error"
        logs_placeholder.error(f"💀 [{username}] Κρίσιμο σφάλμα: {e}")

    return data

# --- ΤΟ UI (Η ΒΙΤΡΙΝΑ) ---
st.title("☁️ TaxisNet Data Miner")
st.markdown("Αυτόματη άντληση στοιχείων (Όνομα, ΑΦΜ, ΑΜΚΑ) μέσω Cloud.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Στοιχεία Εισόδου")
    user_input = st.text_area("Username Password (ανά γραμμή)", height=200, placeholder="user1 pass1\nuser2 pass2")
    start_btn = st.button("🚀 Εκκίνηση", type="primary", use_container_width=True)

if start_btn and user_input:
    lines = user_input.strip().split('\n')
    creds = [line.split() for line in lines if len(line.split()) >= 2]
    
    if not creds:
        st.error("Δεν δώσατε έγκυρα στοιχεία!")
    else:
        with col2:
            st.subheader("Live Logs")
            logs = st.empty()
            results = []
            
            progress = st.progress(0)
            
            for i, (u, p) in enumerate(creds):
                # Καθαρίζουμε το log για τον επόμενο χρήστη ή το αφήνουμε (εδώ το αφήνουμε να φαίνεται η ροή)
                result = run_taxis_scraper(u, p, st.empty()) # st.empty() φτιάχνει νέο placeholder για κάθε χρήστη
                results.append(result)
                progress.progress((i + 1) / len(creds))
            
            # Εμφάνιση πίνακα
            st.success("Ολοκληρώθηκε!")
            df_res = pd.DataFrame(results)
            st.dataframe(df_res)
            
            # Download Button
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_res.to_excel(writer, index=False)
                
            st.download_button("📥 Κατέβασμα Excel", buffer.getvalue(), f"taxis_export_{datetime.now().strftime('%H%M')}.xlsx")