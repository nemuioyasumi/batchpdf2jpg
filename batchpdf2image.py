import os
import platform
import shutil
import subprocess
from pathlib import Path
from pdf2image import convert_from_path
from tqdm import tqdm

custom_dpi = 200

JPG_PRESETS = {
    "low":    {"quality": 60},
    "medium": {"quality": 80},
    "high":   {"quality": 92},
    "max":    {"quality": 100},
}

PNG_PRESETS = {
    "low":    {"compress_level": 9, "optimize": True},
    "medium": {"compress_level": 6, "optimize": True},
    "high":   {"compress_level": 3, "optimize": True},
    "max":    {"compress_level": 0, "optimize": False},
}


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


def parse_selection(raw, total):
    result = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a_s, b_s = part.split("-", 1)
            a, b = int(a_s), int(b_s)
            if not 1 <= a <= b <= total:
                raise ValueError(f"range {a}-{b} out of bounds 1-{total}")
            result.update(range(a, b + 1))
        else:
            n = int(part)
            if not 1 <= n <= total:
                raise ValueError(f"{n} out of bounds 1-{total}")
            result.add(n)
    return sorted(result)


def prompt_for_pdfs(pdf_files):
    if len(pdf_files) == 1:
        print(f"\nFound 1 PDF: {pdf_files[0].name}")
        return pdf_files

    print(f"\nFound {len(pdf_files)} PDF(s):")
    for i, p in enumerate(pdf_files, 1):
        print(f"  [{i}] {p.name}")
    print()

    while True:
        raw = input("Which PDFs to process? [all / numbers like 1,3 / range 1-2 / q to quit]: ").strip().lower()
        if raw in ("", "all"):
            return list(pdf_files)
        if raw in ("q", "quit", "exit"):
            return None
        try:
            indices = parse_selection(raw, len(pdf_files))
            return [pdf_files[i - 1] for i in indices]
        except ValueError as e:
            print(f"  Invalid: {e}")


def prompt_for_image_settings():
    print("\nImage format:")
    print("  [1] JPG (smaller files, lossy) [default]")
    print("  [2] PNG (lossless, larger files)")
    fmt_choice = input("Choice [1]: ").strip()
    is_png = fmt_choice == "2"

    if is_png:
        print("\nPNG preset:")
        print("  [1] Low    (max compression, smallest file, slowest encode)")
        print("  [2] Medium (balanced) [default]")
        print("  [3] High   (less compression, larger file, faster encode)")
        print("  [4] Max    (no compression, largest file, instant encode)")
        default_preset = "medium"
        presets = PNG_PRESETS
        ext = "png"
    else:
        print("\nJPG quality preset:")
        print("  [1] Low    (smallest files, visible artifacts)")
        print("  [2] Medium (balanced) [default]")
        print("  [3] High   (near-original fidelity, larger files)")
        print("  [4] Max    (visually lossless, largest files)")
        default_preset = "medium"
        presets = JPG_PRESETS
        ext = "jpg"

    raw = input(f"Choice [2]: ").strip()
    mapping = {"1": "low", "2": "medium", "3": "high", "4": "max"}
    preset_name = mapping.get(raw, default_preset)
    return ext, presets[preset_name]


def convert_local_pdfs_with_custom_naming():
    ensure_poppler_installed()

    script_folder = Path(__file__).parent.resolve()
    pdf_files = sorted([p for p in script_folder.glob("*.pdf") if p.is_file()])

    if not pdf_files:
        print(f"No PDFs found in: {script_folder}")
        return

    selected = prompt_for_pdfs(pdf_files)
    if selected is None:
        print("Cancelled.")
        return

    ext, save_kwargs = prompt_for_image_settings()

    print(f"\nStarting conversion for {len(selected)} file(s)...\n")
    thread_count = os.cpu_count() or 2

    for pdf_path in tqdm(selected, desc="Overall Progress"):
        pdf_name = pdf_path.stem
        output_folder = script_folder / pdf_name

        if output_folder.is_file():
            print(f"\n[!] Cannot create folder: '{output_folder}' exists as a file. Skipping.")
            continue
        output_folder.mkdir(exist_ok=True)

        if any(output_folder.glob(f"{pdf_name}_*.{ext}")):
            print(f"\nSkipping {pdf_name} (already converted).")
            continue

        try:
            images = convert_from_path(str(pdf_path), dpi=custom_dpi, thread_count=thread_count)
            width = len(str(len(images)))

            for i, image in enumerate(tqdm(images, desc=f" -> {pdf_name}", unit="pg", leave=False)):
                image_filename = f"{pdf_name}_{str(i + 1).zfill(width)}.{ext}"
                image_path = output_folder / image_filename
                try:
                    image.save(image_path, **save_kwargs)
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
