# Using the base image specified in devcontainer.json
# This Dockerfile can be expanded if more specific OS-level setup is needed
# beyond what the devcontainer features provide.

# For now, it can remain minimal or even empty if the image and features in
# devcontainer.json are sufficient.

# Example: Add custom OS packages if needed
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive && apt-get -y install --no-install-recommends <your-package>

# Ensure the vscode user has a home directory (usually handled by base image)
# USER vscode 

ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT} 