import base64
import pyperclip

def pdf_to_base64(file_path):
    """
    Convert a PDF file to a Base64-encoded string.

    :param file_path: Path to the PDF file.
    :return: Base64-encoded string of the PDF content.
    """
    try:
        with open(file_path, "rb") as pdf_file:
            # Read the PDF file as binary
            pdf_data = pdf_file.read()
            # Encode the binary data to Base64
            encoded_data = base64.b64encode(pdf_data).decode("utf-8")
            return encoded_data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"Error: {e}")

# Example usage
if __name__ == "__main__":
    pdf_path = "/Users/ivan/Desktop/typechart.png"  # Replace with your PDF file path
    base64_string = pdf_to_base64(pdf_path)
    if base64_string:
        # Copy Base64 string to clipboard
        pyperclip.copy(base64_string)
        print("Base64 encoded string copied to clipboard!")
