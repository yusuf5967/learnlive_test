"""ayarlar.py - Kontrol paneli: tüm ayarlar tek yerde toplanır.
Gizli değerler (API anahtarları) koda yazılmaz, .env dosyasından okunur."""
import os
import logging
from dotenv import load_dotenv

try:
    load_dotenv()  # .env dosyasındaki gizli ayarları oku
except Exception as hata:  # .env bozuksa program çökmesin
    logging.warning("'.env' okunamadı, varsayılan değerler kullanılacak: %s", hata)

PROJE_KOKU = os.path.dirname(os.path.abspath(__file__))


def _veritabani_yolu():
    """DATABASE_URL göreli ise proje klasörüne göre mutlak yola çevirir."""
    yol = os.environ.get('DATABASE_URL', 'learnlive.db')
    return yol if os.path.isabs(yol) else os.path.join(PROJE_KOKU, yol)


class Ayarlar:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'varsayilan-sifre')
    DATABASE_URL = _veritabani_yolu()
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'groq')
    AI_ZAMAN_ASIMI = 20  # saniye
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*')
    BUSINESS_CONTEXT = os.environ.get(
        'BUSINESS_CONTEXT',
        "Sen Learn&Live dil hazırlık programının satış ve bilgilendirme asistanısın. "
        "Learn&Live, Erasmus veya yüksek lisans için yurt dışına gidecek üniversite "
        "öğrencilerine yönelik bir dil hazırlık programıdır. Akademik başarının yanında "
        "ev kiralama, ulaşım, alışveriş ve sosyal iletişim gibi gündelik yaşam "
        "senaryolarına odaklanır. Program; senaryo tabanlı öğrenme, diyalog "
        "simülasyonları, kültürel uyum atölyeleri ve dijital pratik egzersizlerinden "
        "oluşur; gelişim ön test-son test ve senaryo performansıyla ölçülür. Başlangıçta "
        "İngilizce pilot programı vardır; ödeme abonelik veya modül bazlıdır, pilotta "
        "düşük ücretli ya da ücretsiz deneme sunulur. Kibar, net ve profesyonel ol; "
        "bilmediğin fiyat/tarih gibi bilgileri uydurma; ilgilenen öğrenciyi formu "
        "doldurmaya yönlendir. Türkçe yanıt ver."
    )
    DEBUG = False


class GelistirmeAyarlari(Ayarlar):
    DEBUG = True   # hatalar görünür


class UretimAyarlari(Ayarlar):
    DEBUG = False  # hatalar gizli


ayar_secici = {
    'gelistirme': GelistirmeAyarlari,
    'uretim': UretimAyarlari,
}
