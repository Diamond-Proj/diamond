resource "aws_lb" "main" {
  name               = "${var.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.name}-frontend"
  port        = var.frontend_container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    interval            = 30
    timeout             = 10
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  # Two separate dynamic variants rather than one block with a conditional
  # target_group_arn -- the AWS provider rejects target_group_arn being
  # present at all (even set to null) alongside a redirect block, so the
  # attribute must be structurally absent, not just null, for the redirect
  # case.
  dynamic "default_action" {
    for_each = var.domain_name != null ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.frontend.arn
    }
  }

  dynamic "default_action" {
    for_each = var.domain_name != null ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

# Only created when var.domain_name is set (skippable for throwaway branch
# environments, which stay HTTP-only on their raw ALB DNS name). This
# project's domains aren't in Route 53, so validation is manual -- apply
# once to get the acm_validation_record output, create that CNAME wherever
# DNS actually lives, then apply again once it's propagated (the
# aws_acm_certificate_validation resource just polls ACM until it sees it).
resource "aws_acm_certificate" "frontend" {
  count             = var.domain_name != null ? 1 : 0
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "frontend" {
  count           = var.domain_name != null ? 1 : 0
  certificate_arn = aws_acm_certificate.frontend[0].arn
}

resource "aws_lb_listener" "https" {
  count             = var.domain_name != null ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.frontend[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}
