#!/bin/bash

# Script de validation Terraform pour CI/CD
# Valide la syntaxe et la configuration Terraform

set -e

echo "🔍 Validation Terraform démarrée..."

# Configuration
TERRAFORM_DIR="infrastructure/terraform"
DEV_ENV="$TERRAFORM_DIR/environments/dev"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les erreurs
error() {
    echo -e "${RED}❌ Erreur: $1${NC}"
    exit 1
}

# Fonction pour afficher les succès
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Fonction pour afficher les avertissements
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Vérifier que Terraform est installé
if ! command -v terraform &> /dev/null; then
    error "Terraform n'est pas installé ou n'est pas dans le PATH"
fi

TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
echo "📋 Version Terraform: $TERRAFORM_VERSION"

# Vérifier la structure des répertoires
echo "📁 Vérification de la structure des répertoires..."

if [ ! -d "$TERRAFORM_DIR" ]; then
    error "Répertoire Terraform non trouvé: $TERRAFORM_DIR"
fi

if [ ! -d "$DEV_ENV" ]; then
    error "Environnement de développement non trouvé: $DEV_ENV"
fi

success "Structure des répertoires OK"

# Validation du formatage
echo "🎨 Vérification du formatage Terraform..."
cd "$TERRAFORM_DIR"

if ! terraform fmt -check -recursive; then
    warning "Le formatage Terraform n'est pas correct"
    echo "💡 Exécutez 'terraform fmt -recursive' pour corriger"
    # Ne pas faire échouer pour le formatage, juste avertir
else
    success "Formatage Terraform OK"
fi

# Validation de la syntaxe pour chaque module
echo "🔧 Validation des modules Terraform..."

MODULES=(
    "modules/vpc"
    "modules/s3"
    "modules/kinesis"
    "modules/iam"
    "modules/security"
)

for module in "${MODULES[@]}"; do
    if [ -d "$module" ]; then
        echo "📦 Validation du module: $module"
        cd "$module"
        
        if terraform validate; then
            success "Module $module valide"
        else
            error "Module $module invalide"
        fi
        
        cd - > /dev/null
    else
        warning "Module non trouvé: $module"
    fi
done

# Validation de l'environnement de développement
echo "🏗️  Validation de l'environnement de développement..."
cd "$DEV_ENV"

# Initialisation Terraform (sans backend pour validation)
echo "🔄 Initialisation Terraform..."
if terraform init -backend=false; then
    success "Initialisation réussie"
else
    error "Échec de l'initialisation Terraform"
fi

# Validation de la configuration
echo "✅ Validation de la configuration..."
if terraform validate; then
    success "Configuration valide"
else
    error "Configuration invalide"
fi

# Vérification des variables requises
echo "🔍 Vérification des variables..."
if [ -f "terraform.tfvars" ]; then
    success "Fichier terraform.tfvars trouvé"
    
    # Vérifier les variables importantes
    REQUIRED_VARS=(
        "environment"
        "project_name"
        "aws_region"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var" terraform.tfvars; then
            success "Variable $var définie"
        else
            warning "Variable $var non définie dans terraform.tfvars"
        fi
    done
else
    warning "Fichier terraform.tfvars non trouvé"
fi

# Plan Terraform (dry-run)
if [ "${SKIP_PLAN:-false}" != "true" ]; then
    echo "📋 Génération du plan Terraform..."
    if terraform plan -input=false -no-color > plan.out 2>&1; then
        success "Plan Terraform généré avec succès"
        
        # Analyser le plan pour des insights
        PLAN_SUMMARY=$(grep -E "(Plan:|No changes)" plan.out || echo "Plan généré")
        echo "📊 Résumé du plan: $PLAN_SUMMARY"
        
        # Nettoyer le fichier de plan
        rm -f plan.out
    else
        warning "Impossible de générer le plan Terraform (credentials AWS requis)"
        echo "💡 Définissez SKIP_PLAN=true pour ignorer cette étape"
    fi
fi

# Vérification des bonnes pratiques
echo "📋 Vérification des bonnes pratiques..."

# Vérifier que les ressources ont des tags
if grep -r "tags" . | grep -v ".terraform" | grep -v "plan.out" > /dev/null; then
    success "Tags trouvés dans la configuration"
else
    warning "Aucun tag trouvé - considérez l'ajout de tags pour les ressources"
fi

# Vérifier la présence de versions
if grep -r "required_version" . | grep -v ".terraform" > /dev/null; then
    success "Contraintes de version Terraform définies"
else
    warning "Aucune contrainte de version Terraform trouvée"
fi

# Vérifier la présence de providers avec versions
if grep -r "required_providers" . | grep -v ".terraform" > /dev/null; then
    success "Contraintes de version des providers définies"
else
    warning "Aucune contrainte de version des providers trouvée"
fi

echo ""
success "🎉 Validation Terraform terminée avec succès!"
echo "📝 Consultez les avertissements ci-dessus pour des améliorations possibles"
