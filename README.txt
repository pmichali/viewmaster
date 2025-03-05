DJango based app for viewing movie collection in a variety of ways...

PORTED TO KUBERNETES
====================

See https://blog.michali.net/2024/07/10/django-app-on-kubernetes/ for instructions on how to
port app to Kubernetes.

When completed you can access locally using IP of the viewmaster service and port 8000, or
remotely with your provided domain name.


UPDATE TO INSTRUCTIONS FOR VIEWMASTER 0.2.x
===========================================

The deploy/viewmaster-secrets.env file in Git has dummy values that you must modify for your
use. To make things easier (and not risking committing the updated file with live data), I
renamed the file to viewmaster-secrets.env.template in the Git repo. You can then copy the file
to viewmaster-secrets.env and modify it for use with the app, and not not worry about committing
any private info to Git.


USING OMDB FOR MOVIE INFO
=========================

There is a open-source movie library at http://www.omdbapi.com/ which can be used to provide the
title, plot, actor(s), director(s), poster, release date, rating, duration, among other data for
each movie.

Viewmaster has been enhanced in version 0.2.1 to allow you to lookup a movie my title, and then
have www.omdbapi.com fill out plot, actor(s), director(s), and poster, and to update release date,
rating, and duration. It will also display the possible genres from the database, so you can select
from one of them, when adding a movie, or alter the existing setting, when editing a movie.

When editing a movie, it the OMDB library updates the rating, release date, or duration, the values
will be displayed in red on the edit form, so that you know what was changed. It is comment for the
database to have a slightly different duration, that what may have been manually entered from the
back of the box for the movie.

If the movie cannot be found in the database, you can skip this step when adding or updating a movie.
Sometimes, when editing a movie, the title is not found. You can use the "add movie" command to
search using a part of the time, in an attempt to find out the correct name, and then can edit the
movie title so that a subsequent edit can find the movie in the database.

This new feature requires that you obtain an API key from http://www.omdbapi.com/ by going to the
web site, clicking on the API KEY tab, and then entering the email address you want to use. You are
limited to 1,000 requests per day, unless you become a patron (paid) member.

The key will be emailed to you and you must enter it into the secrets file (for production use)
and bash script (for local use of app and import tool):

deploy/viewmaster-secrets.env
movie_library/dev-setup.bash

The latter is a created file, as described in the next section.


LOCAL DEVELOPMENT
=================

To access the database from local Mac, do the following under Kubernetes:

kubectl expose service viewmaster-postgres -n viewmaster --port=5432 --target-port=5432 --name=viewmaster-postgres-dev --type=LoadBalancer
service/viewmaster-postgres-dev exposed

Then, note the IP address of the viewmaster-postgres-dev service.

Create a dev-setuo.bash in viewmaster/movie_library/ with values from deploy/viewmaster-secrets.env, but
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
export OMDB_API_KEY=KEY-REGISTERED

Note: some of the items in viewmaster-secrets.env may have single quotes (like passwords, and you'll need to
include those inside the double quotes. For example, if you had a password='abcd', you would have an export
line with "'abcd'".

After sourcing the dev-setup.bash file, you can run "python3 manage.py CMD" from the viewmaster/movie_library
area. First, do a 'collectstatic', and then 'runserver' command and access the service at 127.0.0.1:8000/


IMPORTING IMDB INFO
===================

In addition to sourcing the dev-setup.bash file, you can set the python path with:

export PYTHONPATH=/Users/pcm/workspace/kubernetes/viewmaster/movie_library

From viewmaster/movie_library, you can run:

python3 viewmaster/imdb_import.py

Follow the prompts to process each movie that does not have IMDB information. You can select one of the
entries from the list of candidates, and then save that information. If the selection does not seem to
match, rather than confirming, you can go back and select another candidate, skip the movie or quit.

Each time you run the script, it will process the remaining files.
