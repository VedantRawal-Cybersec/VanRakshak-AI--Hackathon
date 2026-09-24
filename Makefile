.PHONY: run test
run:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

test:
	PYTHONPATH=backend pytest -q backend/tests
