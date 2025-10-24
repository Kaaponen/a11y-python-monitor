# Makefile
.PHONY: install test lint format run-ui run-cli clean docker-build docker-run

# Kehitysympäristön asennus
install:
	pip install -r requirements.txt
	playwright install

# Kehitysriippuvuuksien asennus
install-dev:
	pip install -r requirements.txt
	pip install -e .[dev]
	playwright install

# Testien ajaminen
test:
	pytest tests/ -v

# Testikattavuus
test-coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term --cov-report=xml

# Koodin linting
lint:
	flake8 src/ tests/ *.py --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ tests/ *.py --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	mypy src/ --ignore-missing-imports

# Koodin formatointi
format:
	black src/ tests/ *.py

# Koodin formatoinnin tarkistus
format-check:
	black --check --diff src/ tests/ *.py

# Turvallisuustarkistukset
security:
	bandit -r src/ -f txt
	safety check

# CI/CD pipeline (sama kuin GitHub Actions)
ci: install-dev lint format-check test-coverage security
	echo "✅ CI pipeline completed successfully!"

# Web UI:n käynnistys
run-ui:
	python app.py

# Web UI:n käynnistys (vaihtoehtoinen tapa)
run-ui-direct:
	streamlit run src/ui/streamlit_app.py

# CLI:n käyttöesimerkki
run-cli:
	python cli.py https://example.com

# Puhdistus
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf reports/

# Docker imagen rakentaminen
docker-build:
	docker build -t a11y-scanner .

# Docker kontainerin ajaminen
docker-run:
	docker run -p 8501:8501 a11y-scanner

# Kehitysympäristön setup
setup: install-dev
	cp .env.example .env
	echo "Muokkaa .env tiedostoa tarpeen mukaan"