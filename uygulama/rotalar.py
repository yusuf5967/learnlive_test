"""rotalar.py - Trafik polisi. Gelen isteği doğru yere yönlendirir, kendisi iş yapmaz."""
import csv
import io
import logging
import re

from flask import Blueprint, Response, jsonify, render_template, request

from uygulama import database
from uygulama.database import VeritabaniHatasi
from uygulama.servisler.yapay_zeka_servisi import yapay_zeka_servisi, YapayZekaServisHatasi

log = logging.getLogger(__name__)

api_arayuzu = Blueprint('api', __name__)
sayfa_arayuzu = Blueprint('sayfa', __name__)

TELEFON_DESENI = re.compile(r'^\+?[0-9 ()\-]{7,20}$')
GECERLI_SEVIYELER = {'', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'}


def _hata(mesaj, kod):
    return jsonify({'basari': False, 'hata': mesaj}), kod


# ---------- SAYFALAR ----------
@sayfa_arayuzu.route('/')
def ana_sayfa():
    return render_template('index.html')


@sayfa_arayuzu.route('/panel')
def panel():
    return render_template('dashboard.html')


@sayfa_arayuzu.route('/saglik-durumu')
def saglik_durumu():
    """Sunucu çalışıyor mu? Veritabanına da ulaşılabiliyor mu?"""
    try:
        database.istatistik_getir()
        return jsonify({'durum': 'calisiyor', 'veritabani': 'tamam'})
    except VeritabaniHatasi as hata:
        return jsonify({'durum': 'sorunlu', 'veritabani': str(hata)}), 503


# ---------- API ----------
@api_arayuzu.route('/sohbet', methods=['POST'])
def sohbet_et():
    veri = request.get_json(silent=True)  # bozuk JSON gelirse None döner
    if not isinstance(veri, dict):
        return _hata('Geçerli bir JSON gönderilmedi.', 400)

    mesaj = (veri.get('mesaj') or '').strip()
    gecmis = veri.get('gecmis', [])
    if not mesaj:
        return _hata('Mesaj boş olamaz.', 400)
    if len(mesaj) > 1000:
        return _hata('Mesaj en fazla 1000 karakter olabilir.', 400)
    if not isinstance(gecmis, list):
        return _hata("'gecmis' bir liste olmalıdır.", 400)

    try:
        yanit = yapay_zeka_servisi.yanit_uret(mesaj, gecmis)
        return jsonify({'basari': True, 'cevap': yanit})
    except YapayZekaServisHatasi as hata:
        log.warning("Yapay zekâ hatası: %s", hata)
        return _hata(str(hata), 503)
    except Exception:
        log.exception("Sohbette beklenmeyen hata")
        return _hata('Sohbet sırasında beklenmeyen bir hata oluştu.', 500)


@api_arayuzu.route('/adaylar', methods=['POST'])
def aday_kaydet():
    veri = request.get_json(silent=True)
    if not isinstance(veri, dict):
        return _hata('Geçerli bir JSON gönderilmedi.', 400)

    isim = (veri.get('isim') or '').strip()
    telefon = (veri.get('telefon') or '').strip()
    hedef_ulke = (veri.get('hedef_ulke') or '').strip()
    dil_seviyesi = (veri.get('dil_seviyesi') or '').strip().upper()
    mesaj = (veri.get('mesaj') or '').strip()

    if len(isim) < 2:
        return _hata('Lütfen adınızı ve soyadınızı yazın.', 400)
    if not TELEFON_DESENI.match(telefon):
        return _hata('Geçerli bir telefon numarası girin (örn. +90 555 000 0000).', 400)
    if dil_seviyesi not in GECERLI_SEVIYELER:
        return _hata('Dil seviyesi A1-C2 arasında olmalıdır.', 400)
    if len(mesaj) > 1000 or len(isim) > 100 or len(hedef_ulke) > 100:
        return _hata('Girilen alanlardan biri çok uzun.', 400)

    try:
        yeni_id = database.ogrenci_adayi_ekle(isim, telefon, hedef_ulke, dil_seviyesi, mesaj)
        return jsonify({'basari': True, 'mesaj': 'Kaydınız alındı, 48 saat içinde dönüş yapacağız.',
                        'id': yeni_id}), 201
    except VeritabaniHatasi as hata:
        return _hata(str(hata), 500)


@api_arayuzu.route('/adaylar', methods=['GET'])
def adaylari_listele():
    try:
        adaylar = database.tum_adaylari_getir()
        return jsonify({'basari': True, 'toplam': len(adaylar), 'adaylar': adaylar,
                        'istatistik': database.istatistik_getir()})
    except VeritabaniHatasi as hata:
        return _hata(str(hata), 500)


@api_arayuzu.route('/adaylar/csv', methods=['GET'])
def adaylari_csv_indir():
    try:
        adaylar = database.tum_adaylari_getir()
    except VeritabaniHatasi as hata:
        return _hata(str(hata), 500)

    try:
        cikti = io.StringIO()
        sutunlar = ['id', 'isim', 'telefon', 'hedef_ulke', 'dil_seviyesi', 'mesaj', 'olusturulma_tarihi']
        yazici = csv.DictWriter(cikti, fieldnames=sutunlar, extrasaction='ignore')
        yazici.writeheader()
        yazici.writerows(adaylar)
        # utf-8-sig: Excel'de Türkçe karakterler bozulmasın
        return Response('\ufeff' + cikti.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=ogrenci_adaylari.csv'})
    except Exception:
        log.exception("CSV oluşturulamadı")
        return _hata('CSV dosyası oluşturulamadı.', 500)
