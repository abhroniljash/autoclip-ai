output "aws_region" { value = var.aws_region }
output "media_bucket_name" { value = aws_s3_bucket.media.bucket }
output "sqs_queue_url" { value = aws_sqs_queue.jobs.url }
output "sqs_dead_letter_queue_url" { value = aws_sqs_queue.dead_letter.url }
output "ecs_task_role_arn" { value = aws_iam_role.task.arn }
