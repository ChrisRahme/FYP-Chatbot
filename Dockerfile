# Extend the official Rasa SDK image
#ARG RASA_SDK_VERSION
#FROM rasa/rasa-sdk:{RASA_SDK_VERSION}
FROM rasa/rasa-sdk:2.3.0
#FROM rasa/rasa:2.2.3-full

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

# Download spacy language data - We don't need that for the action server(?) - Yes we do(?) - No we don't unless we use rasa-full
#RUN python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.0.0/en_core_web_md-3.0.0.tar.gz
#RUN python -m spacy download en_core_web_lg

# By best practices, don't run the code with root user
USER 1001