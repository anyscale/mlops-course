import datetime
import json
from collections import OrderedDict
from typing import Dict

import numpy as np
import ray
import ray.train.torch  # NOQA: F401 (imported but unused)
import typer
from ray.data import Dataset
from ray.data.preprocessor import Preprocessor
from ray.train.torch.torch_predictor import TorchPredictor
from sklearn.metrics import precision_recall_fscore_support
from snorkel.slicing import PandasSFApplier, slicing_function

from madewithml import predict, utils
from madewithml.config import logger

# Initialize Typer CLI app
app = typer.Typer()


def get_overall_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:  # pragma: no cover, eval workload
    """Get overall performance metrics.

    Args:
        y_true (np.ndarray): ground truth labels.
        y_pred (np.ndarray): predicted labels.

    Returns:
        Dict: overall metrics.
    """
    metrics = precision_recall_fscore_support(y_true, y_pred, average="weighted")
    overall_metrics = {
        "precision": metrics[0],
        "recall": metrics[1],
        "f1": metrics[2],
        "num_samples": np.float64(len(y_true)),
    }
    return overall_metrics


def get_per_class_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, class_to_index: Dict
) -> Dict:  # pragma: no cover, eval workload
    """Get per class performance metrics.

    Args:
        y_true (np.ndarray): ground truth labels.
        y_pred (np.ndarray): predicted labels.
        class_to_index (Dict): dictionary mapping class to index.

    Returns:
        Dict: per class metrics.
    """
    per_class_metrics = {}
    metrics = precision_recall_fscore_support(y_true, y_pred, average=None)
    for i, _class in enumerate(class_to_index):
        per_class_metrics[_class] = {
            "precision": metrics[0][i],
            "recall": metrics[1][i],
            "f1": metrics[2][i],
            "num_samples": np.float64(metrics[3][i]),
        }
    sorted_per_class_metrics = OrderedDict(
        sorted(per_class_metrics.items(), key=lambda tag: tag[1]["f1"], reverse=True)
    )
    return sorted_per_class_metrics


@slicing_function()
def nlp_llm(x):  # pragma: no cover, eval workload
    """NLP projects that use LLMs."""
    nlp_project = "natural-language-processing" in x.tag
    llm_terms = ["transformer", "llm", "bert"]
    llm_project = any(s.lower() in x.text.lower() for s in llm_terms)
    return nlp_project and llm_project


@slicing_function()
def short_text(x):  # pragma: no cover, eval workload
    """Projects with short titles and descriptions."""
    return len(x.text.split()) < 8  # less than 8 words


def get_slice_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, ds: Dataset, preprocessor: Preprocessor
) -> Dict:  # pragma: no cover, eval workload
    """Get performance metrics for slices.

    Args:
        y_true (np.ndarray): ground truth labels.
        y_pred (np.ndarray): predicted labels.
        ds (Dataset): Ray dataset with labels.
        preprocessor (Preprocessor): Ray preprocessor.

    Returns:
        Dict: performance metrics for slices.
    """
    slice_metrics = {}
    df = preprocessor.preprocessors[0].transform(ds).to_pandas()
    slicing_functions = [nlp_llm, short_text]
    applier = PandasSFApplier(slicing_functions)
    slices = applier.apply(df)
    for slice_name in slices.dtype.names:
        mask = slices[slice_name].astype(bool)
        if sum(mask):
            metrics = precision_recall_fscore_support(y_true[mask], y_pred[mask], average="micro")
            slice_metrics[slice_name] = {}
            slice_metrics[slice_name]["precision"] = metrics[0]
            slice_metrics[slice_name]["recall"] = metrics[1]
            slice_metrics[slice_name]["f1"] = metrics[2]
            slice_metrics[slice_name]["num_samples"] = len(y_true[mask])
    return slice_metrics


@app.command()
def evaluate(
    run_id: str = typer.Option(..., "--run-id", help="id of the specific run to load from"),
    dataset_loc: str = typer.Option(..., "--dataset-loc", help="dataset (with labels) to evaluate on"),
    num_cpu_workers: int = typer.Option(
        1, "--num-cpu-workers", help="number of cpu workers to use for distributed data processing"
    ),
    results_fp: str = typer.Option(None, "--results-fp", help="location to save evaluation results to"),
) -> Dict:  # pragma: no cover, eval workload
    """_summary_

    Args:
        run_id (str): id of the specific run to load from. Defaults to None.
        dataset_loc (str): dataset (with labels) to evaluate on.
        num_cpu_workers (int, optional): number of cpu workers to use for
            distributed data processing (and training if `use_gpu` is false). Defaults to 1.
        results_fp (str, optional): location to save evaluation results to. Defaults to None.

    Returns:
        Dict: model's performance metrics on the dataset.
    """
    # Load
    ds = ray.data.read_csv(dataset_loc).repartition(num_cpu_workers)
    best_checkpoint = predict.get_best_checkpoint(run_id=run_id, metric="val_loss", mode="min")
    predictor = TorchPredictor.from_checkpoint(best_checkpoint)

    # y_true
    preprocessor = predictor.get_preprocessor()
    targets = utils.get_arr_col(preprocessor.transform(ds), col="targets")
    y_true = targets.argmax(1)

    # y_pred
    z = predictor.predict(data=ds.to_pandas())["predictions"]
    y_pred = np.stack(z).argmax(1)

    # Components
    label_encoder = preprocessor.preprocessors[1]
    class_to_index = label_encoder.stats_["unique_values(tag)"]

    # Metrics
    metrics = {
        "timestamp": datetime.datetime.now().strftime("%B %d, %Y %I:%M:%S %p"),
        "run_id": run_id,
        "overall": get_overall_metrics(y_true=y_true, y_pred=y_pred),
        "per_class": get_per_class_metrics(y_true=y_true, y_pred=y_pred, class_to_index=class_to_index),
        "slices": get_slice_metrics(y_true=y_true, y_pred=y_pred, ds=ds, preprocessor=preprocessor),
    }
    logger.info(json.dumps(metrics, indent=2))
    if results_fp:  # pragma: no cover, saving results
        utils.save_dict(d=metrics, path=results_fp)
    return metrics


if __name__ == "__main__":  # pragma: no cover, checked during evaluation workload
    app()
