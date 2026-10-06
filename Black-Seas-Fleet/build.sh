:: build.bat (Windows)
pyinstaller --onefile ^
  --add-data "assets;assets" ^
  --add-data "data\\Black_Seas.xlsx;." ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  main.py
