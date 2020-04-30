module "config_cache_syncer" {
  source = "./modules/figgy_lambda"
  deploy_bucket = data.aws_s3_bucket.deploy_bucket.id
  description = "Incrementally synchronizes the cache table used for auto-complete in the figgy CLI tool"
  handler = "functions/config_cache_syncer.handle"
  lambda_name = "figgy-config-cache-syncer"
  lambda_timeout = 60
  policies = [aws_iam_policy.config_cache_manager.arn, aws_iam_policy.lambda_default.arn]
  zip_path = data.archive_file.figgy.output_path
}

module "config_cache_syncer_trigger" {
  source = "./modules/triggers/cron_trigger"
  lambda_name = module.config_cache_syncer.name
  lambda_arn = module.config_cache_syncer.arn
  schedule_expression = "rate(30 minutes)"
}
