from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

def evaluate_classifier(model, X_train, X_test, y_train, y_test, model_name, results_list):
    """
    Fits a classifier, evaluates it on the test set, prints a summary,
    and appends its metrics to results_list for later comparison.
    """
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "Model": model_name,
        "Accuracy": accuracy_score(y_test, y_pred),
        "Precision": precision_score(y_test, y_pred),
        "Recall": recall_score(y_test, y_pred),
        "F1": f1_score(y_test, y_pred),
        "ROC-AUC": roc_auc_score(y_test, y_proba)
    }

    print(f"  {model_name}   ")
    for k, v in metrics.items():
        if k != "Model":
            print(f"{k}: {v:.3f}")

    results_list.append(metrics)
    return model, results_list


from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

def evaluate_regressor(model, X_train, X_test, y_train, y_test, model_name, results_list, log_transform=False):
    """
    Fits a regressor, evaluates it on the test set, prints a summary,
    and appends results to results_list. If log_transform is True,
    fits on log1p(y_train) and converts predictions back via expm1.
    """
    if log_transform:
        y_train_fit = np.log1p(y_train)
    else:
        y_train_fit = y_train

    model.fit(X_train, y_train_fit)
    y_pred = model.predict(X_test)

    if log_transform:
        y_pred = np.clip(np.expm1(y_pred), 0, None)

    metrics = {
        "Model": model_name,
        "MAE": mean_absolute_error(y_test, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
        "R2": r2_score(y_test, y_pred),
        "Max Prediction": y_pred.max()
    }

    print(f"--- {model_name} ---")
    for k, v in metrics.items():
        if k != "Model":
            print(f"{k}: {v:.3f}" if k != "Max Prediction" else f"{k}: £{v:.2f}")

    results_list.append(metrics)
    return model, results_list