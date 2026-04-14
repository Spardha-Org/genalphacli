terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "~> 1.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}

provider "vercel" {
  api_token = var.vercel_api_token
}

# Generate secrets if not provided
resource "random_password" "db_password" {
  count   = var.db_password == "" ? 1 : 0
  length  = 24
  special = false
}

resource "random_password" "tps_secret" {
  count   = var.tps_secret == "" ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "worker_secret" {
  count   = var.worker_secret == "" ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "magic_link_secret" {
  count   = var.magic_link_secret == "" ? 1 : 0
  length  = 32
  special = false
}

locals {
  db_password       = var.db_password != "" ? var.db_password : random_password.db_password[0].result
  tps_secret        = var.tps_secret != "" ? var.tps_secret : random_password.tps_secret[0].result
  worker_secret     = var.worker_secret != "" ? var.worker_secret : random_password.worker_secret[0].result
  magic_link_secret = var.magic_link_secret != "" ? var.magic_link_secret : random_password.magic_link_secret[0].result
}

# Get latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# SSH Key
resource "aws_key_pair" "deploy" {
  key_name   = "${var.project_name}-deploy"
  public_key = var.ssh_public_key != "" ? var.ssh_public_key : file("~/.ssh/id_rsa.pub")
}
