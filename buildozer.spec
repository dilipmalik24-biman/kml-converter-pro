[app]
title = kml converter pro
package.name = kmlconverterpro
package.domain = com.bimanmalik
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pandas,simplekml,openpyxl,jnius
orientation = portrait
fullscreen = 1
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 0
