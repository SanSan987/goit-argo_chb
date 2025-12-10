# experiments/train_and_push.py
import os
import shutil
from dotenv import load_dotenv

# Завантажуємо змінні оточення
load_dotenv()

import mlflow
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss

# Для пушу метрик у Prometheus PushGateway
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# --- Конфігурація ---
# URI для MLflow Tracking Server (в кластері)
# http://<service_name>.<namespace>.svc.cluster.local:<port>
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-tracking-server.mlflow-infra.svc.cluster.local:5000")
# URI для PushGateway (в кластері)
PUSHGATEWAY_URI = os.getenv("PUSHGATEWAY_URI", "pushgateway.monitoring.svc.cluster.local:9091") 

EXPERIMENT_NAME = "Iris Classification - MLOps Demo"
BEST_MODEL_DIR = "best_model"

# Параметри для ітерації
LEARNING_RATES = [0.01, 0.1, 1.0]
MAX_ITERS = [50, 100, 200]
RANDOM_STATE = 42

# --- Налаштування MLflow ---
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)

if experiment is None:
    experiment_id = mlflow.create_experiment(EXPERIMENT_NAME, tags={"demo": "mlops", "model": "LogisticRegression"})
    print(f"✅ Створено експеримент '{EXPERIMENT_NAME}' (ID={experiment_id})")
else:
    experiment_id = experiment.experiment_id
    print(f"ℹ️ Використовується існуючий експеримент '{EXPERIMENT_NAME}' (ID={experiment_id})")

# --- Завантаження та підготовка даних ---
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=RANDOM_STATE, stratify=y)
print(f"📊 Дані завантажено. Розмір тренувальної вибірки: {X_train.shape[0]}")


# --- Тренування та трекінг ---
best_accuracy = -1
best_run_id = None

for lr in LEARNING_RATES:
    for max_iter in MAX_ITERS:
        
        # Використовуємо назву для кращої ідентифікації в MLflow UI
        run_name = f"LR={lr}_Iter={max_iter}"

        with mlflow.start_run(experiment_id=experiment_id, run_name=run_name) as run:
            run_id = run.info.run_id
            print(f"\n🚀 Запуск експерименту: {run_name} (Run ID: {run_id})")

            # 1. Логування параметрів
            mlflow.log_param("learning_rate", lr)
            mlflow.log_param("max_iters", max_iter)
            mlflow.log_param("random_state", RANDOM_STATE)
            
            # 2. Тренування моделі
            # Для LogisticRegression 'learning_rate' не є прямим параметром, використовуємо C=1/lr для симуляції
            C_param = 1/lr 
            model = LogisticRegression(C=C_param, max_iter=max_iter, random_state=RANDOM_STATE, solver='lbfgs')
            model.fit(X_train, y_train)

            # 3. Оцінка моделі
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)

            acc = accuracy_score(y_test, y_pred)
            loss = log_loss(y_test, y_proba)
            
            print(f"   -> Accuracy: {acc:.4f}, Loss: {loss:.4f}")

            # 4. Логування метрик в MLflow
            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("loss", loss)
            
            # 5. Збереження моделі як артефакту
            mlflow.sklearn.log_model(model, "model")
            
            # 6. Пуш метрик у PushGateway з мітками
            registry = CollectorRegistry()
            
            # Створюємо Gauge (індикатор, який може приймати будь-яке значення)
            g_acc = Gauge('mlflow_accuracy', 'Model classification accuracy', ['run_id', 'lr', 'max_iter'], registry=registry)
            g_loss = Gauge('mlflow_loss', 'Model log loss', ['run_id', 'lr', 'max_iter'], registry=registry)

            # Встановлюємо значення з мітками
            g_acc.labels(run_id=run_id, lr=str(lr), max_iter=str(max_iter)).set(acc)
            g_loss.labels(run_id=run_id, lr=str(lr), max_iter=str(max_iter)).set(loss)

            # Пушимо в PushGateway
            try:
                push_to_gateway(PUSHGATEWAY_URI, job='mlflow_experiments', registry=registry, handler=None)
                print("   -> ✅ Метрики запущено в PushGateway")
            except Exception as e:
                print(f"   -> ❌ Помилка пушу в PushGateway: {e}. Перевірте доступність URI: {PUSHGATEWAY_URI}")


            # 7. Визначення найкращої моделі
            if acc > best_accuracy:
                best_accuracy = acc
                best_run_id = run_id
                print("   -> 🏆 Це поки що найкраща модель!")

print("\n--- Завершення експериментів ---")

# --- Пошук та копіювання найкращої моделі ---
if best_run_id:
    print(f"✅ Найкращий Run ID: {best_run_id} з Accuracy: {best_accuracy:.4f}")
    
    # Видаляємо стару директорію, якщо вона існує
    if os.path.exists(BEST_MODEL_DIR):
        shutil.rmtree(BEST_MODEL_DIR)
        
    # Завантажуємо артефакт моделі з MLflow
    # Шлях: runs:/<run_id>/<artifact_path>
    model_uri = f"runs:/{best_run_id}/model"
    
    # Завантажуємо модель і зберігаємо в best_model/
    local_path = mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=BEST_MODEL_DIR)
    print(f"✅ Модель скопійовано у локальну директорію: {local_path}")
    
else:
    print("❌ Не знайдено жодного успішного запуску.")