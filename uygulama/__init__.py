"""uygulama/__init__.py - Montaj hattı: parçaları birleştirip çalışan uygulamayı üretir."""
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from ayarlar import ayar_secici
from uygulama.database import veritabani_baslat, VeritabaniHatasi


def _log_ayarla(uygulama):
    """Hataları hem ekrana hem learnlive.log dosyasına yazar."""
    bicim = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    yoneticiler = [logging.StreamHandler()]
    try:
        yoneticiler.append(logging.FileHandler('learnlive.log', encoding='utf-8'))
    except OSError as hata:  # dosyaya yazılamıyorsa sadece ekrana yaz
        print(f"[UYARI] Log dosyası açılamadı: {hata}")
    kok = logging.getLogger()
    kok.setLevel(logging.INFO)
    if not kok.handlers:
        for y in yoneticiler:
            y.setFormatter(bicim)
            kok.addHandler(y)


def uygulama_olustur(ayar_adi=None):
    uygulama = Flask(__name__, template_folder='sablonlar')

    # 1) Ayarları yükle (geliştirme mi, üretim mi?)
    ayar_adi = ayar_adi or os.environ.get('FLASK_ORTAMI', 'gelistirme')
    secilen_ayar = ayar_secici.get(ayar_adi, ayar_secici['gelistirme'])
    uygulama.config.from_object(secilen_ayar)
    _log_ayarla(uygulama)

    # 2) Dış sitelerin bağlanmasına izin ver (CORS)
    izinli = uygulama.config.get('CORS_ALLOWED_ORIGINS', '*')
    kaynaklar = '*' if izinli.strip() == '*' else [o.strip() for o in izinli.split(',') if o.strip()]
    CORS(uygulama, origins=kaynaklar, methods=['GET', 'POST', 'OPTIONS'])

    # 3) Veritabanı tablosunu hazırla (yoksa oluştur)
    try:
        with uygulama.app_context():
            veritabani_baslat()
    except VeritabaniHatasi as hata:
        logging.critical("Veritabanı hazırlanamadı: %s", hata)
        raise

    # 4) Adresleri (rotaları) sisteme tanıt
    from uygulama.rotalar import api_arayuzu, sayfa_arayuzu
    uygulama.register_blueprint(api_arayuzu, url_prefix='/api')
    uygulama.register_blueprint(sayfa_arayuzu)

    # 5) Genel hata yakalayıcılar (JSON döner, program çökmez)
    @uygulama.errorhandler(404)
    def bulunamadi(_hata):
        return jsonify({'basari': False, 'hata': 'Adres bulunamadı.'}), 404

    @uygulama.errorhandler(405)
    def yontem_yok(_hata):
        return jsonify({'basari': False, 'hata': 'Bu adres için izin verilmeyen yöntem.'}), 405

    @uygulama.errorhandler(Exception)
    def beklenmeyen_hata(hata):
        logging.exception("Beklenmeyen hata: %s", hata)
        return jsonify({'basari': False, 'hata': 'Beklenmeyen bir sunucu hatası oluştu.'}), 500

    return uygulama
