<div align="center">

# Morphe Patch Builder

**A community-maintained Morphe APK and module builder**

[![CI](https://github.com/ausypher/morphe-patch-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/ausypher/morphe-patch-builder/actions/workflows/ci.yml)
[![Releases](https://img.shields.io/github/v/release/ausypher/morphe-patch-builder?display_name=tag&label=latest%20release)](https://github.com/ausypher/morphe-patch-builder/releases)

Build patched APKs and modules with GitHub Actions, using configurable Morphe patches and multiple APK download sources.

[**Latest releases**](https://github.com/ausypher/morphe-patch-builder/releases) · [**Build workflow**](https://github.com/ausypher/morphe-patch-builder/actions/workflows/build.yml)

</div>

---

## About this fork

The core builder is based on [**elohim-etz/morphe-builder**](https://github.com/elohim-etz/morphe-builder). This project uses its build system and configuration-driven workflow as the foundation, with independent modifications and additions for this fork.

The APK download flow also includes components adapted from [**nvbangg/builder-for-morphe**](https://github.com/nvbangg/builder-for-morphe) for retrieving APKs from **APKMirror**. The APKMirror integration was tested in [**my-youtube-morphe**](https://github.com/ausypher/my-youtube-morphe) before being ported to this multi-app builder.

### APK download and cache

The builder resolves the required package/version first, then checks the dedicated
`stock-cache` GitHub Release for an exact package + version + architecture match.
Cached files are checksum-checked and their original signing certificate is
verified before reuse. Split APKM files are cached in their original form so
they can be merged again without losing the upstream signature evidence.

On a cache miss, configured sources are tried in order:

1. **APKMirror** — primary source, using the integrated APKMirror scraper
2. **APKPure** — independent fallback for version-pinned single APKs
3. **GitHub Releases** — configured release assets
4. **Archive.org** — configured archive mirror
5. **Direct URL** — optional manually supplied APK/APKM link

A successfully downloaded file is cached only after the existing signing
certificate check passes. The cache release stores APK binaries separately
from the Git history and does not mix with patched-app releases.
This fork is maintained separately. Links above identify the upstream project and the source of the APKMirror-related components.

Use [**zygisk-detach**](https://github.com/j-hc/zygisk-detach) to detach YouTube and YT Music from Play Store if you are using modules. 

<details><summary><big>Features</big></summary>
<ul>
 <li>Support all present and future <a href="https://github.com/MorpheApp/morphe-patches">Morphe</a> apps</li>
 <li> Can build Modules and non-root APKs</li>
 <li> Updated daily with the latest versions of apps and patches</li>
 <li> Optimize APKs and modules for size</li>
 <li> Modules</li>
    <ul>
     <li> recompile invalidated odex for faster usage</li>
     <li> receive updates from Magisk app</li>
     <li> do not break safetynet or trigger root detections</li>
     <li> handle installation of the correct version of the stock app and all that</li>
     <li> support Magisk and KernelSU</li>
    </ul>
</ul>
Note that the <a href="../../actions/workflows/ci.yml">CI workflow</a> is scheduled to build the modules and APKs everyday using GitHub Actions if there is a change in Morphe patches. You may want to disable it.
</details>

## To include/exclude patches or patch other apps

 * Star the repo :eyes:
 * Use the repo as a [template](https://github.com/new?template_name=morphe-builder&template_owner=elohim-etz)
 * Customize [`config.toml`](./config.toml) using [rvmm-config-gen](https://j-hc.github.io/rvmm-config-gen/)
 * Run the build [workflow](../../actions/workflows/build.yml)
 * Grab your modules and APKs from [releases](../../releases)

also see here [`CONFIG.md`](./CONFIG.md)

## If you are having trouble with the classic mount method of the modules
such as,
- **"Reflash needed"** error after reboots
- **"Suspicious mount detected"** warnings from root detector apps

You can consider using [rvmm-zygisk-mount](https://github.com/j-hc/rvmm-zygisk-mount)

## Building Locally
### On Termux
```console
bash <(curl -sSf https://raw.githubusercontent.com/elohim-etz/morphe-builder/main/build-termux.sh)
```

### On Desktop
```console
$ git clone https://github.com/elohim-etz/morphe-builder
$ cd morphe-builder
$ ./build.sh
```
