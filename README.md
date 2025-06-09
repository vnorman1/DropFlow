# 🚀 DropFlow -  Helyi Fájlmegosztó

**DropFlow** egy modern, letisztult webes fájlmegosztó alkalmazás, amely lehetővé teszi a fájlok egyszerű feltöltését, megosztását és kezelését helyi hálózaton.

## ✨ Főbb Funkciók

### 🎨 **Modern UI/UX**
- **Sötét/Világos téma** - Témaváltás
- **Responsive design** - Tökéletes megjelenés minden eszközön
- **Rácsnézet és listanézet** - Kétféle fájlmegjelenítési mód
- **Intuitív kezelőfelület** - Letisztult és modern design

### 📁 **Fájlkezelés**
- **Drag & Drop feltöltés** - Húzd és ejtsd a fájlokat
- **Többszörös fájlfeltöltés** - Több fájl egyszerre
- **Élő előnézet** - Képek, videók, hangfájlok és dokumentumok
- **Valós idejű törlés** - AJAX-alapú törlés oldal újratöltés nélkül
- **Intelligens keresés és rendezés** - Gyors keresés és szűrés
- **Keresztplatform szinkronizálás** - Automatikus frissítés más eszközökről

### 💬 **Valós Idejű Chat**
- **Socket.IO alapú kommunikáció** - Azonnali üzenetküldés
- **Többfelhasználós chat** - Egyidejű beszélgetések
- **Gépelés jelzés** - Láthatod, amikor mások gépelnek
- **Üzenet előzmények** - Korábbi beszélgetések megőrzése
- **Értesítések** - Új üzenetek jelzése
- **Felhasználónév kezelés** - Személyre szabható azonosítás

### 📱 **Hálózati Funkcók**
- **QR kód generálás** - Könnyű mobilos hozzáférés
- **Helyi IP felderítés** - Automatikus hálózati konfiguráció
- **Hálózati interfészek megjelenítése**
- **Keresztplatform kompatibilitás** - Minden eszközön működik

### 📊 **Rendszermonitorozás**
- **Élő tárhely információ** - Szabad/foglalt hely megjelenítése
- **CPU és RAM használat** - Valós idejű rendszerterhelés
- **Feltöltött fájlok statisztikája** - Fájlok száma és mérete
- **Hálózati interfészek listája** - IP címek megjelenítése
- **Automatikus frissítés** - 5 másodpercenkénti adatfrissítés

## 🛠️ Telepítés és Indítás

### 1. **Előfeltételek**
```bash
Python 3.7+ telepítve
```

### 2. **Függőségek telepítése**
```bash
pip install -r requirements.txt
```

### 3. **Mappa létrehozása**
```bash
mkdir uploads
```
### 4. **Alkalmazás indítása**
```bash
python app_clean.py
```


### 4. **Hozzáférés**
- **Böngészőben:** `http://localhost:5000`
- **Hálózaton:** `http://[LOCAL_IP]:5000`
- **Mobil eszközről:** QR kód beolvasásával

## 📋 Függőségek

| Csomag | Verzió | Leírás |
|--------|--------|---------|
| Flask | >=2.3.0 | Webes keretrendszer |
| Werkzeug | >=2.3.0 | WSGI utility könyvtár |
| qrcode | >=7.4.0 | QR kód generálás |
| Pillow | >=10.0.0 | Képfeldolgozás |
| psutil | >=5.9.0 | Rendszerinformációk |
| Flask-SocketIO | >=5.3.0 | Valós idejű kommunikáció |
| python-socketio | >=5.8.0 | Socket.IO kliens/szerver |

## 🎯 Használat

### **Fájlfeltöltés**
1. **Drag & Drop:** Húzd a fájlokat a feltöltési területre
2. **Tallózás:** Kattints a "Fájlok tallózása" gombra
3. **Mobil:** QR kóddal nyisd meg mobilon és töltsd fel

### **Fájlmegtekintés**
- **Rácsnézet:** Thumbnail előnézetekkel
- **Listanézet:** Részletes fájlinformációkkal
- **Élő előnézet:** Kattints a fájlra az előnézethez

### **Fájlkezelés**
- **Letöltés:** Kattints a letöltés ikonra
- **Törlés:** Kattints a törlés ikonra (nincs oldal újratöltés)
- **Keresés:** Használd a keresőmezőt a szűréshez

### **Chat használata**
- **Chat megnyitása:** Kattints a beszélgetés ikonra a fejlécben
- **Felhasználónév:** Állítsd be a nevedet a beszélgetéshez
- **Üzenetküldés:** Írj egy üzenetet és nyomj Entert (Shift+Enter = új sor)
- **Értesítések:** Piros pont jelzi az új üzeneteket
- **Gépelés jelzés:** Láthatod, amikor mások éppen gépelnek

## 🔧 Konfiguráció

### **Alapbeállítások**
```python
UPLOAD_FOLDER = 'uploads'    # Feltöltési könyvtár
PORT = 5000                  # Szerver port
MAX_CONTENT_LENGTH = 16GB    # Max fájlméret
MAX_MESSAGES = 100           # Chat üzenetek max száma memóriában
```

### **Chat beállítások**
```python
SECRET_KEY = 'dropflow-chat-secret-key'  # SocketIO titkos kulcs
CORS_ALLOWED_ORIGINS = "*"               # CORS beállítások
```

### **Támogatott fájltípusok**
- **Képek:** PNG, JPG, JPEG, GIF, WebP, SVG (thumbnail előnézettel)
- **Videók:** MP4, WebM, MOV, AVI, MKV (lejátszó előnézettel)
- **Hangfájlok:** MP3, WAV, OGG, FLAC (waveform megjelenítéssel)
- **Dokumentumok:** PDF (beágyazott előnézettel)
- **Kód:** PY, JS, HTML, CSS, JSON, XML, MD, SH, JAVA, C, CPP, CS, GO, RB, PHP, SQL (syntax highlighting)
- **Szöveg:** TXT, LOG és minden más fájltípus

## 🌟 Fejlett Funkciók

### **Valós Idejű Chat Rendszer**
- Socket.IO alapú azonnali üzenetküldés
- Többfelhasználós beszélgetések támogatása
- Gépelés jelzés és online státusz
- Üzenet előzmények megőrzése (memóriában)
- Automatikus felhasználónév generálás

### **Élő Rendszermonitorozás**
- 5 másodpercenként frissülő rendszeradatok
- CPU és RAM használat vizualizáció
- Tárhely használat százalékos megjelenítés
- Hálózati interfészek valós idejű listázása

### **Intelligens Fájlkezelés**
- Automatikus fájltípus felismerés
- Thumbnail generálás képekhez
- Video előnézetek lejátszó gombbal
- Hang fájlok waveform megjelenítéssel
- Kód fájlok syntax highlighting-gal

### **Keresztplatform Szinkronizálás**
- Automatikus fájllista frissítés (10 másodpercenként)
- Valós idejű változáskövetés több eszközön
- Adaptive polling frequency (lapfókusz alapján)
- Instant notifications fájl változásokról

### **Modern UX elemek**
- Smooth animációk és átmenetek
- Loading indikátorok és progress bar-ok
- Hover effektek és vizuális visszajelzések
- Dark/Light theme automatic detection
- Responsive design minden képernyőméretre

## 🚀 Fejlesztés

### **Projekt struktúra**
```
File_sharer/
├── app_clean.py          # Főalkalmazás
├── requirements.txt      # Python függőségek
├── README.md            # Dokumentáció
└── uploads/             # Feltöltött fájlok
```

### **Testre szabás**
- **Színséma:** Módosítsd a CSS változókat
- **Port:** Változtasd meg a `PORT` konstanst
- **Fájlméret limit:** Állítsd be a `MAX_CONTENT_LENGTH`-et

## 📝 Licenc

Ez a projekt szabadon használható és módosítható.

## 🤝 Közreműködés

Minden fejlesztési javaslat és hozzájárulás üdvözölt!

---

**Készítette:** Vajda Norman 
**Verzió:** 3.0  
**Frissítve:** 2025.06.09

### 🆕 Legújabb változások (v3.0)
- ✅ **Valós idejű chat rendszer** Socket.IO-val
- ✅ **Keresztplatform szinkronizálás** automatikus fájllista frissítéssel
- ✅ **Fejlett előnézetek** waveform és syntax highlighting
- ✅ **Intelligens értesítések** fájl és chat változásokról
- ✅ **Optimalizált UX** adaptive polling és responsive design
- ✅ **16GB fájlméret támogatás** nagyobb fájlokhoz
