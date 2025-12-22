#!/bin/bash

# Script om te pushen met Personal Access Token
# Gebruik: ./push_with_token.sh [TOKEN]

REPO_URL="https://github.com/CarlosDinel/Recruitmentagent.git"

echo "============================================================"
echo "PUSH MET PERSONAL ACCESS TOKEN"
echo "============================================================"
echo ""

if [ -z "$1" ]; then
    echo "❌ Geen token opgegeven!"
    echo ""
    echo "Gebruik: ./push_with_token.sh [JE_TOKEN]"
    echo ""
    echo "Of voer handmatig uit:"
    echo "  git push -u origin main"
    echo "  Username: CarlosDinel"
    echo "  Password: [plak je token]"
    exit 1
fi

TOKEN=$1

echo "🔐 Token ontvangen"
echo "🚀 Remote URL tijdelijk aanpassen..."
git remote set-url origin https://${TOKEN}@github.com/CarlosDinel/Recruitmentagent.git

echo "📤 Pushen naar GitHub..."
git push -u origin main

PUSH_RESULT=$?

echo ""
echo "🔒 Remote URL terugzetten naar normale URL..."
git remote set-url origin ${REPO_URL}

if [ $PUSH_RESULT -eq 0 ]; then
    echo ""
    echo "✅ Succesvol gepusht!"
    echo "🔗 Repository: https://github.com/CarlosDinel/Recruitmentagent"
else
    echo ""
    echo "❌ Push gefaald"
    echo ""
    echo "Mogelijke oorzaken:"
    echo "  - Token heeft geen 'repo' scope"
    echo "  - Token is verlopen"
    echo "  - Repository bestaat niet of je hebt geen toegang"
    echo ""
    echo "Check je token: https://github.com/settings/tokens"
fi

echo ""
echo "============================================================"

