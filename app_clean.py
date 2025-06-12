import os
import socket
import math
import json
import shutil
import psutil
import platform
from datetime import datetime
from flask import Flask, request, send_from_directory, jsonify, render_template_string, Response, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
import qrcode
from io import BytesIO

# --- Konfiguráció ---
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
NOTES_FILE = os.path.join(DATA_FOLDER, 'notes.json')
SAVED_NOTES_FILE = os.path.join(DATA_FOLDER, 'saved_notes.json')
PORT = 5000

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16 GB max méret
app.config['SECRET_KEY'] = 'dropflow-chat-secret-key'

# SocketIO inicializálása
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# Chat üzenetek tárolása (memóriában)
chat_messages = []
MAX_MESSAGES = 100  # Maximum üzenetek száma a memóriában

# --- Segédfüggvények ---

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1)); IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return IP

def load_notes():
    """Betölti a jegyzeteket a JSON fájlból"""
    try:
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        return {'current_note': '', 'created_at': None, 'updated_at': None}
    except Exception as e:
        print(f"Hiba a jegyzet betöltésekor: {e}")
        return {'current_note': '', 'created_at': None, 'updated_at': None}

def save_notes(notes_data):
    """Elmenti a jegyzeteket a JSON fájlba"""
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Hiba a jegyzet mentésekor: {e}")
        return False

def load_saved_notes():
    """Betölti a mentett jegyzeteket a JSON fájlból"""
    try:
        if os.path.exists(SAVED_NOTES_FILE):
            with open(SAVED_NOTES_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        return []
    except Exception as e:
        print(f"Hiba a mentett jegyzetek betöltésekor: {e}")
        return []

def save_saved_notes(saved_notes):
    """Elmenti a mentett jegyzeteket a JSON fájlba"""
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        with open(SAVED_NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(saved_notes, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Hiba a mentett jegyzetek mentésekor: {e}")
        return False

def get_storage_info():
    """Returns storage information for the current drive"""
    try:
        total, used, free = shutil.disk_usage(os.path.dirname(os.path.abspath(__file__)))
        return {
            'total': total,
            'used': used,
            'free': free,
            'total_formatted': format_bytes(total),
            'used_formatted': format_bytes(used),
            'free_formatted': format_bytes(free),
            'used_percent': round((used / total) * 100, 1)
        }
    except:
        return None

def get_upload_folder_info():
    """Returns information about the upload folder"""
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return {'size': 0, 'count': 0, 'size_formatted': '0 B'}
        
        total_size = 0
        file_count = 0
        
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
                file_count += 1
        
        return {
            'size': total_size,
            'count': file_count,
            'size_formatted': format_bytes(total_size)
        }
    except:
        return {'size': 0, 'count': 0, 'size_formatted': '0 B'}

def get_system_info():
    """Returns basic system information"""
    try:
        return {
            'platform': platform.system(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'uptime': datetime.now().strftime('%H:%M:%S')
        }
    except:
        return None

def get_network_info():
    """Returns network interface information"""
    try:
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interfaces.append({
                        'name': interface,
                        'ip': addr.address
                    })
        return interfaces
    except:
        return []

def format_bytes(size):
    if size == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB"); i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i); s = round(size / p, 2); return f"{s} {size_name[i]}"

def get_file_info(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    info = {
        'image': ('png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'),
        'video': ('mp4', 'webm', 'mov', 'avi', 'mkv'),
        'audio': ('mp3', 'wav', 'ogg', 'flac'),
        'pdf': ('pdf',),
        'code': ('py', 'js', 'html', 'css', 'json', 'xml', 'md', 'sh', 'java', 'c', 'cpp', 'cs', 'go', 'rb', 'php', 'sql'),
        'text': ('txt', 'log'),
    }
    preview_type = 'other'
    for p_type, extensions in info.items():
        if ext in extensions:
            preview_type = p_type
            break
    if preview_type == 'text': preview_type = 'code' # Kezeljük együtt

    icon_map = {
        'image': 'fa-file-image', 'video': 'fa-file-video', 'audio': 'fa-file-audio',
        'pdf': 'fa-file-pdf', 'code': 'fa-file-code',
        'zip': 'fa-file-archive', 'rar': 'fa-file-archive', '7z': 'fa-file-archive',
        'doc': 'fa-file-word', 'docx': 'fa-file-word',
        'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel',
        'ppt': 'fa-file-powerpoint', 'pptx': 'fa-file-powerpoint'
    }
    icon = icon_map.get(ext, icon_map.get(preview_type, 'fa-file'))
    return preview_type, icon


# --- Chat WebSocket események ---

@socketio.on('connect')
def handle_connect():
    """Felhasználó csatlakozása a chat szobához"""
    join_room('main_chat')
    # Küldj el korábbi üzeneteket az új felhasználónak
    emit('previous_messages', {'messages': chat_messages[-50:]})  # Utolsó 50 üzenet
    print('Felhasználó csatlakozott a chathez')

@socketio.on('disconnect')
def handle_disconnect():
    """Felhasználó kilépése a chat szobából"""
    leave_room('main_chat')
    print('Felhasználó kilépett a chatből')

@socketio.on('send_message')
def handle_message(data):
    """Új chat üzenet kezelése"""
    try:
        message = data.get('message', '').strip()
        username = data.get('username', 'Névtelen').strip()
        
        if not message:
            return
        
        # Üzenet létrehozása
        chat_message = {
            'id': len(chat_messages) + 1,
            'username': username[:50],  # Max 50 karakter
            'message': message[:1000],  # Max 1000 karakter
            'timestamp': datetime.now().isoformat(),
            'formatted_time': datetime.now().strftime('%H:%M')
        }
        
        # Hozzáadás a tárolt üzenetekhez
        chat_messages.append(chat_message)
        
        # Ha túl sok üzenet van, töröljük a régieket
        if len(chat_messages) > MAX_MESSAGES:
            chat_messages.pop(0)
        
        # Üzenet broadcast minden csatlakozott felhasználónak
        socketio.emit('new_message', chat_message, room='main_chat')
        
        print(f'Új üzenet: {username}: {message}')
        
    except Exception as e:
        print(f'Hiba az üzenet kezelésekor: {e}')

@socketio.on('typing')
def handle_typing(data):
    """Gépelés jelzés kezelése"""
    try:
        username = data.get('username', 'Valaki')
        socketio.emit('user_typing', {'username': username}, room='main_chat', include_self=False)
    except Exception as e:
        print(f'Hiba a gépelés jelzés kezelésekor: {e}')

@socketio.on('stop_typing')
def handle_stop_typing(data):
    """Gépelés befejezés jelzés kezelése"""
    try:
        username = data.get('username', 'Valaki')
        socketio.emit('user_stop_typing', {'username': username}, room='main_chat', include_self=False)
    except Exception as e:
        print(f'Hiba a gépelés leállítás kezelésekor: {e}')

# --- Notes WebSocket események ---

@socketio.on('join_notes')
def handle_join_notes():
    """Felhasználó csatlakozása a jegyzet szobához"""
    join_room('notes_room')
    print('Felhasználó csatlakozott a jegyzet szobához')

@socketio.on('leave_notes')
def handle_leave_notes():
    """Felhasználó kilépése a jegyzet szobából"""
    leave_room('notes_room')
    print('Felhasználó kilépett a jegyzet szobából')

@socketio.on('notes_content_change')
def handle_notes_content_change(data):
    """Jegyzet tartalom változás kezelése"""
    try:
        content = data.get('content', '')
        cursor_position = data.get('cursor_position', 0)
        username = data.get('username', 'Névtelen')
        
        # Mentés a notes.json fájlba
        notes_data = {
            'current_note': content,
            'updated_at': datetime.now().isoformat(),
            'last_editor': username
        }
        save_notes(notes_data)
        
        # Broadcast a változást minden csatlakozott felhasználónak (kivéve a küldőt)
        socketio.emit('notes_content_updated', {
            'content': content,
            'cursor_position': cursor_position,
            'username': username,
            'timestamp': datetime.now().isoformat()
        }, room='notes_room', include_self=False)
        
    except Exception as e:
        print(f'Hiba a jegyzet tartalom kezelésekor: {e}')

@socketio.on('notes_cursor_change')
def handle_notes_cursor_change(data):
    """Kurzor pozíció változás kezelése"""
    try:
        cursor_position = data.get('cursor_position', 0)
        username = data.get('username', 'Névtelen')
        
        # Broadcast a kurzor pozíciót
        socketio.emit('notes_cursor_updated', {
            'cursor_position': cursor_position,
            'username': username
        }, room='notes_room', include_self=False)
        
    except Exception as e:
        print(f'Hiba a kurzor pozíció kezelésekor: {e}')

@socketio.on('notes_save')
def handle_notes_save(data):
    """Jegyzet mentés kezelése"""
    try:
        note_data = data.get('note_data')
        if not note_data:
            return
            
        # Betöltés és mentés
        saved_notes = load_saved_notes()
        
        # Ellenőrizzük, hogy már létezik-e az ID
        existing_index = -1
        for i, note in enumerate(saved_notes):
            if note.get('id') == note_data.get('id'):
                existing_index = i
                break
        
        if existing_index >= 0:
            # Frissítés
            saved_notes[existing_index] = note_data
        else:
            # Új jegyzet hozzáadása
            saved_notes.append(note_data)
        
        # Mentés fájlba
        if save_saved_notes(saved_notes):
            # Broadcast az összes felhasználónak
            socketio.emit('notes_saved_updated', {
                'notes': saved_notes,
                'action': 'save',
                'note': note_data
            }, room='notes_room')
        
    except Exception as e:
        print(f'Hiba a jegyzet mentésekor: {e}')

@socketio.on('notes_delete')
def handle_notes_delete(data):
    """Jegyzet törlés kezelése"""
    try:
        note_id = data.get('note_id')
        if not note_id:
            return
            
        # Betöltés és törlés
        saved_notes = load_saved_notes()
        saved_notes = [note for note in saved_notes if note.get('id') != note_id]
        
        # Mentés fájlba
        if save_saved_notes(saved_notes):
            # Broadcast az összes felhasználónak
            socketio.emit('notes_saved_updated', {
                'notes': saved_notes,
                'action': 'delete',
                'deleted_id': note_id
            }, room='notes_room')
        
    except Exception as e:
        print(f'Hiba a jegyzet törlésekor: {e}')


# --- HTML & JS Sablon ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="hu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DropFlow</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
        }
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/wavesurfer.js@7"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-okaidia.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
    <style>
        body { 
            font-family: 'Inter', sans-serif; 
            background: #f8fafc;
        }
        
        .dark body {
            background: #0f172a;
        }
        
        .card { 
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(0, 0, 0, 0.08);
            transition: all 0.2s ease;
        }
        
        .dark .card {
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .sidebar { 
            background: rgba(255, 255, 255, 0.95);
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }
        
        .dark .sidebar {
            background: rgba(30, 41, 59, 0.95);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .dragover { 
            transform: scale(1.01); 
            box-shadow: 0 0 0 2px #007aff;
            border-color: #007aff !important;
        }
        
        .file-card:hover { 
            transform: translateY(-2px);
            box-shadow: 0 8px 25px -8px rgba(0, 0, 0, 0.1);
        }
        
        .dark .file-card:hover { 
            box-shadow: 0 8px 25px -8px rgba(0, 0, 0, 0.3);
        }
        
        .image-thumbnail {
            width: 100%;
            height: 120px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        
        .video-thumbnail {
            width: 100%;
            height: 120px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 8px;
            position: relative;
        }
        
        .play-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.7);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
          #preview-modal.hidden { display: none; }
        .preview-content-area { max-height: 85vh; }
        
        /* Custom Scrollbar Styles */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(243, 244, 246, 0.5);
            border-radius: 4px;
        }
        
        .dark ::-webkit-scrollbar-track {
            background: rgba(31, 41, 55, 0.5);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(156, 163, 175, 0.7);
            border-radius: 4px;
            transition: background 0.2s ease;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(107, 114, 128, 0.9);
        }
        
        .dark ::-webkit-scrollbar-thumb {
            background: rgba(75, 85, 99, 0.7);
        }
        
        .dark ::-webkit-scrollbar-thumb:hover {
            background: rgba(107, 114, 128, 0.9);
        }
        
        /* Chat specific scrollbar */
        #chat-messages::-webkit-scrollbar {
            width: 6px;
        }
        
        #chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }
        
        #chat-messages::-webkit-scrollbar-thumb {
            background: rgba(156, 163, 175, 0.5);
            border-radius: 3px;
        }
        
        #chat-messages::-webkit-scrollbar-thumb:hover {
            background: rgba(107, 114, 128, 0.7);
        }
        
        .dark #chat-messages::-webkit-scrollbar-thumb {
            background: rgba(75, 85, 99, 0.5);
        }
        
        .dark #chat-messages::-webkit-scrollbar-thumb:hover {
            background: rgba(107, 114, 128, 0.7);
        }
        
        /* Firefox scrollbar support */
        * {
            scrollbar-width: thin;
            scrollbar-color: rgba(156, 163, 175, 0.7) rgba(243, 244, 246, 0.5);
        }
        
        .dark * {
            scrollbar-color: rgba(75, 85, 99, 0.7) rgba(31, 41, 55, 0.5);
        }
    </style>
</head>
<body class="text-gray-800 dark:text-gray-200 transition-colors duration-300">
    <div class="flex h-screen overflow-hidden">        <!-- Oldalsáv -->
        <aside class="hidden lg:flex w-72 flex-col sidebar flex-shrink-0 overflow-hidden">
            <!-- Fixed Header with Theme Toggle -->
            <div class="flex-shrink-0 p-6 border-b border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-gray-900 dark:bg-white rounded-xl flex items-center justify-center">
                            <i class="fas fa-paper-plane text-white dark:text-gray-900"></i>
                        </div>
                        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">DropFlow</h1>
                    </div>
                    <button id="theme-toggle-desktop" class="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition">
                        <i class="fas fa-moon dark:fa-sun text-gray-700 dark:text-gray-300"></i>
                    </button>
                </div>
            </div>
              <!-- Scrollable Content -->
            <div class="flex-1 overflow-y-auto p-6 space-y-6">
            <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-xl">
                <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Hálózati elérés:</p>
                <input id="server-url" class="bg-transparent text-center font-mono text-sm text-gray-600 dark:text-gray-400 w-full border-b border-gray-300 dark:border-gray-600 pb-1" value="{{ server_url }}" readonly>
                <button onclick="App.copyToClipboard('#server-url')" class="mt-3 w-full text-xs bg-gray-900 dark:bg-white hover:bg-gray-800 dark:hover:bg-gray-100 text-white dark:text-gray-900 py-2 px-3 rounded-lg transition">
                    Másolás
                </button>
            </div>
              <div class="flex justify-center">
                <div class="bg-white dark:bg-gray-800 p-3 rounded-xl shadow-sm">
                    <img src="/qr_code" alt="QR Code" class="w-32 h-32 rounded-lg">
                </div>
            </div>
            
            <!-- Storage Info -->
            <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-xl">
                <div class="flex items-center space-x-2 mb-3">
                    <i class="fas fa-hdd text-gray-600 dark:text-gray-400"></i>
                    <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Tárhely</h3>
                </div>
                <div class="space-y-2">
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div id="storage-bar" class="bg-gray-900 dark:bg-white h-2 rounded-full transition-all duration-300" style="width: {{ storage_info.used_percent }}%"></div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-600 dark:text-gray-400">
                        <span>{{ storage_info.used_formatted }}</span>
                        <span>{{ storage_info.total_formatted }}</span>
                    </div>
                    <p class="text-xs text-gray-500 dark:text-gray-500">{{ storage_info.free_formatted }} szabad</p>
                </div>
            </div>
            
            <!-- Files Info -->
            <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-xl">
                <div class="flex items-center space-x-2 mb-3">
                    <i class="fas fa-folder text-gray-600 dark:text-gray-400"></i>
                    <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Feltöltött fájlok</h3>
                </div>
                <div class="space-y-1">
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-600 dark:text-gray-400">Darab:</span>
                        <span class="text-sm font-medium text-gray-900 dark:text-white">{{ upload_info.count }}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-600 dark:text-gray-400">Méret:</span>
                        <span class="text-sm font-medium text-gray-900 dark:text-white">{{ upload_info.size_formatted }}</span>
                    </div>
                </div>
            </div>
            
            <!-- System Info -->
            <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-xl">
                <div class="flex items-center space-x-2 mb-3">
                    <i class="fas fa-microchip text-gray-600 dark:text-gray-400"></i>
                    <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Rendszer</h3>
                </div>
                <div class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-xs text-gray-600 dark:text-gray-400">CPU:</span>
                        <div class="flex items-center space-x-2">
                            <div class="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                <div id="cpu-bar" class="bg-gray-900 dark:bg-white h-1.5 rounded-full transition-all duration-300" style="width: {{ system_info.cpu_percent }}%"></div>
                            </div>
                            <span class="text-xs font-medium text-gray-900 dark:text-white">{{ system_info.cpu_percent }}%</span>
                        </div>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-xs text-gray-600 dark:text-gray-400">RAM:</span>
                        <div class="flex items-center space-x-2">
                            <div class="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                <div id="ram-bar" class="bg-gray-900 dark:bg-white h-1.5 rounded-full transition-all duration-300" style="width: {{ system_info.memory_percent }}%"></div>
                            </div>
                            <span class="text-xs font-medium text-gray-900 dark:text-white">{{ system_info.memory_percent }}%</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Network Info -->
            <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-xl">
                <div class="flex items-center space-x-2 mb-3">
                    <i class="fas fa-wifi text-gray-600 dark:text-gray-400"></i>
                    <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Hálózat</h3>
                </div>
                <div class="space-y-1">
                    {% for interface in network_info %}
                    <div class="flex justify-between">
                        <span class="text-xs text-gray-600 dark:text-gray-400 truncate">{{ interface.name[:8] }}:</span>
                        <span class="text-xs font-mono text-gray-900 dark:text-white">{{ interface.ip }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <div class="flex-grow"></div>
            
            <button id="theme-toggle" class="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition">
                <i class="fas fa-moon dark:fa-sun"></i>
                <span>Téma váltás</span>
            </button>
        </aside>

        <!-- Főtartalom -->
        <main class="flex-1 flex flex-col overflow-hidden">
            <!-- Header -->
            <header class="p-6 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
                <div class="flex items-center justify-between">
                    <div class="relative w-full max-w-md">
                        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                        <input id="search-input" type="text" placeholder="Keresés..." 
                               class="w-full pl-10 pr-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-gray-900 dark:focus:ring-white focus:outline-none transition">
                    </div>                    <div class="flex items-center space-x-3 ml-4">
                        <!-- Notes Toggle Button -->
                        <button id="notes-toggle" class="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition" title="Jegyzetfüzet">
                            <i class="fas fa-sticky-note text-gray-600 dark:text-gray-400"></i>
                        </button>
                        
                        <!-- Chat Toggle Button -->
                        <button id="chat-toggle" class="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition relative">
                            <i class="fas fa-comments text-gray-600 dark:text-gray-400"></i>
                            <span id="chat-notification" class="hidden absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
                        </button>
                        
                        <!-- Mobile Theme Toggle - csak kis képernyőkön látható -->
                        <button id="mobile-theme-toggle" class="lg:hidden flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition">
                            <i class="fas fa-moon dark:fa-sun text-gray-600 dark:text-gray-400"></i>
                        </button>
                        
                        <select id="sort-select" class="bg-gray-100 dark:bg-gray-800 rounded-lg py-2 px-3 focus:ring-2 focus:ring-gray-900 dark:focus:ring-white focus:outline-none transition">
                            <option value="date_desc">Dátum ↓</option>
                            <option value="date_asc">Dátum ↑</option>
                            <option value="name_asc">Név A-Z</option>
                            <option value="name_desc">Név Z-A</option>
                            <option value="size_desc">Méret ↓</option>
                            <option value="size_asc">Méret ↑</option>
                        </select>
                        <div class="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                            <button id="grid-view-btn" class="view-btn bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-md p-2 transition">
                                <i class="fas fa-th-large"></i>
                            </button>
                            <button id="list-view-btn" class="view-btn p-2 transition text-gray-600 dark:text-gray-400">
                                <i class="fas fa-list"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <!-- Upload Container -->
            <div id="upload-container" class="flex-1 overflow-y-auto p-6">
                <div id="drop-zone" class="relative border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:border-gray-900 dark:hover:border-white mb-6">
                    <div class="flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
                        <i class="fas fa-cloud-upload-alt text-5xl text-gray-400 dark:text-gray-500 mb-4"></i>
                        <h2 class="text-xl font-medium text-gray-700 dark:text-gray-300">Húzd ide a fájlokat</h2>
                        <p class="text-gray-500 dark:text-gray-400">vagy <span class="text-gray-900 dark:text-white font-medium">kattints a feltöltéshez</span></p>
                    </div>
                    <input type="file" id="file-input" class="hidden" multiple>
                </div>
                <div id="progress-container" class="mb-6 space-y-3"></div>
                <div id="file-display" class=""></div>
                <p id="no-results" class="hidden text-center text-gray-500 mt-8">Nincs a keresésnek megfelelő fájl.</p>
            </div>
        </main>
    </div>    <!-- Chat Modal -->
    <div id="chat-modal" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
        <div class="card rounded-2xl w-full max-w-2xl h-[90vh] sm:h-[80vh] flex flex-col shadow-2xl">
            <header class="flex items-center justify-between p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
                <div class="flex items-center space-x-2 sm:space-x-3">
                    <i class="fas fa-comments text-lg sm:text-xl text-gray-600 dark:text-gray-400"></i>
                    <h3 class="font-semibold text-base sm:text-lg">Valós idejű chat</h3>
                </div>
                <button id="chat-close" class="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-lg transition">
                    <i class="fas fa-times"></i><span class="hidden sm:inline">Bezárás</span>
                </button>
            </header>
              <!-- Chat Messages Area -->
            <div id="chat-messages" class="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 bg-gray-50 dark:bg-gray-900/50">
                <div class="text-center text-gray-500 dark:text-gray-400 text-sm py-4">
                    <i class="fas fa-comments text-2xl mb-2"></i>
                    <p>Üdvözöl a DropFlow chat!</p>
                    <p class="text-xs mt-1">Itt gyorsan küldhetsz jegyzeteket és üzeneteket.</p>
                </div>
            </div>
            
            <!-- Typing Indicator -->
            <div id="typing-indicator" class="hidden px-3 sm:px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic border-t border-gray-200 dark:border-gray-700">
                <i class="fas fa-ellipsis-h fa-pulse"></i> <span id="typing-users"></span> gépel...
            </div>
            
            <!-- Chat Input -->
            <div class="border-t border-gray-200 dark:border-gray-700 p-3 sm:p-4 flex-shrink-0">
                <div class="flex items-center space-x-2 sm:space-x-3 mb-3">
                    <input id="username-input" type="text" placeholder="Neved..." 
                           class="flex-1 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-gray-900 dark:focus:ring-white focus:outline-none transition text-sm"
                           maxlength="50">
                </div>
                <div class="flex items-end space-x-2 sm:space-x-3">
                    <textarea id="message-input" placeholder="Írj egy üzenetet..." 
                              class="flex-1 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-gray-900 dark:focus:ring-white focus:outline-none transition resize-none text-sm"
                              rows="2" maxlength="1000"></textarea>
                    <button id="send-message" class="px-3 sm:px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-800 dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-lg transition flex items-center space-x-1 sm:space-x-2 h-fit">
                        <i class="fas fa-paper-plane"></i>
                        <span class="hidden sm:inline">Küldés</span>
                    </button>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Enter = küldés, Shift+Enter = új sor</p>
            </div>        </div>
    </div>

    <!-- Notes Modal -->
    <div id="notes-modal" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
        <div class="card rounded-2xl w-full max-w-4xl h-[90vh] sm:h-[85vh] flex flex-col shadow-2xl">
            <header class="flex items-center justify-between p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
                <div class="flex items-center space-x-2 sm:space-x-3">
                    <i class="fas fa-sticky-note text-lg sm:text-xl text-gray-600 dark:text-gray-400"></i>
                    <h3 class="font-semibold text-base sm:text-lg">Jegyzetfüzet</h3>
                </div>
                <div class="flex items-center space-x-2">
                    <button id="notes-copy" class="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3 py-2 bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 text-blue-900 dark:text-blue-100 rounded-lg transition" title="Jegyzet másolása">
                        <i class="fas fa-copy"></i><span class="hidden sm:inline">Másolás</span>
                    </button>
                    <button id="notes-close" class="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-lg transition">
                        <i class="fas fa-times"></i><span class="hidden sm:inline">Bezárás</span>
                    </button>
                </div>
            </header>
            
            <div class="flex flex-1 overflow-hidden">
                <!-- Saved Notes Sidebar -->
                <div class="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col bg-gray-50 dark:bg-gray-900/50">
                    <div class="p-3 border-b border-gray-200 dark:border-gray-700">
                        <h4 class="font-medium text-sm text-gray-700 dark:text-gray-300 mb-2">Mentett jegyzetek</h4>
                        <div class="flex space-x-1">
                            <button id="save-note" class="flex-1 px-2 py-1 bg-green-100 dark:bg-green-900 hover:bg-green-200 dark:hover:bg-green-800 text-green-900 dark:text-green-100 rounded text-xs transition">
                                <i class="fas fa-save mr-1"></i>Mentés
                            </button>
                            <button id="new-note" class="flex-1 px-2 py-1 bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 text-blue-900 dark:text-blue-100 rounded text-xs transition">
                                <i class="fas fa-plus mr-1"></i>Új
                            </button>
                        </div>
                    </div>
                    <div id="saved-notes-list" class="flex-1 overflow-y-auto p-2 space-y-1">
                        <div class="text-center text-gray-500 dark:text-gray-400 text-sm py-8">
                            <i class="fas fa-sticky-note text-2xl mb-2"></i>
                            <p>Még nincsenek mentett jegyzetek</p>
                        </div>
                    </div>
                </div>
                
                <!-- Notes Editor -->
                <div class="flex-1 flex flex-col">
                    <div class="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                        <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                            <span id="note-status">Nincs betöltve jegyzet</span>
                            <span id="note-info"></span>
                        </div>
                    </div>
                    <div class="flex-1 p-3">
                        <textarea id="notes-editor" 
                                  placeholder="Kezdj el írni a jegyzeteidet..."
                                  class="w-full h-full p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-gray-900 dark:focus:ring-white focus:outline-none transition resize-none text-sm font-mono"
                                  spellcheck="false"></textarea>
                    </div>
                    <div class="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                        <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                            <span>Ctrl+S = gyors mentés, Ctrl+N = új jegyzet</span>
                            <span id="char-count">0 karakter</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Előnézeti Modal -->
    <div id="preview-modal" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div id="preview-box" class="card rounded-2xl w-full max-w-5xl flex flex-col shadow-2xl">
            <header class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 id="preview-title" class="font-semibold text-lg truncate"></h3>
                <div class="flex space-x-3">
                    <a id="preview-download" href="#" class="flex items-center space-x-2 px-3 py-2 bg-gray-900 dark:bg-white hover:bg-gray-800 dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-lg transition">
                        <i class="fas fa-download"></i><span>Letöltés</span>
                    </a>
                    <button id="preview-close" class="flex items-center space-x-2 px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-lg transition">
                        <i class="fas fa-times"></i><span>Bezárás</span>
                    </button>
                </div>
            </header>
            <div id="preview-content-area" class="preview-content-area p-4 overflow-auto">
                <div id="preview-loader" class="text-center p-16">
                    <i class="fas fa-spinner fa-spin text-4xl text-gray-400"></i>
                    <p class="mt-4 text-gray-500">Betöltés...</p>
                </div>
                <div id="preview-content" class="hidden"></div>
            </div>
        </div>
    </div>

<script>    const App = {
        files: {{ files_json | safe }},
        view: 'grid',
        sort: 'date_desc',
        wavesurfer: null,
        lastModified: 0,
        fileCount: 0,
        pollingInterval: null,        init() {
            this.cacheDOMElements();
            this.initTheme();
            this.bindEvents();
            this.loadState();
            this.renderFiles();
            this.startSystemMonitoring();
            this.startFilePolling();
        },        cacheDOMElements() {
            this.dom = {
                themeToggle: document.getElementById('theme-toggle'),
                themeToggleDesktop: document.getElementById('theme-toggle-desktop'),
                mobileThemeToggle: document.getElementById('mobile-theme-toggle'),
                searchInput: document.getElementById('search-input'),
                sortSelect: document.getElementById('sort-select'),
                gridViewBtn: document.getElementById('grid-view-btn'),
                listViewBtn: document.getElementById('list-view-btn'),
                dropZone: document.getElementById('drop-zone'),
                fileInput: document.getElementById('file-input'),
                progressContainer: document.getElementById('progress-container'),
                fileDisplay: document.getElementById('file-display'),
                noResults: document.getElementById('no-results'),
                previewModal: document.getElementById('preview-modal'),
                previewBox: document.getElementById('preview-box'),
                previewTitle: document.getElementById('preview-title'),
                previewDownload: document.getElementById('preview-download'),
                previewClose: document.getElementById('preview-close'),
                previewLoader: document.getElementById('preview-loader'),
                previewContent: document.getElementById('preview-content'),
                notesToggle: document.getElementById('notes-toggle'),
            };
        },        bindEvents() {
            this.dom.themeToggle.addEventListener('click', this.toggleTheme.bind(this));
            this.dom.themeToggleDesktop.addEventListener('click', this.toggleTheme.bind(this));
            this.dom.mobileThemeToggle.addEventListener('click', this.toggleTheme.bind(this));
            this.dom.searchInput.addEventListener('input', () => this.debounce(this.renderFiles.bind(this), 300)());
            this.dom.sortSelect.addEventListener('change', (e) => { this.sort = e.target.value; this.renderFiles(); });
            this.dom.gridViewBtn.addEventListener('click', () => this.setView('grid'));
            this.dom.listViewBtn.addEventListener('click', () => this.setView('list'));
            
            this.dom.dropZone.addEventListener('click', () => this.dom.fileInput.click());
            this.dom.fileInput.addEventListener('change', () => this.handleFiles(this.dom.fileInput.files));
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e => this.dom.dropZone.addEventListener(e, this.preventDefaults.bind(this)));
            ['dragenter', 'dragover'].forEach(e => this.dom.dropZone.addEventListener(e, () => this.dom.dropZone.classList.add('dragover')));
            ['dragleave', 'drop'].forEach(e => this.dom.dropZone.addEventListener(e, () => this.dom.dropZone.classList.remove('dragover')));
            this.dom.dropZone.addEventListener('drop', e => this.handleFiles(e.dataTransfer.files));

            this.dom.previewClose.addEventListener('click', this.closePreview.bind(this));
            this.dom.previewModal.addEventListener('click', (e) => { if (e.target === this.dom.previewModal) this.closePreview(); });
            document.addEventListener('keydown', (e) => { if (e.key === "Escape") this.closePreview(); });

            // Notes toggle
            this.dom.notesToggle.addEventListener('click', () => Notes.toggleNotes());
        },

        initTheme() {
            const isDark = localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
            if (isDark) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        },

        toggleTheme() {
            document.documentElement.classList.toggle('dark');
            localStorage.theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        },
        
        loadState() {
            this.view = localStorage.getItem('view') || 'grid';
            this.sort = localStorage.getItem('sort') || 'date_desc';
            this.dom.sortSelect.value = this.sort;
            this.setView(this.view, false);
        },
        
        saveState() {
            localStorage.setItem('view', this.view);
            localStorage.setItem('sort', this.sort);
        },

        setView(viewType, shouldRender = true) {
            this.view = viewType;
            if (viewType === 'grid') {
                this.dom.gridViewBtn.classList.add('bg-gray-900', 'dark:bg-white', 'text-white', 'dark:text-gray-900');
                this.dom.gridViewBtn.classList.remove('text-gray-600', 'dark:text-gray-400');
                this.dom.listViewBtn.classList.remove('bg-gray-900', 'dark:bg-white', 'text-white', 'dark:text-gray-900');
                this.dom.listViewBtn.classList.add('text-gray-600', 'dark:text-gray-400');
                this.dom.fileDisplay.className = 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4';
            } else {
                this.dom.listViewBtn.classList.add('bg-gray-900', 'dark:bg-white', 'text-white', 'dark:text-gray-900');
                this.dom.listViewBtn.classList.remove('text-gray-600', 'dark:text-gray-400');
                this.dom.gridViewBtn.classList.remove('bg-gray-900', 'dark:bg-white', 'text-white', 'dark:text-gray-900');
                this.dom.gridViewBtn.classList.add('text-gray-600', 'dark:text-gray-400');
                this.dom.fileDisplay.className = 'space-y-2';
            }
            if(shouldRender) this.renderFiles();
        },

        getFilteredAndSortedFiles() {
            const searchTerm = this.dom.searchInput.value.toLowerCase();
            let filtered = this.files.filter(f => f.name.toLowerCase().includes(searchTerm));

            const [sortBy, sortDir] = this.sort.split('_');
            filtered.sort((a, b) => {
                let valA = a[sortBy];
                let valB = b[sortBy];
                if(sortBy === 'name') {
                    valA = valA.toLowerCase();
                    valB = valB.toLowerCase();
                }
                if (valA < valB) return sortDir === 'asc' ? -1 : 1;
                if (valA > valB) return sortDir === 'asc' ? 1 : -1;
                return 0;
            });
            return filtered;
        },

        renderFiles() {
            this.saveState();
            const files = this.getFilteredAndSortedFiles();
            this.dom.fileDisplay.innerHTML = '';

            if (files.length === 0) {
                this.dom.noResults.style.display = 'block';
                return;
            }
            this.dom.noResults.style.display = 'none';

            files.forEach(file => {
                const element = this.view === 'grid' ? this.createGridCard(file) : this.createListItem(file);
                this.dom.fileDisplay.insertAdjacentHTML('beforeend', element);
            });
            
            // Re-bind events to newly created elements
            document.querySelectorAll('.file-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    // Prevent preview on action button click
                    if (e.target.closest('.file-actions')) return;
                    const file = this.files.find(f => f.name === item.dataset.name);
                    this.openPreview(file);
                });
            });
        },
        
        createGridCard(file) {
            const fileUrl = `/download/${encodeURIComponent(file.name)}`;
            let thumbnailHtml = '';
            
            if (file.preview_type === 'image') {
                thumbnailHtml = `<img src="${fileUrl}" alt="${file.name}" class="image-thumbnail" loading="lazy">`;
            } else if (file.preview_type === 'video') {
                thumbnailHtml = `
                    <div class="relative">
                        <video class="video-thumbnail" preload="metadata">
                            <source src="${fileUrl}#t=1" type="video/mp4">
                        </video>
                        <div class="play-overlay">
                            <i class="fas fa-play"></i>
                        </div>
                    </div>
                `;
            } else {
                thumbnailHtml = `<div class="w-full h-30 flex items-center justify-center mb-4">
                    <div class="text-5xl text-gray-400 mb-2"><i class="fas ${file.icon}"></i></div>
                </div>`;
            }
            
            return `
                <div class="file-item file-card cursor-pointer card rounded-xl p-4 flex flex-col shadow-sm" data-name="${file.name}">
                    ${thumbnailHtml}
                    <div class="text-center flex-grow flex flex-col justify-end">
                        <p class="font-medium text-sm text-gray-800 dark:text-gray-200 mb-1 truncate" title="${file.name}">${file.name}</p>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">${file.size_formatted}</p>                        <div class="file-actions flex justify-center space-x-2 text-gray-400 dark:text-gray-500">
                            <a href="/download/${encodeURIComponent(file.name)}" onclick="event.stopPropagation()" 
                               class="p-2 bg-gray-900 dark:bg-white hover:bg-gray-800 dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-lg transition" title="Letöltés">
                                <i class="fas fa-download"></i>
                            </a>
                            <button onclick="event.stopPropagation(); App.deleteFile('${file.name}')" 
                               class="p-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-lg transition" title="Törlés">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>`;
        },

        createListItem(file) {
            const fileUrl = `/download/${encodeURIComponent(file.name)}`;
            let thumbnailHtml = '';
            
            if (file.preview_type === 'image') {
                thumbnailHtml = `<img src="${fileUrl}" alt="${file.name}" class="w-12 h-12 object-cover rounded-lg mr-3" loading="lazy">`;
            } else {
                thumbnailHtml = `<div class="w-12 h-12 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg mr-3">
                    <i class="fas ${file.icon} text-xl text-gray-400"></i>
                </div>`;
            }
            
            return `
                <div class="file-item file-list-item cursor-pointer card rounded-xl p-3 flex items-center justify-between shadow-sm" data-name="${file.name}">
                    <div class="flex items-center min-w-0 flex-grow">
                        ${thumbnailHtml}
                        <div class="min-w-0 flex-grow">
                            <p class="font-medium text-gray-800 dark:text-gray-200 truncate" title="${file.name}">${file.name}</p>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${file.size_formatted}</p>
                        </div>
                    </div>                    <div class="file-actions flex space-x-2 flex-shrink-0 ml-4">
                        <a href="/download/${encodeURIComponent(file.name)}" onclick="event.stopPropagation()" 
                           class="p-2 bg-gray-900 dark:bg-white hover:bg-gray-800 dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-lg transition" title="Letöltés">
                            <i class="fas fa-download"></i>
                        </a>
                        <button onclick="event.stopPropagation(); App.deleteFile('${file.name}')" 
                           class="p-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-lg transition" title="Törlés">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>`;
        },
        
        async openPreview(file) {
            this.dom.previewModal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            this.dom.previewTitle.textContent = file.name;
            this.dom.previewDownload.href = `/download/${encodeURIComponent(file.name)}`;
            this.dom.previewLoader.style.display = 'block';
            this.dom.previewContent.style.display = 'none';
            this.dom.previewContent.innerHTML = '';
            
            let contentHTML = '';
            const fileUrl = `/download/${encodeURIComponent(file.name)}`;
            
            switch(file.preview_type) {
                case 'image':
                    contentHTML = `<img src="${fileUrl}" class="max-w-full max-h-full mx-auto object-contain rounded-xl">`;
                    break;
                case 'video':
                    contentHTML = `<video src="${fileUrl}" controls autoplay class="w-full h-full rounded-xl"></video>`;
                    break;
                case 'audio':
                    contentHTML = `<div id="waveform" class="w-full"></div>`;
                    break;
                case 'pdf':
                    contentHTML = `<iframe src="${fileUrl}" class="w-full h-[75vh] rounded-xl" frameborder="0"></iframe>`;
                    break;
                case 'code':
                    try {
                        const response = await fetch(`/preview/${encodeURIComponent(file.name)}`);
                        if (!response.ok) throw new Error('File content could not be loaded.');
                        const data = await response.json();
                        const lang = file.name.split('.').pop();
                        contentHTML = `<pre class="language-${lang} rounded-xl"><code class="language-${lang}">${Prism.highlight(data.content, Prism.languages[lang] || Prism.languages.clike, lang)}</code></pre>`;
                    } catch (error) {
                        contentHTML = `<p class="text-red-500">Hiba a fájl tartalmának betöltésekor: ${error.message}</p>`;
                    }
                    break;
                default:
                    contentHTML = `<div class="text-center p-16"><i class="fas ${file.icon} text-6xl text-gray-400 mb-4"></i><p class="text-lg text-gray-600 dark:text-gray-400">Ehhez a fájltípushoz nincs elérhető előnézet.</p></div>`;
            }
            
            this.dom.previewLoader.style.display = 'none';
            this.dom.previewContent.innerHTML = contentHTML;
            this.dom.previewContent.style.display = 'block';

            if (file.preview_type === 'audio') {
                if (this.wavesurfer) this.wavesurfer.destroy();
                this.wavesurfer = WaveSurfer.create({
                    container: '#waveform',
                    waveColor: '#6b7280',
                    progressColor: '#111827',
                    url: fileUrl,
                    barWidth: 3,
                    barRadius: 3,
                    height: 100,
                });
                this.wavesurfer.on('ready', () => this.wavesurfer.play());
            }
        },

        closePreview() {
            this.dom.previewModal.classList.add('hidden');
            document.body.style.overflow = 'auto';
            this.dom.previewContent.innerHTML = '';
            if (this.wavesurfer) {
                this.wavesurfer.destroy();
                this.wavesurfer = null;
            }
        },

        // --- Feltöltés ---
        preventDefaults(e) { e.preventDefault(); e.stopPropagation(); },

        handleFiles(files) {
            if (!files.length) return;
            [...files].forEach(this.uploadFile.bind(this));
        },
        
        uploadFile(file) {
            const formData = new FormData();
            formData.append('files[]', file);

            const progressId = `progress-${Math.random().toString(36).substring(2, 9)}`;
            const progressHTML = `
                <div id="wrapper-${progressId}" class="card p-4 rounded-xl shadow-sm">
                    <div class="flex justify-between items-center text-sm mb-2">
                        <span class="font-medium text-gray-700 dark:text-gray-300 truncate pr-4">${file.name}</span>
                        <span class="font-mono text-gray-600 dark:text-gray-400" id="percent-${progressId}">0%</span>
                    </div>
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div id="${progressId}" class="bg-gray-900 dark:bg-white h-2 rounded-full transition-all duration-300"></div>
                    </div>
                </div>
            `;
            this.dom.progressContainer.insertAdjacentHTML('beforeend', progressHTML);
            
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/', true);

            xhr.upload.addEventListener('progress', e => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    document.getElementById(progressId).style.width = percent + '%';
                    document.getElementById(`percent-${progressId}`).textContent = percent + '%';
                }
            });            xhr.addEventListener('load', async (e) => {
                console.log('Upload completed with status:', xhr.status);
                const bar = document.getElementById(progressId);
                const wrapper = document.getElementById(`wrapper-${progressId}`);
                if (xhr.status === 200) {
                    console.log('Upload successful, refreshing file list...');
                    bar.className = 'bg-green-600 h-2 rounded-full transition-all duration-300';
                    document.getElementById(`percent-${progressId}`).textContent = 'Kész!';
                    setTimeout(() => {
                        wrapper.style.opacity = '0';
                        setTimeout(() => wrapper.remove(), 300);
                    }, 1000);
                      // Refresh file list without page reload
                    try {
                        await App.refreshFileList();
                        // Update polling state immediately to prevent duplicate notifications
                        await App.updatePollingState();
                        App.showNotification('Fájl sikeresen feltöltve!', 'success');
                    } catch (error) {
                        console.error('Failed to refresh file list after upload:', error);
                        App.showNotification('Fájl feltöltve, de a lista frissítése sikertelen. Frissítsd az oldalt!', 'warning');
                    }
                } else {
                    console.log('Upload failed with status:', xhr.status);
                    bar.className = 'bg-red-600 h-2 rounded-full transition-all duration-300';
                    document.getElementById(`percent-${progressId}`).textContent = 'Hiba!';
                    App.showNotification('Hiba a fájl feltöltésekor!', 'error');
                }
            });
            xhr.send(formData);
        },
        
        // --- Segédfüggvények ---
        debounce(func, delay) {
            let timeoutId;
            return (...args) => {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => func.apply(this, args), delay);
            };
        },
          copyToClipboard(element) {
            const input = document.querySelector(element);
            input.select();
            input.setSelectionRange(0, 99999);
            document.execCommand('copy');
        },
          // --- System Monitoring ---
        startSystemMonitoring() {
            // Update system info every 5 seconds
            setInterval(() => this.updateSystemInfo(), 5000);
        },
        
        async updateSystemInfo() {
            try {
                const response = await fetch('/api/system-info');
                if (!response.ok) return;
                
                const data = await response.json();
                
                // Update CPU bar
                const cpuBar = document.getElementById('cpu-bar');
                if (cpuBar && data.system_info) {
                    cpuBar.style.width = data.system_info.cpu_percent + '%';
                    cpuBar.parentElement.nextElementSibling.textContent = data.system_info.cpu_percent + '%';
                }
                
                // Update RAM bar
                const ramBar = document.getElementById('ram-bar');
                if (ramBar && data.system_info) {
                    ramBar.style.width = data.system_info.memory_percent + '%';
                    ramBar.parentElement.nextElementSibling.textContent = data.system_info.memory_percent + '%';
                }
                
                // Update storage info
                const storageBar = document.getElementById('storage-bar');
                if (storageBar && data.storage_info) {
                    storageBar.style.width = data.storage_info.used_percent + '%';
                }
                
            } catch (error) {
                console.log('System monitoring update failed:', error);
            }
        },
        
        // --- File Operations ---
        async deleteFile(filename) {
            if (!confirm(`Biztosan törlöd a(z) "${filename}" fájlt?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/delete/${encodeURIComponent(filename)}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                  if (result.success) {
                    // Remove from files array
                    this.files = this.files.filter(f => f.name !== filename);
                    
                    // Re-render file list
                    this.renderFiles();
                    
                    // Update upload info in sidebar
                    this.updateUploadInfo();
                    
                    // Update polling state immediately to prevent duplicate notifications
                    await this.updatePollingState();
                    
                    // Show success message (optional)
                    this.showNotification('Fájl sikeresen törölve!', 'success');
                } else {
                    this.showNotification('Hiba a fájl törlésekor: ' + result.error, 'error');
                }
            } catch (error) {
                console.error('Delete error:', error);
                this.showNotification('Hiba történt a fájl törlésekor.', 'error');
            }        },
          async refreshFileList() {
            try {
                console.log('Refreshing file list...');
                
                // Fetch updated file list from server
                const response = await fetch('/api/files');
                if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                
                const data = await response.json();
                console.log('Received file data:', data);
                
                // Update files array
                this.files = data.files;
                
                // Re-render file list
                this.renderFiles();
                
                // Update upload info in sidebar
                this.updateUploadInfo();
                
                console.log('File list refreshed successfully');
                
            } catch (error) {
                console.error('Failed to refresh file list:', error);
                this.showNotification('Hiba a fájllista frissítésekor', 'error');
            }
        },
        
        async updateUploadInfo() {
            // Recalculate upload folder info
            const totalSize = this.files.reduce((sum, file) => sum + file.size, 0);
            const count = this.files.length;
            
            // Update sidebar display
            const countSpan = document.querySelector('.bg-gray-100.dark\\:bg-gray-800 .space-y-1 .flex:first-child .text-sm.font-medium');
            const sizeSpan = document.querySelector('.bg-gray-100.dark\\:bg-gray-800 .space-y-1 .flex:last-child .text-sm.font-medium');
            
            if (countSpan) countSpan.textContent = count;
            if (sizeSpan) sizeSpan.textContent = this.formatBytes(totalSize);
        },
        
        showNotification(message, type = 'info') {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full ${
                type === 'success' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-700' :
                type === 'error' ? 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-700' :
                'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-700'
            }`;
            
            notification.innerHTML = `
                <div class="flex items-center">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-2"></i>
                    <span class="text-sm font-medium">${message}</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {
                notification.style.transform = 'translateX(0)';
            }, 100);
            
            // Auto remove after 3 seconds
            setTimeout(() => {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        },
          formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },        // File polling methods for cross-device synchronization
        startFilePolling() {
            console.log('Starting file polling for cross-device sync...');
            
            // Initialize current state
            this.updatePollingState();
            
            // Start polling every 10 seconds
            this.setPollingInterval(10000);
            
            // Adjust polling frequency based on page visibility
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    // Slow down polling when page is hidden (30 seconds)
                    this.setPollingInterval(30000);
                    console.log('Page hidden, reduced polling frequency');
                } else {
                    // Resume normal polling when page becomes visible
                    this.setPollingInterval(10000);
                    console.log('Page visible, resumed normal polling');
                    // Immediately check for changes when returning to page
                    this.checkForFileChanges();
                }
            });
        },

        setPollingInterval(interval) {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
            }
            this.pollingInterval = setInterval(() => {
                this.checkForFileChanges();
            }, interval);
        },

        async updatePollingState() {
            try {
                const response = await fetch('/api/files/check');
                if (response.ok) {
                    const data = await response.json();
                    this.lastModified = data.last_modified;
                    this.fileCount = data.file_count;
                    console.log('Polling state updated:', data);
                }
            } catch (error) {
                console.error('Failed to update polling state:', error);
            }
        },

        async checkForFileChanges() {
            try {
                const response = await fetch('/api/files/check');
                if (!response.ok) return;
                
                const data = await response.json();
                
                // Check if files have changed
                const hasChanges = (
                    data.last_modified > this.lastModified || 
                    data.file_count !== this.fileCount
                );
                
                if (hasChanges) {
                    console.log('File changes detected, refreshing list...');
                    await this.refreshFileList();
                    this.lastModified = data.last_modified;
                    this.fileCount = data.file_count;
                    this.showNotification('Fájlok frissítve más eszközről', 'info');
                }
            } catch (error) {
                console.error('Failed to check for file changes:', error);
            }
        },

        stopFilePolling() {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
                console.log('File polling stopped');
            }        }
    };

    // Chat funkcionalitás
    const Chat = {
        socket: null,
        isOpen: false,
        username: '',
        typingTimeout: null,
        isTyping: false,
        unreadCount: 0,

        init() {
            this.cacheDOMElements();
            this.bindEvents();
            this.loadUsername();
            this.initSocket();
        },        cacheDOMElements() {
            this.dom = {
                chatToggle: document.getElementById('chat-toggle'),
                chatModal: document.getElementById('chat-modal'),
                chatClose: document.getElementById('chat-close'),
                chatMessages: document.getElementById('chat-messages'),
                usernameInput: document.getElementById('username-input'),
                messageInput: document.getElementById('message-input'),
                sendButton: document.getElementById('send-message'),
                typingIndicator: document.getElementById('typing-indicator'),
                typingUsers: document.getElementById('typing-users'),
                chatNotification: document.getElementById('chat-notification')
            };
        },

        bindEvents() {
            this.dom.chatToggle.addEventListener('click', () => this.toggleChat());
            this.dom.chatClose.addEventListener('click', () => this.closeChat());
            this.dom.chatModal.addEventListener('click', (e) => {
                if (e.target === this.dom.chatModal) this.closeChat();
            });

            this.dom.usernameInput.addEventListener('input', () => this.saveUsername());
            this.dom.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
            this.dom.messageInput.addEventListener('input', () => this.handleTyping());
            this.dom.sendButton.addEventListener('click', () => this.sendMessage());
            
            document.addEventListener('keydown', (e) => {
                if (e.key === "Escape" && this.isOpen) this.closeChat();
            });
        },

        loadUsername() {
            const savedUsername = localStorage.getItem('chat-username');
            if (savedUsername) {
                this.username = savedUsername;
                this.dom.usernameInput.value = savedUsername;
            } else {
                // Generálj egy random nevet
                const adjectives = ['Gyors', 'Okos', 'Kedves', 'Ügyes', 'Kreatív', 'Bátor'];
                const nouns = ['Felhasználó', 'Látogató', 'Vendég', 'User', 'Ember', 'Barát'];
                const randomName = adjectives[Math.floor(Math.random() * adjectives.length)] + 
                                 nouns[Math.floor(Math.random() * nouns.length)] + 
                                 Math.floor(Math.random() * 100);
                this.username = randomName;
                this.dom.usernameInput.value = randomName;
                this.saveUsername();
            }
        },

        saveUsername() {
            this.username = this.dom.usernameInput.value.trim() || 'Névtelen';
            localStorage.setItem('chat-username', this.username);
        },

        initSocket() {
            try {
                this.socket = io();
                
                this.socket.on('connect', () => {
                    console.log('Chat kapcsolat létrejött');
                });

                this.socket.on('disconnect', () => {
                    console.log('Chat kapcsolat megszakadt');
                });

                this.socket.on('previous_messages', (data) => {
                    this.loadPreviousMessages(data.messages);
                });

                this.socket.on('new_message', (message) => {
                    this.addMessage(message);
                    if (!this.isOpen) {
                        this.showNotification();
                    }
                });

                this.socket.on('user_typing', (data) => {
                    this.showTyping(data.username);
                });

                this.socket.on('user_stop_typing', (data) => {
                    this.hideTyping(data.username);
                });
                
            } catch (error) {
                console.error('Chat kapcsolódási hiba:', error);
            }
        },

        toggleChat() {
            if (this.isOpen) {
                this.closeChat();
            } else {
                this.openChat();
            }
        },        openChat() {
            this.isOpen = true;
            this.dom.chatModal.classList.remove('hidden');
            // Only prevent body scroll on larger screens
            if (window.innerWidth >= 640) {
                document.body.style.overflow = 'hidden';
            }
            this.dom.messageInput.focus();
            this.clearNotification();
            this.scrollToBottom();
        },

        closeChat() {
            this.isOpen = false;
            this.dom.chatModal.classList.add('hidden');
            document.body.style.overflow = 'auto';
        },

        loadPreviousMessages(messages) {
            this.dom.chatMessages.innerHTML = '';
            
            if (messages.length === 0) {
                this.dom.chatMessages.innerHTML = `
                    <div class="text-center text-gray-500 dark:text-gray-400 text-sm py-4">
                        <i class="fas fa-comments text-2xl mb-2"></i>
                        <p>Üdvözöl a DropFlow chat!</p>
                        <p class="text-xs mt-1">Itt gyorsan küldhetsz jegyzeteket és üzeneteket.</p>
                    </div>
                `;
                return;
            }

            messages.forEach(message => this.addMessage(message, false));
            this.scrollToBottom();
        },        addMessage(message, shouldScroll = true) {
            const isOwnMessage = message.username === this.username;
            
            const messageElement = document.createElement('div');
            messageElement.className = `flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`;
            
            messageElement.innerHTML = `
                <div class="max-w-[85%] sm:max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                    isOwnMessage 
                        ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900' 
                        : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
                }">
                    ${!isOwnMessage ? `<p class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">${this.escapeHtml(message.username)}</p>` : ''}
                    <p class="text-sm break-words">${this.escapeHtml(message.message)}</p>
                    <p class="text-xs opacity-70 mt-1 ${isOwnMessage ? 'text-right' : 'text-left'}">${message.formatted_time}</p>
                </div>
            `;
            
            this.dom.chatMessages.appendChild(messageElement);
            
            if (shouldScroll) {
                this.scrollToBottom();
            }
        },

        handleKeyDown(e) {
            if (e.key === 'Enter') {
                if (e.shiftKey) {
                    // Shift+Enter = új sor, ne küldjük el
                    return;
                } else {
                    // Enter = küldés
                    e.preventDefault();
                    this.sendMessage();
                }
            }
        },

        handleTyping() {
            if (!this.isTyping) {
                this.isTyping = true;
                this.socket.emit('typing', { username: this.username });
            }

            // Reset typing timeout
            clearTimeout(this.typingTimeout);
            this.typingTimeout = setTimeout(() => {
                this.isTyping = false;
                this.socket.emit('stop_typing', { username: this.username });
            }, 1000);
        },

        sendMessage() {
            const message = this.dom.messageInput.value.trim();
            if (!message) return;

            this.saveUsername();

            this.socket.emit('send_message', {
                message: message,
                username: this.username
            });

            this.dom.messageInput.value = '';
            
            // Állítsd le a gépelés jelzést
            if (this.isTyping) {
                this.isTyping = false;
                this.socket.emit('stop_typing', { username: this.username });
                clearTimeout(this.typingTimeout);
            }
        },

        showTyping(username) {
            this.dom.typingUsers.textContent = username;
            this.dom.typingIndicator.classList.remove('hidden');
            this.scrollToBottom();
        },

        hideTyping(username) {
            // Egyszerűsítjük: ha bárki abbahagyja a gépelést, elrejtjük az indikátort
            this.dom.typingIndicator.classList.add('hidden');
        },

        showNotification() {
            this.unreadCount++;
            this.dom.chatNotification.classList.remove('hidden');
        },

        clearNotification() {
            this.unreadCount = 0;
            this.dom.chatNotification.classList.add('hidden');
        },

        scrollToBottom() {
            setTimeout(() => {
                this.dom.chatMessages.scrollTop = this.dom.chatMessages.scrollHeight;
            }, 100);
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;            return div.innerHTML;
        }
    };    // Notes funkcionalitás
    const Notes = {
        isOpen: false,
        currentNote: '',
        savedNotes: [],
        currentNoteId: null,
        hasUnsavedChanges: false,
        socket: null,
        lastCursorPosition: 0,
        isReceivingUpdate: false,
        username: '',

        init() {
            this.cacheDOMElements();
            this.bindEvents();
            this.loadSavedNotes();
            this.loadCurrentNote();
            this.initSocket();
            this.loadUsername();
        },

        cacheDOMElements() {
            this.dom = {
                notesModal: document.getElementById('notes-modal'),
                notesClose: document.getElementById('notes-close'),
                notesCopy: document.getElementById('notes-copy'),
                notesEditor: document.getElementById('notes-editor'),
                saveNote: document.getElementById('save-note'),
                newNote: document.getElementById('new-note'),
                savedNotesList: document.getElementById('saved-notes-list'),
                noteStatus: document.getElementById('note-status'),
                noteInfo: document.getElementById('note-info'),
                charCount: document.getElementById('char-count')
            };
        },

        bindEvents() {
            this.dom.notesClose.addEventListener('click', () => this.closeNotes());
            this.dom.notesModal.addEventListener('click', (e) => {
                if (e.target === this.dom.notesModal) this.closeNotes();
            });

            this.dom.notesCopy.addEventListener('click', () => this.copyNoteToClipboard());
            this.dom.saveNote.addEventListener('click', () => this.saveCurrentNote());
            this.dom.newNote.addEventListener('click', () => this.createNewNote());

            let inputTimeout;
            this.dom.notesEditor.addEventListener('input', () => {
                if (this.isReceivingUpdate) return;
                
                this.handleEditorChange();
                
                // Debounce a realtime frissítést
                clearTimeout(inputTimeout);
                inputTimeout = setTimeout(() => {
                    this.sendContentUpdate();
                }, 300);
            });

            this.dom.notesEditor.addEventListener('selectionchange', () => {
                this.handleCursorChange();
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                if (e.key === "Escape" && this.isOpen) {
                    this.closeNotes();
                } else if (e.ctrlKey && e.key === 's' && this.isOpen) {
                    e.preventDefault();
                    this.saveCurrentNote();
                } else if (e.ctrlKey && e.key === 'n' && this.isOpen) {
                    e.preventDefault();
                    this.createNewNote();
                }
            });
        },

        loadUsername() {
            // Használjuk a Chat modul felhasználónevét, ha van
            if (typeof Chat !== 'undefined' && Chat.username) {
                this.username = Chat.username;
            } else {
                const savedUsername = localStorage.getItem('chat-username');
                if (savedUsername) {
                    this.username = savedUsername;
                } else {
                    this.username = 'Felhasználó' + Math.floor(Math.random() * 1000);
                }
            }
        },

        initSocket() {
            try {
                // Használjuk a Chat modul socket-jét ha létezik
                if (typeof Chat !== 'undefined' && Chat.socket) {
                    this.socket = Chat.socket;
                } else {
                    this.socket = io();
                }

                // Notes specifikus események
                this.socket.on('notes_content_updated', (data) => {
                    this.handleRemoteContentUpdate(data);
                });

                this.socket.on('notes_cursor_updated', (data) => {
                    this.handleRemoteCursorUpdate(data);
                });

                this.socket.on('notes_saved_updated', (data) => {
                    this.handleSavedNotesUpdate(data);
                });

            } catch (error) {
                console.error('Notes socket kapcsolódási hiba:', error);
            }
        },

        toggleNotes() {
            if (this.isOpen) {
                this.closeNotes();
            } else {
                this.openNotes();
            }
        },

        openNotes() {
            this.isOpen = true;
            this.dom.notesModal.classList.remove('hidden');
            if (window.innerWidth >= 640) {
                document.body.style.overflow = 'hidden';
            }
            this.dom.notesEditor.focus();
            this.updateCharCount();
            
            // Csatlakozás a notes szobához
            if (this.socket) {
                this.socket.emit('join_notes');
            }
        },

        closeNotes() {
            if (this.hasUnsavedChanges) {
                if (!confirm('Vannak nem mentett változások. Biztosan be akarod zárni?')) {
                    return;
                }
            }
            this.isOpen = false;
            this.dom.notesModal.classList.add('hidden');
            document.body.style.overflow = 'auto';
            
            // Kilépés a notes szobából
            if (this.socket) {
                this.socket.emit('leave_notes');
            }
        },

        handleEditorChange() {
            const content = this.dom.notesEditor.value;
            this.currentNote = content;
            this.hasUnsavedChanges = true;
            this.updateStatus();
            this.updateCharCount();
        },

        sendContentUpdate() {
            if (this.socket && !this.isReceivingUpdate) {
                const cursorPosition = this.dom.notesEditor.selectionStart;
                this.socket.emit('notes_content_change', {
                    content: this.currentNote,
                    cursor_position: cursorPosition,
                    username: this.username
                });
            }
        },

        handleCursorChange() {
            const cursorPosition = this.dom.notesEditor.selectionStart;
            if (cursorPosition !== this.lastCursorPosition) {
                this.lastCursorPosition = cursorPosition;
                if (this.socket && !this.isReceivingUpdate) {
                    this.socket.emit('notes_cursor_change', {
                        cursor_position: cursorPosition,
                        username: this.username
                    });
                }
            }
        },

        handleRemoteContentUpdate(data) {
            if (data.username === this.username) return; // Saját frissítés
            
            this.isReceivingUpdate = true;
            const oldCursor = this.dom.notesEditor.selectionStart;
            
            this.currentNote = data.content;
            this.dom.notesEditor.value = data.content;
            
            // Próbáljuk megőrizni a kurzor pozíciót
            this.dom.notesEditor.setSelectionRange(oldCursor, oldCursor);
            
            this.updateCharCount();
            this.updateStatus();
            
            // Mutassuk, hogy ki szerkeszti
            this.dom.noteStatus.textContent = `${data.username} szerkeszti...`;
            
            setTimeout(() => {
                this.isReceivingUpdate = false;
                this.updateStatus();
            }, 1000);
        },

        handleRemoteCursorUpdate(data) {
            // Itt lehetne megjeleníteni más felhasználók kurzor pozícióját
            // Ezt egyszerűbb implementációnál kihagyjuk
        },

        handleSavedNotesUpdate(data) {
            this.savedNotes = data.notes;
            this.renderSavedNotes();
            
            if (data.action === 'save') {
                App.showNotification(`${data.note.title} jegyzet mentve!`, 'info');
            } else if (data.action === 'delete') {
                App.showNotification('Jegyzet törölve!', 'info');
                
                // Ha az éppen betöltött jegyzetet törölték
                if (this.currentNoteId === data.deleted_id) {
                    this.currentNoteId = null;
                    this.updateStatus();
                    this.dom.noteInfo.textContent = '';
                }
            }
        },

        updateStatus() {
            if (this.isReceivingUpdate) return;
            
            if (this.currentNoteId) {
                this.dom.noteStatus.textContent = this.hasUnsavedChanges ? 
                    'Szerkesztés alatt - nem mentett változások' : 'Mentett jegyzet betöltve';
            } else {
                this.dom.noteStatus.textContent = this.hasUnsavedChanges ? 
                    'Új jegyzet - nem mentett' : 'Nincs betöltve jegyzet';
            }
        },

        updateCharCount() {
            const count = this.dom.notesEditor.value.length;
            this.dom.charCount.textContent = `${count} karakter`;
        },

        async loadCurrentNote() {
            try {
                const response = await fetch('/api/notes/current');
                if (response.ok) {
                    const data = await response.json();
                    this.currentNote = data.current_note || '';
                    this.dom.notesEditor.value = this.currentNote;
                    this.hasUnsavedChanges = false;
                    this.updateStatus();
                    this.updateCharCount();
                    
                    if (data.updated_at) {
                        const date = new Date(data.updated_at);
                        const editor = data.last_editor ? ` (${data.last_editor})` : '';
                        this.dom.noteInfo.textContent = `Utolsó módosítás: ${date.toLocaleString('hu-HU')}${editor}`;
                    }
                }
            } catch (error) {
                console.error('Hiba a jegyzet betöltésekor:', error);
            }
        },

        async saveCurrentNote() {
            const noteTitle = prompt('Add meg a jegyzet címét:', `Jegyzet - ${new Date().toLocaleDateString('hu-HU')}`);
            if (!noteTitle) return;

            try {
                const noteData = {
                    id: Date.now().toString(),
                    title: noteTitle,
                    content: this.currentNote,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    author: this.username
                };

                // Küldés SocketIO-n keresztül a realtime frissítéshez
                if (this.socket) {
                    this.socket.emit('notes_save', {
                        note_data: noteData
                    });
                }

                this.hasUnsavedChanges = false;
                this.currentNoteId = noteData.id;
                this.updateStatus();
                
            } catch (error) {
                console.error('Hiba a jegyzet mentésekor:', error);
                App.showNotification('Hiba a jegyzet mentésekor!', 'error');
            }
        },

        async loadSavedNotes() {
            try {
                const response = await fetch('/api/notes/saved');
                if (response.ok) {
                    const data = await response.json();
                    this.savedNotes = data.notes || [];
                    this.renderSavedNotes();
                }
            } catch (error) {
                console.error('Hiba a mentett jegyzetek betöltésekor:', error);
            }
        },

        renderSavedNotes() {
            if (this.savedNotes.length === 0) {
                this.dom.savedNotesList.innerHTML = `
                    <div class="text-center text-gray-500 dark:text-gray-400 text-sm py-8">
                        <i class="fas fa-sticky-note text-2xl mb-2"></i>
                        <p>Még nincsenek mentett jegyzetek</p>
                    </div>
                `;
                return;
            }

            this.dom.savedNotesList.innerHTML = '';
            this.savedNotes.forEach(note => {
                const noteElement = document.createElement('div');
                noteElement.className = 'note-item p-2 rounded-lg bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border border-gray-200 dark:border-gray-600 transition';
                
                const date = new Date(note.updated_at).toLocaleDateString('hu-HU');
                const preview = (note.content || '').substring(0, 50) + (note.content && note.content.length > 50 ? '...' : '');
                const author = note.author ? ` (${note.author})` : '';
                
                noteElement.innerHTML = `
                    <div class="flex items-start justify-between">
                        <div class="flex-1 min-w-0">
                            <h5 class="text-sm font-medium text-gray-900 dark:text-white truncate" title="${this.escapeHtml(note.title)}">${this.escapeHtml(note.title)}</h5>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">${date}${author}</p>
                            ${preview ? `<p class="text-xs text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">${this.escapeHtml(preview)}</p>` : ''}
                        </div>
                        <button class="delete-note ml-2 p-1 text-gray-400 hover:text-red-500 transition" data-id="${note.id}" title="Törlés">
                            <i class="fas fa-trash text-xs"></i>
                        </button>
                    </div>
                `;

                noteElement.addEventListener('click', (e) => {
                    if (e.target.closest('.delete-note')) {
                        this.deleteNote(note.id);
                    } else {
                        this.loadNote(note);
                    }
                });

                this.dom.savedNotesList.appendChild(noteElement);
            });
        },

        loadNote(note) {
            if (this.hasUnsavedChanges) {
                if (!confirm('Vannak nem mentett változások. Biztosan be akarod tölteni a másik jegyzetet?')) {
                    return;
                }
            }

            this.currentNote = note.content || '';
            this.currentNoteId = note.id;
            this.dom.notesEditor.value = this.currentNote;
            this.hasUnsavedChanges = false;
            this.updateStatus();
            this.updateCharCount();

            const date = new Date(note.updated_at);
            const author = note.author ? ` (${note.author})` : '';
            this.dom.noteInfo.textContent = `"${note.title}" - ${date.toLocaleString('hu-HU')}${author}`;
        },

        async deleteNote(noteId) {
            if (!confirm('Biztosan törölni akarod ezt a jegyzetet?')) {
                return;
            }

            try {
                // Küldés SocketIO-n keresztül a realtime frissítéshez
                if (this.socket) {
                    this.socket.emit('notes_delete', {
                        note_id: noteId
                    });
                }
                
            } catch (error) {
                console.error('Hiba a jegyzet törlésekor:', error);
                App.showNotification('Hiba a jegyzet törlésekor!', 'error');
            }
        },

        createNewNote() {
            if (this.hasUnsavedChanges) {
                if (!confirm('Vannak nem mentett változások. Biztosan új jegyzetet akarsz kezdeni?')) {
                    return;
                }
            }

            this.currentNote = '';
            this.currentNoteId = null;
            this.dom.notesEditor.value = '';
            this.hasUnsavedChanges = false;
            this.updateStatus();
            this.updateCharCount();
            this.dom.noteInfo.textContent = '';
            this.dom.notesEditor.focus();
        },

        copyNoteToClipboard() {
            if (!this.currentNote.trim()) {
                App.showNotification('Nincs mit másolni!', 'warning');
                return;
            }

            navigator.clipboard.writeText(this.currentNote).then(() => {
                App.showNotification('Jegyzet a vágólapra másolva!', 'success');
            }).catch(() => {
                // Fallback for older browsers
                this.dom.notesEditor.select();
                document.execCommand('copy');
                App.showNotification('Jegyzet a vágólapra másolva!', 'success');
            });
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };document.addEventListener('DOMContentLoaded', () => {
        App.init();
        Chat.init();
        Notes.init();
    });
</script>
</body>
</html>
"""

# --- Flask Útvonalak (Routes) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'files[]' not in request.files: 
            return jsonify({'error': 'No file part'}), 400
        files = request.files.getlist('files[]')
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'success': 'Files uploaded successfully'})

    try:
        filenames = os.listdir(app.config['UPLOAD_FOLDER'])
        files_data = []
        for name in filenames:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], name)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                preview_type, icon = get_file_info(name)
                files_data.append({
                    'name': name,
                    'size': stat.st_size,
                    'size_formatted': format_bytes(stat.st_size),
                    'date': stat.st_mtime,
                    'date_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    'preview_type': preview_type,
                    'icon': icon                })
    except FileNotFoundError:
        files_data = []

    server_url = f"http://{get_local_ip()}:{PORT}"
    
    # Get additional system information
    storage_info = get_storage_info() or {'used_percent': 0, 'total_formatted': 'N/A', 'used_formatted': 'N/A', 'free_formatted': 'N/A'}
    upload_info = get_upload_folder_info()
    system_info = get_system_info() or {'cpu_percent': 0, 'memory_percent': 0}
    network_info = get_network_info()
    
    return render_template_string(HTML_TEMPLATE, 
                                files_json=json.dumps(files_data), 
                                server_url=server_url,
                                storage_info=storage_info,
                                upload_info=upload_info,
                                system_info=system_info,
                                network_info=network_info)

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True, 'message': 'Fájl sikeresen törölve'})
        else:
            return jsonify({'success': False, 'error': 'Fájl nem található'}), 404
    except Exception as e:
        print(f"Error deleting file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/preview/<path:filename>')
def preview_file(filename):
    """Visszaadja a szöveges fájlok tartalmát JSON-ként az előnézethez."""
    safe_filename = secure_filename(filename)
    preview_type, _ = get_file_info(safe_filename)
    if preview_type not in ['code']:
        return jsonify({'error': 'Preview not available for this file type'}), 400
    
    try:
        with open(os.path.join(app.config['UPLOAD_FOLDER'], safe_filename), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1024 * 500) # Max 500KB olvasása a biztonság kedvéért
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/qr_code')
def qr_code_img():
    """Generál egy QR kódot a szerver címéből."""
    url = f"http://{get_local_ip()}:{PORT}"
    img_buffer = BytesIO()
    qr_img = qrcode.make(url)
    qr_img.save(img_buffer, 'PNG')
    img_buffer.seek(0)
    return Response(img_buffer, mimetype='image/png')

@app.route('/api/system-info')
def api_system_info():
    """API endpoint for real-time system information."""
    try:
        storage_info = get_storage_info()
        system_info = get_system_info()
        upload_info = get_upload_folder_info()
        
        return jsonify({
            'storage_info': storage_info,
            'system_info': system_info,
            'upload_info': upload_info,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files')
def api_files():
    """API endpoint to get current file list."""
    try:
        filenames = os.listdir(app.config['UPLOAD_FOLDER'])
        files_data = []
        for name in filenames:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], name)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                preview_type, icon = get_file_info(name)
                files_data.append({
                    'name': name,
                    'size': stat.st_size,
                    'size_formatted': format_bytes(stat.st_size),
                    'date': stat.st_mtime,
                    'date_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    'preview_type': preview_type,
                    'icon': icon                })
        
        return jsonify({
            'files': files_data,
            'count': len(files_data),
            'total_size': sum(f['size'] for f in files_data)
        })
    except FileNotFoundError:
        return jsonify({'files': [], 'count': 0, 'total_size': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/check')
def api_files_check():
    """API endpoint to check for file changes (for polling)."""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            return jsonify({
                'last_modified': 0,
                'file_count': 0,
                'has_changes': False
            })
        
        # Get the latest modification time in the upload folder
        latest_time = 0
        file_count = 0
        
        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            if os.path.isfile(filepath):
                file_count += 1
                mtime = os.path.getmtime(filepath)
                if mtime > latest_time:
                    latest_time = mtime
        
        return jsonify({
            'last_modified': latest_time,
            'file_count': file_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/messages')
def api_chat_messages():
    """API endpoint to get chat messages."""
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Maximum 100 üzenet
        
        messages = chat_messages[-limit:] if chat_messages else []
        
        return jsonify({
            'messages': messages,
            'count': len(messages),
            'total_count': len(chat_messages)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes/current', methods=['GET', 'POST'])
def api_notes_current():
    """API endpoint for current note operations."""
    if request.method == 'GET':
        try:
            notes_data = load_notes()
            return jsonify(notes_data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            notes_data = {
                'current_note': data.get('current_note', ''),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at', datetime.now().isoformat())
            }
            
            if save_notes(notes_data):
                return jsonify({'success': True, 'message': 'Jegyzet mentve'})
            else:
                return jsonify({'error': 'Failed to save note'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/notes/saved', methods=['GET', 'POST'])
def api_notes_saved():
    """API endpoint for saved notes operations."""
    if request.method == 'GET':
        try:
            saved_notes = load_saved_notes()
            return jsonify({'notes': saved_notes})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            saved_notes = load_saved_notes()
            
            # Check if note with same ID already exists (update case)
            existing_index = next((i for i, note in enumerate(saved_notes) if note.get('id') == data.get('id')), None)
            
            if existing_index is not None:
                # Update existing note
                saved_notes[existing_index] = data
            else:
                # Add new note
                saved_notes.append(data)
            
            if save_saved_notes(saved_notes):
                return jsonify({'success': True, 'message': 'Jegyzet mentve'})
            else:
                return jsonify({'error': 'Failed to save note'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/notes/saved/<note_id>', methods=['DELETE'])
def api_notes_saved_delete(note_id):
    """API endpoint to delete a saved note."""
    try:
        saved_notes = load_saved_notes()
        original_count = len(saved_notes)
        
        # Filter out the note with the specified ID
        saved_notes = [note for note in saved_notes if note.get('id') != note_id]
        
        if len(saved_notes) == original_count:
            return jsonify({'error': 'Note not found'}), 404
        
        if save_saved_notes(saved_notes):
            return jsonify({'success': True, 'message': 'Jegyzet törölve'})
        else:
            return jsonify({'error': 'Failed to delete note'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Szerver Indítása ---
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    
    local_ip = get_local_ip()
    print("*" * 60)
    print("  DropFlow - elindult!")
    print("  Nyisd meg a böngésződben vagy olvasd be a QR kódot:")
    print(f"  -> http://{local_ip}:{PORT}")
    print("  Chat funkció engedélyezve!")
    print("  Jegyzetfüzet funkció engedélyezve!")
    print("*" * 60)
    
    # SocketIO szerver indítása
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
