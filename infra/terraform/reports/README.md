# Formen Aylık Rapor Storage — Terraform

Bu modül **henüz deploy edilmemiştir**. Private S3 bucket + CloudFront (OAC ile) + backend
için least-privilege IAM policy'yi tanımlar. Gerçek değerler (bucket adı, bölge, ECS task
role adı) IT/DevOps tarafından sağlanana kadar `terraform apply` çalıştırılmamalıdır.

## CloudFront signing key çifti nasıl üretilir

Private key **hiçbir zaman** Terraform'a veya repoya girmez. Adımlar:

```bash
openssl genrsa -out cloudfront-report-signing-key.pem 2048
openssl rsa -pubout -in cloudfront-report-signing-key.pem -out cloudfront-report-signing-key-public.pem
```

- `cloudfront-report-signing-key-public.pem` içeriği → `cloudfront_public_key_pem` Terraform
  değişkenine (bu, güvenlik riski taşımaz, public key'dir).
- `cloudfront-report-signing-key.pem` (private key) → doğrudan kurumun merkezi sır yönetimi
  servisine yüklenir; backend'e `CLOUDFRONT_PRIVATE_KEY` ortam değişkeni olarak **yalnızca o
  servisten** inject edilir (bkz. `tier1/playbook-backend-python-fastapi.md` "Konfigürasyon
  & Sır Yönetimi"). Yerel diskte/terminalde tutulan kopya iş bitince silinir.

## Kullanım

```bash
terraform init
terraform plan \
  -var="environment=prod" \
  -var="aws_region=eu-central-1" \
  -var="bucket_name=formen-takip-reports-prod" \
  -var="cloudfront_public_key_pem=$(cat cloudfront-report-signing-key-public.pem)" \
  -var="ecs_task_role_name=<gerçek ECS task role adı>"
```

`terraform apply`'dan sonra `outputs.tf`'teki değerleri (`bucket_name`, `cloudfront_domain`,
`cloudfront_key_pair_id`, `backend_iam_policy_arn`) uygulamanın `.env`/Secrets Manager
yapılandırmasına aktarın — bkz. repo kökü README "Production Setup Required".
