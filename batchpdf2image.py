from pathlib import Path
from pdf2image import convert_from_path
from tqdm import tqdm

custom_dpi = 200

def convert_local_pdfs_with_custom_naming():
    # 1. Locate the folder where this script is saved
    script_folder = Path(__file__).parent.resolve()
    
    # 2. Grab all PDF files in that folder
    pdf_files = list(script_folder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in: {script_folder}")
        return

    print(f"Starting conversion for {len(pdf_files)} file(s)...\n")

    for pdf_path in tqdm(pdf_files, desc="Overall Progress"):
        # The 'stem' is the filename without the '.pdf' extension
        pdf_name = pdf_path.stem 
        output_folder = script_folder / pdf_name
        
        if not output_folder.exists():
            output_folder.mkdir(exist_ok=True)

        try:
            # 3. Convert PDF to images
            images = convert_from_path(str(pdf_path), dpi= custom_dpi, thread_count=4)

            # 4. Save with custom naming: {pdf_name}_{page_number}.jpg
            for i, image in enumerate(tqdm(images, desc=f" -> {pdf_name}", unit="pg", leave=False)):
                # This line creates your specific naming format
                image_filename = f"{pdf_name}_{i + 1}.jpg"
                
                image.save(output_folder / image_filename, "JPEG")
        
        except Exception as e:
            print(f"\n[!] Error processing {pdf_name}: {e}")

if __name__ == "__main__":
    convert_local_pdfs_with_custom_naming()
    print("\nConversion complete! Check your folders.")