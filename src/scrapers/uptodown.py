"""Uptodown APK source for the Morphe build pipeline."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.core.network import NetworkManager
from src.scrapers.base import AppMetadata, BaseScraper, DownloadResult, ScraperError, parse_html


class UptodownError(ScraperError):
    pass


class UptodownScraper(BaseScraper):
    def _base_url(self, url: str) -> str:
        return url.rstrip("/")

    def _package_name(self, url: str, soup: BeautifulSoup) -> str:
        for cell in soup.find_all(["th", "td"]):
            if "package name" in cell.get_text(" ", strip=True).lower():
                sibling = cell.find_next_sibling("td")
                if sibling:
                    package = sibling.get_text(strip=True)
                    if re.fullmatch(r"[\w.]+", package) and "." in package:
                        return package

        match = re.search(r"play\.google\.com/store/apps/details\?id=([\w.]+)", str(soup))
        if match:
            return match.group(1)

        known = (
            ("youtube-music", "com.google.android.apps.youtube.music"),
            ("youtube", "com.google.android.youtube"),
            ("photos", "com.google.android.apps.photos"),
            ("reddit", "com.reddit.frontpage"),
            ("twitter", "com.twitter.android"),
            ("instagram", "com.instagram.android"),
        )
        lowered = url.lower()
        return next((pkg for key, pkg in known if key in lowered), "")

    def fetch_metadata(self, url: str) -> AppMetadata:
        base = self._base_url(url)
        download_soup = parse_html(self.net.get(f"{base}/download"))
        package = self._package_name(base, download_soup)
        if not package:
            raise UptodownError(f"Could not determine package name from {base}")

        versions_soup = parse_html(self.net.get(f"{base}/versions"))
        versions = [node.get_text(strip=True) for node in versions_soup.select(".version")]
        if not versions:
            raise UptodownError(f"No versions were listed for {base}")
        return AppMetadata(pkg_name=package, versions=versions)

    @staticmethod
    def _data_code(soup: BeautifulSoup) -> str | None:
        node = soup.select_one("#detail-app-name[data-code]")
        if node:
            return str(node.get("data-code"))
        node = soup.find(attrs={"data-code": True})
        if node:
            return str(node.get("data-code"))
        match = re.search(r'data-code=["\'](\d+)["\']', str(soup))
        return match.group(1) if match else None

    @staticmethod
    def _arch_matches(label: str, arch: str) -> bool:
        value = re.sub(r"[^a-z0-9]+", "", label.lower())
        target = arch.lower().replace("-", "")
        aliases = {
            "armv7a": ("armeabiv7a", "armv7a"),
            "armeabiv7a": ("armeabiv7a", "armv7a"),
            "arm64v8a": ("arm64v8a",),
            "x8664": ("x8664",),
            "x86": ("x86",),
        }
        return arch in ("all", "both", "") or any(alias in value for alias in aliases.get(target, (target,)))

    def download(
        self,
        url: str,
        version: str,
        dest: Path,
        arch: str,
        dpi: str,
        version_code: str | None = None,
    ) -> DownloadResult:
        del dpi, version_code
        base = self._base_url(url)
        versions_soup = parse_html(self.net.get(f"{base}/versions"))
        data_code = self._data_code(versions_soup)
        if not data_code:
            raise UptodownError("Uptodown app data-code was not found")

        clean_version = re.sub(
            r"-(all|arm64-v8a|armeabi-v7a|arm-v7a|x86_64|x86)$",
            "",
            version,
            flags=re.IGNORECASE,
        ).strip()
        version_data: dict | None = None

        for page in range(1, 21):
            endpoint = urljoin(f"{base}/", f"apps/{data_code}/versions/{page}")
            try:
                payload = json.loads(self.net.get(endpoint))
            except (json.JSONDecodeError, TypeError):
                continue
            entries = payload.get("data", []) if isinstance(payload, dict) else []
            for entry in entries:
                entry_version = str(entry.get("version", "")).strip()
                if entry_version in (version, clean_version):
                    version_data = entry.get("versionURL") or {}
                    break
            if version_data:
                break

        if not version_data:
            raise UptodownError(f"Version {version} was not found on Uptodown")

        parts = [
            str(version_data.get("url", "")).strip("/"),
            str(version_data.get("extraURL", "")).strip("/"),
            str(version_data.get("versionID", "")).strip("/"),
        ]
        version_url = "/".join(part for part in parts if part)
        if not version_url.startswith(("http://", "https://")):
            version_url = urljoin(f"{base}/", version_url)

        detail_soup = parse_html(self.net.get(version_url))
        is_bundle = False
        variants = detail_soup.select_one(".button.variants")
        if variants and variants.get("data-version"):
            origin = base.rsplit("/", 1)[0]
            files_url = (
                f"{origin}/app/{data_code}/version/"
                f"{variants['data-version']}/files"
            )
            files_payload = json.loads(self.net.get(files_url))
            files_soup = parse_html(str(files_payload.get("content", "")))

            candidates: list[tuple[str, bool, str]] = []
            current_arch = ""
            content = files_soup.select_one(".content")
            if content:
                for child in content.children:
                    if not getattr(child, "name", None):
                        continue
                    if "variant" not in (child.get("class") or []):
                        current_arch = child.get_text(" ", strip=True)
                        continue

                    report = child.select_one(".v-report[data-file-id]")
                    if not report:
                        continue
                    file_type = child.select_one(".v-file > span")
                    bundle = bool(
                        file_type
                        and file_type.get_text(strip=True).lower() == "xapk"
                    )
                    candidates.append(
                        (str(report["data-file-id"]), bundle, current_arch)
                    )

            selected = next(
                (item for item in candidates if self._arch_matches(item[2], arch)),
                None,
            )
            if selected is None and len(candidates) == 1:
                selected = candidates[0]
            if selected is None:
                raise UptodownError(
                    f"No Uptodown variant matches architecture {arch}"
                )

            file_id, is_bundle, _ = selected
            detail_url = urljoin(f"{base}/", f"download/{file_id}-x")
            detail_soup = parse_html(self.net.get(detail_url))

        button = detail_soup.select_one("#detail-download-button[data-url]")
        if not button:
            raise UptodownError("Uptodown download button was not found")

        download_url = f"https://dw.uptodown.com/dwn/{button['data-url']}"
        output = dest.with_suffix(".apkm") if is_bundle else dest
        self.net.download(download_url, output)

        with output.open("rb") as downloaded:
            if downloaded.read(2) != b"PK":
                output.unlink(missing_ok=True)
                raise UptodownError("Uptodown returned a file that is not a valid APK archive")

        return DownloadResult(path=output, is_bundle=is_bundle)
