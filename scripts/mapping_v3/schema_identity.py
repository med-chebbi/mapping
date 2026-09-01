"""Semantic identities obtained from official FLYNC model annotations."""

from __future__ import annotations

from pathlib import Path
from typing import Type

from flync.core.annotations.implied import Implied, ImpliedStrategy
from flync.core.base_models import FLYNCBaseModel
from flync.sdk.utils.field_utils import get_metadata


def implied_semantic_identity(model_type: Type[FLYNCBaseModel], document: Path) -> str | None:
    """Apply the identity strategy declared on the typed model's ``name`` field."""
    field = model_type.model_fields.get("name")
    if field is None:
        return None
    implied = get_metadata(field.metadata, Implied)
    if implied is None:
        return None
    if implied.strategy == ImpliedStrategy.FOLDER_NAME:
        return document.parent.name
    if implied.strategy == ImpliedStrategy.FILE_NAME:
        name = document.name
        return name.removesuffix(".flync.yaml").removesuffix(".flync.yml")
    return None
