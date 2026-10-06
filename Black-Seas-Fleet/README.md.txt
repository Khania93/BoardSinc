# FILE: README.md

Generador de Flotas Black Seas
==============================

Aplicación de escritorio en Python/Tkinter para crear y gestionar flotas
del juego Black Seas. Lee datos desde `data/Black_Seas.xlsx` si existe,
pero funciona con datos demo si no hay Excel o faltan dependencias.

Requisitos opcionales:
- Python 3.10+
- pip install -r requirements.txt (opcional para Excel y mejor manejo de imágenes)

Ejecución:
- `python main.py` (modo normal)
- `python main.py --demo` (forzar datos demo)

Estructura:
- `core/` : lógica, carga de datos, cálculos
- `ui/` : ventanas y widgets
- `assets/barcos/velero.png` : imagen demo del barco
- `data/Black_Seas.xlsx` : (opcional) base de datos
- `saves/` : partidas guardadas (JSON)

Notas:
- Si no tienes `pandas` o `openpyxl`, el programa usa datos demo.
- Si no tienes `Pillow`, Tkinter usará `PhotoImage` para PNG/GIF; si falla, se muestra placeholder.
