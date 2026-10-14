// Wix Velo örneği - Wix editöründe ID'ler: #inputMesaj, #btnSor, #txtCevap
import { fetch } from 'wix-fetch';

const API = 'https://SIZIN-APP.onrender.com';  // Render adresiniz
let gecmis = [];

$w.onReady(function () {
  $w('#btnSor').onClick(sohbetGonder);
});

async function sohbetGonder() {
  const mesaj = $w('#inputMesaj').value;
  if (!mesaj) return;
  try {
    const cevap = await fetch(`${API}/api/sohbet`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mesaj, gecmis })
    });
    const veri = await cevap.json();
    if (veri.basari) {
      $w('#txtCevap').text = veri.cevap;
      gecmis.push({ role: 'user', content: mesaj });
      gecmis.push({ role: 'assistant', content: veri.cevap });
    } else {
      $w('#txtCevap').text = veri.hata;
    }
  } catch (hata) {
    $w('#txtCevap').text = 'Sunucuya ulaşılamadı, lütfen tekrar deneyin.';
  }
}
