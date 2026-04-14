# EC2 #2 — Infra (Temporal + Temporal UI + Temporal PostgreSQL)

resource "aws_eip" "infra" {
  domain = "vpc"
  tags   = { Name = "${var.project_name}-infra-eip" }
}

resource "aws_eip_association" "infra" {
  instance_id   = aws_instance.infra.id
  allocation_id = aws_eip.infra.id
}

resource "aws_instance" "infra" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.small"
  key_name               = aws_key_pair.deploy.key_name
  vpc_security_group_ids = [aws_security_group.infra.id]
  subnet_id              = aws_subnet.public_a.id

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data_infra.sh", {
    project_name = var.project_name
  })

  tags = { Name = "${var.project_name}-infra" }
}
