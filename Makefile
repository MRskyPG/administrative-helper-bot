include ./app/.env
.PHONY: migrate
migrate:
	 docker build -t db-avrunev-image .
build:
	 docker run --name db-avrunev -p 5439:5432 -d -e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) -e POSTGRES_DB=$(POSTGRES_DATABASE) -e POSTGRES_USER=$(POSTGRES_USER) db-avrunev-image
run:
	 python bot.py
stop_db:
	 docker stop db-avrunev
run_db:
	 docker start db-avrunev
del_image:
	 docker rmi db-avrunev-image
del_cont:
	 docker rm db-avrunev

