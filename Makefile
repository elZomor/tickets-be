format:
	docker exec -it admin black .
lint:
	docker exec -it admin flake8
lint-html:
	docker exec -it admin flake8 --format=html --htmldir=flake8-report
make-migrations:
	docker exec -it admin python manage.py makemigrations
migrate:
	docker exec -it admin python manage.py migrate