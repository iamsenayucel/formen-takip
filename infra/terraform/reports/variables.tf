variable "environment" {
  description = "Ortam adı (prod/staging vb.) — kaynak isimlendirmesine ve tag'lere yansır."
  type        = string
}

variable "aws_region" {
  description = "S3 bucket + destek kaynaklarının oluşturulacağı AWS bölgesi."
  type        = string
}

variable "bucket_name" {
  description = <<-EOT
    Formen aylık performans raporu PDF'lerinin tutulacağı S3 bucket adı.
    Global olarak benzersiz olmalıdır (ör. "formen-takip-reports-prod").
  EOT
  type        = string
}

variable "cloudfront_public_key_pem" {
  description = <<-EOT
    CloudFront signed URL doğrulaması için PUBLIC key (PEM, RSA-2048+).
    Karşılık gelen PRIVATE key Terraform'a HİÇBİR ZAMAN girmez — Terraform state'i
    okunabilir bir dosyadır ve private key'i orada tutmak sır sızıntısıdır. Anahtar
    çifti Terraform DIŞINDA üretilir (ör. `openssl genrsa`), private key doğrudan
    merkezi sır yönetimi servisine yüklenir ve backend'e CLOUDFRONT_PRIVATE_KEY olarak
    oradan inject edilir; yalnızca public key buraya, bir değişken olarak geçirilir.
  EOT
  type        = string
}

variable "ecs_task_role_name" {
  description = <<-EOT
    Backend'in çalıştığı ECS task role'ünün adı — least-privilege S3 IAM policy'si
    bu role'e attach edilir (bkz. tier1/playbook-backend-python-fastapi.md "Konfigürasyon
    & Sır Yönetimi": production'da secret'lar ECS task tanımı üzerinden inject edilir).
    Bu role henüz mevcut değilse (ör. compute katmanı ayrı bir Terraform modülünde
    yönetiliyorsa) boş bırakın — bu durumda yalnızca IAM policy oluşturulur, attach
    edilmez; `aws iam attach-role-policy` ile sonradan elle bağlanabilir.
  EOT
  type        = string
  default     = ""
}

variable "signed_url_key_group_comment" {
  description = "CloudFront key group açıklaması."
  type        = string
  default     = "Formen aylık rapor signed URL doğrulama anahtar grubu"
}

variable "tags" {
  description = "Tüm kaynaklara uygulanacak ortak tag'ler."
  type        = map(string)
  default     = {}
}
