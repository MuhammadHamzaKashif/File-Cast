import sys
import os
import traceback
from datetime import datetime


LOG_FILE_PATH = "kiwi_crash_log.txt"


if "ANDROID_ARGUMENT" in os.environ:
    LOG_FILE_PATH = "/storage/emulated/0/Download/kiwi_crash_log.txt"

def log_lifecycle(msg):
    """Writes a message to the log file immediately."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    print(formatted_msg)
    
    # Write to file
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"!!! COULD NOT WRITE TO LOG FILE: {e}")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_lifecycle("\n" + "="*30)
    log_lifecycle("💀 FATAL CRASH DETECTED 💀")
    log_lifecycle(error_msg)
    log_lifecycle("="*30 + "\n")
    
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

log_lifecycle("--------------------------------------------------")
log_lifecycle(" APP STARTUP INITIATED")
log_lifecycle(f" Log file path set to: {LOG_FILE_PATH}")

# 
# IMPORTS
# 
try:
    log_lifecycle("📦 Importing Asyncio & Standard Libs...")
    import asyncio
    import json
    import struct
    import socket
    import threading
    from hashlib import sha1
    
    log_lifecycle("📦 Importing Kivy Config...")
    from kivy.config import Config
    Config.set('graphics', 'width', '900')
    Config.set('graphics', 'height', '700')
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

    log_lifecycle("📦 Importing Kivy UI Elements...")
    from kivy.app import App
    from kivy.lang import Builder
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.recycleview import RecycleView
    from kivy.uix.recycleview.views import RecycleDataViewBehavior
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.progressbar import ProgressBar
    from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
    from kivy.clock import Clock, mainthread
    from kivy.uix.popup import Popup
    from kivy.uix.textinput import TextInput
    from kivy.utils import get_color_from_hex
    from kivy.utils import platform
    log_lifecycle("✅ Kivy Imported Successfully")

except Exception as e:
    log_lifecycle(f"❌ CRASH DURING IMPORTS: {e}")
    raise e

#
# ASYNCIO PATCHES
#
log_lifecycle("🔧 Applying Asyncio Patches for Android...")
if not getattr(asyncio.gather, "_is_patched", False):
    _original_gather = asyncio.gather
    def _patched_gather(*args, **kwargs):
        kwargs.pop('loop', None)
        return _original_gather(*args, **kwargs)
    _patched_gather._is_patched = True
    asyncio.gather = _patched_gather

if not getattr(asyncio.wait_for, "_is_patched", False):
    _original_wait_for = asyncio.wait_for
    def _patched_wait_for(fut, timeout, **kwargs):
        kwargs.pop('loop', None)
        return _original_wait_for(fut, timeout, **kwargs)
    _patched_wait_for._is_patched = True
    asyncio.wait_for = _patched_wait_for

class SafeQueue(asyncio.Queue):
    def __init__(self, *args, **kwargs):
        kwargs.pop('loop', None)
        super().__init__(*args, **kwargs)
asyncio.Queue = SafeQueue

#
# IMPORT AIOBTDHT
#
try:
    log_lifecycle("📦 Attempting to import aiobtdht...")
    from aiobtdht import DHT
    log_lifecycle("✅ aiobtdht Imported Successfully")
except ImportError as e:
    log_lifecycle("❌ FAILED TO IMPORT aiobtdht. Did you include the folder?")
    log_lifecycle(f"Error details: {e}")


#
# GUI KV LAYOUT
#
KV_CODE = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

<TorrentRow>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(40)
    padding: dp(5)
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: get_color_from_hex('#2b2b2b') if self.index % 2 == 0 else get_color_from_hex('#333333')
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: root.name
        size_hint_x: 0.4
        shorten: True
        text_size: self.size
        halign: 'left'
        valign: 'center'
        color: get_color_from_hex('#ffffff')

    BoxLayout:
        size_hint_x: 0.3
        orientation: 'vertical'
        valign: 'center'
        Label:
            text: "{:.1f}%".format(root.progress)
            font_size: dp(10)
            size_hint_y: 0.4
        ProgressBar:
            value: root.progress
            max: 100
            size_hint_y: 0.6

    Label:
        text: root.status
        size_hint_x: 0.2
        color: get_color_from_hex('#aaaaaa')
        font_size: dp(12)

    Label:
        text: root.peers_count
        size_hint_x: 0.1
        font_size: dp(12)

<PeerFileRow>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(50)
    Button:
        text: root.text
        background_color: get_color_from_hex('#444488')
        on_release: root.select_callback(root.torrent_id, root.text)

<PeerFileListPopup>:
    title: "Files Available at Peer"
    size_hint: 0.8, 0.8
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)
        Label:
            text: "Click a file to download:"
            size_hint_y: None
            height: dp(30)
        RecycleView:
            id: rv_peer_files
            viewclass: 'PeerFileRow'
            RecycleBoxLayout:
                default_size: None, dp(50)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(5)
        Button:
            text: "Close"
            size_hint_y: None
            height: dp(40)
            on_release: root.dismiss()

<MainWindow>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: get_color_from_hex('#1e1e1e')
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(30)
        canvas.before:
            Color:
                rgba: get_color_from_hex('#003366') 
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            id: ip_status
            text: "Initializing..."
            color: get_color_from_hex('#00ffff')
            bold: True
            font_size: dp(14)

    BoxLayout:
        size_hint_y: None
        height: dp(50)
        padding: dp(5)
        spacing: dp(5)
        canvas.before:
            Color:
                rgba: get_color_from_hex('#3c3f41')
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "🥝 Kiwi"
            bold: True
            font_size: dp(18)
            size_hint_x: None
            width: dp(80)
            color: get_color_from_hex('#4caf50')
        Button:
            text: "+ Add ID"
            size_hint_x: None
            width: dp(80)
            background_color: get_color_from_hex('#444444')
            on_release: root.show_add_popup()
        Button:
            text: "Seed"
            size_hint_x: None
            width: dp(60)
            background_color: get_color_from_hex('#8844aa') 
            on_release: app.show_file_chooser()
        Button:
            text: "Debug"
            size_hint_x: None
            width: dp(60)
            background_color: get_color_from_hex('#aa4444')
            on_release: app.debug_dht()
        Label:
            text: " | IP:"
            size_hint_x: None
            width: dp(40)
        TextInput:
            id: direct_ip
            hint_text: "IP:PORT"
            size_hint_x: 0.3
            multiline: False
        Button:
            text: "Go"
            size_hint_x: None
            width: dp(50)
            background_color: get_color_from_hex('#4444aa')
            on_release: app.direct_connect_wrapper(direct_ip.text)

    BoxLayout:
        size_hint_y: None
        height: dp(30)
        padding: dp(5)
        spacing: dp(10)
        Label:
            text: "Name"
            size_hint_x: 0.4
            bold: True
        Label:
            text: "Progress"
            size_hint_x: 0.3
            bold: True
        Label:
            text: "Status"
            size_hint_x: 0.2
            bold: True
        Label:
            text: "Peers"
            size_hint_x: 0.1
            bold: True

    RecycleView:
        id: rv
        viewclass: 'TorrentRow'
        scroll_type: ['bars', 'content']
        bar_width: dp(10)
        RecycleBoxLayout:
            default_size: None, dp(40)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'

    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.3
        canvas.before:
            Color:
                rgba: get_color_from_hex('#000000')
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Log / Output"
            size_hint_y: None
            height: dp(20)
            halign: 'left'
            color: get_color_from_hex('#888888')
        TextInput:
            id: console_log
            readonly: True
            foreground_color: get_color_from_hex('#00ff00')
            background_color: 0, 0, 0, 0
            font_size: dp(11)

<AddTorrentPopup>:
    title: "Download from DHT"
    size_hint: 0.8, 0.4
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)
        Label:
            text: "Enter Torrent ID:"
            size_hint_y: None
            height: dp(30)
        TextInput:
            id: t_id_input
            multiline: False
        BoxLayout:
            spacing: dp(10)
            Button:
                text: "Cancel"
                on_release: root.dismiss()
            Button:
                text: "Download"
                on_release: root.download(t_id_input.text)

<FileLoadDialog>:
    title: "Select File"
    size_hint: 0.9, 0.9
    BoxLayout:
        orientation: "vertical"
        FileChooserListView:
            id: filechooser
            path: "/storage/emulated/0" if app.is_android() else "."
        BoxLayout:
            size_hint_y: None
            height: dp(30)
            Button:
                text: "Cancel"
                on_release: root.dismiss()
            Button:
                text: "Select"
                on_release: root.load(filechooser.path, filechooser.selection)

<PieceSizePopup>:
    title: "Set Piece Size"
    size_hint: 0.6, 0.4
    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        Label:
            text: "Piece Size (Bytes):"
        TextInput:
            id: p_size
            text: "262144"
            multiline: False
        BoxLayout:
            Button:
                text: "Cancel"
                on_release: root.dismiss()
            Button:
                text: "Seed"
                on_release: root.confirm(p_size.text)
'''

MSG_LEN = 4

def pack_msg(msg_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(msg_type + payload)) + msg_type + payload

async def read_msg(reader):
    try:
        raw_len = await reader.readexactly(MSG_LEN)
    except asyncio.IncompleteReadError:
        return None, None
    (l,) = struct.unpack(">I", raw_len)
    data = await reader.readexactly(l)
    return data[:1], data[1:]

class UDPAdapter(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.subscriber = None
        self.dht = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if self.subscriber:
            asyncio.create_task(self.subscriber(data, addr))

    def send(self, data, addr):
        if self.transport:
            self.transport.sendto(data, addr)
            
    def subscribe(self, callback):
        self.subscriber = callback

#
# KIVY UI CLASSES
# 

class TorrentRow(BoxLayout, RecycleDataViewBehavior):
    index = NumericProperty(0)
    name = StringProperty("Unknown")
    progress = NumericProperty(0.0)
    status = StringProperty("Idle")
    peers_count = StringProperty("0")

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

class PeerFileRow(BoxLayout, RecycleDataViewBehavior):
    text = StringProperty("")
    torrent_id = StringProperty("")
    select_callback = ObjectProperty(None)
    
    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

class PeerFileListPopup(Popup):
    def set_data(self, files, callback):
        data = []
        for f in files:
            data.append({
                'text': f['name'],
                'torrent_id': f['torrent_id'],
                'select_callback': callback
            })
        self.ids.rv_peer_files.data = data

class AddTorrentPopup(Popup):
    def download(self, t_id):
        t_id = t_id.strip()
        if t_id:
            app = App.get_running_app()
            app.root.add_log(f"Requesting download for: {t_id}")
            app.add_download_task(t_id)
        self.dismiss()

class FileLoadDialog(Popup):
    load = ObjectProperty(None)

class PieceSizePopup(Popup):
    confirm = ObjectProperty(None)

class MainWindow(BoxLayout):
    def show_add_popup(self):
        p = AddTorrentPopup()
        p.open()
    
    def add_log(self, text):
        log_lifecycle(text) # Also save to file
        def _update(dt):
            ts = datetime.now().strftime("%H:%M:%S")
            self.ids.console_log.text += f"[{ts}] {text}\n"
            self.ids.console_log.cursor = (0, 0)
        Clock.schedule_once(_update)

    def update_dht_status(self, count):
        self.ids.dht_status.text = f"DHT Nodes: {count}"

#
# MAIN APP CLASS
#

class KiwiTorrentApp(App):
    data_items = ListProperty([])

    def build(self):
        log_lifecycle("🎨 Building GUI...")
        Builder.load_string(KV_CODE)
        return MainWindow()

    def is_android(self):
        return platform == 'android'

    def on_start(self):
        log_lifecycle("📱 App Started (on_start)")
        if platform == 'android':
            log_lifecycle("🤖 Android detected. Requesting permissions...")
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.ACCESS_NETWORK_STATE
            ])
            log_lifecycle("✅ Permissions requested.")
        else:
            log_lifecycle("💻 Desktop detected.")
            
        asyncio.create_task(self.setup_backend())

    @mainthread
    def update_row(self, t_id, **kwargs):
        new_data = []
        found = False
        for item in self.data_items:
            if item.get('id') == t_id:
                item.update(kwargs)
                found = True
            new_data.append(item)
        
        if not found and 'name' in kwargs:
            item = {'id': t_id}
            item.update(kwargs)
            new_data.append(item)
        
        self.data_items = new_data
        self.root.ids.rv.data = self.data_items
        self.root.ids.rv.refresh_from_data()

    def debug_dht(self):
        if not hasattr(self, 'dht') or not self.dht: 
            self.root.add_log("DHT Not Ready")
            return
        count = 0
        try:
            rt = self.dht.routing_table
            buckets = getattr(rt, 'buckets', getattr(rt, '_buckets', []))
            for bucket in buckets:
                count += len(bucket.nodes)
        except Exception as e:
            self.root.add_log(f"DHT Debug Error: {e}")
        self.root.add_log(f"--- DHT Nodes: {count} ---")

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    # --- SEEDING LOGIC ---
    def show_file_chooser(self):
        content = FileLoadDialog(load=self.load_file)
        self._popup = content
        self._popup.open()

    def load_file(self, path, selection):
        self._popup.dismiss()
        if selection:
            self.selected_file = selection[0]
            content = PieceSizePopup(confirm=self.process_seed_file)
            self._size_popup = content
            self._size_popup.open()

    def process_seed_file(self, size_text):
        self._size_popup.dismiss()
        try:
            piece_size = int(size_text)
        except ValueError:
            piece_size = 262144 
        threading.Thread(target=self.make_pieces_worker, args=(self.selected_file, piece_size)).start()

    def make_pieces_worker(self, file_path, piece_size):
        try:
            self.root.add_log(f"Hashing: {os.path.basename(file_path)}...")
            base_name = os.path.basename(file_path)
            size = os.path.getsize(file_path)
            torent_id_hasher = sha1()
            pieces = []

            # fpr android
            if platform == 'android':
                from android.storage import primary_external_storage_path
                base_dir = os.path.join(primary_external_storage_path(), "Download", "KiwiTorrent")
            else:
                base_dir = "torrents"

            out_dir = os.path.join(base_dir, f"torrent_{base_name}_{size}")
            pieces_dir = os.path.join(out_dir, "pieces")
            os.makedirs(pieces_dir, exist_ok=True)

            with open(file_path, "rb") as f:
                i = 0
                while True:
                    data = f.read(piece_size)
                    if not data: break
                    h = sha1(data).hexdigest()
                    pieces.append(h)
                    torent_id_hasher.update(bytes.fromhex(h))
                    piece_name = os.path.join(pieces_dir, f"piece_{i:06d}.bin")
                    with open(piece_name, "wb") as pf:
                        pf.write(data)
                    i += 1

            torrent_id = torent_id_hasher.hexdigest()
            metadata = {"name": base_name, "length": size, "piece_length": piece_size, "pieces": pieces, "torrent_id": torrent_id}
            
            meta_path = os.path.join(out_dir, "metadata.json")
            with open(meta_path, "w") as m:
                json.dump(metadata, m, indent=2)
            
            self.root.add_log(f"Seeding ID: {torrent_id}")
            self.update_row(torrent_id, name=base_name, progress=100, status="Seeding (Local)")
            if self.dht:
                asyncio.run_coroutine_threadsafe(self.dht.announce(bytes.fromhex(torrent_id), self.port), self.loop)

        except Exception as e:
            self.root.add_log(f"Seeding failed: {e}")

    # --- BACKEND ---
    async def setup_backend(self):
        log_lifecycle("⚙️ Setting up backend...")
        self.loop = asyncio.get_running_loop()
        self.port = 6881
        self.host = "0.0.0.0"
        
        self.udp_adapter = UDPAdapter()
        
        try:
            await self.loop.create_datagram_endpoint(lambda: self.udp_adapter, local_addr=(self.host, self.port))
            self.root.add_log(f"Bound to port {self.port}")
        except OSError:
            self.port = 0 
            await self.loop.create_datagram_endpoint(lambda: self.udp_adapter, local_addr=(self.host, self.port))
            if self.udp_adapter.transport:
                self.port = self.udp_adapter.transport.get_extra_info('sockname')[1]
            self.root.add_log(f"Port busy. Using random port {self.port}")

        my_ip = self.get_local_ip()
        self.root.ids.ip_status.text = f"My Address: {my_ip}:{self.port}"

        try:
            log_lifecycle("⚙️ Initializing DHT...")
            local_id = int.from_bytes(os.urandom(20), "big")
            self.dht = DHT(local_id, self.udp_adapter, self.loop)
            self.udp_adapter.dht = self.dht
            
            bootstrap_shii = [("router.utorrent.com", 6881)]
            await self.dht.bootstrap(bootstrap_shii)
            self.root.add_log("DHT Bootstrapped.")
        except Exception as e:
            log_lifecycle(f"❌ DHT INIT FAILED: {e}")

        asyncio.create_task(self.announce_loop())
        asyncio.create_task(self.server_loop())

    async def announce_loop(self):
        while True:
            # Need to scan both possible locations (app internal and external)
            scan_dirs = ["torrents"]
            if platform == 'android':
                from android.storage import primary_external_storage_path
                scan_dirs.append(os.path.join(primary_external_storage_path(), "Download", "KiwiTorrent"))

            for base in scan_dirs:
                if os.path.exists(base):
                    for folder in os.listdir(base):
                        meta_path = os.path.join(base, folder, "metadata.json")
                        if os.path.exists(meta_path):
                            try:
                                with open(meta_path, 'r') as rf: m = json.load(rf)
                                if "torrent_id" in m and self.dht:
                                    await self.dht.announce(bytes.fromhex(m["torrent_id"]), self.port)
                            except: pass
            await asyncio.sleep(60)

    async def server_loop(self):
        log_lifecycle("⚙️ Starting TCP Server...")
        server = await asyncio.start_server(self.handle_peer_connection, host=self.host, port=self.port)
        self.root.add_log(f"TCP Server listening on {self.port}")
        async with server: await server.serve_forever()

    async def handle_peer_connection(self, reader, writer):
        try:
            typ, payload = await read_msg(reader=reader)
            if typ is None: return

            if typ == b'L': # LIST
                available = []
                # Scan both locations
                scan_dirs = ["torrents"]
                if platform == 'android':
                    from android.storage import primary_external_storage_path
                    scan_dirs.append(os.path.join(primary_external_storage_path(), "Download", "KiwiTorrent"))

                for base in scan_dirs:
                    if os.path.exists(base):
                        for f in os.listdir(base):
                            mp = os.path.join(base, f, "metadata.json")
                            if os.path.exists(mp):
                                try:
                                    with open(mp) as rf: available.append(json.load(rf))
                                except: pass
                
                writer.write(pack_msg(b'L', json.dumps(available).encode()))
                await writer.drain()
                return

            if typ == b'M': # META
                req_id = payload.decode()
                metadata = {}
                found = False
                
                scan_dirs = ["torrents"]
                if platform == 'android':
                    from android.storage import primary_external_storage_path
                    scan_dirs.append(os.path.join(primary_external_storage_path(), "Download", "KiwiTorrent"))

                for base in scan_dirs:
                    if os.path.exists(base):
                        for f in os.listdir(base):
                            mp = os.path.join(base, f, "metadata.json")
                            if os.path.exists(mp):
                                try:
                                    with open(mp) as rf: temp = json.load(rf)
                                    if temp['torrent_id'] == req_id:
                                        metadata = temp
                                        found = True
                                        break
                                except: pass
                    if found: break

                if not found:
                    writer.close(); return
                writer.write(pack_msg(b'M', json.dumps(metadata).encode()))
                await writer.drain()

                # Handshake
                typ, payload = await read_msg(reader)
                if typ != b'H': return
                writer.write(pack_msg(b'H', metadata["torrent_id"].encode()))
                await writer.drain()

                # Bitfield
                n_pieces = len(metadata["pieces"])
                bitfield_bytes = bytearray((n_pieces + 7) // 8)
                for i in range(n_pieces):
                    bitfield_bytes[i // 8] |= (1 << (i % 8))
                
                writer.write(pack_msg(b'B', bytes(bitfield_bytes)))
                await writer.drain()

                # Pieces
                # Locate pieces
                p_dir = None
                folder_name = f"torrent_{metadata['name'].split('.')[0]}_{metadata['torrent_id'][:6]}"
                
                # Check known paths
                for base in scan_dirs:
                    check_path = os.path.join(base, folder_name, "pieces")
                    if os.path.exists(check_path):
                        p_dir = check_path
                        break
                    # Brute force search if name mismatch
                    if os.path.exists(base):
                        for f in os.listdir(base):
                            mp = os.path.join(base, f, "metadata.json")
                            if os.path.exists(mp):
                                try:
                                    with open(mp) as rf:
                                        if json.load(rf)['torrent_id'] == metadata['torrent_id']:
                                            p_dir = os.path.join(base, f, "pieces")
                                            break
                                except: pass
                        if p_dir: break

                while True:
                    typ, payload = await read_msg(reader)
                    if typ != b'R': break
                    (piece_idx,) = struct.unpack(">I", payload[:4])
                    if p_dir:
                        p_path = os.path.join(p_dir, f"piece_{piece_idx:06d}.bin")
                        if os.path.exists(p_path):
                            with open(p_path, "rb") as pf: p_data = pf.read()
                            writer.write(pack_msg(b'P', struct.pack(">I", piece_idx) + p_data))
                            await writer.drain()
        except: pass
        finally: writer.close()

    # --- CLIENT ---
    def add_download_task(self, torrent_id):
        self.update_row(torrent_id, name=f"Finding peers...", progress=0, status="Searching DHT")
        asyncio.create_task(self.download_workflow(torrent_id))

    def direct_connect_wrapper(self, ip_port_str):
        if ":" not in ip_port_str:
            self.root.add_log("Invalid format. Use IP:PORT")
            return
        host, port = ip_port_str.split(":")
        try:
            port = int(port)
            asyncio.create_task(self.direct_list_and_download(host, port))
        except ValueError:
            self.root.add_log("Port must be a number")

    async def direct_list_and_download(self, host, port):
        self.root.add_log(f"Connecting directly to {host}:{port}...")
        try:
            reader, writer = await asyncio.open_connection(host, port)
            
            # Request List
            writer.write(pack_msg(b'L', b''))
            await writer.drain()
            
            typ, payload = await read_msg(reader)
            if typ == b'L':
                files = json.loads(payload.decode())
                if not files:
                    self.root.add_log("Peer has no files.")
                else:
                    self.current_peer = (host, port)
                    self._peer_list_popup = PeerFileListPopup()
                    self._peer_list_popup.set_data(files, self.on_peer_file_selected)
                    self._peer_list_popup.open()
            else:
                self.root.add_log("Peer sent unknown response.")
            
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.root.add_log(f"Direct connection failed: {e}")

    def on_peer_file_selected(self, torrent_id, file_name):
        if hasattr(self, '_peer_list_popup'):
            self._peer_list_popup.dismiss()
        host, port = self.current_peer
        self.root.add_log(f"Selected: {file_name}. Starting...")
        self.update_row(torrent_id, name=file_name, progress=0, status="Direct Connect")
        asyncio.create_task(self.download_torrent(host, port, torrent_id))

    async def download_workflow(self, torrent_id):
        self.root.add_log(f"Searching DHT for {torrent_id}")
        peers = []
        for attempt in range(2): 
            shii_info = bytes.fromhex(torrent_id)
            if self.dht:
                peers = await self.dht[shii_info]
            if peers: break
            await asyncio.sleep(1)
        
        if not peers:
            self.update_row(torrent_id, status="Stalled (No Peers)")
            self.root.add_log("No peers found via DHT.")
            return

        host, port = peers[0]
        await self.download_torrent(host, port, torrent_id)

    async def download_torrent(self, peer_host, peer_port, torrent_id):
        self.update_row(torrent_id, status="Connecting...", peers_count="1")
        try:
            reader, writer = await asyncio.open_connection(peer_host, peer_port)
        except:
            self.root.add_log(f"Connection failed to {peer_host}:{peer_port}")
            self.update_row(torrent_id, status="Conn Failed")
            return

        try:
            # Meta
            writer.write(pack_msg(b'M', torrent_id.encode()))
            await writer.drain()
            typ, payload = await read_msg(reader)
            if typ != b'M': return
            
            metadata = json.loads(payload.decode())
            name = metadata['name']
            self.update_row(torrent_id, name=name, status="Downloading")
            
            # Storage
            save_dir = os.path.join("downloads", name)
            if platform == 'android':
                from android.storage import primary_external_storage_path
                save_dir = os.path.join(primary_external_storage_path(), "Download", "KiwiTorrent", name)
            
            pieces_dir = os.path.join(save_dir, "pieces")
            os.makedirs(pieces_dir, exist_ok=True)

            # Handshake
            writer.write(pack_msg(b'H', metadata["torrent_id"].encode()))
            await writer.drain()
            typ, _ = await read_msg(reader) 
            
            # Bitfield
            typ, payload = await read_msg(reader) 
            
            # Download Loop
            n_pieces = len(metadata["pieces"])
            downloaded = 0
            
            for i in range(n_pieces):
                p_path = os.path.join(pieces_dir, f"piece_{i:06d}.bin")
                if os.path.exists(p_path): 
                    downloaded += 1
                    continue

                writer.write(pack_msg(b'R', struct.pack(">I", i)))
                await writer.drain()

                typ, payload = await read_msg(reader)
                if typ == b'P':
                    with open(p_path, "wb") as f: f.write(payload[4:])
                    downloaded += 1
                    pct = (downloaded / n_pieces) * 100
                    self.update_row(torrent_id, progress=pct)
                    await asyncio.sleep(0.1)

            self.update_row(torrent_id, progress=100, status="Seeding")
            self.root.add_log(f"Finished: {name}")
            
            # Assemble
            final_file = os.path.join(save_dir, name)
            with open(final_file, 'wb') as outfile:
                for i in range(n_pieces):
                    with open(os.path.join(pieces_dir, f"piece_{i:06d}.bin"), 'rb') as pf:
                        outfile.write(pf.read())
            self.root.add_log(f"File saved to: {final_file}")

        except Exception as e:
            self.root.add_log(f"Download Error: {e}")
            self.update_row(torrent_id, status="Error")
        finally:
            writer.close()

if __name__ == '__main__':
    log_lifecycle("🔄 App Main Entry Point Reached")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app = KiwiTorrentApp()
        loop.run_until_complete(app.async_run(async_lib='asyncio'))
    except KeyboardInterrupt:
        log_lifecycle("🛑 App stopped by user")
    except Exception as e:
        log_lifecycle(f"🔥 FATAL: {e}")