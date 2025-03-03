# Infrastructure Terraform

Modules Terraform pour le déploiement de l'infrastructure AWS.

## Structure

- `modules/` - Modules réutilisables
- `environments/` - Configurations par environnement
- `shared/` - Ressources partagées

## Usage

```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```
