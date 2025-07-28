#!/bin/bash
set -e

REPO_URL="https://github.com/RDFonseca82/iWebITAgent_Linux.git"
INSTALL_DIR="/opt/iwebit-agent"

if [ -d "$INSTALL_DIR" ]; then
  echo "Atualizando o iwebit-agent..."
  cd "$INSTALL_DIR" && git pull
else
  echo "Clonando o iwebit-agent..."
  git clone "$
