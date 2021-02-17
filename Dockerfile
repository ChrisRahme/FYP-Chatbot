# Extend the official Rasa SDK image
#ARG RASA_SDK_VERSION
#FROM rasa/rasa-sdk:{RASA_SDK_VERSION}
FROM rasa/rasa-sdk:2.2.0

# Use subdirectory as working directory
WORKDIR /app

# Copy any additional custom requirements, if necessary (uncomment next line)
COPY actions/requirements-actions.txt ./

# Change back to root user to install dependencies
USER root

# Install extra requirements for actions code, if necessary (uncomment next line)
RUN pip install -r requirements-actions.txt

# Copy actions folder to working directory
COPY ./actions /app/actions
COPY data/lookups/* data/lookups
#COPY data/pokemon_name.txt data/

# Download spacy language data
RUN python -m spacy download en_core_web_md

# By best practices, don't run the code with root user
USER 1001