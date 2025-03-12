# GitHub Actions Setup Guide

Ce guide explique comment configurer les secrets et environnements nécessaires pour le pipeline CI/CD.

## Secrets requis

### Secrets globaux du repository

Les secrets suivants doivent être configurés dans Settings > Secrets and variables > Actions :

#### AWS Development
- `AWS_ACCESS_KEY_ID` : Clé d'accès AWS pour l'environnement de développement
- `AWS_SECRET_ACCESS_KEY` : Clé secrète AWS pour l'environnement de développement

#### AWS Production
- `AWS_ACCESS_KEY_ID_PROD` : Clé d'accès AWS pour l'environnement de production
- `AWS_SECRET_ACCESS_KEY_PROD` : Clé secrète AWS pour l'environnement de production

#### Déploiement
- `LAMBDA_ARTIFACTS_BUCKET` : Nom du bucket S3 pour stocker les artefacts Lambda
- `DOCS_DOMAIN` : Domaine personnalisé pour la documentation (optionnel)

## Environnements

### Configuration des environnements

Créez les environnements suivants dans Settings > Environments :

#### development
- **Protection rules** : Aucune (déploiement automatique)
- **Reviewers** : Optionnel
- **Wait timer** : 0 minutes

#### production
- **Protection rules** : Required reviewers (au moins 1)
- **Reviewers** : Propriétaires du repository ou équipe senior
- **Wait timer** : 5 minutes (optionnel)

## Permissions nécessaires

### IAM Policies pour AWS

#### Politique de développement (AWS_ACCESS_KEY_ID)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*",
                "kinesis:*",
                "lambda:*",
                "iam:*",
                "ec2:*",
                "ecs:*",
                "logs:*",
                "cloudwatch:*"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": "us-east-1"
                }
            }
        }
    ]
}
```

#### Politique de production (AWS_ACCESS_KEY_ID_PROD)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "kinesis:DescribeStream",
                "kinesis:PutRecord",
                "kinesis:PutRecords",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:GetFunction",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": "us-east-1"
                }
            }
        }
    ]
}
```

## Workflows disponibles

### infrastructure.yml
- **Trigger** : Push/PR sur `infrastructure/**`
- **Jobs** :
  - Validation Terraform
  - Scan de sécurité avec Checkov
  - Déploiement automatique en dev
  - Déploiement avec approbation en prod

### application.yml
- **Trigger** : Push/PR sur code applicatif
- **Jobs** :
  - Tests et linting Python
  - Scan de sécurité avec Bandit
  - Build et déploiement des fonctions Lambda

### docs-and-release.yml
- **Trigger** : Push sur documentation ou release
- **Jobs** :
  - Validation de la documentation
  - Génération automatique de docs
  - Création de releases
  - Déploiement sur GitHub Pages

## Configuration initiale

1. **Créer les secrets** dans le repository GitHub
2. **Configurer les environnements** avec les règles de protection
3. **Créer les buckets S3** pour les artefacts (si nécessaire)
4. **Tester le pipeline** avec un commit de test

## Commandes utiles

```bash
# Tester la validation Terraform localement
terraform fmt -check -recursive infrastructure/terraform
terraform validate infrastructure/terraform/environments/dev

# Tester le linting Python localement
black --check .
flake8 .
pytest tests/

# Tester la documentation localement
markdownlint '**/*.md'
```

## Dépannage

### Erreurs communes

1. **Terraform init fails** : Vérifier les credentials AWS et les permissions
2. **Security scan fails** : Corriger les vulnérabilités détectées par Checkov/Bandit
3. **Deployment stuck** : Vérifier les environnements et les reviewers configurés
4. **Lambda deployment fails** : Vérifier que le bucket S3 existe et les permissions

### Logs et debugging

- Consulter les logs des actions dans l'onglet Actions du repository
- Activer le mode debug en ajoutant `ACTIONS_STEP_DEBUG: true` dans les secrets
- Utiliser `continue-on-error: true` pour les étapes non-critiques
