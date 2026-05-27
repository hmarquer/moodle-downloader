# Moodle PDF Downloader (UAM)

Script en Python para descargar automaticamente los PDFs de tus cursos en Moodle UAM. Abre un navegador para iniciar sesion con SSO, guarda la sesion en un archivo local y luego recorre cada curso para descargar los PDFs en carpetas separadas por asignatura dentro de `~/Descargas/moodle/`.

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

2) En el primer uso, se abrira el navegador para iniciar sesion en https://moodle.uam.es/.

3) Cuando termines el login, vuelve a la terminal y pulsa Enter. El script guardara la sesion en `storage_state.json` y empezara la descarga.

## Salida

- Los PDFs se guardan en `~/Descargas/moodle/`.
- Cada asignatura se guarda en una subcarpeta con el nombre del curso.
- Si un PDF ya existe, no se descarga de nuevo.

## Notas

- Si cambias de cuenta o la sesion expira, borra `storage_state.json` y vuelve a ejecutar el script para hacer login de nuevo.
- El script solo descarga PDFs. Si quieres extenderlo a otros tipos de archivos o contenido, dimelo.
