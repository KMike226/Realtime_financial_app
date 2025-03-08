# Configuration du backend Terraform pour l'état distant
# Décommentez et configurez selon vos besoins

# Option 1: Backend S3 (recommandé pour la production)
# terraform {
#   backend "s3" {
#     bucket         = "votre-bucket-terraform-state"
#     key            = "dev/terraform.tfstate"
#     region         = "eu-west-1"
#     encrypt        = true
#     dynamodb_table = "terraform-state-locks"
#   }
# }

# Option 2: Backend local (pour développement/test)
terraform {
  backend "local" {
    path = "./terraform.tfstate"
  }
}

# Instructions pour configurer le backend S3:
# 1. Créer un bucket S3 pour stocker l'état Terraform
# 2. Créer une table DynamoDB pour les verrous d'état
# 3. Décommenter la configuration S3 ci-dessus
# 4. Remplacer "votre-bucket-terraform-state" par le nom de votre bucket
# 5. Exécuter: terraform init -migrate-state
