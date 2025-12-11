# goit-argo_chb
MLOps Stack на AWS EKS з ArgoCD (Lesson 8-9)
Цей проект демонструє розгортання повноцінного MLOps-стека (MLflow, PostgreSQL, MinIO, Prometheus PushGateway) на кластері AWS EKS з використанням GitOps-підходу через ArgoCD.

ІНСТРУКЦІЯ
- Як запустити train_and_push.py:
Для успішного запуску скрипту необхідно, щоб Pods minio-... та postgres-mlflow-postgresql-0 були у стані Running.
Встановлення змінних середовища (PowerShell):
У кореневій директорії experiments/ встановити URI для MLflow та PushGateway.
PowerShell
$env:MLFLOW_TRACKING_URI = "http://localhost:5000"
$env:PUSHGATEWAY_URI = "localhost:9091"
Виконання скрипту:
PowerShell
py train_and_push.py

- Перевірка наявності MLflow і PushGateway у кластері:
Наявність цих компонентів підтверджується, коли їхні Kubernetes-ресурси досягають стану Synced та Healthy в ArgoCD:
Перевірка Pods:
kubectl get pods -n mlflow-infra -l app.kubernetes.io/name=mlflow-tracking-server
kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus-pushgateway
(Очікуваний стан: 1/1 Running).
Перевірка Service: Переконатися, що Service створені для доступу:
kubectl get svc -n mlflow-infra | Select-String "mlflow-tracking-server"
kubectl get svc -n monitoring | Select-String "prometheus-pushgateway"

- Як зробити port-forward:
Для доступу до сервісів з локальної машини відкрити три окремі вкладки терміналу та запустити ці команди:
ArgoCD UI (використовується для управління):
kubectl port-forward svc/argocd-server 8080:443 -n infra-tools
MLflow Tracking Server (для скрипту):
kubectl port-forward svc/mlflow-tracking-server 5000:5000 -n mlflow-infra
Prometheus PushGateway (для метрик):
kubectl port-forward svc/prometheus-pushgateway 9091:9091 -n monitoring

- Як подивитись метрики в Grafana:
Запустити Port-Forward для Grafana:
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring
(Якщо використовується Helm-чарт kube-prometheus-stack).
Доступ: Відкрити http://localhost:3000 у браузері.
Перегляд: Переходимо до Explore (Дослідження) та вибираємо джерело даних Prometheus. Можемо перевірити метрики, надіслані PushGateway (наприклад, iris_model_train_duration_seconds). 
MLflow UI URL: http://localhost:5000
Grafana URL:  http://localhost:3000/explore


ПІДСУМКИ РЕЗУЛЬТАТІВ виконання Завдання:
Категорія	Статус	Коментар
EKS Cluster (t3.small)	✅ Успішно розгорнуто	Кластер масштабовано до 4 вузлів t3.small (оптимізація Free Tier).
ArgoCD Instance	✅ Успішно розгорнуто	ArgoCD працює у режимі App of Apps.
Persistent Volumes (PV/PVC)	✅ Успішно розгорнуто	Вирішено критичну проблему з дозволами IAM/CSI Driver, що дозволило успішно прив'язати томи EBS для MinIO та PostgreSQL.
MLflow/Postgres/MinIO Deployment	Блокування	Master Application розгорнутий і згенерований, але Pods MinIO та PostgreSQL блокуються на етапі ImagePullBackOff.
Можливість запуску train_and_push.py	❌ Не досягнуто	Запуск неможливий через відсутність підключення до MLflow (Connection Refused), оскільки Pod MLflow не може запуститися через залежності (MinIO, PostgreSQL).
Ключові причини незавершення:
Стійке кешування Helm: ArgoCD/Repo Server мав стійке внутрішнє кешування індексу Bitnami, що спричинило проблему "Chart Not Found" (це було ВИРІШЕНО).
Обмеження Docker Hub (ImagePullBackOff): Фінальне блокування виникло через те, що Kubelet кешує помилку ImagePullBackOff, найбільш ймовірно, через досягнення ліміту завантажень з публічних реєстрів (Docker Hub / Bitnami), або видалення старих тегів образів.

Результати виведень з робочого терміналу:
PS C:\Users\sansa\goit-argo_chb> kubectl get pods -n infra-tools
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          12h
argocd-applicationset-controller-7d76f8784f-2k8jt   1/1     Running   0          18h
argocd-redis-566887dfcd-7zllp                       1/1     Running   0          12h
argocd-repo-server-5db9d847b4-4f528                 1/1     Running   0          2m13s
argocd-server-9dbd4fbcb-lrtx4                       1/1     Running   0          12h

PS C:\Users\sansa\goit-argo_chb> kubectl port-forward svc/mlflow-tracking-server 5000:5000 -n mlflow-infra
Forwarding from 127.0.0.1:5000 -> 5000
Forwarding from [::1]:5000 -> 5000

PS C:\Users\sansa\terraform\argocd> kubectl port-forward svc/argocd-server 8080:443 -n infra-tools
Forwarding from 127.0.0.1:8080 -> 8080
Forwarding from [::1]:8080 -> 8080
Handling connection for 8080
Handling connection for 8080

PS C:\Users\sansa\eks-vpc-cluster> kubectl port-forward svc/prometheus-pushgateway 9091:9091 -n monitoring
Forwarding from 127.0.0.1:9091 -> 9091
Forwarding from [::1]:9091 -> 9091

PS C:\Users\sansa\goit-argo_chb> kubectl get pods -n mlflow-infra
NAME                                      READY   STATUS             RESTARTS         AGE
minio-84cdcc596-7hdtq                     0/1     ImagePullBackOff   0                42m
mlflow-tracking-server-656ffcbbfd-2qn2g   0/1     CrashLoopBackOff   22 (3m53s ago)   93m
postgres-mlflow-postgresql-0              0/1     ImagePullBackOff   0                42m

