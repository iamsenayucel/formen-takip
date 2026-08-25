# Formen Aylık Performans Raporu — Private S3 + CloudFront Signed URL storage katmanı.
#
# Bu modül henüz DEPLOY EDİLMEMİŞTİR. Gerçek bucket adı, bölge, ECS task role ve
# CloudFront signing key çifti IT/DevOps tarafından sağlanacaktır (bkz. repo kökü
# README "Production Setup Required"). Burada yalnızca kod hazırdır.

locals {
  common_tags = merge(var.tags, {
    Environment = var.environment
    Project     = "formen-takip"
    Component   = "monthly-foreman-reports"
    ManagedBy   = "terraform"
  })
}

# ---------------------------------------------------------------------------
# S3 — kalıcı PDF depolama. PRIVATE: public ACL yok, Public Access Block açık,
# yalnızca CloudFront (OAC üzerinden) ve backend'in IAM role'ü erişebilir.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "reports" {
  bucket = var.bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket = aws_s3_bucket.reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ---------------------------------------------------------------------------
# CloudFront — private S3 origin'e Origin Access Control (OAC) ile erişir.
# Bucket'a DOĞRUDAN internet erişimi yoktur; yalnızca bu distribution üzerinden,
# ve yalnızca signed URL ile (TrustedKeyGroup) içerik servis edilir.
# ---------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "reports" {
  name                              = "${var.bucket_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_public_key" "report_signing_key" {
  name        = "${var.bucket_name}-signing-key"
  encoded_key = var.cloudfront_public_key_pem
  comment     = "Formen aylık rapor CloudFront signed URL public key"
}

resource "aws_cloudfront_key_group" "report_signers" {
  name    = "${var.bucket_name}-signers"
  comment = var.signed_url_key_group_comment
  items   = [aws_cloudfront_public_key.report_signing_key.id]
}

resource "aws_cloudfront_distribution" "reports" {
  enabled         = true
  comment         = "Formen aylık performans raporu private PDF dağıtımı"
  is_ipv6_enabled = true
  tags            = local.common_tags

  origin {
    domain_name              = aws_s3_bucket.reports.bucket_regional_domain_name
    origin_id                = "reports-s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.reports.id
  }

  default_cache_behavior {
    allowed_methods         = ["GET", "HEAD"]
    cached_methods          = ["GET", "HEAD"]
    target_origin_id        = "reports-s3-origin"
    viewer_protocol_policy  = "redirect-to-https"
    trusted_key_groups      = [aws_cloudfront_key_group.report_signers.id]
    compress                = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_s3_bucket_policy" "reports_cloudfront_only" {
  bucket = aws_s3_bucket.reports.id
  policy = data.aws_iam_policy_document.reports_cloudfront_access.json
}

data "aws_iam_policy_document" "reports_cloudfront_access" {
  statement {
    sid    = "AllowCloudFrontServicePrincipalReadOnly"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.reports.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.reports.arn]
    }
  }
}

# ---------------------------------------------------------------------------
# IAM — backend uygulamasının S3'e erişimi. Least privilege: yalnızca
# PutObject/GetObject/HeadObject. DeleteObject verilmez (uygulama kodu hiçbir
# zaman S3 objesi silmez — rapor yeniden üretilirse aynı object_key overwrite edilir).
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "backend_reports_access" {
  statement {
    sid    = "ReportsObjectReadWrite"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:HeadObject",
    ]
    resources = ["${aws_s3_bucket.reports.arn}/*"]
  }

  statement {
    sid       = "ReportsBucketNoList"
    effect    = "Allow"
    actions   = ["s3:GetBucketLocation"]
    resources = [aws_s3_bucket.reports.arn]
  }
}

resource "aws_iam_policy" "backend_reports_access" {
  name        = "${var.bucket_name}-backend-access"
  description = "Formen backend'inin rapor S3 bucket'ına least-privilege erişimi (Put/Get/Head, Delete yok)"
  policy      = data.aws_iam_policy_document.backend_reports_access.json
  tags        = local.common_tags
}

resource "aws_iam_role_policy_attachment" "backend_reports_access" {
  count      = var.ecs_task_role_name != "" ? 1 : 0
  role       = var.ecs_task_role_name
  policy_arn = aws_iam_policy.backend_reports_access.arn
}
