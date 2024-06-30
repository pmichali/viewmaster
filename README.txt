DJango based app for viewing movie collection in a variety of ways..

Have Dockerfile with python based configuration that will install everything under user 'pcm'.

Have viewmaster.yaml with configuration. Uses port 8642.

load.py was used to import Excel spreadsheet (old copy in movies.xmls) into the database.

SQLite3 database at DBase/movies.db. Not in this repo, so would need to create directory to hold database.


To build the docker image and run (assuming you already have a working database at DBase/movies.db):

docker-compose -f viewmaster.yaml up --build -d

Access from a browser with:

http://<HOST_IP>:8642/viewmaster/

