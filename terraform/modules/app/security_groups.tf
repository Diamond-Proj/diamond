resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "Public ALB - allows inbound HTTP from the internet"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-alb" }
}

resource "aws_security_group" "frontend" {
  name        = "${var.name}-frontend"
  description = "Frontend ECS tasks - allows inbound from the ALB only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "From ALB"
    from_port       = var.frontend_container_port
    to_port         = var.frontend_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-frontend" }
}

resource "aws_security_group" "backend" {
  name        = "${var.name}-backend"
  description = "Backend ECS tasks - allows inbound from this environments frontend service only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "From frontend service"
    from_port       = var.backend_container_port
    to_port         = var.backend_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.frontend.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-backend" }
}

# The RDS security group lives in the database module (possibly in a
# different environment's state, for branch instances) -- add our ingress
# rule to it here rather than requiring it to know about every client SG.
resource "aws_security_group_rule" "backend_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.backend.id
  description              = var.name
}
