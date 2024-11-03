FROM postgres:latest

COPY ./schema/data.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
