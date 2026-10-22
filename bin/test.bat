@echo off
docker-compose run --rm web pytest %*
