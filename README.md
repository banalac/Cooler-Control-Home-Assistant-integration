# CoolerControl Home Assistant integráció

Egyéni (custom) Home Assistant integráció, amely a `coolercontrold` daemon
REST API-ját olvassa `Authorization: Bearer <token>` fejléccel, és minden
felismert hőmérséklet-, fordulatszám- (RPM) és duty%-értékből érzékelő
(sensor) entitást hoz létre.

## Telepítés

1. Másold a `custom_components/coolercontrol` mappát a Home Assistant
   konfigurációs könyvtáradba, úgy hogy a végeredmény
   `config/custom_components/coolercontrol/...` legyen.
2. Indítsd újra a Home Assistant-ot.
3. **Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása →
   CoolerControl**.
4. Add meg:
   - **Host**: `192.168.31.198`
   - **Port**: `11987`
   - **Access token**: a CoolerControl webes felületén, az *Access
     Protection* menüben generált token (elég egy *Read-Only* token, ha
     csak monitorozni szeretnél).
   - **SSL tanúsítvány ellenőrzése**: alapértelmezetten kikapcsolva, mert a
     daemon általában önaláírt (self-signed) tanúsítványt használ. Ha
     saját, hitelesített tanúsítványt állítottál be, bekapcsolhatod.

Az integráció 10 másodpercenként lekérdezi az adatokat, és eszközönként
(fancontroller, AIO, GPU stb.) csoportosítva hozza létre az érzékelőket –
minden hőmérséklet-szenzor °C-ban, minden fordulatszám RPM-ben, minden
duty/load pedig %-ban jelenik meg.

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

## Amit ez az integráció (még) nem csinál

Csak **olvasásra** (sensorokra) készült. Ventilátor/pumpa fordulatszám
vagy profil beállítására (írás, `POST` a daemon felé) szándékosan nem
tartalmaz kódot, mert az írási végpontok pontos JSON payload-ját nem
tudtam megbízhatóan ellenőrizni – rossz payload esetén könnyen félreírná a
hűtésvezérlést.
