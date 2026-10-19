# Explain the project in your own words

## The full flow

Health measurements arrive as one JSON object. Pydantic checks the fields. The
saved pipeline fills missing values, scales continuous measurements and encodes
categories in exactly the same way as training. The classifier produces class 1
probability. The API applies a fixed 0.5 threshold and returns the result.

## Questions you should be able to answer

**Why use a pipeline?** It saves preprocessing and the classifier together, so
training and prediction use the same transformations. During CV it learns
imputation/scaling/encoding from each training fold only.

**Why two models?** Logistic Regression is a simple baseline; Random Forest can
model nonlinear interactions. The validation score chooses between them.

**Why not select using test accuracy?** Choosing hyperparameters on the holdout
would leak information and make the final estimate optimistic.

**What do precision and recall mean?** Precision is TP/(TP+FP); recall is
TP/(TP+FN). ROC AUC measures how well scores rank positive above negative cases
across thresholds. Accuracy is (TP+TN)/all. No single metric proves clinical value.

**Why is the cleaned CSV still missing values?** The cleanup normalizes the data
format; the learned imputer must fit only within training partitions. Filling
the whole CSV first would leak validation information.

**What is an MLflow run?** One candidate evaluation with its parameters, metrics
and files. Six candidates produce six runs per training invocation.

**What is CI?** GitHub checks code automatically on every push or pull request.
Failures block the successful delivery path. The workflow preserves evidence.

**What is delivery here?** CI packages and smoke-tests the image and exports it.
Deploying to local Minikube is a documented manual step after checks pass.

**Why Docker?** It packages Python, dependencies and the saved model into one
repeatable service image. A healthy container is evidence that it runs in isolation.

**Why Kubernetes?** It manages replicas, health probes and service routing. An
Ingress exposes the service; Minikube provides a small cluster on your laptop.

**What is monitoring?** Request counts, response status and latency show whether
the service works. They do not show model accuracy unless outcomes are collected.

**What would you improve?** External validation, calibration, fairness analysis,
model/data version promotion, authentication/TLS, drift alerts and a locked
container digest. The small historical dataset limits generalization.

## Personalize before submitting

After understanding the baseline, try one justified hyperparameter change in
train.py and rerun training and tests. Explain whether it improved CV results.
Do not repeatedly use the holdout to choose changes. Keep a final untouched
evaluation set if making repeated experiments. Record your own decisions and
acknowledge assistance as required by your course.
