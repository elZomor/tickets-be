format:
	docker exec -it tickets-py-admin-1 black .
lint:
	docker exec -it tickets-py-admin-1 flake8
lint-html:
	docker exec -it tickets-py-admin-1 flake8 --format=html --htmldir=flake8-report
make-migrations:
	docker exec -it tickets-py-admin-1 python manage.py makemigrations
migrate:
	docker exec -it tickets-py-admin-1 python manage.py migrate