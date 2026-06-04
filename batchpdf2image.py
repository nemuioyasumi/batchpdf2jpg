import os
import platform
import shutil
import subprocess
from pathlib import Path
from pdf2image import convert_from_path
from tqdm import tqdm

custom_dpi = 200
jpeg_quality = 95


def ensure_poppler_installed():
    if shutil.which("pdftoppm"):
        return None

    system = platform.system().lower()
    print("pdftoppm not found in PATH. poppler is required by pdf2image.\n")

    if system == "darwin":
        if not shutil.which("brew"):
            raise RuntimeError(
                "Homebrew not found. Install it from https://brew.sh, then run: brew install poppler"
            )
        cmd = ["brew", "install", "poppler"]
    elif system == "linux":
        if shutil.which("apt-get"):
            cmd = ["sudo", "apt-get", "install", "-y", "poppler-utils"]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "install", "-y", "poppler-utils"]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-S", "--noconfirm", "poppler"]
        else:
            raise RuntimeError(
                "No supported package manager found (apt/dnf/pacman). Install poppler manually."
            )
    elif system == "windows":
        if shutil.which("choco"):
            cmd = ["choco", "install", "-y", "poppler"]
        elif shutil.which("winget"):
            cmd = ["winget", "install", "--id", "oschwartz10612.Poppler", "--accept-package-agreements"]
        else:
            raise RuntimeError(
                "On Windows, install poppler manually:\n"
                "  choco install poppler\n"
                "  winget install oschwartz10612.Poppler\n"
                "  or download from https://github.com/oschwartz10612/poppler-windows/releases"
            )
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

    print(f"About to run: {' '.join(cmd)}")
    if input("Proceed? [y/N] ").strip().lower() != "y":
        raise RuntimeError("poppler installation cancelled.")

    subprocess.run(cmd, check=True)

    if not shutil.which("pdftoppm"):
        raise RuntimeError(
            "poppler installed but pdftoppm is still not on PATH. "
            "Open a new terminal and rerun, or add the poppler bin directory to PATH manually."
        )

    return None


def convert_local_pdfs_with_custom_naming():
    ensure_poppler_installed()

    script_folder = Path(__file__).parent.resolve()
    pdf_files = [p for p in script_folder.glob("*.pdf") if p.is_file()]

    if not pdf_files:
        print(f"No PDFs found in: {script_folder}")
        return

    print(f"Starting conversion for {len(pdf_files)} file(s)...\n")
    thread_count = os.cpu_count() or 2

    for pdf_path in tqdm(pdf_files, desc="Overall Progress"):
        pdf_name = pdf_path.stem
        output_folder = script_folder / pdf_name

        if output_folder.is_file():
            print(f"\n[!] Cannot create folder: '{output_folder}' exists as a file. Skipping.")
            continue
        output_folder.mkdir(exist_ok=True)

        if any(output_folder.glob(f"{pdf_name}_*.jpg")):
            print(f"\nSkipping {pdf_name} (already converted).")
            continue

        try:
            images = convert_from_path(str(pdf_path), dpi=custom_dpi, thread_count=thread_count)
            width = len(str(len(images)))

            for i, image in enumerate(tqdm(images, desc=f" -> {pdf_name}", unit="pg", leave=False)):
                image_filename = f"{pdf_name}_{str(i + 1).zfill(width)}.jpg"
                image_path = output_folder / image_filename
                try:
                    image.save(image_path, "JPEG", quality=jpeg_quality)
                except KeyboardInterrupt:
                    image.close()
                    image_path.unlink(missing_ok=True)
                    raise
                finally:
                    image.close()

        except Exception as e:
            print(f"\n[!] Error processing {pdf_name}: {e}")


if __name__ == "__main__":
    convert_local_pdfs_with_custom_naming()
    print("\nConversion complete! Check your folders.")
