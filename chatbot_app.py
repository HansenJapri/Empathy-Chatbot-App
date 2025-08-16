import streamlit as st
import random
import time
import asyncio
import requests # Pustaka untuk melakukan panggilan API

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Teman Curhat AI",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- Judul dan Deskripsi ---
st.title("Teman Curhat AI Anda 🧠")
st.markdown("""
Selamat datang di versi yang lebih canggih! Saya sekarang didukung oleh **Model Bahasa Skala Besar (LLM)** untuk memberikan pemahaman dan respons yang lebih mendalam dan berempati.
""")
st.warning("""
**Penting:** Saya adalah AI dan bukan pengganti profesional kesehatan mental. 
Saran yang saya berikan dihasilkan oleh AI dan bersifat umum. Mohon pertimbangkan untuk berbicara dengan profesional jika Anda merasa sangat tertekan.
""", icon="⚠️")
st.divider()

# --- Input API Key (PENTING) ---
# Mengambil API key dari secrets management Streamlit untuk keamanan.
# Pastikan Anda sudah mengaturnya di dashboard Streamlit Community Cloud.
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("Kunci API Google tidak ditemukan. Mohon atur di secrets.toml atau di pengaturan Streamlit Cloud.")
    st.stop()
    
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"

# --- Inisialisasi Riwayat Obrolan ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya di sini untuk mendengarkan dengan lebih baik. Apa yang ingin kamu ceritakan?"}
    ]

# --- Menampilkan Pesan dari Riwayat ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- "Model" yang Ditingkatkan: Panggilan ke LLM (Gemini) ---
async def get_llm_response(user_input, chat_history):
    """
    Fungsi ini memanggil LLM (Gemini) untuk mendapatkan respons yang empatik dan solutif.
    Ini adalah inti dari peningkatan kecerdasan chatbot.
    """
    
    # **PROMPT ENGINEERING**: Ini adalah "pelatihan" utama kita.
    # Kita memberikan instruksi yang sangat spesifik kepada model.
    system_prompt = """
    Anda adalah "Teman Curhat AI", seorang asisten AI yang memiliki empati mendalam, suportif, dan tidak menghakimi. 
    Tujuan utama Anda adalah membantu pengguna merasa didengar, divalidasi, dan diberdayakan.
    
    Ikuti TIGA langkah berikut dalam merespons:
    1.  **Validasi Perasaan (Empathy First):** Mulailah selalu dengan mengakui dan memvalidasi perasaan pengguna. Gunakan frasa seperti "Aku mengerti itu pasti terasa berat...", "Wajar sekali kamu merasa begitu...", "Terima kasih sudah berbagi, aku bisa merasakan kekecewaanmu.". Tunjukkan bahwa Anda benar-benar mendengarkan.
    2.  **Eksplorasi Mendalam (Understanding):** Ajukan pertanyaan terbuka yang lembut untuk membantu pengguna merefleksikan situasinya lebih dalam. Contoh: "Apa bagian tersulit dari situasi itu untukmu?", "Sejak kapan kamu mulai merasa seperti ini?". Hindari pertanyaan yang terdengar seperti interogasi.
    3.  **Tawarkan Solusi yang Memberdayakan (Empowerment):** Jika relevan, tawarkan 2-3 ide solusi atau langkah praktis yang bersifat umum, aman, dan bisa dilakukan. Fokus pada tindakan kecil yang bisa mengembalikan rasa kontrol kepada pengguna. Contoh: "Mungkin memecah masalah besar menjadi satu langkah kecil bisa membantu?", "Terkadang menuliskan perasaan di jurnal bisa sedikit melegakan.", "Apakah ada satu orang teman yang bisa kamu hubungi untuk sekadar mengobrol ringan?". JANGAN pernah memberikan nasihat medis, finansial, atau hukum. Selalu ingatkan bahwa ini hanyalah saran umum.

    Gunakan bahasa Indonesia yang hangat, alami, dan mudah dimengerti. Jaga agar respons tetap ringkas dan tidak berlebihan.
    """
    
    # Memformat riwayat obrolan untuk API
    # Gemini menggunakan format 'user' dan 'model'
    formatted_history = []
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        formatted_history.append({"role": role, "parts": [{"text": msg["content"]}]})
        
    # Menambahkan pesan pengguna saat ini
    formatted_history.append({"role": "user", "parts": [{"text": user_input}]})

    # Gabungkan system prompt dengan riwayat
    # Cara sederhana untuk menyisipkan instruksi sistem
    final_prompt_content = [{"role": "user", "parts": [{"text": system_prompt}]},
                            {"role": "model", "parts": [{"text": "Tentu, saya siap menjadi Teman Curhat AI yang empatik dan membantu."}]}]
    final_prompt_content.extend(formatted_history)

    payload = {
        "contents": final_prompt_content
    }

    try:
        # Menggunakan requests untuk melakukan panggilan API
        response = requests.post(API_URL, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status() # Akan error jika status code bukan 2xx
        
        result = response.json()
        
        # Ekstrak teks dari respons JSON yang kompleks
        if (result.get('candidates') and 
            result['candidates'][0].get('content') and 
            result['candidates'][0]['content'].get('parts')):
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            # Fallback jika struktur respons tidak sesuai harapan
            return "Maaf, sepertinya ada sedikit gangguan. Bisa coba ulangi lagi?"

    except requests.exceptions.RequestException as e:
        st.error(f"Terjadi masalah saat menghubungi AI: {e}")
        return "Maaf, saya sedang mengalami kesulitan teknis saat ini. Mohon coba beberapa saat lagi."
    except Exception as e:
        st.error(f"Terjadi kesalahan yang tidak terduga: {e}")
        return "Aduh, ada yang tidak beres. Coba refresh halaman ini."

# --- Input dari Pengguna ---
if prompt := st.chat_input("Tuliskan perasaanmu di sini..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Sedang berpikir..."):
            # Jalankan fungsi async untuk mendapatkan respons dari LLM
            assistant_response = asyncio.run(get_llm_response(prompt, st.session_state.messages))
        
        # Efek mengetik untuk respons yang lebih alami
        full_response = ""
        for chunk in assistant_response.split():
            full_response += chunk + " "
            time.sleep(0.02)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
