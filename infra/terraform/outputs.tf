# Outputs — displayed after terraform apply

output "backend_ip" {
  description = "Backend EC2 public IP (Core + TPS + Worker)"
  value       = aws_eip.backend.public_ip
}

output "infra_ip" {
  description = "Infra EC2 public IP (Temporal)"
  value       = aws_eip.infra.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
}

output "temporal_address" {
  description = "Temporal gRPC address"
  value       = "${aws_eip.infra.public_ip}:7233"
}

output "temporal_ui" {
  description = "Temporal UI URL"
  value       = "http://${aws_eip.infra.public_ip}:8080"
}

output "core_api" {
  description = "Core API URL"
  value       = "http://${aws_eip.backend.public_ip}"
}

output "ssh_backend" {
  description = "SSH to backend"
  value       = "ssh -i ~/.ssh/id_rsa ec2-user@${aws_eip.backend.public_ip}"
}

output "ssh_infra" {
  description = "SSH to infra"
  value       = "ssh -i ~/.ssh/id_rsa ec2-user@${aws_eip.infra.public_ip}"
}

output "db_password" {
  description = "Generated DB password"
  value       = local.db_password
  sensitive   = true
}
