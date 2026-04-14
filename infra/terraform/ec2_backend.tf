# EC2 #1 — Backend (Core + TPS + Worker)

resource "aws_eip" "backend" {
  domain = "vpc"
  tags   = { Name = "${var.project_name}-backend-eip" }
}

resource "aws_eip_association" "backend" {
  instance_id   = aws_instance.backend.id
  allocation_id = aws_eip.backend.id
}

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro"
  key_name               = aws_key_pair.deploy.key_name
  vpc_security_group_ids = [aws_security_group.backend.id]
  subnet_id              = aws_subnet.public_a.id

  root_block_device {
    volume_size = 20 # GB — free tier allows up to 30
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data_backend.sh", {
    db_host           = aws_db_instance.main.address
    db_port           = aws_db_instance.main.port
    db_user           = aws_db_instance.main.username
    db_password       = local.db_password
    temporal_host     = aws_eip.infra.public_ip
    tps_secret        = local.tps_secret
    worker_secret     = local.worker_secret
    fernet_key        = var.fernet_key
    magic_link_secret = local.magic_link_secret
    resend_api_key    = var.resend_api_key
    app_url           = "http://${aws_eip.backend.public_ip}"
  })

  tags = { Name = "${var.project_name}-backend" }

  depends_on = [aws_db_instance.main]
}
