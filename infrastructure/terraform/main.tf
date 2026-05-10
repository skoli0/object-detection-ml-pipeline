terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.31"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.14"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

resource "kubernetes_namespace" "mlops" {
  metadata {
    name = "mlops-demo"
  }
}

resource "helm_release" "mlops_demo" {
  name       = "mlops-demo"
  chart      = "../../infrastructure/helm/mlops-demo"
  namespace  = kubernetes_namespace.mlops.metadata[0].name
  depends_on = [kubernetes_namespace.mlops]
}
