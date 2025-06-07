# 🚀 DropFlow -  Helyi Fájlmegosztó

**DropFlow** egy modern, letisztult webes fájlmegosztó alkalmazás, amely lehetővé teszi a fájlok egyszerű feltöltését, megosztását és kezelését helyi hálózaton.

## ✨ Főbb Funkciók

### 🎨 **Modern UI/UX**
- **Sötét/Világos téma** - Témaváltás
- **Responsive design** - Tökéletes megjelenés minden eszközön
- **Rácsnézet és listanézet** - Kétféle fájlmegjelenítési mód

### 📁 **Fájlkezelés**
- **Drag & Drop feltöltés** - Húzd és ejtsd a fájlokat
- **Többszörös fájlfeltöltés** - Több fájl egyszerre
- **Élő előnézet** - Képek, videók, hangfájlok és dokumentumok
- **Valós idejű törlés** - AJAX-alapú törlés oldal újratöltés nélkül
- **Intelligens keresés és rendezés**

### 📱 **Hálózati Funkcók**
- **QR kód generálás** - Könnyű mobilos hozzáférés
- **Helyi IP felderítés** - Automatikus hálózati konfiguráció
- **Hálózati interfészek megjelenítése**

### 📊 **Rendszermonitorozás**
- **Élő tárhely információ** - Szabad/foglalt hely megjelenítése
- **CPU és RAM használat** - Valós idejű rendszerterhelés
- **Feltöltött fájlok statisztikája** - Fájlok száma és mérete
- **Hálózati interfészek listája** - IP címek megjelenítése

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

## 🔧 Konfiguráció

### **Alapbeállítások**
```python
UPLOAD_FOLDER = 'uploads'    # Feltöltési könyvtár
PORT = 5000                  # Szerver port
MAX_CONTENT_LENGTH = 16GB    # Max fájlméret
```

### **Támogatott fájltípusok**
- **Képek:** PNG, JPG, JPEG, GIF, WebP, SVG
- **Videók:** MP4, WebM, MOV, AVI, MKV
- **Hangfájlok:** MP3, WAV, OGG, FLAC
- **Dokumentumok:** PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- **Kód:** PY, JS, HTML, CSS, JSON, XML, MD és még sok más

## 🌟 Fejlett Funkciók

### **Élő Rendszermonitorozás**
- 5 másodpercenként frissülő rendszeradatok
- CPU és RAM használat vizualizáció
- Tárhely használat százalékos megjelenítés

### **Intelligens Fájlkezelés**
- Automatikus fájltípus felismerés
- Thumbnail generálás képekhez
- Video előnézetek lejátszó gombbal

### **Modern UX elemek**
- Smooth animációk és átmenetek
- Loading indikátorok
- Hover effektek és vizuális visszajelzések

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
**Verzió:** 2.0  
**Frissítve:** 2025.06.07
