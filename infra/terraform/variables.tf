variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "genalpha"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "genalpha"
}

variable "vercel_api_token" {
  description = "Vercel API token"
  type        = string
  sensitive   = true
}

variable "github_repo" {
  description = "GitHub repo (org/name)"
  type        = string
  default     = "Spardha-Org/genalphacli"
}

variable "db_password" {
  description = "RDS PostgreSQL password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tps_secret" {
  description = "Shared secret for Core ↔ TPS communication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "worker_secret" {
  description = "Shared secret for Worker → Core internal routes"
  type        = string
  sensitive   = true
  default     = ""
}

variable "fernet_key" {
  description = "Fernet encryption key for TPS credential storage"
  type        = string
  sensitive   = true
  default     = ""
}

variable "magic_link_secret" {
  description = "Secret for magic link token signing"
  type        = string
  sensitive   = true
  default     = ""
}

variable "my_ip" {
  description = "Your IP for SSH access (CIDR, e.g., 1.2.3.4/32)"
  type        = string
  default     = "0.0.0.0/0" # Restrict in production
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
  default     = ""
}

variable "resend_api_key" {
  description = "Resend API key for magic link emails"
  type        = string
  sensitive   = true
  default     = ""
}
