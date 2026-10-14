"""baslat.py - "Aç" düğmesi. Programı uyandırır ve çalıştırır."""
import logging
import sys

try:
    from uygulama import uygulama_olustur
    uygulama = uygulama_olustur()  # gunicorn: gunicorn baslat:uygulama
except Exception as hata:
    logging.critical("Uygulama başlatılamadı: %s", hata, exc_info=True)
    print(f"[HATA] Uygulama başlatılamadı: {hata}")
    sys.exit(1)

if __name__ == '__main__':
    try:
        uygulama.run(host='0.0.0.0', port=5000, debug=uygulama.config.get('DEBUG', False))
    except OSError as hata:
        print(f"[HATA] 5000 numaralı port kullanılamıyor (başka bir program açık olabilir): {hata}")
        sys.exit(1)
