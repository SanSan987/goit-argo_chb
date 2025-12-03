# goit-argo_chb

 ArgoCD + MLflow GitOps інфраструктура
(Git-репозиторій goit-argo_chb)

Мета завдання – розгорнути GitOps-інфраструктуру на базі:

- Amazon EKS (кластер Kubernetes),
- ArgoCD, встановленого через Terraform,
- MLflow, задеплоєного як Helm-чарт (Bitnami),
- керування маніфестами через Git-репозиторій (`goit-argo_chb`) у GitOps.

Структура репозиторію

```text
goit-argo_chb/
├─ applications/
│  ├─ root-app.yaml                # Root Application (app-of-apps) для ArgoCD
│  └─ mlflow/
│     └─ application.yaml          # ArgoCD Application для MLflow
├─ namespaces/
│  ├─ infra-tools/ns.yaml          # Namespace для ArgoCD
│  └─ application/ns.yaml          # Namespace для MLflow
└─ README.md                       # Цей файл

namespaces/infra-tools/ns.yaml – опис namespace infra-tools, де працює ArgoCD.
namespaces/application/ns.yaml – опис namespace application для MLflow.
applications/root-app.yaml – ArgoCD Application типу “root-app”, який:
вказує на Git-репозиторій goit-argo_chb, рекурсивно підтягує маніфести з /applications (включно з MLflow).
applications/mlflow/application.yaml – ArgoCD Application для MLflow, який:
посилається на Helm-чарт Bitnami MLflow у Git-репозиторії, конфігурує namespace application,
налаштовує сервіс mlflow-tracking як LoadBalancer.
Інфраструктура та деплой
EKS та ArgoCD (через Terraform)
Інфраструктура піднімається в два етапи (окремі Terraform-конфігурації):
EKS + VPC + node groups (eks-vpc-cluster):
кластер my-education-cluster у регіоні us-east-1,
кілька nodegroup’ів (CPU/GPU),
auto scaling (збільшення кількості нодів для розміщення ArgoCD та MLflow).
ArgoCD (terraform/argocd):
helm_release.argocd встановлює ArgoCD в namespace infra-tools,
використовується офіційний Helm-чарт argo-cd з репозиторію https://argoproj.github.io/argo-helm,
kubectl get pods -n infra-tools показує всі основні компоненти в стані Running:
argocd-application-controller,
argocd-applicationset-controller,
argocd-redis,
argocd-repo-server,
argocd-server.
ArgoCD UI доступний через:
kubectl port-forward svc/argocd-server -n infra-tools 8080:443
і відкриття в браузері:
https://localhost:8080

GitOps-потік (ArgoCD + репозиторій)
Root app (applications/root-app.yaml)
створюється через kubectl apply -f applications/root-app.yaml -n infra-tools;
в ArgoCD з’являється Application root-app зі статусом Synced / Healthy;
root-app сканує каталог /applications у цьому репозиторії.
MLflow Application (applications/mlflow/application.yaml)
описує ArgoCD Application mlflow;
вказує:
джерело (source) – Git-репозиторій goit-argo_chb + шлях до Helm-чарта Bitnami MLflow;
ціль (destination) – кластер Kubernetes (https://kubernetes.default.svc), namespace application;
syncPolicy.automated з prune: true, selfHeal: true;
syncOptions з CreateNamespace=true.
Будь-які зміни в applications/mlflow/application.yaml:
комітяться в Git (git commit → git push),
підхоплюються ArgoCD,
можна форсувати оновлення:
kubectl annotate application mlflow \
  -n infra-tools \
  argocd.argoproj.io/refresh=hard \
  --overwrite

Перевірка деплою MLflow
Після налаштування MLflow Application:
kubectl get applications -n infra-tools
показує:
root-app зі статусом Synced / Healthy,
mlflow зі статусом OutOfSync / Progressing / Degraded (залежно від моменту та ресурсів), але при цьому ArgoCD створює необхідні ресурси в namespace application.
У namespace application створюються:
kubectl get svc -n application
NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP                                                              PORT(S)        AGE
mlflow-minio           ClusterIP      172.20.136.201   <none>                                                                   80/TCP         ...
mlflow-postgresql      ClusterIP      172.20.164.76    <none>                                                                   5432/TCP       ...
mlflow-postgresql-hl   ClusterIP      None             <none>                                                                   5432/TCP       ...
mlflow-tracking        LoadBalancer   172.20.170.98    af9f3edcf7cf74386be7a10ff91f437e-838529507.us-east-1.elb.amazonaws.com   80:32280/TCP   ...
Це означає:
MinIO (S3-сховище) для артефактів MLflow створено.
PostgreSQL для metadata/БД MLflow створено.
mlflow-tracking опублікований як LoadBalancer → є зовнішній DNS (*.elb.amazonaws.com).
Таким чином:
-	 MLflow-апка декларована через ArgoCD Application.
-	Сервіси для MLflow створені, включно з LoadBalancer.
-	 ArgoCD встановлено через Terraform. Встановлення ArgoCD виконується з Terraform-модуля (terraform/argocd) через ресурс: resource "helm_release" "argocd" { ... }
-	Namespace infra-tools створюється Terraform.
-	kubectl get pods -n infra-tools показує всі компоненти ArgoCD в стані Running.
-	ArgoCD UI доступний через kubectl port-forward до svc/argocd-server.
-	 Root app створює application namespace + MLflow Application
-	applications/root-app.yaml описує ArgoCD Application root-app (app-of-apps).
root-app в ArgoCD:
має статус Synced / Healthy,
керує дочірнім Application mlflow.
-	Namespace application створюється та використовується для MLflow.
-	MLflow application керується через Git (GitOps)
-	applications/mlflow/application.yaml лежить у цьому репозиторії.
-	Зміни в цьому файлі проходять через стандартний Git-потік:
git add applications/mlflow/application.yaml
git commit -m "Update MLflow settings"
git push origin ...
-	ArgoCD автоматично підтягує зміни (або після анотації argocd.argoproj.io/refresh=hard).
-	Статуси Sync Status та Health Status для mlflow змінювалися в залежності від конфігурацій та стану кластера, що доводить роботу GitOps-потоку.
-	Сервіси для MLflow створені (включно з mlflow-tracking як LoadBalancer)
-	kubectl get svc -n application показує:
mlflow-minio (ClusterIP),
mlflow-postgresql та mlflow-postgresql-hl,
mlflow-tracking (LoadBalancer) з зовнішнім DNS.
-	Helm-чарт MLflow відпрацював до стадії створення сервісів,
-	MLflow-трекер експонується назовні через LoadBalancer.

Повноцінний запуск усіх Pod’ів MLflow не виконаний в повній мірі
Хоча усі ресурси (Deployment/StatefulSet/Service/PVC) були створені, поди MLflow (mlflow-tracking, mlflow-minio, mlflow-postgresql, mlflow-run) в реальній інфраструктурі не дійшли до стабільного стану Running.
Основні, найбільш вірогідні, причини (з логів kubectl describe pod та kubectl get events):
Нестача ресурсів кластера (Insufficient memory / Too many pods)
Повідомлення типу: 4 Insufficient memory; 4 Too many pods
Це означає, що на наявних EC2-нодах (особливо малих типів) просто не вистачає RAM/под-слотів для усіх компонентів (EKS system, ArgoCD, MLflow, PostgreSQL, MinIO тощо).
 
З огляду на навчальний сенс завдання, збільшення розміру нодів, додавання ще більше EC2-ресурсів та дисків могло б суттєво підняти вартість. Тому було прийнято рішення:
залишити налаштування MLflow Application і Services в поточному стані (враховуючи наявність правильного налаштування GitOps-процесу і інтеграції з ArgoCD та Helm),
але не додавлювати до повного Running усіх Pod’ів за рахунок значного масштабування кластера.

Фактичний доступ до працюючого UI MLflow:
mlflow-tracking має тип LoadBalancer і зовнішній DNS *.elb.amazonaws.com, отже схема доступу через LB коректно налаштована.
Веб-інтерфейс ArgoCD відкривається, що підтверджується доданими сріншотами веб-сторінки URL: http://localhost:8080/...
Це означає: port-forward працює; ArgoCD-сервер живий; відбулося успішне залогінення як admin.

Результати з терміналу (на підтвердження):
(base) PS C:\Users\sansa\eks-vpc-cluster> kubectl get nodes
NAME                         STATUS   ROLES    AGE     VERSION
ip-10-0-1-170.ec2.internal   Ready    <none>   4m45s   v1.29.15-eks-ecaa3a6
ip-10-0-1-250.ec2.internal   Ready    <none>   5h      v1.29.15-eks-ecaa3a6
ip-10-0-2-219.ec2.internal   Ready    <none>   6h46m   v1.29.15-eks-ecaa3a6
ip-10-0-2-220.ec2.internal   Ready    <none>   4h2m    v1.29.15-eks-ecaa3a6
ip-10-0-2-57.ec2.internal    Ready    <none>   6h45m   v1.29.15-eks-ecaa3a6
(base) PS C:\Users\sansa\eks-vpc-cluster> kubectl get pods -n infra-tools
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          167m
argocd-applicationset-controller-7746b8f6c4-fgwfj   1/1     Running   0          167m
argocd-redis-d9c98c74d-992v5                        1/1     Running   0          167m
argocd-repo-server-587c5d5546-msmtb                 1/1     Running   0          167m
argocd-server-7564795f7c-9rx22                      1/1     Running   0          167m


(base) PS C:\Users\sansa\goit-argo_chb> kubectl apply -f applications/root-app.yaml -n infra-tools
application.argoproj.io/root-app created
(base) PS C:\Users\sansa\goit-argo_chb> kubectl get applications -n infra-tools
NAME       SYNC STATUS   HEALTH STATUS
mlflow     Unknown       Healthy
root-app   Synced        Healthy

(base) PS C:\Users\sansa\goit-argo_chb> kubectl get svc -n application
NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP                                                              PORT(S)        AGE
mlflow-minio           ClusterIP      172.20.136.201   <none>                                                                   80/TCP         94m
mlflow-postgresql      ClusterIP      172.20.164.76    <none>                                                                   5432/TCP       94m
mlflow-postgresql-hl   ClusterIP      None             <none>                                                                   5432/TCP       94m
mlflow-tracking        LoadBalancer   172.20.170.98    af9f3edcf7cf74386be7a10ff91f437e-838529507.us-east-1.elb.amazonaws.com   80:32280/TCP   94m
