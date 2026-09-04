from dataclasses import dataclass
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig


@dataclass
class S3Entry:
    name: str
    key: str
    is_folder: bool
    size: int = 0
    last_modified: datetime | None = None


class S3Client:
    def __init__(self, profile_name: str, region: str, endpoint_url: str, bucket_name: str):
        self.profile_name = profile_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        session = boto3.session.Session(profile_name=profile_name)
        self._client = session.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=BotoConfig(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )

    def test_connection(self) -> None:
        self._client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)

    def list_entries(self, prefix: str) -> list[S3Entry]:
        entries: list[S3Entry] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix, Delimiter="/"):
            for cp in page.get("CommonPrefixes", []):
                folder_key = cp["Prefix"]
                name = folder_key[len(prefix):].rstrip("/")
                entries.append(S3Entry(name=name, key=folder_key, is_folder=True))
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key == prefix:
                    continue
                name = key[len(prefix):]
                if not name:
                    continue
                entries.append(
                    S3Entry(
                        name=name,
                        key=key,
                        is_folder=False,
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                    )
                )
        return entries

    def list_all_keys(self, prefix: str) -> list[str]:
        """All keys that actually exist under prefix, including any zero-byte
        folder marker objects. Use for delete/rename, which must only ever
        touch keys that are real objects (RunPod errors on deleting a
        virtual/non-existent prefix key)."""
        return [key for key, _size in self._list_all_raw(prefix)]

    def list_all_with_sizes(self, prefix: str) -> list[tuple[str, int]]:
        """Real files under prefix, excluding zero-byte folder marker
        objects. Use for downloads, where a marker key isn't a file to
        write to disk."""
        return [(k, s) for k, s in self._list_all_raw(prefix) if not (k.endswith("/") and s == 0)]

    def _list_all_raw(self, prefix: str) -> list[tuple[str, int]]:
        results: list[tuple[str, int]] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                results.append((obj["Key"], obj["Size"]))
        return results

    def create_folder(self, prefix: str) -> None:
        self._client.put_object(Bucket=self.bucket_name, Key=prefix, Body=b"")

    def delete_keys(self, keys: list[str]) -> None:
        # RunPod's S3-compatible endpoint doesn't support the bulk
        # DeleteObjects API (returns 307 Temporary Redirect), so delete
        # objects one at a time instead.
        for key in keys:
            self._client.delete_object(Bucket=self.bucket_name, Key=key)

    def delete_prefix(self, prefix: str) -> None:
        """Delete every real object under prefix, then best-effort clean up
        the empty directory nodes RunPod's backend otherwise leaves behind
        (it errors 'directory not empty' on a folder delete unless every
        nested subdirectory was also explicitly removed, deepest first)."""
        keys = self.list_all_keys(prefix)
        self.delete_keys(keys)

        dir_paths: set[str] = {prefix}
        for key in keys:
            parts = key.split("/")[:-1]
            accum = ""
            for part in parts:
                accum += part + "/"
                dir_paths.add(accum)
        for dir_key in sorted(dir_paths, key=len, reverse=True):
            try:
                self._client.delete_object(Bucket=self.bucket_name, Key=dir_key)
            except Exception:
                pass

    def copy_key(self, src_key: str, dst_key: str) -> None:
        self._client.copy_object(
            Bucket=self.bucket_name,
            CopySource={"Bucket": self.bucket_name, "Key": src_key},
            Key=dst_key,
        )

    def upload_file(self, local_path: str, key: str, progress_callback=None) -> None:
        self._client.upload_file(local_path, self.bucket_name, key, Callback=progress_callback)

    def download_file(self, key: str, local_path: str, progress_callback=None) -> None:
        self._client.download_file(self.bucket_name, key, local_path, Callback=progress_callback)

    def get_object_size(self, key: str) -> int:
        head = self._client.head_object(Bucket=self.bucket_name, Key=key)
        return head["ContentLength"]
