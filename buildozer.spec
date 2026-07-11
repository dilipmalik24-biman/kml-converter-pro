[app]
title = KML Converter Pro
package.name = kmlconverterpro
package.domain = com.bimanmalik
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
android.numeric_version = 1

# Kivy aur KivyMD ke stable versions bina strictly system check ke block hone ke liye
requirements = python3,kivy==2.2.1,kivymd==1.2.0,simplekml,openpyxl,jnius,pillow

orientation = portrait
fullscreen = 1

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
