"""Closed identities for preserved, intentionally unapplied historical source."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from specify_cli.migration.owned_single_branch_proof import Sha

__all__ = ["CustodyManifest"]

_Text = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
_Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _TreeIdentity(_ClosedModel):
    mode: Literal["100644", "100755"]
    oid: Sha


class _Modification(_ClosedModel):
    path: _Text
    before: _TreeIdentity
    after: _TreeIdentity


class _ParentEdge(_ClosedModel):
    commit: Sha
    parent: Sha
    changes: Annotated[list[_Modification], Field(max_length=256)]


class _RefHistory(_ClosedModel):
    ref: _Text
    sha: Sha
    commits: Annotated[list[Sha], Field(max_length=256)]


class _TipVersion(_TreeIdentity):
    revision: Sha
    path: _Text


class _BlobEvidence(_ClosedModel):
    oid: Sha
    sha256: _Digest
    bytes: Annotated[int, Field(ge=0, le=8_388_608)]
    file: _Text


class CustodyManifest(_ClosedModel):
    schema_version: Literal[1]
    mission_id: _Text
    mission_slug: _Text
    owner_root: _Text
    owner_branch: _Text
    owner_head: Sha
    planning_commit_sha: Sha
    historical_base: Sha
    scope: Annotated[list[_Text], Field(min_length=1, max_length=256)]
    refs: Annotated[list[_RefHistory], Field(min_length=1, max_length=16)]
    edges: Annotated[list[_ParentEdge], Field(max_length=4096)]
    tips: Annotated[list[_TipVersion], Field(max_length=4608)]
    blobs: Annotated[list[_BlobEvidence], Field(max_length=1024)]
