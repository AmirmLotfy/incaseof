"""A real DynamoDB, in process.

moto implements the service's actual semantics -- conditional expressions, transaction
cancellation, index sparseness -- so an invariant proven here is proven about DynamoDB
rather than about a stub that agrees with whatever the code does.

The table definition mirrors infra/cdk/lib/storage.ts. test_storage.test.ts asserts the
deployed table matches, so the two cannot drift.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws

from services.adapters import keys

TABLE_NAME = "ico-test"


@pytest.fixture(autouse=True)
def _credentials() -> Iterator[None]:
    """Dummy credentials so a misconfigured test can never reach a real account."""
    previous = dict(os.environ)
    os.environ.update(
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    )
    yield
    os.environ.clear()
    os.environ.update(previous)


@pytest.fixture
def table() -> Iterator[Any]:
    with mock_aws():
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        created = resource.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": keys.GSI1_PK, "AttributeType": "S"},
                {"AttributeName": keys.GSI1_SK, "AttributeType": "S"},
                {"AttributeName": keys.GSI2_PK, "AttributeType": "S"},
                {"AttributeName": keys.GSI2_SK, "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": keys.GSI1,
                    "KeySchema": [
                        {"AttributeName": keys.GSI1_PK, "KeyType": "HASH"},
                        {"AttributeName": keys.GSI1_SK, "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": keys.GSI2,
                    "KeySchema": [
                        {"AttributeName": keys.GSI2_PK, "KeyType": "HASH"},
                        {"AttributeName": keys.GSI2_SK, "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield created
