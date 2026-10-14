"""yapay_zeka_servisi.py - Tercüman. Soruyu seçilen yapay zekâya iletir, yanıtı geri getirir."""
import logging

import requests
from flask import current_app

log = logging.getLogger(__name__)

GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama-3.3-70b-versatile'
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'
OPENAI_MODEL = 'gpt-4o-mini'
GEMINI_MODEL = 'gemini-2.0-flash'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
MAKS_GECMIS = 10  # yapay zekâya gönderilecek son mesaj sayısı


class YapayZekaServisHatasi(Exception):
    """Yapay zekâ servisi yanıt veremediğinde fırlatılır (mesajı ziyaretçiye gösterilebilir)."""


class YapayZekaServisi:

    # ---- 1) Akıllı seçim ----
    def yanit_uret(self, kullanici_mesaji, sohbet_gecmisi=None):
        saglayici = current_app.config.get('AI_PROVIDER', 'groq').lower()
        anahtarlar = {
            'groq': current_app.config.get('GROQ_API_KEY', ''),
            'openai': current_app.config.get('OPENAI_API_KEY', ''),
            'gemini': current_app.config.get('GEMINI_API_KEY', ''),
        }
        if saglayici not in anahtarlar:
            raise YapayZekaServisHatasi(
                f"Geçersiz AI_PROVIDER değeri: '{saglayici}' (groq / gemini / openai olmalı).")
        if not anahtarlar[saglayici].strip():
            return self._demo_yaniti_ver()  # anahtar yoksa çökme, demo moduna geç

        mesajlar = self._mesajlari_hazirla(kullanici_mesaji, sohbet_gecmisi)
        if saglayici == 'openai':
            return self._openai_cagir(mesajlar)
        if saglayici == 'groq':
            return self._groq_cagir(mesajlar)
        return self._gemini_cagir(mesajlar)

    # ---- 2) Yardımcılar ----
    def _sistem_talimati_olustur(self):
        return current_app.config.get('BUSINESS_CONTEXT', '')

    def _mesajlari_hazirla(self, mesaj, gecmis):
        """Geçmişi temizler (bozuk kayıtları atar) ve son mesajı ekler."""
        temiz = []
        for kayit in (gecmis or [])[-MAKS_GECMIS:]:
            try:
                rol, icerik = kayit['role'], str(kayit['content'])
            except (KeyError, TypeError):
                continue  # bozuk kaydı sessizce atla
            if rol in ('user', 'assistant') and icerik.strip():
                temiz.append({'role': rol, 'content': icerik[:1000]})
        temiz.append({'role': 'user', 'content': mesaj})
        return temiz

    def _istek_gonder(self, url, govde, basliklar, servis_adi):
        """Dış servise istek atar; her tür hatayı anlaşılır bir mesaja çevirir."""
        zaman_asimi = current_app.config.get('AI_ZAMAN_ASIMI', 20)
        try:
            yanit = requests.post(url, json=govde, headers=basliklar, timeout=zaman_asimi)
            yanit.raise_for_status()
            return yanit.json()
        except requests.exceptions.Timeout as hata:
            raise YapayZekaServisHatasi(f'{servis_adi} zamanında yanıt vermedi, lütfen tekrar deneyin.') from hata
        except requests.exceptions.ConnectionError as hata:
            raise YapayZekaServisHatasi(f'{servis_adi} servisine bağlanılamadı. İnternetinizi kontrol edin.') from hata
        except requests.exceptions.HTTPError as hata:
            kod = hata.response.status_code if hata.response is not None else 0
            if kod == 429:
                raise YapayZekaServisHatasi('Çok fazla istek (429). Biraz bekleyin veya AI_PROVIDER=groq yapın.') from hata
            if kod in (401, 403):
                raise YapayZekaServisHatasi(f'{servis_adi} API anahtarı geçersiz. .env dosyasını kontrol edin.') from hata
            raise YapayZekaServisHatasi(f'{servis_adi} servisi hata verdi (HTTP {kod}).') from hata
        except ValueError as hata:  # yanıt JSON değil
            raise YapayZekaServisHatasi(f'{servis_adi} geçersiz bir yanıt döndürdü.') from hata
        except requests.exceptions.RequestException as hata:
            log.error("%s isteği başarısız: %s", servis_adi, hata)
            raise YapayZekaServisHatasi(f'{servis_adi} ile iletişim kurulamadı.') from hata

    def _openai_uyumlu_cagir(self, url, model, anahtar, mesajlar, servis_adi):
        govde = {
            'model': model,
            'messages': [{'role': 'system', 'content': self._sistem_talimati_olustur()}] + mesajlar,
            'temperature': 0.5,
            'max_tokens': 500,
        }
        veri = self._istek_gonder(url, govde, {'Authorization': f'Bearer {anahtar}'}, servis_adi)
        try:
            return veri['choices'][0]['message']['content'].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as hata:
            raise YapayZekaServisHatasi(f'{servis_adi} yanıtı beklenen biçimde değil.') from hata

    # ---- 3) Sağlayıcılar ----
    def _groq_cagir(self, mesajlar):
        return self._openai_uyumlu_cagir(GROQ_URL, GROQ_MODEL,
                                         current_app.config['GROQ_API_KEY'], mesajlar, 'Groq')

    def _openai_cagir(self, mesajlar):
        return self._openai_uyumlu_cagir(OPENAI_URL, OPENAI_MODEL,
                                         current_app.config['OPENAI_API_KEY'], mesajlar, 'OpenAI')

    def _gemini_cagir(self, mesajlar):
        govde = {
            'system_instruction': {'parts': [{'text': self._sistem_talimati_olustur()}]},
            'contents': [{'role': 'model' if m['role'] == 'assistant' else 'user',
                          'parts': [{'text': m['content']}]} for m in mesajlar],
        }
        basliklar = {'x-goog-api-key': current_app.config['GEMINI_API_KEY']}
        veri = self._istek_gonder(GEMINI_URL, govde, basliklar, 'Gemini')
        try:
            return veri['candidates'][0]['content']['parts'][0]['text'].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as hata:
            raise YapayZekaServisHatasi('Gemini yanıtı beklenen biçimde değil.') from hata

    def _demo_yaniti_ver(self):
        return ('Sistem demo modunda çalışıyor, lütfen .env dosyanızı kontrol edin. '
                '(Learn&Live; Erasmus ve yüksek lisans öğrencileri için gündelik yaşam '
                'odaklı dil hazırlık programıdır.)')


yapay_zeka_servisi = YapayZekaServisi()
