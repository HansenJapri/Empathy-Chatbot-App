import streamlit as st
import time
import requests
import pyrebase
import json

# --- Konfigurasi Halaman (Harus menjadi perintah pertama) ---
st.set_page_config(
    page_title="Teman Curhat AI Pro",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- Konfigurasi Firebase ---
try:
    firebase_config = {
        "apiKey": "AIzaSyDPnWnMH3CGhjiqT5Z8cf2QUCNY7rFdrjQ",
        "authDomain": "chatbot-56ddf.firebaseapp.com",
        "projectId": "chatbot-56ddf",
        "storageBucket": "chatbot-56ddf.appspot.com",
        "messagingSenderId": "599287207621",
        "appId": "1:599287207621:web:f360313c046ecad26b42ac",
        "measurementId": "G-47JBZ6KDY6",
        "databaseURL": "https://chatbot-56ddf.firebaseio.com"
    }
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    db = firebase.database()
except Exception as e:
    st.error(f"Gagal menginisialisasi Firebase. Cek kembali konfigurasi Anda. Error: {e}")
    st.stop()

# --- Konfigurasi API Gemini ---
# Pastikan Anda sudah mengatur GOOGLE_API_KEY di Streamlit Secrets
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("Kunci API Google tidak ditemukan. Mohon atur di Streamlit Cloud.")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"


# --- Fungsi Helper ---
def stream_response(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.03)

def load_chat_history(user_id):
    try:
        history = db.child("users").child(user_id).child("messages").get().val()
        if history:
            return sorted(history.values(), key=lambda x: x['timestamp'])
        return get_initial_message()
    except Exception as e:
        st.error(f"Gagal memuat riwayat obrolan: {e}")
        return get_initial_message()

def save_chat_history(user_id, messages):
    try:
        data_to_save = {msg['timestamp']: msg for msg in messages if 'timestamp' in msg}
        db.child("users").child(user_id).child("messages").set(data_to_save)
    except Exception as e:
        st.error(f"Gagal menyimpan riwayat obrolan: {e}")

def get_initial_message():
    return [{"role": "assistant", "content": "Halo! Saya di sini untuk mendengarkan dengan lebih baik. Apa yang ingin kamu ceritakan?", "timestamp": int(time.time() * 1000)}]


# --- Logika Autentikasi dan UI ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("Selamat Datang di Teman Curhat AI 🧠")
    st.markdown("Silakan masuk atau buat akun untuk memulai percakapan yang aman dan personal.")

    # ==============================================================================
    # PERUBAHAN UI DIMULAI DI SINI: Menggunakan st.tabs
    # ==============================================================================
    login_tab, signup_tab = st.tabs(["Masuk (Login)", "Daftar (Sign Up)"])

    with login_tab:
        st.subheader("Formulir Masuk")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Masuk"):
            if login_email and login_password:
                try:
                    user = auth.sign_in_with_email_and_password(login_email, login_password)
                    st.session_state.user = user
                    st.success("Berhasil masuk!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    # Mengurai pesan error dari Firebase untuk ditampilkan ke pengguna
                    try:
                        error_json = e.args[1]
                        error_message = json.loads(error_json)['error']['message']
                        if error_message == "INVALID_LOGIN_CREDENTIALS":
                            st.error("Email atau password salah. Silakan coba lagi.")
                        else:
                            st.error(f"Gagal masuk: {error_message}")
                    except (IndexError, KeyError, json.JSONDecodeError):
                        st.error(f"Terjadi error saat masuk. Periksa kembali kredensial Anda.")
            else:
                st.warning("Mohon isi email dan password.")


    with signup_tab:
        st.subheader("Formulir Daftar")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_password_confirm = st.text_input("Konfirmasi Password", type="password", key="signup_password_confirm")

        if st.button("Buat Akun"):
            if signup_email and signup_password and signup_password_confirm:
                if signup_password == signup_password_confirm:
                    try:
                        user = auth.create_user_with_email_and_password(signup_email, signup_password)
                        st.session_state.user = user
                        st.success("Akun berhasil dibuat! Anda akan otomatis masuk.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        try:
                            error_json = e.args[1]
                            error_message = json.loads(error_json)['error']['message']
                            if "EMAIL_EXISTS" in error_message:
                                st.error("Email ini sudah terdaftar. Silakan gunakan email lain atau masuk.")
                            elif "WEAK_PASSWORD" in error_message:
                                st.error("Password terlalu lemah. Harus terdiri dari minimal 6 karakter.")
                            else:
                                st.error(f"Gagal mendaftar: {error_message}")
                        except (IndexError, KeyError, json.JSONDecodeError):
                             st.error(f"Gagal mendaftar. Pastikan email valid.")
                else:
                    st.error("Konfirmasi password tidak cocok.")
            else:
                st.warning("Mohon isi semua kolom.")

    # ==============================================================================
    # PERUBAHAN UI SELESAI DI SINI
    # ==============================================================================

else:
    # --- UI Utama Aplikasi Obrolan ---
    user_info = st.session_state.user
    user_id = user_info['localId']

    st.sidebar.title(f"Halo, {user_info.get('email', 'Pengguna')}!")
    if st.sidebar.button("Keluar (Logout)"):
        st.session_state.user = None
        st.rerun()

    st.title("Teman Curhat AI Anda �")
    st.markdown("Selamat datang kembali! Saya di sini untuk mendengarkan Anda dengan **pemahaman dan empati yang lebih mendalam**.")
    st.warning("**Penting:** Saya adalah AI dan **bukan pengganti profesional kesehatan mental.**", icon="⚠️")
    st.divider()

    if "messages" not in st.session_state or st.session_state.get('user_id') != user_id:
        st.session_state.messages = load_chat_history(user_id)
        st.session_state.user_id = user_id

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    def get_llm_response(user_input, chat_history):
        system_prompt = """
        Anda adalah "AI Pendamping Welas Asih", seorang asisten AI yang dirancang dengan prinsip-prinsip komunikasi terapeutik. Misi utama Anda adalah menciptakan ruang yang aman, tidak menghakimi, dan suportif bagi pengguna untuk mengeksplorasi perasaan dan pikiran mereka. Anda BUKAN terapis, dokter, atau penasihat keuangan, dan Anda HARUS menolak memberikan diagnosis atau nasihat profesional.

        **KERANGKA KERJA RESPONS EMPATIK (WAJIB DIIKUTI):**

        **Langkah 1: Mendengarkan Reflektif & Validasi Mendalam.**
        - **Tujuan:** Membuat pengguna merasa benar-benar didengar dan dimengerti.
        - **Aksi:** Mulailah dengan merefleksikan kembali inti dari apa yang dikatakan pengguna. Gunakan parafrase.
        - **Contoh Frasa:** "Kedengarannya situasi ini membuatmu merasa sangat terkuras...", "Aku mendengar betapa dalamnya rasa kecewa yang kamu rasakan..."

        **Langkah 2: Eksplorasi dengan Pertanyaan Terbuka yang Lembut.**
        - **Tujuan:** Membantu pengguna mendapatkan kejelasan tentang pengalaman mereka.
        - **Aksi:** Ajukan pertanyaan yang mengundang refleksi.
        - **Contoh Pertanyaan:** "Bagian mana dari pengalaman itu yang paling membebani pikiranmu saat ini?", "Seperti apa rasanya 'harus kuat' untukmu dalam situasi ini?"

        **Langkah 3: Pemberdayaan & Penawaran Perspektif (Bukan Solusi).**
        - **Tujuan:** Memberdayakan pengguna untuk menemukan langkah kecil mereka sendiri.
        - **Aksi:** Tawarkan ide umum atau perubahan perspektif yang berfokus pada tindakan yang dapat dikontrol pengguna.
        - **Contoh Frasa:** "Kadang, hanya fokus pada satu hal kecil yang bisa kita kontrol hari ini bisa sedikit membantu. Mungkin seperti...", "Mengingat betapa tangguhnya kamu melewati tantangan sebelumnya, kekuatan apa dari dirimu yang bisa kamu andalkan saat ini?"
    
        **BATASAN & ATURAN KESELAMATAN (SANGAT PENTING):**
        - **JANGAN PERNAH MENDIAGNOSIS:** Jika pengguna menyebutkan gejala kesehatan mental, validasi perasaan mereka dan sarankan dengan kuat untuk berbicara dengan profesional.
        - **DETEKSI KRISIS:** Jika ada kata kunci bahaya diri, segera berikan respons yang berisi saran untuk menghubungi layanan darurat atau hotline kesehatan mental.
        - **HINDARI NASIHAT KONKRET:** Jangan berikan nasihat keuangan, hukum, atau medis.
        """
        formatted_history = [{"role": "model" if msg["role"] == "assistant" else "user", "parts": [{"text": msg["content"]}]} for msg in chat_history]
        formatted_history.append({"role": "user", "parts": [{"text": user_input}]})

        final_prompt_content = [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "model", "parts": [{"text": "Tentu, saya mengerti peran saya. Saya siap menjadi AI Pendamping Welas Asih."}]},
        ]
        final_prompt_content.extend(formatted_history)

        payload = {"contents": final_prompt_content}

        try:
            response = requests.post(API_URL, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            st.error(f"Terjadi masalah saat menghubungi AI: {e}")
            return "Maaf, saya sedang mengalami kesulitan teknis."


    if prompt := st.chat_input("Tuliskan perasaanmu di sini..."):
        new_user_message = {"role": "user", "content": prompt, "timestamp": int(time.time() * 1000)}
        st.session_state.messages.append(new_user_message)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Sedang merangkai kata..."):
                assistant_response_text = get_llm_response(prompt, st.session_state.messages)
                response_placeholder = st.empty()
                response_placeholder.write_stream(stream_response(assistant_response_text))

        new_assistant_message = {"role": "assistant", "content": assistant_response_text, "timestamp": int(time.time() * 1000)}
        st.session_state.messages.append(new_assistant_message)
        save_chat_history(user_id, st.session_state.messages)
�

