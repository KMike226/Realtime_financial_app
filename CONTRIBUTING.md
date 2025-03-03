# Guide de Contribution

Merci de votre intérêt pour contribuer au projet de Pipeline de Données Financières !

## 🚀 Comment Contribuer

### 1. Fork et Clone
```bash
# Fork le repository sur GitHub
# Puis cloner votre fork
git clone https://github.com/votre-username/Realtime_financial_app.git
cd Realtime_financial_app
```

### 2. Créer une Branche
```bash
git checkout -b feature/nouvelle-fonctionnalite
```

### 3. Développement
- Suivre les conventions de code existantes
- Ajouter des tests pour les nouvelles fonctionnalités
- Documenter les changements importants

### 4. Tests
```bash
# Lancer les tests
make test

# Vérifier le linting
make lint
```

### 5. Commit et Push
```bash
git add .
git commit -m "feat(scope): description de la modification"
git push origin feature/nouvelle-fonctionnalite
```

### 6. Pull Request
- Créer une PR avec une description détaillée
- Lier les issues concernées
- S'assurer que tous les tests passent

## 📋 Standards de Code

### Messages de Commit
Utiliser le format Conventional Commits :
```
type(scope): description

- feat: nouvelle fonctionnalité
- fix: correction de bug
- docs: documentation
- style: formatage
- refactor: refactoring
- test: ajout de tests
- chore: maintenance
```

### Structure des Fichiers
- Respecter la structure existante des répertoires
- Ajouter des README dans les nouveaux modules
- Documenter les APIs publiques

## 🐛 Signaler des Bugs

Utiliser le template d'issue pour signaler les bugs :
- Description du problème
- Étapes de reproduction
- Comportement attendu vs observé
- Environnement (OS, versions)

## 💡 Proposer des Fonctionnalités

- Ouvrir une issue de discussion
- Expliquer le cas d'usage
- Proposer une implémentation
- Considérer l'impact sur les performances

## 📞 Questions

Pour toute question, ouvrir une issue avec le label `question`.

Merci pour vos contributions ! 🙏
