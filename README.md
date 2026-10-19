# HeartCare MLOps assignment

A small educational classifier for the presence of heart disease in the original
UCI Cleveland dataset. This is an assignment demonstration, not a diagnostic tool.
Author: Lokesh Verma. Student ID: 2025ct05026@wilp.bits-pilani.ac.in.

## Verified GitHub execution

Repository: https://github.com/2025ct05026/heartcare-mlops

The first GitHub Actions run passed dependency installation, lint, EDA, all six
MLflow experiments, all 19 tests, Docker construction and a real HTTP smoke test
against the isolated container:
https://github.com/2025ct05026/heartcare-mlops/actions/runs/39261525975

Actual workflow metadata and build/test logs are saved in `evidence/github-actions.json`,
`evidence/github-docker-build.txt`, `evidence/github-container-smoke.txt` and
`evidence/github-tests.txt`. The local Kubernetes and Grafana steps below still
need Docker Desktop execution and screenshots.

## Start here on Windows

Install Python 3.12 (recommended), Git and Docker Desktop. Enable Docker Desktop's
Linux containers and wait until its engine is running. Minikube and kubectl are
needed only for the deployment section. Run commands from this project folder.
The included dataset and fitted model allow an offline API run after installation.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m heartcare.data
python -m heartcare.eda
python -m heartcare.train
python -m ruff check heartcare test scripts
python -m pytest -q
python -m uvicorn heartcare.api:app --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python`; activation is optional. On macOS/Linux use `python3 -m venv .venv` and
`source .venv/bin/activate`. The code was verified with Python 3.12; CI uses 3.12.
To refresh the raw source, run `python -m heartcare.data --download`.

Open http://127.0.0.1:8000/docs. Expand POST /predict, click Try it out, paste
examples/patient.json and Execute. All 13 keys are required; an explicit JSON
`null` is imputed using statistics learned from training data. An omitted key,
invalid category or unexpected key returns HTTP 422.

In another terminal in the project folder:

```powershell
python -m scripts.smoke
$patient = Get-Content examples/patient.json -Raw
Invoke-RestMethod http://127.0.0.1:8000/predict -Method Post -ContentType application/json -Body $patient
```

`probability` is P(class 1), the estimated probability of disease presence in this
dataset. Prediction is 1 when probability >= 0.5. `confidence` is the probability
of the predicted class. Neither value is a calibrated clinical risk estimate.
`model_version` is the first 12 characters of the fitted artifact SHA256.

## Read the project in this order

Optional Windows shortcuts after creating the environment: `.\run.ps1 setup`,
`.\run.ps1 train`, `.\run.ps1 verify`, `.\run.ps1 serve` and `.\run.ps1 tracking`.
These call the same Python commands above without requiring environment activation.
`DATA_DICTIONARY.md` explains every input and its original UCI codes.

1. `heartcare/data.py`: downloads, validates labels and writes a cleaned CSV.
2. `heartcare/model.py`: defines imputation, scaling, encoding and the classifier.
3. `heartcare/eda.py`: draws development-data histograms, class balance and correlations.
4. `heartcare/train.py`: evaluates six candidates with five-fold CV and logs MLflow runs.
5. `heartcare/api.py`: loads the saved pipeline, validates JSON and serves predictions.
6. `test/`: verifies data, pipeline serialization and API behavior.
7. `.github/workflows/ci.yml`: runs checks, trains, tests and builds a container.
8. `k8s/api.yaml` and `monitoring/`: deployment and monitoring configurations.

There are 303 rows, 13 predictors and one target. The brief's 14-column description
includes the diagnosis column; do not invent a fourteenth predictor. The original
diagnosis codes 1, 2, 3, 4 become positive class 1; code 0 stays class 0. Missing
predictors remain empty in the cleaned CSV so imputation is learned within each
CV fold. Duplicate removal and schema/target validation are deterministic.

## Experiment tracking

```powershell
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000 and choose `heartcare-cleveland`. Each training run logs
parameters, four CV metric means and standard deviations, fold scores, EDA plots,
and the complete fitted pipeline as a joblib artifact. The winning run also logs
holdout metrics and evaluation plots. `reports/experiments.csv` is a portable run
summary. The local SQLite database and artifact folders are reproducible outputs;
run training again after moving the project because tracking artifact paths are
absolute. The submission ZIP includes the actual run exports under `evidence/`.

80% of data is used for development; 20% is held out using seed 42 and stratified
sampling. All six candidates see the same five folds. Highest mean CV ROC AUC
wins; a tie keeps the earlier candidate. The selected pipeline remains fitted on
the 242 development rows and is evaluated once on 61 holdout rows. The holdout
does not select hyperparameters or thresholds. CV estimates after choosing the
best candidate may be optimistic; the holdout is the separate check.

## Docker proof

Stop the Python API first to free port 8000. Build uses the saved model rather
than silently training a different model inside the image.

```powershell
docker version
docker build -t heartcare:1.0 .
docker run -d --name heartcare -p 8000:8000 heartcare:1.0
python -m scripts.smoke
docker logs heartcare
docker inspect --format='{{.State.Health.Status}}' heartcare
```

Wait about 25 seconds for the first health check. Capture the successful build,
smoke result and health status. Save screenshots in `screenshots/`. Stop and
remove only this project container before switching modes:
`docker rm -f heartcare`.

## Local Kubernetes deployment with Minikube

This route satisfies the brief's local Kubernetes option and avoids cloud cost.
Docker Desktop must be running. Use the same terminal directory as above.

```powershell
minikube start --driver=docker
minikube addons enable ingress
minikube image load heartcare:1.0
kubectl apply -f k8s/api.yaml
kubectl rollout status deployment/heartcare --timeout=180s
kubectl get pods,svc,ingress
```

In a separate **administrator terminal**, keep `minikube tunnel` running. On the
Windows Docker driver the ingress can be accessed through 127.0.0.1 while the
tunnel is active. Verify the ingress route using:

```powershell
$env:API_URL = 'http://127.0.0.1'
python -m scripts.smoke
kubectl logs deployment/heartcare --tail=20
```

If port 80 is occupied, stop the conflicting application. Capture the rollout,
two ready pods, ingress and real prediction response. For debugging only, use
`kubectl port-forward service/heartcare 8000:8000`, then set API_URL to
http://127.0.0.1:8000. Port forwarding verifies the service; also verify ingress
to meet the exposure requirement. For a different driver check `minikube ip`
and the Minikube ingress guide linked below.

The manifest has two replicas, health probes, CPU/memory bounds and a nonroot
read-only application container. Scaling is available using
`kubectl scale deployment/heartcare --replicas=3`. Prometheus counters in each
replica are independent. The supplied monitoring demo intentionally uses one API
container in Compose for an easy, unambiguous dashboard.

To roll out a changed model, retrain, build/tag `heartcare:1.1`, load it into
Minikube, then run `kubectl set image deployment/heartcare api=heartcare:1.1`.
Verify rollout and smoke tests. If it fails use `kubectl rollout undo deployment/heartcare`.

## Monitoring and logs

Stop any local API using port 8000 before starting Compose. This is a separate
monitoring demonstration; Kubernetes need not be running at the same time.

```powershell
$env:GRAFANA_PASSWORD = 'choose-your-own-local-password'
docker compose -f monitoring/compose.yaml up --build -d
$env:API_URL = 'http://127.0.0.1:8000'
1..20 | ForEach-Object { python -m scripts.smoke }
docker compose -f monitoring/compose.yaml logs api --tail 20
```

Open Prometheus at http://127.0.0.1:9090. Targets should show `heartcare` as UP.
Grafana is at http://127.0.0.1:3000; username admin and the password you chose.
The HeartCare folder contains a provisioned dashboard. Panels show prediction
request rate, mean latency, total invalid requests and prediction class counts.
Wait 30 seconds after traffic for rate charts. Grafana's Prometheus datasource is
provisioned automatically. API logs include route, method, status and latency;
patient values are not logged. `/metrics` also exposes Python process metrics.
This demonstrates service observability, not data drift or clinical accuracy
monitoring. There are no automatic retraining or alerting claims.

Clean up this project's monitoring containers with
`docker compose -f monitoring/compose.yaml down`. Remove Kubernetes resources
using `kubectl delete -f k8s/api.yaml` when finished.

## GitHub and CI

Create an empty GitHub repository in your own account. From this project folder:

```powershell
git init
git add .
git commit -m "Add HeartCare MLOps assignment"
git branch -M main
git remote add origin https://github.com/2025ct05026/heartcare-mlops.git
git push -u origin main
```

Use the GitHub account that owns this repository. Do not upload the virtual environment or local
tracking database. The workflow triggers on push and pull requests. Lint, training,
tests and the real container smoke test must all pass. Nonzero exits fail the
job. Artifact and container-log collection runs even on failure. Download the
experiment evidence artifact and capture the green workflow summary. CI exports
a verified Docker image tar, which can be loaded using `docker load -i
heartcare-image.tar`; tag the loaded SHA image as `heartcare:1.0` before Minikube.
Deployment is a deliberate local step, since GitHub's hosted runner cannot reach
your laptop's Minikube cluster. No automatic production deployment is claimed.

## Submission finishing steps

The ten-page Word report is the written submission. The code ZIP is supporting
material for upload to your own GitHub repository. Read `SUBMISSION_CHECKLIST.md`.
The DOCX includes https://github.com/2025ct05026/heartcare-mlops. Before handing in, add your own
successful CI, Docker, Kubernetes and Grafana screenshots in the indicated areas.
Keep the report at ten pages by replacing the evidence instructions rather than
appending pages. Verify all ten pages in Word after editing.

The assignment asks for independent understanding. Study the project, rerun it,
personalize your experiment choices, and follow your course's AI assistance policy.
Do not claim unperformed deployment steps. No video is included in this package.

## Sources

- UCI Heart Disease dataset, Janosi, Steinbrunn, Pfisterer and Detrano (1989),
  DOI https://doi.org/10.24432/C52P4X. CC BY 4.0. Original archive:
  https://archive.ics.uci.edu/static/public/45/heart+disease.zip
- MLflow tracking: https://mlflow.org/docs/latest/ml/tracking/
- sklearn pipelines: https://scikit-learn.org/stable/modules/compose.html
- FastAPI request bodies: https://fastapi.tiangolo.com/tutorial/body/
- Minikube ingress: https://minikube.sigs.k8s.io/docs/handbook/addons/ingress-dns/
- Kubernetes Minikube ingress example:
  https://kubernetes.io/docs/tasks/access-application-cluster/ingress-minikube/
- GitHub Actions: https://docs.github.com/en/actions
- Prometheus instrumentation: https://prometheus.github.io/client_python/
