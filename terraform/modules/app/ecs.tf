resource "aws_service_discovery_service" "backend" {
  name = "${var.name}-backend"

  dns_config {
    namespace_id = var.service_discovery_namespace_id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.name}/backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.name}/frontend"
  retention_in_days = 14
}

# --- IAM ---

# Both roles are created once, shared across every environment, by
# terraform/bootstrap-iam -- this project's applies deliberately run under a
# principal with no IAM permissions. diamond-ecs-execution already grants
# secretsmanager:GetSecretValue on every "diamond-*" secret (which covers
# var.db_url_secret_arn), so no per-environment policy is needed here.
data "aws_iam_role" "execution" {
  name = "diamond-ecs-execution"
}

data "aws_iam_role" "task" {
  name = "diamond-ecs-task"
}

# --- Backend service ---

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = data.aws_iam_role.execution.arn
  task_role_arn            = data.aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = var.backend_image
      essential = true
      portMappings = [
        { containerPort = var.backend_container_port, protocol = "tcp" }
      ]
      environment = [
        for k, v in merge({
          FLASK_ENV = "production"
        }, var.backend_extra_env) : { name = k, value = v }
      ]
      secrets = [
        { name = "SQLALCHEMY_DATABASE_URI", valueFrom = var.db_url_secret_arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.name}-backend"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.backend.id]
  }

  service_registries {
    registry_arn = aws_service_discovery_service.backend.arn
  }
}

# --- Frontend service ---

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = data.aws_iam_role.execution.arn
  task_role_arn            = data.aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = var.frontend_image
      essential = true
      portMappings = [
        { containerPort = var.frontend_container_port, protocol = "tcp" }
      ]
      environment = [
        for k, v in merge({
          NODE_ENV = "production"
          # Server-side Next.js proxy target - resolves via this instance's
          # own service-discovery entry, no public exposure of the backend.
          FLASK_URL              = "http://${aws_service_discovery_service.backend.name}.${var.service_discovery_namespace_name}:${var.backend_container_port}"
          NEXT_PUBLIC_VERCEL_URL = "http://${aws_lb.main.dns_name}"
        }, var.frontend_extra_env) : { name = k, value = v }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.name}-frontend"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.frontend.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = var.frontend_container_port
  }

  depends_on = [aws_lb_listener.http]
}
