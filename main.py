# --- Python 3.13 Compatibility Fix ---
import os
import sys
import types
import math
import re

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
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import pandas as pd
import simplekml

def utm_to_latlon(easting, northing, zone):
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
    
    phi1 = (mu 
            + (3.0 * e1 / 2.0 - 27.0 * e1**3 / 32.0) * math.sin(2.0 * mu)
            + (21.0 * e1**2 / 16.0 - 55.0 * e1**4 / 32.0) * math.sin(4.0 * mu)
            + (151.0 * e1**3 / 96.0) * math.sin(6.0 * mu))
    
    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)
    
    N1 = a / math.sqrt(1.0 - e2 * sin_phi1**2)
    R1 = a * (1.0 - e2) / math.pow(1.0 - e2 * sin_phi1**2, 1.5)
    D = x / (N1 * k0)
    
    lat = phi1 - (N1 * tan_phi1 / R1) * (
        D**2 / 2.0 
        - (5.0 + 3.0 * tan_phi1**2 + 10.0 * (ep2 * cos_phi1**2) - 4.0 * (ep2 * cos_phi1**2)**2 - 9.0 * ep2) * D**4 / 24.0
        + (61.0 + 90.0 * tan_phi1**2 + 298.0 * (ep2 * cos_phi1**2) + 45.0 * tan_phi1**4 - 252.0 * ep2 - 3.0 * (ep2 * cos_phi1**2)**2) * D**6 / 720.0
    )
    
    lon = lon0 + (
        D 
        - (1.0 + 2.0 * tan_phi1**2 + (ep2 * cos_phi1**2)) * D**3 / 6.0
        + (5.0 - 2.0 * (ep2 * cos_phi1**2) + 28.0 * tan_phi1**2 - 3.0 * (ep2 * cos_phi1**2)**2 + 8.0 * ep2 + 24.0 * tan_phi1**4) * D**5 / 120.0
    ) / cos_phi1
    
    return math.degrees(lat), math.degrees(lon)

class GISMasterApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager, select_path=self.select_path
        )
        self.selected_file = None
        self.mode = "WGS84"
        self.sel_x = self.sel_y = self.sel_label = None
        self.icon_url = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
        self.i_color, self.l_color = "ff0000ff", "ffffffff"
        self.menus = {}

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        screen = MDScreen()
        scroll = ScrollView()
        layout = MDBoxLayout(
            orientation="vertical", padding=15, spacing=10, size_hint_y=None
        )
        layout.bind(minimum_height=layout.setter("height"))

        header = MDCard(
            size_hint=(1, None),
            height="75dp",
            radius=[15,],
            md_bg_color=(0, 0.4, 0.4, 1),
            padding=10,
        )
        header.add_widget(
            MDLabel(
                text="KML/KMZ SMART CONVERTER\nDeveloped by Biman Malik",
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                font_style="H6",
            )
        )
        layout.add_widget(header)

        self.btn_file = MDRaisedButton(
            text="1. LOAD DATA FILE", size_hint=(1, None), on_release=self.open_file_manager
        )
        self.btn_mode = MDRaisedButton(
            text="2. INPUT SYSTEM", size_hint=(1, None), md_bg_color=(0.1, 0.4, 0.6, 1)
        )
        self.btn_x = MDRaisedButton(text="SELECT X COLUMN", size_hint=(1, None), disabled=True)
        self.btn_y = MDRaisedButton(text="SELECT Y COLUMN", size_hint=(1, None), disabled=True)
        self.btn_label = MDRaisedButton(text="SELECT POINT LABEL", size_hint=(1, None), disabled=True)
        self.btn_icon = MDRaisedButton(text="ICON SHAPE", size_hint=(1, None), md_bg_color=(0.4, 0.2, 0.6, 1))
        self.btn_i_col = MDRaisedButton(text="ICON COLOR", size_hint=(1, None), md_bg_color=(1, 0, 0, 1))
        self.btn_l_col = MDRaisedButton(
            text="LABEL COLOR", size_hint=(1, None), md_bg_color=(1, 1, 1, 1), text_color=(0, 0, 0, 1)
        )

        self.i_scale = MDTextField(hint_text="Icon Size (1.0)", text="1.0", size_hint=(1, None))
        self.l_scale = MDTextField(hint_text="Label Size (0.9)", text="0.9", size_hint=(1, None))
        self.out_name = MDTextField(hint_text="Output Filename", size_hint=(1, None))

        for w in [
            self.btn_file, self.btn_mode, self.btn_x, self.btn_y,
            self.btn_label, self.btn_icon, self.btn_i_col, self.btn_l_col,
            self.i_scale, self.l_scale, self.out_name,
        ]:
            layout.add_widget(w)

        self.btn_gen = MDRaisedButton(
            text="GENERATE PROFESSIONAL KMZ", md_bg_color=(0, 0.7, 0.3, 1), size_hint=(1, None), on_release=self.start_conversion
        )
        layout.add_widget(self.btn_gen)

        self.status = MDLabel(
            text="Status: Ready", halign="center", theme_text_color="Secondary", size_hint_y=None, height=100
        )
        layout.add_widget(self.status)

        self.setup_menus()
        scroll.add_widget(layout)
        screen.add_widget(scroll)
        return screen

    def setup_menus(self):
        m_list = [("WGS84 (Lat/Long)", "WGS84"), ("UTM 42N", 42), ("UTM 43N", 43)]
        self.menus["mode"] = MDDropdownMenu(
            caller=self.btn_mode,
            items=[{"text": x[0], "on_release": lambda v=x: self.set_mode(v)} for x in m_list],
            width_mult=4,
        )
        self.btn_mode.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["mode"].open(), 0.05))

        s_list = [
            ("Circle", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"),
            ("Square", "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png"),
            ("Star", "http://maps.google.com/mapfiles/kml/shapes/star.png"),
            ("Triangle", "http://maps.google.com/mapfiles/kml/shapes/triangle.png"),
            ("Diamond", "http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png"),
            ("Pushpin", "http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png"),
            ("Target", "http://maps.google.com/mapfiles/kml/shapes/target.png"),
            ("Arrow", "http://maps.google.com/mapfiles/kml/shapes/arrow.png"),
            ("Crosshairs", "http://maps.google.com/mapfiles/kml/shapes/crosshairs.png"),
            ("Marker", "http://maps.google.com/mapfiles/kml/paddle/red-circle.png"),
        ]
        self.menus["icon"] = MDDropdownMenu(
            caller=self.btn_icon,
            items=[{"text": x[0], "on_release": lambda v=x: self.set_icon(v)} for x in s_list],
            width_mult=4,
        )
        self.btn_icon.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["icon"].open(), 0.05))

        c_list = [
            ("Red", "ff0000ff", (1, 0, 0, 1)), ("Green", "ff00ff00", (0, 1, 0, 1)),
            ("Blue", "ffff0000", (0, 0, 1, 1)), ("Yellow", "ff00ffff", (1, 1, 0, 1)),
            ("White", "ffffffff", (1, 1, 1, 1)), ("Cyan", "ffff00ff", (0, 1, 1, 1)),
            ("Orange", "ff00a5ff", (1, 0.6, 0, 1)), ("Purple", "ff800080", (0.5, 0, 0.5, 1)),
        ]
        self.menus["i_col"] = MDDropdownMenu(
            caller=self.btn_i_col, items=[{"text": x[0], "on_release": lambda v=x: self.set_color("i", v)} for x in c_list], width_mult=4
        )
        self.menus["l_col"] = MDDropdownMenu(
            caller=self.btn_l_col, items=[{"text": x[0], "on_release": lambda v=x: self.set_color("l", v)} for x in c_list], width_mult=4
        )
        self.btn_i_col.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["i_col"].open(), 0.05))
        self.btn_l_col.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["l_col"].open(), 0.05))

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
            self.btn_i_col.md_bg_color = c[2]
            self.menus["i_col"].dismiss()
        else:
            self.l_color = c[1]
            self.btn_l_col.md_bg_color = c[2]
            self.menus["l_col"].dismiss()

    def select_path(self, path):
        self.selected_file = path
        df = pd.read_excel(path) if path.endswith(".xlsx") else pd.read_csv(path)
        col_list = [str(col) for col in df.columns]

        if "x" in self.menus: self.menus["x"].dismiss()
        if "y" in self.menus: self.menus["y"].dismiss()
        if "label" in self.menus: self.menus["label"].dismiss()

        self.menus["x"] = MDDropdownMenu(
            caller=self.btn_x, items=[{"text": c, "on_release": lambda x=c: self.set_val("x", x)} for c in col_list], width_mult=4
        )
        self.menus["y"] = MDDropdownMenu(
            caller=self.btn_y, items=[{"text": c, "on_release": lambda x=c: self.set_val("y", x)} for c in col_list], width_mult=4
        )
        self.menus["label"] = MDDropdownMenu(
            caller=self.btn_label, items=[{"text": c, "on_release": lambda x=c: self.set_val("l", x)} for c in col_list], width_mult=4
        )

        self.btn_x.disabled = self.btn_y.disabled = self.btn_label.disabled = False
        self.btn_x.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["x"].open(), 0.05))
        self.btn_y.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["y"].open(), 0.05))
        self.btn_label.bind(on_release=lambda x: Clock.schedule_once(lambda dt: self.menus["label"].open(), 0.05))

        self.btn_file.text = "DATA LOADED ✅"
        self.exit_manager()

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

    def start_conversion(self, *args):
        if not self.selected_file: return
        self.df = pd.read_excel(self.selected_file) if self.selected_file.endswith(".xlsx") else pd.read_csv(self.selected_file)
        self.kml, self.total, self.curr = simplekml.Kml(), len(self.df), 0
        self.generated_count = 0
        self.missing_count = 0
        self.btn_gen.disabled = True
        Clock.schedule_interval(self.update_kml, 0.01)

    def update_kml(self, dt):
        chunk_size = 500
        for _ in range(chunk_size):
            if self.curr >= self.total: break
            row = self.df.iloc[self.curr]
            try:
                val_x = row[self.sel_x]
                val_y = row[self.sel_y]

                if (pd.isna(val_x) or pd.isna(val_y) or str(val_x).strip() == "" or 
                    str(val_y).strip() == "" or str(val_x).strip().lower() == "nan" or 
                    str(val_y).strip().lower() == "nan"):
                    self.missing_count += 1
                    self.curr += 1
                    continue

                vx, vy = float(val_x), float(val_y)
                if self.mode == "WGS84":
                    lon, lat = vx, vy
                else:
                    lat, lon = utm_to_latlon(vx, vy, self.mode)

                pnt = self.kml.newpoint(name=str(row[self.sel_label]), coords=[(lon, lat)])
                desc = (
                    '<div style="font-family:Segoe UI,Arial,sans-serif; width:320px; background:#fdfdfd; '
                    'padding:0; border-radius:8px; overflow:hidden; border:1px solid #ccc; box-shadow:0 4px 10px rgba(0,0,0,0.15);">'
                )
                desc += (
                    f'<div style="background:#005A5B; color:#ffffff; padding:10px 14px; font-size:14px; '
                    f'font-weight:bold; letter-spacing:0.5px; text-transform:uppercase; border-bottom:2px solid #004041;">'
                    f'Asset ID: {row[self.sel_label]}</div>'
                )
                desc += '<table style="width:100%; border-collapse:collapse; font-size:12px; background:#ffffff;">'

                img_section = ""
                row_idx = 0

                for col in self.df.columns:
                    val = str(row[col]).strip()
                    if pd.isna(row[col]) or val.lower() == "nan" or val == "": continue
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
                pnt.style.iconstyle.icon.href, pnt.style.iconstyle.color = self.icon_url, self.i_color
                pnt.style.iconstyle.scale = float(self.i_scale.text)
                pnt.style.labelstyle.scale, pnt.style.labelstyle.color = float(self.l_scale.text), self.l_color
                self.generated_count += 1
            except Exception:
                self.missing_count += 1
            self.curr += 1

        if self.curr < self.total:
            pct = int((self.curr / self.total) * 100)
            self.status.text = f"Processing: {pct}%\n✅ Generated: {self.generated_count}\n❌ Missing: {self.missing_count}"
            return True
        else:
            out_filename = self.out_name.text or "Smart_Survey_Output"
            if not out_filename.endswith(".kmz"): out_filename += ".kmz"

            self.status.text = "Saving KMZ file..."
            
            # Cross-platform secure path handler for Android vs Desktop
            if platform == 'android':
                from android.storage import primary_external_storage_path
                primary_ext_storage = primary_external_storage_path()
                save_path = os.path.join(primary_ext_storage, "Download", out_filename)
            else:
                save_path = out_filename

            self.kml.savekmz(save_path)
            self.status.text = (
                f"SAMPANN! ✅ File Download Folder Me Hai.\n\n"
                f"📊 --- FINAL REPORT ---\n"
                f"📁 Total Rows Checked: {self.total}\n"
                f"🟢 Successfully Generated: {self.generated_count}\n"
                f"🔴 Skipped: {self.missing_count}"
            )
            self.btn_gen.disabled = False
            return False

    def exit_manager(self, *args):
        self.file_manager.close()

    def open_file_manager(self, *args):
        if platform == 'android':
            from android.storage import primary_external_storage_path
            path = primary_external_storage_path()
        else:
            path = os.path.expanduser("~")
        self.file_manager.show(path)

if __name__ == "__main__":
    GISMasterApp().run()
