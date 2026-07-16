# CoolerControl Home Assistant integráció

Egyéni (custom) Home Assistant integráció, amely a `coolercontrold` daemon
REST API-ját olvassa `Authorization: Bearer <token>` fejléccel, és minden
felismert hőmérséklet-, fordulatszám- (RPM) és duty%-értékből érzékelő
(sensor) entitást hoz létre.

## Telepítés

1. A. opció: Másold a `custom_components/coolercontrol` mappát a Home Assistant
   konfigurációs könyvtáradba, úgy hogy a végeredmény
   `config/custom_components/coolercontrol/...` legyen.
   
2. B. opció: HACS-ban add hozzá egyéni repónak a https://github.com/banalac/Cooler-Control-Home-Assistant-integration címet és állítsd be integrációnak.
    Hozzáadás után töltsd le HACS-ból.
3. Indítsd újra a Home Assistant-ot.
5. **Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása →
   CoolerControl**.
6. Add meg:
   - **Host**: pl. `192.168.31.198`
   - **Port**: `11987`
   - **Access token**: a CoolerControl webes felületén, az *Access
     Protection* menüben generált token (elég egy *Read-Only* token, ha
     csak monitorozni szeretnél).
   - **SSL tanúsítvány ellenőrzése**: alapértelmezetten kikapcsolva, mert a
     daemon általában önaláírt (self-signed) tanúsítványt használ. Ha
     saját, hitelesített tanúsítványt állítottál be, bekapcsolhatod.

Az integráció 1 másodpercenként lekérdezi az adatokat (a `const.py`
`DEFAULT_SCAN_INTERVAL` értéke), és eszközönként (fancontroller, AIO, GPU
stb.) csoportosítva hozza létre az érzékelőket – minden hőmérséklet-szenzor
°C-ban, minden fordulatszám RPM-ben, minden duty/load pedig %-ban jelenik
meg.

## Fontos megjegyzés a daemon API-járól

A CoolerControl daemon REST API-ja nincs hivatalosan, stabil formában
dokumentálva (nincs publikált OpenAPI spec a fő projektben), csak annyi
biztos:

- a daemon HTTPS-en fut a megadott porton (alapértelmezés: `11987`),
  önaláírt tanúsítvánnyal,
- minden kérésbe `Authorization: Bearer <token>` fejléc kell,
- a `GET /devices` végpont biztosan létezik és eszközlistát ad vissza,
- az élő mérési adatokat (hőmérséklet, RPM, duty) a UI a `/status`
  végponton keresztül kéri le.

Mivel a pontos JSON mezőneveket (pl. `status_history` / `temps` /
`channels`) nem tudtam 100%-osan, hivatalos forrásból ellenőrizni, a
`coordinator.py` **védekezően** van megírva: bármilyen eszközlistát kap,
megpróbálja megtalálni benne a hőmérséklet- és csatorna-adatokat, és csak
azokból hoz létre entitást, amit ténylegesen talál. Ha az első indítás
után nem jelenik meg érzékelő, vagy hiányzik valami:

1. Nézd meg a Home Assistant logot (`custom_components.coolercontrol`
   debug szinten) – kiírja a nyers eszköz-kulcsokat, ha nem talált benne
   `temps`/`channels` mezőt.
2. Nyisd meg a daemon webes felületét a böngészőben, és a Fejlesztői
   eszközök → Hálózat fülön nézd meg, pontosan milyen JSON-t ad vissza a
   `/status` hívás – ha a mezőnevek eltérnek, a `coordinator.py`
   `_parse_device` függvényét könnyű hozzáigazítani.
3. Alternatívaként terminálból is tesztelheted:
   ```
   curl -k -H "Authorization: Bearer <TOKEN>" https://192.168.31.198:11987/status
   ```

## Ikon a Beállítások → Integrációk listában

A `custom_components/coolercontrol/brand/` mappa tartalmaz egy saját,
eredeti ("cooling fan" témájú) ikont `icon.png` / `icon@2x.png` /
`logo.png` / `logo@2x.png` néven. **Home Assistant 2026.3-tól** ez a
hivatalos módja annak, hogy egy custom integrációnak saját ikonja legyen
a felületen — nem kell hozzá a `home-assistant/brands` repóba PR-t
küldeni, a HA automatikusan felismeri és megjeleníti, amint az
integrációt telepíted és újraindítod a rendszert.

Ha 2026.3-nál régebbi Home Assistant verziót használsz, ez a mechanizmus
nem működik nálad (akkor a `brands` repóba kellene PR-t küldeni, ami
nyilvános, hosszabb folyamat) — ez esetben az integráció generikus
ikonnal fog megjelenni, ami nem befolyásolja a működését.

Ha másik ikont/logót szeretnél, csak cseréld le a 4 fájlt a `brand/`
mappában ugyanazokkal a fájlnevekkel (256×256, ill. 512×512 px, átlátszó
háttér ajánlott).

## Amit ez az integráció (még) nem csinál

Csak **olvasásra** (sensorokra) készült. Ventilátor/pumpa fordulatszám
vagy profil beállítására (írás, `POST` a daemon felé) szándékosan nem
tartalmaz kódot, mert az írási végpontok pontos JSON payload-ját nem
tudtam megbízhatóan ellenőrizni – rossz payload esetén könnyen félreírná a
hűtésvezérlést.
