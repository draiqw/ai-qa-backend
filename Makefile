include tests/.env
export

IMAGE_NAME = my-postgres-test
CONTAINER_NAME = postgres_test_container
BROWSER ?= python -m http.server -d

.PHONY: help
help:
	@echo "lint: запустить flake8"
	@echo "docs: собрать документацию (Sphinx)"
	@echo "db-build: собрать Docker-образ PostgreSQL"
	@echo "db-run: запустить контейнер PostgreSQL"
	@echo "db-fill: заполнить БД начальными данными"
	@echo "db-clean: очистить БД (удалить данные)"
	@echo "db-delete: удалить контейнер PostgreSQL"
	@echo "compose-up: запустить docker-compose (бекенд + база данных)"
	@echo "compose-down: остановить docker-compose (убрать все контейнеры)"

.PHONY: lint
lint:
	flake8 .

.PHONY: docs
docs:
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/build/html

.PHONY: db-build
db-build:
	docker build \
		--build-arg DB_NAME=$${DB_NAME} \
		--build-arg DB_USER=$${DB_USER} \
		--build-arg DB_PASSWORD=$${DB_PASSWORD} \
		-t $(IMAGE_NAME) tests/

.PHONY: db-run
db-run:
	docker run -d \
		-p 5432:5432 \
		--env POSTGRES_PASSWORD=$${DB_PASSWORD} \
		--env POSTGRES_USER=$${DB_USER} \
		--env POSTGRES_DB=$${DB_NAME} \
		--env-file tests/.env \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)

.PHONY: db-fill
db-fill:
	python3 fill_db.py update_migrations
	python3 fill_db.py fill_db
	python3 fill_db.py create_admin

.PHONY: db-clean
db-clean:
	python3 fill_db.py clean

.PHONY: db-delete
db-delete:
	docker rm -f $(CONTAINER_NAME) || true

.PHONY: compose-up
compose-up:
	docker-compose -f docker-compose.backend-db.yml up --build

.PHONY: compose-down
compose-down:
	docker-compose down
