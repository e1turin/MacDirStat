#!/usr/bin/env python3
"""Build a signed, distributable MacDirStat.app bundle from the Swift package.

By default this creates build/MacDirStat.app with an ad-hoc signature, suitable
for local installation. For distribution outside your own machines, provide a
Developer ID Application certificate with --sign and notarize the resulting app.
"""

import argparse
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "MacDirStat"
EXECUTABLE_NAME = "MacDirStat"
BUNDLE_IDENTIFIER = "com.phalladar.MacDirStat"
VERSION = "1.0.0"
MINIMUM_SYSTEM_VERSION = "15.0"


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE)
    return completed.stdout.strip()


def build_app(configuration: str, output_directory: Path, signing_identity: str) -> Path:
    binary_directory = Path(
        run(["swift", "build", "--configuration", configuration, "--show-bin-path"])
    )
    source_binary = binary_directory / EXECUTABLE_NAME
    if not source_binary.is_file():
        raise FileNotFoundError(f"Swift build did not produce the expected executable: {source_binary}")

    app_directory = output_directory / f"{APP_NAME}.app"
    if app_directory.exists():
        shutil.rmtree(app_directory)

    contents_directory = app_directory / "Contents"
    macos_directory = contents_directory / "MacOS"
    macos_directory.mkdir(parents=True)

    shutil.copy2(source_binary, macos_directory / EXECUTABLE_NAME)
    (macos_directory / EXECUTABLE_NAME).chmod(0o755)

    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": EXECUTABLE_NAME,
        "CFBundleIdentifier": BUNDLE_IDENTIFIER,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "LSMinimumSystemVersion": MINIMUM_SYSTEM_VERSION,
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    }
    with (contents_directory / "Info.plist").open("wb") as plist_file:
        plistlib.dump(info, plist_file, sort_keys=False)

    # An ad-hoc signature permits local use; a Developer ID signature is required
    # before submitting the bundle for Apple's notarization service.
    run(["codesign", "--force", "--deep", "--sign", signing_identity, str(app_directory)])
    run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app_directory)])

    return app_directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--configuration",
        choices=("debug", "release"),
        default="release",
        help="Swift build configuration (default: release)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "build",
        help="directory in which to create the .app bundle (default: build)",
    )
    parser.add_argument(
        "--sign",
        default="-",
        metavar="IDENTITY",
        help="code-signing identity; '-' uses an ad-hoc signature (default: '-')",
    )
    args = parser.parse_args()

    output_directory = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    output_directory.mkdir(parents=True, exist_ok=True)
    app_directory = build_app(args.configuration, output_directory, args.sign)

    print(f"Created {app_directory}")
    print("Install it by dragging the .app bundle to /Applications.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, OSError, subprocess.CalledProcessError) as error:
        print(f"build-app: error: {error}", file=sys.stderr)
        sys.exit(1)
