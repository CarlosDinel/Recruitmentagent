# Git Account Instellen

## Huidige Configuratie

Je hebt al een lokale Git configuratie ingesteld:
- **Naam**: CarlosDinel
- **Email**: carlos_almeida@hotmail.nl
- **Remote**: https://github.com/CarlosDinel/Recruitment-agent.git

## Git Account Aanpassen

### 1. Lokale Configuratie (alleen deze repository)

```bash
# Naam instellen
git config --local user.name "Jouw Nieuwe Naam"

# Email instellen
git config --local user.email "jouw.nieuwe.email@voorbeeld.com"
```

### 2. Globale Configuratie (voor alle repositories)

```bash
# Naam instellen
git config --global user.name "Jouw Naam"

# Email instellen
git config --global user.email "jouw.email@voorbeeld.com"
```

### 3. Configuratie Verifiëren

```bash
# Huidige naam bekijken
git config user.name

# Huidige email bekijken
git config user.email

# Alle configuratie bekijken
git config --list
```

## Remote Repository Instellen

### Huidige Remote

Je remote is al geconfigureerd:
```
origin: https://github.com/CarlosDinel/Recruitment-agent.git
```

### Remote Aanpassen

```bash
# Bestaande remote verwijderen
git remote remove origin

# Nieuwe remote toevoegen (HTTPS)
git remote add origin https://github.com/username/repository.git

# OF met SSH (aanbevolen voor push/pull)
git remote add origin git@github.com:username/repository.git
```

### Remote Verifiëren

```bash
# Remote repositories bekijken
git remote -v
```

## SSH Key Instellen (Aanbevolen)

SSH keys maken het werken met GitHub/GitLab makkelijker (geen wachtwoord nodig).

### 1. SSH Key Genereren

```bash
# Genereer een nieuwe SSH key
ssh-keygen -t ed25519 -C "carlos_almeida@hotmail.nl"

# Volg de instructies (druk Enter voor standaard locatie)
# Optioneel: voeg een passphrase toe voor extra beveiliging
```

### 2. SSH Agent Starten

```bash
# Start ssh-agent
eval "$(ssh-agent -s)"

# Voeg je SSH key toe
ssh-add ~/.ssh/id_ed25519
```

### 3. Publieke Key Kopiëren

```bash
# Toon je publieke key
cat ~/.ssh/id_ed25519.pub

# Kopieer de output (begint met ssh-ed25519)
```

### 4. Key Toevoegen aan GitHub

1. Ga naar GitHub.com → Settings → SSH and GPG keys
2. Klik op "New SSH key"
3. Plak je publieke key
4. Klik op "Add SSH key"

### 5. Remote naar SSH Veranderen

```bash
# Verander remote URL naar SSH
git remote set-url origin git@github.com:CarlosDinel/Recruitment-agent.git

# Verifieer
git remote -v
```

## Eerste Commit & Push

```bash
# Status bekijken
git status

# Bestanden toevoegen
git add .

# Commit maken
git commit -m "Initial commit: Clean Architecture migration complete"

# Push naar remote
git push -u origin main
# OF als je branch 'master' heet:
git push -u origin master
```

## Handige Git Commands

```bash
# Status bekijken
git status

# Wijzigingen bekijken
git diff

# Commit geschiedenis
git log --oneline

# Branch maken
git checkout -b nieuwe-feature

# Branch wisselen
git checkout main

# Wijzigingen pullen
git pull origin main

# Wijzigingen pushen
git push origin main
```

## Troubleshooting

### Authentication Problemen

Als je problemen hebt met authenticatie:

1. **HTTPS**: Gebruik Personal Access Token in plaats van wachtwoord
   - GitHub → Settings → Developer settings → Personal access tokens
   - Genereer nieuwe token met `repo` rechten
   - Gebruik token als wachtwoord bij push/pull

2. **SSH**: Test je SSH verbinding
   ```bash
   ssh -T git@github.com
   ```
   Je zou moeten zien: "Hi CarlosDinel! You've successfully authenticated..."

### Configuratie Resetten

```bash
# Lokale configuratie verwijderen
git config --local --unset user.name
git config --local --unset user.email

# Globale configuratie verwijderen
git config --global --unset user.name
git config --global --unset user.email
```

