#!/bin/bash

# Script om naar GitHub te pushen
# Gebruik: ./push_to_github.sh

echo "============================================================"
echo "GITHUB PUSH SCRIPT"
echo "============================================================"
echo ""

# Check of repository bestaat
echo "🔍 Controleren of repository bestaat..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://github.com/CarlosDinel/Recruitment-agent 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Repository bestaat!"
    echo ""
    echo "🚀 Pushen naar GitHub..."
    git push -u origin main
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Succesvol gepusht naar GitHub!"
        echo "🔗 Repository: https://github.com/CarlosDinel/Recruitment-agent"
    else
        echo ""
        echo "❌ Push gefaald. Controleer:"
        echo "   1. Is je token correct?"
        echo "   2. Heb je toegang tot de repository?"
        echo "   3. Is de remote URL correct?"
    fi
else
    echo "❌ Repository bestaat nog niet op GitHub!"
    echo ""
    echo "📋 STAPPEN:"
    echo "   1. Maak repository aan: https://github.com/new"
    echo "      - Naam: Recruitment-agent"
    echo "      - Eigenaar: CarlosDinel"
    echo "      - NIET initialiseren met README"
    echo ""
    echo "   2. Revoke oude token en maak nieuw:"
    echo "      https://github.com/settings/tokens"
    echo ""
    echo "   3. Run dit script opnieuw: ./push_to_github.sh"
    echo ""
fi

echo ""
echo "============================================================"

