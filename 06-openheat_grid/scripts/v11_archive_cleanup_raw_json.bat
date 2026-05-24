@echo off
setlocal
set CONFIG=configs\v11\v11_longterm_archive_config.example.json
python scripts\v11_archive_cleanup_raw_json.py --config %CONFIG%
