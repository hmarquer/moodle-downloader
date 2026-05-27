# Moodle PDF Downloader (UAM)

Script en Python para descargar automaticamente los PDFs de tus cursos en Moodle UAM. Abre un navegador para iniciar sesion con SSO, guarda la sesion en un archivo local y luego recorre cada curso para descargar los PDFs en carpetas separadas por asignatura.

## Requisitos

- Python 3.10+ (recomendado)
- Navegador compatible con Playwright

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install
```

## Uso

1) Ejecuta el script:

```bash
python moodle_pdfs.py
```

2) El script pedira `BASE_URL` y `DOWNLOAD_ROOT`. Pulsa Enter para aceptar los valores por defecto.

3) En el primer uso, se abrira el navegador para iniciar sesion en https://moodle.uam.es/.

4) Cuando termines el login, vuelve a la terminal y pulsa Enter. El script guardara la sesion en `storage_state.json`.

5) El script listara las asignaturas y podras seleccionar las que quieres descargar (por ejemplo: `1,3,5`). Si pulsas Enter, descargara todas.

## Salida

- Los PDFs se guardan en `DOWNLOAD_ROOT`.
- Cada asignatura se guarda en una subcarpeta con el nombre del curso.
- Si un PDF ya existe, no se descarga de nuevo.

## Valores por defecto

- `BASE_URL`: https://moodle.uam.es
- `DOWNLOAD_ROOT`:
	- Linux: `~/Descargas/moodle/`
	- macOS: `~/Downloads/moodle/`
	- Windows: `~/Downloads/moodle/`

## Notas

- Si cambias de cuenta o la sesion expira, borra `storage_state.json` y vuelve a ejecutar el script para hacer login de nuevo.
- El script solo descarga PDFs. Si quieres extenderlo a otros tipos de archivos o contenido, dimelo.
