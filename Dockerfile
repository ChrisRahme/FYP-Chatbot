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
# When using COPY with more than one source file, the destination must be a directory and end with a /
COPY ./actions /app/actions
COPY data/lookups/* data/lookups/ 
#COPY data/pokemon_name.txt data/

# Download spacy language data - We don't need that for the action server(?) - Yes we do(?)
# RUN python -m spacy download en_core_web_md
RUN python -m spacy download en_core_web_lg

# By best practices, don't run the code with root user
USER 1001