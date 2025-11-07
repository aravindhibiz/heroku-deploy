web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
release: cd backend && python init_db.py && python seed_permissions.py