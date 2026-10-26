# GHL-kalenderwidget

Kalender en uitslagen van Heren A en Dames A voor golazohaasrodeleuven.be.

- `index.html` — de widget (`?ploeg=heren` of `?ploeg=dames`)
- `data.json` — wedstrijden + uitslagen, automatisch bijgewerkt
- `scripts/update_data.py` — haalt de data op bij volleyscores.be
- `.github/workflows/update.yml` — draait het script elke 2 uur

## Opzetten (eenmalig)
1. Maak een publieke repository, bv. `ghl-kalender`, en upload deze bestanden.
2. Settings → Pages → Source: *Deploy from a branch*, branch `main`, map `/ (root)`.
3. Actions → *Kalender bijwerken* → *Run workflow* om de eerste update te testen.

## Op de website (embedded-codeblok)
Heren A (pagina /kalender):
```html
<iframe src="https://<gebruiker>.github.io/ghl-kalender/?ploeg=heren" style="border:0;width:100%;height:900px" title="Kalender Heren A"></iframe>
```
Dames A (pagina /kalender-da): idem met `?ploeg=dames`.
