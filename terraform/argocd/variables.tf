variable "region" {
  type        = string
  description = "AWS region for EKS cluster"
  default     = "us-east-1"
}

variable "cluster_name" {
  type        = string
  description = "Existing EKS cluster name"
  default     = "my-education-cluster"
}
