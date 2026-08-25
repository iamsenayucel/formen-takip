output "bucket_name" {
  description = "REPORTS_S3_BUCKET env değişkenine girilecek değer."
  value       = aws_s3_bucket.reports.bucket
}

output "cloudfront_domain" {
  description = "CLOUDFRONT_DOMAIN env değişkenine girilecek değer (distribution domain adı)."
  value       = aws_cloudfront_distribution.reports.domain_name
}

output "cloudfront_key_pair_id" {
  description = "CLOUDFRONT_KEY_PAIR_ID env değişkenine girilecek değer."
  value       = aws_cloudfront_public_key.report_signing_key.id
}

output "backend_iam_policy_arn" {
  description = "Backend'in ECS task role'üne (veya eşdeğer compute IAM identity'sine) attach edilmesi gereken policy ARN'i."
  value       = aws_iam_policy.backend_reports_access.arn
}
