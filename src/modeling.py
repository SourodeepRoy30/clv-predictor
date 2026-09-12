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
