# --- Python 3.13 & Pydroid Fixed Layout Advanced GIS Engine ---
import os
import sys

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_LOG_MODE"] = "MIXED"

import types
import math
import re
import csv

try:
    import cgi
except Exception:
    from html import escape
    cgi = types.ModuleType("cgi")
    cgi.escape = escape
    sys.modules["cgi"] = cgi

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.filemanager import MDFileManager
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import simplekml
import openpyxl

def utm_to_latlon(easting, northing, zone):
    try:
        a = 6378137.0         
        f = 1.0 / 298.257223563 
        k0 = 0.9996           
        b = a * (1.0 - f)
        e2 = (a**2 - b**2) / (a**2)
        ep2 = (a**2 - b**2) / (b**2)
        lon0 = ((zone * 6.0) - 183.0) * (math.pi / 180.0)
        x = easting - 500000.0
        y = northing
        M = y / k0
        mu = M / (a * (1.0 - e2 / 4.0 - 3.0 * e2**2 / 64.0 - 5.0 * e2**3 / 256.0))
        e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
        phi1 = (mu + (3.0 * e1 / 2.0 - 27.0 * e1**3 / 32.0) * math.sin(2.0 * mu)
                + (21.0 * e1**2 / 16.0 - 55.0 * e1**4 / 32.0) * math.sin(4.0 * mu)
                + (151.0 * e1**3 / 96.0) * math.sin(6.0 * mu))
        sin_phi1 = math.sin(phi1)
        cos_phi1 = math.cos(phi1)
        tan_phi1 = math.tan(phi1)
        N1 = a / math.sqrt(1.0 - e2 * sin_phi1**2)
        R1 = a * (1.0 - e2) / math.pow(1.0 - e2 * sin_phi1**2, 1.5)
        D = x / (N1 * k0)
        lat = phi1 - (N1 * tan_phi1 / R1) * (D**2 / 2.0 - (5.0 + 3.0 * tan_phi1**2 + 10.0 * (ep2 * cos_phi1**2) - 4.0 * (ep2 * cos_phi1**2)**2 - 9.0 * ep2) * D**4 / 24.0 + (61.0 + 90.0 * tan_phi1**2 + 298.0 * (ep2 * cos_phi1**2) + 45.0 * tan_phi1**4 - 252.0 * ep2 - 3.0 * (ep2 * cos_phi1**2)**2) * D**6 / 720.0)
        lon = lon0 + (D - (1.0 + 2.0 * tan_phi1**2 + (ep2 * cos_phi1**2)) * D**3 / 6.0 + (5.0 - 2.0 * (ep2 * cos_phi1**2) + 28.0 * tan_phi1**2 - 3.0 * (ep2 * cos_phi1**2)**2 + 8.0 * ep2 + 24.0 * tan_phi1**4) * D**5 / 120.0) / cos_phi1
        return math.degrees(lat), math.degrees(lon)
    except Exception:
        return 0.0, 0.0

class GISMasterApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
        self.mode = "WGS84"
        self.sel_x = self.sel_y = self.sel_label = None
        # Yahan Default URL ko Circle (placemark_circle) se replace kar diya hai takia automatic pehle se hi circle bane
        self.icon_url = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
        self.i_color, self.l_color = "ff0000ff", "ffffffff"
        self.menus = {}
        self.columns = []
        self.data_rows = []
        self.layer_queue = [] 

        self.internal_file_manager = MDFileManager(
            exit_manager=self.exit_internal_manager,
            select_path=self.on_file_selected
        )

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        screen = MDScreen()
        scroll = ScrollView()
        layout = MDBoxLayout(orientation="vertical", padding=15, spacing=12, size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        header = MDCard(size_hint=(1, None), height="85dp", radius=[12,], md_bg_color=(0, 0.4, 0.4, 1), padding=12)
        header.add_widget(MDLabel(text="MULTI-LAYER KMZ COMPILER\nAdvanced GIS Workspace Engine", halign="center", theme_text_color="Custom", text_color=(1, 1, 1, 1), font_style="H6"))
        layout.add_widget(header)

        self.status_card = MDCard(size_hint=(1, None), height="220dp", padding=15, radius=[12,], md_bg_color=(0.12, 0.12, 0.12, 1))
        self.status = MDLabel(text="STATUS: WORKSPACE READY\n\nQueue Pipeline: 0 Layers Loaded\nConfigure and append target attributes below.", halign="center", theme_text_color="Primary", font_style="Body1")
        self.status_card.add_widget(self.status)
        layout.add_widget(self.status_card)

        self.btn_file = MDRaisedButton(text="1. BROWSE DATA FILE (LAYER SOURCE)", size_hint=(1, None), on_release=self.trigger_file_selection)
        self.btn_mode = MDRaisedButton(text="2. INPUT CRS SYSTEM", size_hint=(1, None), md_bg_color=(0.1, 0.4, 0.6, 1))
        self.btn_x = MDRaisedButton(text="SELECT X (EASTING / LON)", size_hint=(1, None), disabled=True)
        self.btn_y = MDRaisedButton(text="SELECT Y (NORTHING / LAT)", size_hint=(1, None), disabled=True)
        self.btn_label = MDRaisedButton(text="SELECT POINT LABEL", size_hint=(1, None), disabled=True)
        self.btn_icon = MDRaisedButton(text="SELECT LAYER ICON SHAPE", size_hint=(1, None), md_bg_color=(0.4, 0.2, 0.6, 1))
        self.btn_icon_col = MDRaisedButton(text="SELECT LAYER ICON COLOR", size_hint=(1, None), md_bg_color=(1, 0, 0, 1))
        self.btn_label_col = MDRaisedButton(text="SELECT LAYER LABEL COLOR", size_hint=(1, None), md_bg_color=(1, 1, 1, 1), text_color=(0, 0, 0, 1))

        self.i_scale = MDTextField(hint_text="Icon Display Scale (e.g. 1.0)", text="1.0", size_hint=(1, None))
        self.l_scale = MDTextField(hint_text="Label Display Scale (e.g. 0.9)", text="0.9", size_hint=(1, None))
        self.layer_name_input = MDTextField(hint_text="Custom Layer Folder Name (e.g. Transformers)", size_hint=(1, None))
        
        self.btn_add_layer = MDRaisedButton(text="ADD THIS LAYER TO PIPELINE QUEUE", md_bg_color=(0.5, 0.35, 0.0, 1), size_hint=(1, None), on_release=self.add_layer_to_queue)
        
        self.out_name = MDTextField(hint_text="Final Master KMZ Filename", size_hint=(1, None))
        self.btn_gen = MDRaisedButton(text="COMPILE ALL LAYERS TO SINGLE KMZ", md_bg_color=(0, 0.6, 0.3, 1), size_hint=(1, None), on_release=self.compile_master_kmz)

        for w in [
            self.btn_file, self.btn_mode, self.btn_x, self.btn_y, self.btn_label, 
            self.btn_icon, self.btn_icon_col, self.btn_label_col, 
            self.i_scale, self.l_scale, self.layer_name_input, self.btn_add_layer,
            self.out_name, self.btn_gen
        ]:
            layout.add_widget(w)

        self.setup_menus()
        scroll.add_widget(layout)
        screen.add_widget(scroll)
        return screen

    def setup_menus(self):
        m_list = [("WGS84 (Lat/Long)", "WGS84"), ("UTM 42N", 42), ("UTM 43N", 43)]
        self.menus["mode"] = MDDropdownMenu(caller=self.btn_mode, items=[{"text": x[0], "on_release": lambda v=x: self.set_mode(v)} for x in m_list], width_mult=4)
        self.btn_mode.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["mode"].open(), 0.05))

        # Yahan Circle aur baaki shapes ke functional URLs update kar diye hain
        s_list = [
            ("Circle", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"),
            ("Square", "http://maps.google.com/mapfiles/kml/shapes/square.png"),
            ("Star", "http://maps.google.com/mapfiles/kml/shapes/star.png"),
            ("Triangle", "http://maps.google.com/mapfiles/kml/shapes/triangle.png"),
            ("Diamond", "http://maps.google.com/mapfiles/kml/shapes/polygon.png"),
            ("Pushpin", "http://maps.google.com/mapfiles/kml/pushpin/blue-pushpin.png"),
            ("Target", "http://maps.google.com/mapfiles/kml/shapes/target.png"),
            ("Arrow", "http://maps.google.com/mapfiles/kml/shapes/arrow.png"),
            ("Crosshairs", "http://maps.google.com/mapfiles/kml/shapes/crosshairs.png"),
            ("Marker", "http://maps.google.com/mapfiles/kml/shapes/poi.png")
        ]
        self.menus["icon"] = MDDropdownMenu(caller=self.btn_icon, items=[{"text": x[0], "on_release": lambda v=x: self.set_icon(v)} for x in s_list], width_mult=4)
        self.btn_icon.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["icon"].open(), 0.05))

        c_list = [
            ("Red", "ff0000ff", (1, 0, 0, 1)), 
            ("Green", "ff00ff00", (0, 1, 0, 1)), 
            ("Blue", "ffff0000", (0, 0, 1, 1)), 
            ("Yellow", "ff00ffff", (1, 1, 0, 1)), 
            ("White", "ffffffff", (1, 1, 1, 1)),
            ("Cyan", "ffff00ff", (0, 1, 1, 1)),
            ("Orange", "ff00a5ff", (1, 0.6, 0, 1)),
            ("Purple", "ff800080", (0.5, 0, 0.5, 1)),
            ("Magenta", "ffff00ff", (1, 0, 1, 1)),
            ("Lime Green", "ff32cd32", (0.2, 0.8, 0.2, 1))
        ]
        self.menus["i_col"] = MDDropdownMenu(caller=self.btn_icon_col, items=[{"text": x[0], "on_release": lambda v=x: self.set_color("i", v)} for x in c_list], width_mult=4)
        self.menus["l_col"] = MDDropdownMenu(caller=self.btn_label_col, items=[{"text": x[0], "on_release": lambda v=x: self.set_color("l", v)} for x in c_list], width_mult=4)
        self.btn_icon_col.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["i_col"].open(), 0.05))
        self.btn_label_col.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["l_col"].open(), 0.05))

    def set_mode(self, m):
        self.mode = m[1]
        self.btn_mode.text = f"Mode: {m[0]}"
        self.menus["mode"].dismiss()

    def set_icon(self, s):
        self.icon_url = s[1]
        self.btn_icon.text = f"Shape: {s[0]}"
        self.menus["icon"].dismiss()

    def set_color(self, t, c):
        if t == "i":
            self.i_color = c[1]
            self.btn_icon_col.md_bg_color = c[2]
            self.menus["i_col"].dismiss()
        else:
            self.l_color = c[1]
            self.btn_label_col.md_bg_color = c[2]
            self.menus["l_col"].dismiss()

    def trigger_file_selection(self, *args):
        initial_path = "/storage/emulated/0/Download"
        if not os.path.exists(initial_path):
            initial_path = "/storage/emulated/0"
        self.internal_file_manager.show(initial_path)

    def exit_internal_manager(self, *args):
        self.internal_file_manager.close()

    def on_file_selected(self, path):
        self.exit_internal_manager()
        if not path or not os.path.isfile(path):
            return
            
        self.selected_file = path
        self.columns = []
        self.data_rows = []

        base_filename = os.path.splitext(os.path.basename(path))[0]
        self.layer_name_input.text = base_filename

        if path.endswith(".xlsx"):
            wb = openpyxl.load_workbook(path, data_only=True)
            sheet = wb.active
            for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                if r_idx == 0:
                    self.columns = [str(c).strip() for c in row if c is not None]
                else:
                    if any(x is not None for x in row):
                        self.data_rows.append(list(row))
        else:
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                self.columns = [c.strip() for c in next(reader)]
                for row in reader:
                    if row: self.data_rows.append(row)

        self.menus["x"] = MDDropdownMenu(caller=self.btn_x, items=[{"text": c, "on_release": lambda x=c: self.set_val("x", x)} for c in self.columns], width_mult=4)
        self.menus["y"] = MDDropdownMenu(caller=self.btn_y, items=[{"text": c, "on_release": lambda x=c: self.set_val("y", x)} for c in self.columns], width_mult=4)
        self.menus["label"] = MDDropdownMenu(caller=self.btn_label, items=[{"text": c, "on_release": lambda x=c: self.set_val("l", x)} for c in self.columns], width_mult=4)

        self.btn_x.disabled = self.btn_y.disabled = self.btn_label.disabled = False
        self.btn_x.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["x"].open(), 0.05))
        self.btn_y.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["y"].open(), 0.05))
        self.btn_label.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["label"].open(), 0.05))

        self.btn_file.text = f"FILE LOADED: {os.path.basename(path)}"

    def set_val(self, t, v):
        if t == "x":
            self.sel_x = v
            self.btn_x.text = f"X: {v}"
            self.menus["x"].dismiss()
        elif t == "y":
            self.sel_y = v
            self.btn_y.text = f"Y: {v}"
            self.menus["y"].dismiss()
        else:
            self.sel_label = v
            self.btn_label.text = f"Label: {v}"
            self.menus["label"].dismiss()

    def add_layer_to_queue(self, *args):
        if not self.selected_file or not self.sel_x or not self.sel_y or not self.sel_label:
            self.status.text = "Error: Configure all columns before adding layer!"
            return
            
        layer_name = self.layer_name_input.text.strip() or f"Layer_{len(self.layer_queue)+1}"
        
        layer_pack = {
            "name": layer_name,
            "data_rows": self.data_rows,
            "columns": self.columns,
            "x_idx": self.columns.index(self.sel_x),
            "y_idx": self.columns.index(self.sel_y),
            "l_idx": self.columns.index(self.sel_label),
            "mode": self.mode,
            "icon_url": self.icon_url,
            "i_color": self.i_color,
            "l_color": self.l_color,
            "i_scale": float(self.i_scale.text or "1.0"),
            "l_scale": float(self.l_scale.text or "0.9")
        }
        
        self.layer_queue.append(layer_pack)
        
        self.selected_file = None
        self.btn_file.text = "1. BROWSE DATA FILE (NEXT LAYER SOURCE)"
        self.btn_x.text = "SELECT X (EASTING / LON)"
        self.btn_y.text = "SELECT Y (NORTHING / LAT)"
        self.btn_label.text = "SELECT POINT LABEL"
        self.btn_x.disabled = self.btn_y.disabled = self.btn_label.disabled = True
        
        self.status.text = f"SUCCESS: Added Layer '{layer_name}'!\nPipeline Status: {len(self.layer_queue)} Layers in Queue."

    def compile_master_kmz(self, *args):
        if not self.layer_queue:
            self.status.text = "Processing Failed:\nPipeline is empty. Load and add layers first."
            return
            
        self.kml = simplekml.Kml()
        self.btn_gen.disabled = True
        
        report_output = "CONVERSION COMPLETED\n------------------------------\n"
        
        for layer in self.layer_queue:
            kml_folder = self.kml.newfolder(name=layer["name"])
            success_points = 0
            skipped_points = 0
            
            for row in layer["data_rows"]:
                try:
                    while len(row) < len(layer["columns"]): row.append("")
                    val_x = str(row[layer["x_idx"]]).strip()
                    val_y = str(row[layer["y_idx"]]).strip()
                    val_lbl = str(row[layer["l_idx"]]).strip()

                    if not val_x or not val_y or val_x.lower() == "nan" or val_y.lower() == "nan":
                        skipped_points += 1
                        continue

                    try:
                        vx, vy = float(val_x), float(val_y)
                    except ValueError:
                        skipped_points += 1
                        continue

                    if layer["mode"] == "WGS84":
                        lon, lat = vx, vy
                    else:
                        lat, lon = utm_to_latlon(vx, vy, layer["mode"])

                    if lat == 0.0 and lon == 0.0:
                        skipped_points += 1
                        continue

                    pnt = kml_folder.newpoint(name=val_lbl, coords=[(lon, lat)])
                    
                    desc = (
                        '<div style="font-family:\'Segoe UI\',Arial,sans-serif; width:320px; background:#fdfdfd; '
                        'padding:0; border-radius:8px; overflow:hidden; border:1px solid #ccc; box-shadow:0 4px 10px rgba(0,0,0,0.15);">'
                    )
                    desc += (
                        f'<div style="background:#005A5B; color:#ffffff; padding:10px 14px; font-size:14px; '
                        f'font-weight:bold; letter-spacing:0.5px; text-transform:uppercase; border-bottom:2px solid #004041;">'
                        f'Asset ID: {val_lbl}</div>'
                    )
                    desc += '<table style="width:100%; border-collapse:collapse; font-size:12px; background:#ffffff;">'

                    img_section = ""
                    row_idx = 0

                    for idx, col in enumerate(layer["columns"]):
                        if idx >= len(row): break
                        val = str(row[idx]).strip()
                        if not val or val.lower() == "nan": continue
                        
                        is_photo = any(x in col.lower() for x in ["photo", "image", "link"])
                        bg_color = "#f9f9f9" if row_idx % 2 == 0 else "#ffffff"

                        if is_photo:
                            desc += (
                                f'<tr style="background:{bg_color}; border-bottom:1px solid #eaeaea;">'
                                f'<td style="padding:8px 12px; color:#555; font-weight:bold; width:35%; border-right:1px solid #eaeaea;">{col}</td>'
                                f'<td style="padding:8px 12px;"><a href="{val}" style="color:#007B7C; font-weight:bold; text-decoration:none;">View Link</a></td></tr>'
                            )
                            links = re.split(r"[ ,|;]+", val)
                            for l in links:
                                if l.lower().startswith("http"):
                                    img_section += (
                                        f'<div style="padding:12px; background:#f4f4f4; text-align:center; border-top:1px solid #ddd;">'
                                        f'<img src="{l}" width="290" style="border-radius:6px; box-shadow:0 2px 5px rgba(0,0,0,0.1); border:1px solid #ccc;">'
                                        f'<br><a href="{l}" style="font-size:11px; color:#005A5B; font-weight:bold; text-decoration:none; display:inline-block; margin-top:6px;">Open Full Resolution</a>'
                                        f'</div>'
                                    )
                        else:
                            desc += (
                                f'<tr style="background:{bg_color}; border-bottom:1px solid #eaeaea;">'
                                f'<td style="padding:8px 12px; color:#555; font-weight:bold; width:35%; border-right:1px solid #eaeaea;">{col}</td>'
                                f'<td style="padding:8px 12px; color:#222; word-wrap:break-word;">{val}</td></tr>'
                            )
                        row_idx += 1

                    pnt.description = desc + "</table>" + img_section + "</div>"
                    pnt.style.iconstyle.icon.href, pnt.style.iconstyle.color = layer["icon_url"], layer["i_color"]
                    pnt.style.iconstyle.scale = layer["i_scale"]
                    pnt.style.labelstyle.scale, pnt.style.labelstyle.color = layer["l_scale"], layer["l_color"]
                    success_points += 1
                except Exception:
                    skipped_points += 1
                    continue
            
            report_output += f"Layer: {layer['name']}\n -> Success: {success_points} | Skipped: {skipped_points}\n"

        out_filename = self.out_name.text.strip() or "Master_Workspace_Output"
        if not out_filename.endswith(".kmz"): out_filename += ".kmz"
        
        save_path = os.path.join("/storage/emulated/0/Download", out_filename)
        self.kml.savekmz(save_path)
        
        report_output += f"------------------------------\nS
