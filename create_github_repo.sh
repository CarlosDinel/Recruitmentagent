#!/bin/bash

# Script om GitHub repository aan te maken en code te pushen
# Gebruik: ./create_github_repo.sh

REPO_NAME="Recruitment-agent"
USERNAME="CarlosDinel"

echo "============================================================"
echo "GITHUB REPOSITORY AANMAKEN"
echo "============================================================"
echo ""

# Check of GitHub CLI geïnstalleerd is
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI gevonden!"
    echo ""
    echo "🔐 Eerst inloggen op GitHub (als nog niet gedaan):"
    echo "   gh auth login"
    echo ""
    read -p "Wil je doorgaan met GitHub CLI? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Repository aanmaken met GitHub CLI..."
        gh repo create $REPO_NAME --public --source=. --remote=origin --push
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Repository succesvol aangemaakt en code gepusht!"
            echo "🔗 https://github.com/$USERNAME/$REPO_NAME"
            exit 0
        else
            echo ""
            echo "❌ Fout bij aanmaken repository"
        fi
    fi
fi

echo ""
echo "📋 MANUELE STAPPEN:"
echo ""
echo "1. Open in browser: https://github.com/new"
echo ""
echo "2. Vul in:"
echo "   Repository name: $REPO_NAME"
echo "   Owner: $USERNAME"
echo "   Public / Private: (kies wat je wilt)"
echo ""
echo "3. BELANGRIJK - Vink NIETS aan:"
echo "   ❌ Add a README file"
echo "   ❌ Add .gitignore"
echo "   ❌ Choose a license"
echo ""
echo "4. Klik 'Create repository'"
echo ""
echo "5. Na aanmaken, voer uit:"
echo "   git push -u origin main"
echo ""
echo "============================================================"

