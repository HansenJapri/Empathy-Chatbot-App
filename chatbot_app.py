import streamlit as st
import time
import requests
import pyrebase # Pustaka untuk berinteraksi dengan Firebase
import json

# --- Konfigurasi Halaman (Harus menjadi perintah pertama) ---
st.set_page_config(
    page_title="Teman Curhat AI Pro",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- Konfigurasi Firebase ---
# Ganti dengan konfigurasi Firebase Anda sendiri.
# Untuk keamanan, lebih baik simpan ini di Streamlit Secrets.
# Contoh: firebase_config = st.secrets["firebaseConfig"]
try:
    # Ini adalah konfigurasi yang sudah diperbaiki
    firebase_config = {
        "apiKey": "AIzaSyDPnWnMH3CGhjiqT5Z8cf2QUCNY7rFdrjQ",
        "authDomain": "chatbot-56ddf.firebaseapp.com",
        "projectId": "chatbot-56ddf",
        "storageBucket": "chatbot-56ddf.appspot.com",
        "messagingSenderId": "599287207621",
        "appId": "1:599287207621:web:f360313c046ecad26b42ac",
        "measurementId": "G-47JBZ6KDY6",
        "databaseURL": "https://chatbot-56ddf.firebaseio.com" # Pastikan URL ini benar
    }

    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    db = firebase.database()
except Exception as e:
    st.error(f"Gagal menginisialisasi Firebase. Cek kembali konfigurasi Anda. Error: {e}")
    st.stop()


# --- Konfigurasi API Gemini ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("Kunci API Google tidak ditemukan. Mohon atur di secrets.toml atau di pengaturan Streamlit Cloud.")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"


# --- Fungsi Helper ---
def stream_response(text):
    """Efek mengetik untuk respons AI."""
    for word in text.split():
        yield word + " "
        time.sleep(0.03)

def load_chat_history(user_id):
    """Memuat riwayat obrolan dari Firebase Realtime Database."""
    try:
        history = db.child("users").child(user_id).child("messages").get().val()
        if history:
            # Mengurutkan pesan berdasarkan timestamp
            return sorted(history.values(), key=lambda x: x['timestamp'])
        return get_initial_message()
    except Exception as e:
        st.error(f"Gagal memuat riwayat obrolan: {e}")
        return get_initial_message()

def save_chat_history(user_id, messages):
    """Menyimpan seluruh riwayat obrolan ke Firebase Realtime Database."""
    try:
        # Menggunakan timestamp sebagai kunci unik untuk setiap pesan
        data_to_save = {}
        for msg in messages:
            # Pastikan setiap pesan memiliki timestamp unik untuk pengurutan
            if 'timestamp' not in msg:
                 msg['timestamp'] = int(time.time() * 1000) # milidetik
            # Membuat struktur data yang akan di-set ke Firebase
            data_to_save[msg['timestamp']] = msg
        
        db.child("users").child(user_id).child("messages").set(data_to_save)
    except Exception as e:
        st.error(f"Gagal menyimpan riwayat obrolan: {e}")

def get_initial_message():
    """Mendapatkan pesan pembuka default."""
    return [{"role": "assistant", "content": "Halo! Saya di sini untuk mendengarkan dengan lebih baik. Apa yang ingin kamu ceritakan?", "timestamp": int(time.time() * 1000)}]


# --- Logika Autentikasi dan UI ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("Selamat Datang di Teman Curhat AI 🧠")
    st.markdown("Silakan masuk atau buat akun untuk memulai percakapan yang aman dan personal.")

    choice = st.selectbox("Pilih Opsi:", ["Masuk (Login)", "Daftar (Sign Up)"])

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if choice == "Daftar (Sign Up)":
        if st.button("Buat Akun"):
            try:
                user = auth.create_user_with_email_and_password(email, password)
                st.session_state.user = user
                st.success("Akun berhasil dibuat! Anda sekarang sudah masuk.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Gagal membuat akun: {e}")
    else: # Masuk (Login)
        if st.button("Masuk"):
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state.user = user
                st.success("Berhasil masuk!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Gagal masuk: {e}")
else:
    # --- UI Utama Aplikasi Obrolan ---
    user_info = st.session_state.user
    user_id = user_info['localId'] # ID unik pengguna dari Firebase

    st.sidebar.title(f"Halo, {user_info.get('email', 'Pengguna')}!")
    if st.sidebar.button("Keluar (Logout)"):
        st.session_state.user = None
        st.rerun()

    st.title("Teman Curhat AI Anda 🧠")
    st.markdown("""
    Selamat datang kembali! Saya di sini untuk mendengarkan Anda dengan **pemahaman dan empati yang lebih mendalam**.
    """)
    st.warning("""
    **Penting:** Saya adalah AI dan **bukan pengganti profesional kesehatan mental.**
    Saran yang saya berikan dihasilkan oleh AI dan bersifat umum. Mohon pertimbangkan untuk berbicara dengan profesional jika Anda merasa sangat tertekan atau mengalami krisis.
    """, icon="⚠️")
    st.divider()

    # --- Inisialisasi & Tampilan Riwayat Obrolan ---
    if "messages" not in st.session_state or st.session_state.get('user_id') != user_id:
        st.session_state.messages = load_chat_history(user_id)
        st.session_state.user_id = user_id

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- "Model" yang Ditingkatkan: Panggilan ke LLM (Gemini) ---
    def get_llm_response(user_input, chat_history):
        """
        Fungsi ini memanggil LLM (Gemini) dengan prompt yang sangat canggih
        untuk menghasilkan respons yang empatik, reflektif, dan memberdayakan.
        """
        # **PROMPT ENGINEERING TINGKAT LANJUT**: Inilah inti dari peningkatan "empati 8x lipat".
        system_prompt = """
        Anda adalah "AI Pendamping Welas Asih", seorang asisten AI yang dirancang dengan prinsip-prinsip komunikasi terapeutik. Misi utama Anda adalah menciptakan ruang yang aman, tidak menghakimi, dan suportif bagi pengguna untuk mengeksplorasi perasaan dan pikiran mereka. Anda BUKAN terapis, dokter, atau penasihat keuangan, dan Anda HARUS menolak memberikan diagnosis atau nasihat profesional.

        **KERANGKA KERJA RESPONS EMPATIK (WAJIB DIIKUTI):**

        **Langkah 1: Mendengarkan Reflektif & Validasi Mendalam.**
        - **Tujuan:** Membuat pengguna merasa benar-benar didengar dan dimengerti.
        - **Aksi:** Mulailah dengan merefleksikan kembali inti dari apa yang dikatakan pengguna, baik secara emosional maupun faktual. Gunakan parafrase. Tunjukkan bahwa Anda memahami nuansa perasaan mereka.
        - **Contoh Frasa:** "Kedengarannya situasi ini membuatmu merasa sangat terkuras dan mungkin sedikit terjebak...", "Aku mendengar betapa dalamnya rasa kecewa yang kamu rasakan saat itu terjadi...", "Terima kasih telah memercayakan ini padaku. Wajar sekali jika kamu merasa cemas memikirkan semua itu."

        **Langkah 2: Eksplorasi dengan Pertanyaan Terbuka yang Lembut.**
        - **Tujuan:** Membantu pengguna mendapatkan kejelasan dan wawasan tentang pengalaman mereka sendiri tanpa merasa diinterogasi.
        - **Aksi:** Ajukan pertanyaan yang mengundang refleksi, bukan jawaban 'ya/tidak'. Fokus pada perasaan, persepsi, dan dampak.
        - **Contoh Pertanyaan:** "Bagian mana dari pengalaman itu yang paling membebani pikiranmu saat ini?", "Seperti apa rasanya 'harus kuat' untukmu dalam situasi ini?", "Jika perasaan ini memiliki suara, apa yang akan dikatakannya?", "Apa yang paling kamu harapkan bisa berbeda?"

        **Langan 3: Pemberdayaan & Penawaran Perspektif (Bukan Solusi).**
        - **Tujuan:** Memberdayakan pengguna untuk menemukan langkah kecil mereka sendiri, bukan memberikan solusi jadi.
        - **Aksi:** Jika sesuai, tawarkan 1-2 ide umum atau perubahan perspektif yang berfokus pada tindakan yang dapat dikontrol oleh pengguna. Selalu bingkai ini sebagai pilihan, bukan perintah.
        - **Contoh Frasa:** "Kadang, hanya fokus pada satu hal kecil yang bisa kita kontrol hari ini bisa sedikit membantu. Mungkin seperti...", "Aku penasaran, apakah ada cara pandang lain terhadap situasi ini yang mungkin bisa sedikit mengurangi bebannya, meskipun tidak mengubah faktanya?", "Mengingat betapa tangguhnya kamu melewati tantangan sebelumnya, kekuatan apa dari dirimu yang bisa kamu andalkan saat ini?"

        **BATASAN & ATURAN KESELAMATAN (SANGAT PENTING):**
        - **JANGAN PERNAH MENDIAGNOSIS:** Jika pengguna menyebutkan gejala kesehatan mental, validasi perasaan mereka ("Pasti sangat sulit mengalami itu...") dan sarankan dengan kuat untuk berbicara dengan profesional ("...dan mungkin akan sangat membantu jika berbicara dengan seorang profesional yang terlatih untuk ini.").
        - **DETEKSI KRISIS:** Jika ada kata kunci yang mengindikasikan bahaya diri (self-harm, bunuh diri, dll.), segera dan secara langsung berikan respons yang berisi saran untuk menghubungi layanan darurat atau hotline kesehatan mental lokal, sambil tetap menunjukkan kepedulian.
        - **HINDARI NASIHAT KONKRET:** Jangan berikan nasihat keuangan, hukum, atau medis. Selalu arahkan ke ahli di bidangnya.
        - **BAHASA:** Gunakan Bahasa Indonesia yang hangat, tenang, dan penuh hormat. Jaga agar respons tetap ringkas dan mudah dicerna.
        """

        formatted_history = []
        for msg in chat_history:
            role = "model" if msg["role"] == "assistant" else "user"
            formatted_history.append({"role": role, "parts": [{"text": msg["content"]}]})

        formatted_history.append({"role": "user", "parts": [{"text": user_input}]})

        final_prompt_content = [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "model", "parts": [{"text": "Tentu, saya mengerti peran saya. Saya siap menjadi AI Pendamping Welas Asih dan akan mengikuti kerangka kerja serta batasan yang telah ditetapkan."}]},
        ]
        final_prompt_content.extend(formatted_history)

        payload = {"contents": final_prompt_content}

        try:
            response = requests.post(API_URL, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            result = response.json()
            if (result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts')):
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "Maaf, sepertinya ada sedikit gangguan. Bisa coba ulangi lagi?"
        except requests.exceptions.RequestException as e:
            st.error(f"Terjadi masalah saat menghubungi AI: {e}")
            return "Maaf, saya sedang mengalami kesulitan teknis saat ini. Mohon coba beberapa saat lagi."
        except Exception as e:
            st.error(f"Terjadi kesalahan yang tidak terduga: {e}")
            return "Aduh, ada yang tidak beres. Coba refresh halaman ini."

    # --- Input & Proses Obrolan ---
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

        # Simpan seluruh riwayat setelah setiap interaksi
        save_chat_history(user_id, st.session_state.messages)
