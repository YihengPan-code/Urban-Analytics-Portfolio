@echo off
setlocal
set CONFIG=configs\v11\v11_longterm_archive_config.example.json
python scripts\v11_archive_preflight.py --config %CONFIG%
