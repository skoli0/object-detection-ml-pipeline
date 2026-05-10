from prefect import flow, task

from pipelines.train import train
from scripts.validate_data import validate_dataset


@task
def validate_task() -> None:
    validate_dataset()


@task
def train_task() -> None:
    train()


@flow(name="cv-mlops-pipeline")
def cv_pipeline() -> None:
    validate_task()
    train_task()


if __name__ == "__main__":
    cv_pipeline()
