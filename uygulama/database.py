"""database.py - Arşiv memuru. Veritabanıyla ilgili HER işlem yalnızca burada yapılır."""
import logging
import sqlite3

from flask import current_app

log = logging.getLogger(__name__)


class VeritabaniHatasi(Exception):
    """Veritabanı işlemi başarısız olduğunda fırlatılır."""


def baglanti_al():
    """Veritabanı dosyasına bağlanır."""
    try:
        baglanti = sqlite3.connect(current_app.config['DATABASE_URL'])
        baglanti.row_factory = sqlite3.Row
        return baglanti
    except sqlite3.Error as hata:
        log.error("Veritabanına bağlanılamadı: %s", hata)
        raise VeritabaniHatasi("Veritabanına bağlanılamadı.") from hata


def veritabani_baslat():
    """Tablo yoksa oluşturur (ilk açılışta)."""
    baglanti = baglanti_al()
    try:
        baglanti.execute('''
            CREATE TABLE IF NOT EXISTS ogrenci_adaylari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isim TEXT NOT NULL,
                telefon TEXT NOT NULL,
                hedef_ulke TEXT,
                dil_seviyesi TEXT,
                mesaj TEXT,
                olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        baglanti.commit()
    except sqlite3.Error as hata:
        baglanti.rollback()
        log.error("Tablo oluşturulamadı: %s", hata)
        raise VeritabaniHatasi("Tablo oluşturulamadı.") from hata
    finally:
        baglanti.close()


def ogrenci_adayi_ekle(isim, telefon, hedef_ulke, dil_seviyesi, mesaj):
    """Yeni öğrenci adayını arşive ekler. ? yer tutucuları SQL Injection'ı önler."""
    baglanti = baglanti_al()
    try:
        imlec = baglanti.cursor()
        imlec.execute(
            'INSERT INTO ogrenci_adaylari (isim, telefon, hedef_ulke, dil_seviyesi, mesaj) '
            'VALUES (?, ?, ?, ?, ?)',
            (isim, telefon, hedef_ulke, dil_seviyesi, mesaj)
        )
        baglanti.commit()  # değişikliği kalıcı yap
        return imlec.lastrowid
    except sqlite3.Error as hata:
        baglanti.rollback()  # yarım kalan işlemi geri al
        log.error("Kayıt eklenemedi: %s", hata)
        raise VeritabaniHatasi("Kayıt eklenemedi.") from hata
    finally:
        baglanti.close()


def tum_adaylari_getir():
    """Tüm öğrenci adaylarını en yeniden eskiye sıralı getirir."""
    baglanti = baglanti_al()
    try:
        satirlar = baglanti.execute(
            'SELECT * FROM ogrenci_adaylari ORDER BY olusturulma_tarihi DESC, id DESC'
        ).fetchall()
        return [dict(satir) for satir in satirlar]
    except sqlite3.Error as hata:
        log.error("Kayıtlar getirilemedi: %s", hata)
        raise VeritabaniHatasi("Kayıtlar getirilemedi.") from hata
    finally:
        baglanti.close()


def istatistik_getir():
    """Yönetim paneli kartları: toplam, bu ay, bugün."""
    baglanti = baglanti_al()
    try:
        s = baglanti.execute('''
            SELECT
              COUNT(*) AS toplam,
              COALESCE(SUM(strftime('%Y-%m', olusturulma_tarihi) = strftime('%Y-%m','now')), 0) AS bu_ay,
              COALESCE(SUM(date(olusturulma_tarihi) = date('now')), 0) AS bugun
            FROM ogrenci_adaylari
        ''').fetchone()
        return {'toplam': s['toplam'], 'bu_ay': s['bu_ay'], 'bugun': s['bugun']}
    except sqlite3.Error as hata:
        log.error("İstatistik hesaplanamadı: %s", hata)
        raise VeritabaniHatasi("İstatistik hesaplanamadı.") from hata
    finally:
        baglanti.close()
