#!/bin/bash

# Script de déploiement des dashboards Grafana
# ============================================

set -euo pipefail

# Configuration
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin123!}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour attendre que Grafana soit disponible
wait_for_grafana() {
    log_info "Attente de la disponibilité de Grafana..."
    
    for i in {1..30}; do
        if curl -s -f "${GRAFANA_URL}/api/health" >/dev/null 2>&1; then
            log_success "Grafana est disponible !"
            return 0
        fi
        
        log_info "Tentative $i/30... Attente 10s"
        sleep 10
    done
    
    log_error "Grafana n'est pas disponible après 5 minutes"
    return 1
}

# Fonction pour créer les dossiers
create_folders() {
    log_info "Création des dossiers Grafana..."
    
    local folders=(
        "Financial Platform"
        "System"
        "Development"
    )
    
    for folder in "${folders[@]}"; do
        local response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
            -d "{\"title\":\"${folder}\"}" \
            "${GRAFANA_URL}/api/folders")
        
        if echo "$response" | grep -q '"id"'; then
            log_success "Dossier créé: ${folder}"
        else
            log_warning "Dossier existe déjà ou erreur: ${folder}"
        fi
    done
}

# Fonction pour importer un dashboard
import_dashboard() {
    local dashboard_file="$1"
    local folder_title="$2"
    
    log_info "Import du dashboard: $(basename "$dashboard_file")"
    
    # Récupération de l'ID du dossier
    local folder_response=$(curl -s -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        "${GRAFANA_URL}/api/folders")
    
    local folder_id=$(echo "$folder_response" | jq -r ".[] | select(.title==\"$folder_title\") | .id")
    
    if [[ "$folder_id" == "null" || -z "$folder_id" ]]; then
        log_warning "Dossier '$folder_title' non trouvé, utilisation du dossier par défaut"
        folder_id=""
    fi
    
    # Préparation du payload
    local dashboard_content=$(cat "$dashboard_file")
    local payload
    
    if [[ -n "$folder_id" ]]; then
        payload=$(jq -n \
            --argjson dashboard "$dashboard_content" \
            --arg folderId "$folder_id" \
            '{
                dashboard: $dashboard.dashboard,
                folderId: ($folderId | tonumber),
                overwrite: true,
                message: "Deployed via script"
            }')
    else
        payload=$(jq -n \
            --argjson dashboard "$dashboard_content" \
            '{
                dashboard: $dashboard.dashboard,
                overwrite: true,
                message: "Deployed via script"
            }')
    fi
    
    # Import du dashboard
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        -d "$payload" \
        "${GRAFANA_URL}/api/dashboards/db")
    
    if echo "$response" | grep -q '"status":"success"'; then
        local dashboard_url=$(echo "$response" | jq -r '.url')
        log_success "Dashboard importé: ${GRAFANA_URL}${dashboard_url}"
    else
        log_error "Échec de l'import: $(echo "$response" | jq -r '.message // "Erreur inconnue"')"
        return 1
    fi
}

# Fonction pour configurer les sources de données
configure_datasources() {
    log_info "Configuration des sources de données..."
    
    if [[ -f "${SCRIPT_DIR}/datasources.yaml" ]]; then
        # Pour le moment, on affiche juste un message car la configuration automatique
        # des datasources nécessite une configuration plus complexe
        log_info "Fichier de configuration des datasources trouvé: ${SCRIPT_DIR}/datasources.yaml"
        log_warning "La configuration automatique des datasources n'est pas encore implémentée"
        log_info "Veuillez configurer manuellement les datasources via l'interface Grafana"
    else
        log_warning "Fichier datasources.yaml non trouvé"
    fi
}

# Fonction principale
main() {
    log_info "🚀 Démarrage du déploiement des dashboards Grafana"
    log_info "Grafana URL: $GRAFANA_URL"
    log_info "Utilisateur: $GRAFANA_USER"
    
    # Vérification des prérequis
    command -v curl >/dev/null 2>&1 || { log_error "curl est requis"; exit 1; }
    command -v jq >/dev/null 2>&1 || { log_error "jq est requis"; exit 1; }
    
    # Attendre que Grafana soit disponible
    wait_for_grafana
    
    # Créer les dossiers
    create_folders
    
    # Configurer les sources de données
    configure_datasources
    
    # Importer les dashboards
    log_info "Import des dashboards..."
    
    # Dashboard principal financier
    if [[ -f "${SCRIPT_DIR}/financial-overview-dashboard.json" ]]; then
        import_dashboard "${SCRIPT_DIR}/financial-overview-dashboard.json" "Financial Platform"
    else
        log_warning "Dashboard financier non trouvé"
    fi
    
    # Dashboard système
    if [[ -f "${SCRIPT_DIR}/system-monitoring-dashboard.json" ]]; then
        import_dashboard "${SCRIPT_DIR}/system-monitoring-dashboard.json" "System"
    else
        log_warning "Dashboard système non trouvé"
    fi
    
    log_success "🎉 Déploiement terminé !"
    log_info "Accédez à Grafana: $GRAFANA_URL"
    log_info "Identifiants: $GRAFANA_USER / [mot de passe configuré]"
}

# Gestion des arguments de ligne de commande
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h           Afficher cette aide"
        echo "  --check              Vérifier la connectivité Grafana"
        echo "  --folders-only       Créer uniquement les dossiers"
        echo "  --dashboards-only    Importer uniquement les dashboards"
        echo ""
        echo "Variables d'environnement:"
        echo "  GRAFANA_URL          URL de Grafana (défaut: http://localhost:3000)"
        echo "  GRAFANA_USER         Utilisateur Grafana (défaut: admin)"
        echo "  GRAFANA_PASSWORD     Mot de passe Grafana (défaut: admin123!)"
        exit 0
        ;;
    --check)
        log_info "Vérification de la connectivité Grafana..."
        wait_for_grafana
        exit $?
        ;;
    --folders-only)
        wait_for_grafana
        create_folders
        exit 0
        ;;
    --dashboards-only)
        wait_for_grafana
        if [[ -f "${SCRIPT_DIR}/financial-overview-dashboard.json" ]]; then
            import_dashboard "${SCRIPT_DIR}/financial-overview-dashboard.json" "Financial Platform"
        fi
        if [[ -f "${SCRIPT_DIR}/system-monitoring-dashboard.json" ]]; then
            import_dashboard "${SCRIPT_DIR}/system-monitoring-dashboard.json" "System"
        fi
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Option inconnue: $1"
        echo "Utilisez --help pour voir les options disponibles"
        exit 1
        ;;
esac
