# Actual execution screenshots

- mlflow.jpg: original local MLflow experiment view with six runs.
- github-actions.png: successful training, tests and Docker workflow.
- ingress-prediction.png: HTTP 200 prediction through the temporary Minikube ingress.
- grafana.png: actual provisioned Compose dashboard after measured traffic.
- prometheus.png: actual scrape target UP.

The deployment and monitoring browser captures were taken by Playwright in a
disposable GitHub Actions Linux runner. The cluster and containers were deleted
after capture. See evidence/deployment-actions.json and browser-verification.json
for provenance, and the Kubernetes and monitoring logs for raw results.
api.jpg is an earlier local API documentation capture; the report uses the clearer
ingress-prediction.png. Figures under reports/figures are computed experiment plots.
