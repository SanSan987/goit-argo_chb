# Створюємо namespace для ArgoCD
resource "kubernetes_namespace" "infra_tools" {
  metadata {
    name = "infra-tools"
  }
}

# Ставимо ArgoCD як Helm-реліз
resource "helm_release" "argocd" {
  name      = "argocd"
  namespace = kubernetes_namespace.infra_tools.metadata[0].name

  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"

  create_namespace = false

  timeout = 900
  wait    = false  # не чекати повної готовності ресурсів

  values = [
    file("${path.module}/values/argocd-values.yaml")
  ]
}

