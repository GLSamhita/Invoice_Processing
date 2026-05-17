import os
import pdfplumber
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from google import generativeai as genai
from pdf2image import convert_from_path
from PIL import Image

from validation import validate_invoice

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
app = FastAPI()
model = genai.GenerativeModel("gemini-2.5-flash")

# LOAD API AT - http://127.0.0.1:8000/docs 

def extract_text_from_pdf(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text

@app.post("/extract")
async def extract_invoice(file: UploadFile = File(...)):

    try:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        raw_text = extract_text_from_pdf(temp_path)
        print("\n--- RAW TEXT ---\n")
        print(raw_text)

        prompt = f"""
        Extract invoice details from this invoice text.

        Return ONLY valid JSON.

        Fields:
        - subtotal
        - discount
        - taxable_amount
        - tax_amount
        - cgst
        - sgst
        - igst
        - total_amount

        If any field does not have a value, use 'null'

        Invoice text:
        {raw_text}
        """

        if len(raw_text.strip()) > 50: # Digitally generated invoice
            print("\n--- DIGITAL PDF DETECTED ---\n")
            
            prompt = f"""
            Extract invoice details from this invoice text.

            The PDF may contain one or more invoices.

            Return ONLY valid JSON.

            Output format:
            {{
            "invoices": [
                {{
                "vendor_name": null,
                "gstin": null,
                "pan": null,
                "invoice_number": null,
                "invoice_date": null,
                "due_date": null,
                "subtotal": null,
                "discount": null,
                "taxable_amount": null,
                "tax_amount": null,
                "cgst": null,
                "sgst": null,
                "igst": null,
                "total_amount": null
                }}
            ]
            }}

            Rules:
            - Each invoice must be a separate object
            - Use snake_case keys
            - Monetary values must be numeric
            - If any field is unavailable, return null
            - Return ONLY JSON and nothing else

            Invoice text:
            {raw_text}
            """
            response = model.generate_content(prompt)

        else: # Scanned invoice
            print("\n--- SCANNED PDF DETECTED ---\n")
            pages = convert_from_path(temp_path)

            image_inputs = []

            for page in pages:
                image_inputs.append(page)

            response = model.generate_content([
                """
                The uploaded PDF may contain MULTIPLE invoices.

                Detect every invoice separately across all pages.

                Return ONLY valid JSON.

                Output format:
                {
                "invoices": [
                    {
                    "vendor_name": null,
                    "gstin": null,
                    "pan": null,
                    "invoice_number": null,
                    "invoice_date": null,
                    "due_date": null,
                    "subtotal": null,
                    "discount": null,
                    "taxable_amount": null,
                    "tax_amount": null,
                    "cgst": null,
                    "sgst": null,
                    "igst": null,
                    "total_amount": null
                    }
                ]
                }

                Rules:
                - Each invoice must be a separate object
                - Do not merge invoices together
                - If a page belongs to the same invoice, combine its data
                - If a new invoice starts, create a new object
                - Monetary values must be numeric
                - Use snake_case keys
                - If any field is unavailable, return null
                - Return ONLY JSON and nothing else
                """,
                *image_inputs
            ])

        os.remove(temp_path)

        cleaned_response = (response.text.replace("```json", "").replace("```", "").strip())
        parsed_json = json.loads(cleaned_response)
        # flags = validate_invoice(parsed_json) #calling the validation function
        all_flags = []

        for invoice in parsed_json["invoices"]:
            flags = validate_invoice(invoice)
            all_flags.append({
                "invoice_number": invoice.get("invoice_number"),
                "flags": flags
            })

        return {
            "success": True,
            "data": parsed_json,
            "flags": all_flags
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }