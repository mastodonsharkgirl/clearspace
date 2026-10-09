from pathlib import Path


def pytest_configure(config):
    # Fresh clones do not contain the ignored fixture parent.
    (Path(__file__).resolve().parent.parent/'work').mkdir(exist_ok=True)
