DJango based app for viewing movie collection in a variety of ways...

PORTED TO KUBERNETES

See https://blog.michali.net/2024/07/10/django-app-on-kubernetes/ for instructions on how to
port app to Kubernetes.

When completed you can access locally using IP of the viewmaster service and port 8000, or
remotely with your provided domain name.

LOCAL DEVELOPMENT
To access the database from local Mac, do the following under Kubernetes:

kubectl expose service viewmaster-postgres -n viewmaster --port=5432 --target-port=5432 --name=viewmaster-postgres-dev --type=LoadBalancer
service/viewmaster-postgres-dev exposed

Then, note the IP address of the viewmaster-postgres-dev service.

Create a det-setuo.bash in viewmaster/movie_library/ with values from deploy/viewmaster-secrets.env, but
using export clause, so file can be sourced:

export SECRET_KEY="SECRET FOR APP"
export DB_HOST=viewmaster-postgres-dev service IP
export POSTGRES_DB=DATABASE_NAME
export POSTGRES_USER=DATABASE_USER
export POSTGRES_PASSWORD="PASSWORD"
export PUBLIC_DOMAIN=movies.YOURDOMAIN.COM
export DEBUG=1
export ALLOWED_HOSTS=127.0.0.1
# export DJANGO_LOG_LEVEL="DEBUG"
export TEST_LOG_ROOT="."
export HOSTNAME=NAME_OF_YOUR_HOST

Note: some of the items in viewmaster-secrets.env may have single quotes (like passwords, and you'll need to
include those inside the double quotes. For example, if you had a password='abcd', you would have an export
line with "'abcd'".

After sourcing the dev-setup.bash file, you can run "python3 manage.py CMD" from the viewmaster/movie_library
area. First, do a 'collectstatic', and then 'runserver' command and access the service at 127.0.0.1:8000/


IMPORTING IMDB INFO
In addition to sourcing the dev-setup.bash file, you can set the python path with:

export PYTHONPATH=/Users/pcm/workspace/kubernetes/viewmaster/movie_library

From viewmaster/movie_library, you can run:

python3 viewmaster/imdb_import.py

Follow the prompts to process each movie that does not have IMDB information. You can select one of the
entries from the list of candidates, and then save that information. If the selection does not seem to
match, rather than confirming, you can go back and select another candidate, skip the movie or quit.

Each time you run the script, it will process the remaining files.
