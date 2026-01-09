install:
	poetry install

run:
	poetry run project

build:
	poetry build

publish:
	poetry publish --dry-run

package-install:
	python -m pip install dist/*.whl

lint:
	poetry run ruff check .

fix:
	poetry run ruff check --fix .

format:
	poetry run ruff format .

clean:
	rmdir /s /q .venv 2>nul || echo .venv not found
	rmdir /s /q dist 2>nul || echo dist not found
	rmdir /s /q *.egg-info 2>nul || echo *.egg-info not found

.PHONY: install run build publish package-install lint format clean