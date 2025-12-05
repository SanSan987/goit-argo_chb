# goit-argo_chb
ArgoCD + GitOps-інфраструктура

Основні компоненти інфраструктури:
 Amazon EKS – кластер `my-education-cluster` (us-east-1)
ArgoCD – встановлений через Terraform у namespace `infra-tools`
Simple nginx Helm-service, який деплоїться з окремого Helm-репозиторію
  [`goit-helm-nginx_chb`](https://github.com/SanSan987/goit-helm-nginx_chb)
  під керуванням ArgoCD

Структура репозиторію

goit-argo_chb/
├─ applications/
│  ├─ root-app.yaml              # Root Application (app-of-apps) для ArgoCD
│  └─ nginx/
│     └─ application.yaml        # ArgoCD Application для nginx Helm-чарта
├─ namespaces/
│  ├─ infra-tools/
│  │  └─ ns.yaml                 # Namespace для ArgoCD
│  └─ application/
│     └─ ns.yaml                 # Namespace, в який деплоїться nginx
└─ README.md
Ключові файли:
-	namespaces/infra-tools/ns.yaml – декларація namespace infra-tools, де працює ArgoCD.
-	namespaces/application/ns.yaml – декларація namespace application.
-	applications/root-app.yaml – root Application, який підтягує всі підзастосунки з каталогу
applications/ (app-of-apps).
-	applications/nginx/application.yaml – ArgoCD Application, який:
дивиться в репозиторій goit-helm-nginx_chb,
бере Helm-чарт з шляху nginx,
деплоїть його у namespace application,
увімкнено automated sync + selfHeal,
опція syncOptions: [CreateNamespace=true] дозволяє автоматично створювати namespace.

Інфраструктура: EKS + ArgoCD (Terraform)
1. EKS + VPC + node groups
У репозиторії eks-vpc-cluster (окремо від цього проекту) Terraform:
створює VPC, сабнети, інтернет-шлюз;
піднімає кластер my-education-cluster у us-east-1;
створює node group (cpu_nodes-…).
Після terraform apply:
aws eks update-kubeconfig --region us-east-1 --name my-education-cluster
kubectl get nodes
2. ArgoCD через Terraform
У каталозі terraform/argocd:
ресурс helm_release.argocd встановлює ArgoCD у namespace infra-tools;
після terraform apply:
kubectl get pods -n infra-tools
kubectl get svc  -n infra-tools
Всі pod’и argocd-* у стані Running, сервіс argocd-server доступний як ClusterIP.
Для доступу до UI:
kubectl port-forward svc/argocd-server -n infra-tools 8080:443
# в браузері: https://localhost:8080
 
GitOps-потік для nginx (ArgoCD + Helm)
Окремий Helm-репозиторій:
Окремий репозиторій:
goit-helm-nginx_chb
Структура:
goit-helm-nginx_chb/
└─ nginx/
   ├─ Chart.yaml
   ├─ values.yaml
   └─ templates/
      ├─ _helpers.tpl
      ├─ deployment.yaml
      └─ service.yaml
У values.yaml сервіс налаштовано як:
service:
  type: LoadBalancer
  port: 80
ArgoCD Application для nginx (applications/nginx/application.yaml):
Root-app (applications/root-app.yaml) додається в кластер командою:
kubectl apply -f applications/root-app.yaml -n infra-tools
Після цього ArgoCD автоматично підтягує і створює nginx Application.
 
Перевірка, що все працює
Статус ArgoCD Applications:
kubectl get applications -n infra-tools
Очікувано:
root-app – Synced / Healthy
nginx – Synced / Healthy
Pod’и та сервіс у namespace application:
kubectl get pods -n application
kubectl get svc  -n application
Фактичний результат:
NAME                           READY   STATUS    RESTARTS   AGE
nginx-nginx-54c7b4dcfb-whqp9   1/1     Running   0          ...

NAME          TYPE           CLUSTER-IP       EXTERNAL-IP                                                               PORT(S)        AGE
nginx-nginx   LoadBalancer   172.20.224.158   ad58e0026ca2141ca87d93af977d8306-1483855393.us-east-1.elb.amazonaws.com   80:32582/TCP   ...
Це підтверджує, що:
Helm-чарт nginx задеплоєний через ArgoCD.
Pod nginx працює.
Є зовнішній доступ через LoadBalancer (*.elb.amazonaws.com).
 
Примітка щодо MLflow
На попередньому етапі в рамках цього ж завдання було реалізовано:
ArgoCD Application для Bitnami MLflow,
створення сервісів mlflow-minio, mlflow-postgresql, mlflow-tracking (LoadBalancer).
Однак через обмеження ресурсів кластера (переповнення pod-слотів і пам’яті на маленьких EC2-нодах) MLflow-поди не могли стабільно перейти в стан Running.

Результати з терміналу (на підтвердження):
(base) PS C:\Users\sansa\terraform\argocd> kubectl get pods -n application
NAME                           READY   STATUS    RESTARTS   AGE
nginx-nginx-54c7b4dcfb-whqp9   1/1     Running   0          9m46s
(base) PS C:\Users\sansa\terraform\argocd> kubectl get svc  -n application
NAME          TYPE           CLUSTER-IP       EXTERNAL-IP                                                               PORT(S)        AGE
nginx-nginx   LoadBalancer   172.20.224.158   ad58e0026ca2141ca87d93af977d8306-1483855393.us-east-1.elb.amazonaws.com   80:32582/TCP   9m48s
