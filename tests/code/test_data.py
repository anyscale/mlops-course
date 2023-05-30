import numpy as np
import pandas as pd
import pytest

from madewithml import data


@pytest.fixture(scope="module")
def df():
    data = [{"title": "a0", "description": "b0", "tag": "c0"}]
    df = pd.DataFrame(data)
    return df


def test_load_data(dataset_loc):
    num_samples = 10
    ds = data.load_data(dataset_loc=dataset_loc, num_samples=num_samples)
    assert ds.count() == num_samples


@pytest.mark.parametrize(
    "text, sw, clean_text",
    [
        ("hi", [], "hi"),
        ("hi you", ["you"], "hi"),
        ("hi yous", ["you"], "hi yous"),
    ],
)
def test_clean_text(text, sw, clean_text):
    assert data.clean_text(text=text, stopwords=sw) == clean_text


def test_preprocess(df):
    assert "text" not in df.columns
    df = data.preprocess(df)
    assert df.columns.tolist() == ["text", "tag"]


def test_tokenize(df):
    df = data.preprocess(df)
    in_batch = {col: df[col].to_numpy() for col in df.columns}
    out_batch = data.tokenize(in_batch)
    assert set(out_batch) == {"ids", "masks", "targets"}


def test_to_one_hot():
    in_batch = {"targets": [1]}
    out_batch = data.to_one_hot(in_batch, num_classes=3)
    assert np.array_equal(out_batch["targets"], [[0.0, 1.0, 0.0]])
