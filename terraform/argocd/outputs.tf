output "argocd_namespace" {
  value       = kubernetes_namespace.infra_tools.metadata[0].name
  description = "Namespace where ArgoCD is installed"
}

output "argocd_helm_release_name" {
  value       = helm_release.argocd.name
  description = "ArgoCD Helm release name"
}

