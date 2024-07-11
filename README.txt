DJango based app for viewing movie collection in a variety of ways...

PORTED TO KUBERNETES

See https://blog.michali.net/2024/07/10/django-app-on-kubernetes/ for instructions on how to
port app to Kubernetes.

When completed you can access locally using IP of the viewmaster service and port 8000, or
remotely with your provided domain name.

<<<<<<< HEAD
SQLite3 database at DBase/movies.db.

To build and run:

docker-compose -f viewmaster.yaml up --build -d

Access from any browser with:

http://<HOST_IP>:8642/viewmaster/


