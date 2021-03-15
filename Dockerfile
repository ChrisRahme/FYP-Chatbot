# Extend the official Rasa SDK image
# https://hub.docker.com/r/rasa/rasa-sdk/tags
# https://hub.docker.com/r/rasa/rasa/tags
#FROM rasa/rasa-sdk:latest
#FROM rasa/rasa:latest-full
FROM rasa/rasa-sdk:2.3.1

# Use subdirectory as working directory
WORKDIR /app

# Copy any additional custom requirements, if necessary
COPY actions/requirements-actions.txt ./
COPY _helpers/requirements-helpers.txt ./

# Change back to root user to install dependencies
USER root

# Install extra requirements for actions code, if necessary
RUN pip install -r requirements-actions.txt
RUN pip install -r requirements-helpers.txt

# Copy actions folder to working directory
# When using COPY with more than one source file, the destination must be a directory and end with a /
COPY ./actions /app/actions
COPY data/lookups/* data/lookups/

# Download spacy language data - Only if we use rasa-full and a model other than en_core_web_md
#RUN python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.0.0/en_core_web_md-3.0.0.tar.gz
#RUN python -m spacy download en_core_web_lg

# By best practices, don't run the code with root user
USER 1001