# RDS PostgreSQL — Free Tier (db.t3.micro, 20GB)

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro" # Free tier

  allocated_storage     = 20 # Free tier max
  max_allocated_storage = 20
  storage_type          = "gp2"

  db_name  = "genalpha"
  username = "genalpha"
  password = local.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  publicly_accessible    = false

  # Free tier settings
  multi_az            = false
  skip_final_snapshot = true
  deletion_protection = false

  # Backups
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  tags = { Name = "${var.project_name}-db" }
}

# Create the two databases (core + tps) via provisioner
# RDS creates the 'genalpha' database by default (db_name above)
# We'll create 'core' and 'tps' databases in the EC2 user data init script
