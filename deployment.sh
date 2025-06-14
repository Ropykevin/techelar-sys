sh mypostgresql.sh
git pull origin master
docker-compose -f docker-compose.yml up -d --build 
docker logs -f techelar