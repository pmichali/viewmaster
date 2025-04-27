FROM python:3.13.1

# Python and setup timezone
RUN apt-get update -y && apt-get install -y software-properties-common python3-pip postgresql-client

# Fault handler dumps traceback on seg faults
# Unbuffered sends stdout/stderr to log vs buffering
ENV CODEBASE=/code \
  PYTHONENV=/code \
  PYTHONPATH=/code \
  EDITOR=vim \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=2.1.2

# System dependencies
RUN pip3 install "poetry==$POETRY_VERSION"

# Copy over all needed files
WORKDIR /code
COPY README.txt poetry.lock pyproject.toml runserver.bash /code/
COPY movie_library/ /code/movie_library/

# setup tools for environment, using pyproject.toml file
RUN poetry config virtualenvs.create false && \
    poetry install

EXPOSE 80

# CMD sleep infinity
CMD ["/code/runserver.bash"]
