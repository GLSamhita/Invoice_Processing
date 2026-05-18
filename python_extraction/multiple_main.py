import os
import json
import pdfplumber
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from google import generativeai as genai
from pdf2image import convert_from_path
from openpyxl import Workbook
from datetime import datetime

from validation import validate_invoice

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") #set as system variable
genai.configure(api_key=api_key)
app = FastAPI()
model = genai.GenerativeModel("gemini-2.5-flash")

def extract_text_from_pdf(pdf_path): #checking if any text can be extracted from the PDF
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

#expense classification - CapEx or OpEx (includes only a few categories)
EXPENSE_CLASSIFICATION = {
    "CapEx": {
        "Computer Equipment": ["laptop", "desktop", "monitor","printer", "server", "hardware"],
        "Furniture & Fixtures": ["chair", "desk", "table", "furniture"]
    },
    "OpEx": {
        "Travel Expense": ["flight", "hotel", "uber", "ola", "cab"],
        "Software Subscription": ["subscription", "saas", "cloud","zoom", "slack", "adobe"],
        "Office Expenses": ["stationery", "office supplies", "paper","pen"]
    }
}

def classify_invoice(invoice):
    text = " ".join([
        str(invoice.get("vendor_name", "")),
        str(invoice.get("description", "")),
        str(invoice.get("invoice_number", ""))
    ]).lower()
    for expense_type, categories in EXPENSE_CLASSIFICATION.items():
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return {
                    "expense_type": expense_type
                }

    return {
        "expense_type": "OpEx (miscellaneous)"
    }

# Single PDF processing
def process_invoice_pdf(temp_path):
    raw_text = extract_text_from_pdf(temp_path)

    print("\n--- RAW TEXT ---\n")
    print(raw_text)

    if len(raw_text.strip()) > 50: #digitally generated invoice PDF, considers text
        print("\n--- DIGITALLY GENERATED INVOICE ---\n")
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
              "total_amount": null,
              "expense_type": null
            }}
          ]
        }}
        Rules:
        - Each invoice must be separate
        - Monetary values must be numeric
        - Use snake_case keys
        - If unavailable return null
        - Return ONLY JSON

        Invoice text:
        {raw_text}
        """
        response = model.generate_content(prompt)

    else: #scanned invoice PDF, considers images
        print("\n--- SCANNED INVOICE ---\n")
        pages = convert_from_path(temp_path)
        response = model.generate_content([
            """
            The uploaded PDF may contain MULTIPLE invoices.
            Detect every invoice separately.
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
                  "total_amount": null,
                  "expense_type":null
                }
              ]
            }
            """,
            *pages
        ])

    cleaned_response = (response.text.replace("```json", "").replace("```", "").strip())
    parsed_json = json.loads(cleaned_response)

    #validating the extracted information per pdf
    all_flags = []
    for invoice in parsed_json["invoices"]:
        flags = validate_invoice(invoice)
        classification = classify_invoice(invoice)
        invoice["expense_type"] = classification["expense_type"]
        all_flags.append({
            "invoice_number": invoice.get("invoice_number"),
            "flags": flags
        })

    return {
        "data": parsed_json,
        "flags": all_flags
    }

def save_results_to_excel(results):
    os.makedirs("exports", exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    headers = [
        "pdf_file_name",
        "vendor_name",
        "gstin",
        "pan",
        "invoice_number",
        "invoice_date",
        "due_date",
        "subtotal",
        "discount",
        "taxable_amount",
        "tax_amount",
        "cgst",
        "sgst",
        "igst",
        "total_amount",
        "flags",
        "expense_type"
    ]
    ws.append(headers)

    for result in results:
        file_name = result["file_name"]
        invoices = result["result"]["data"]["invoices"]
        flags_data = result["result"]["flags"]
        flags_map = {} # Create invoice_number -> flags mapping
        for item in flags_data:
            invoice_number = item.get("invoice_number")
            flags = item.get("flags", [])
            flags_map[invoice_number] = flags

        for invoice in invoices:
            invoice_number = invoice.get("invoice_number")
            invoice_flags = flags_map.get(invoice_number, [])
            row = [
                file_name,
                invoice.get("vendor_name"),
                invoice.get("gstin"),
                invoice.get("pan"),
                invoice.get("invoice_number"),
                invoice.get("invoice_date"),
                invoice.get("due_date"),
                invoice.get("subtotal"),
                invoice.get("discount"),
                invoice.get("taxable_amount"),
                invoice.get("tax_amount"),
                invoice.get("cgst"),
                invoice.get("sgst"),
                invoice.get("igst"),
                invoice.get("total_amount"),
                invoice.get("expense_type"),
                json.dumps(invoice_flags)
            ]
            ws.append(row)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file_path = f"exports/invoice_results_{timestamp}.xlsx"
    wb.save(excel_file_path)

    return excel_file_path

# API to take input of multiple files
@app.post("/extract")
async def extract_invoice(files: List[UploadFile] = File(...)):
    try:
        final_results = []
        for file in files:
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as f:
                f.write(await file.read())

            result = process_invoice_pdf(temp_path)
            final_results.append({
                "file_name": file.filename,
                "result": result
            })
            os.remove(temp_path)
        
        # Save Excel file
        excel_file_path = save_results_to_excel(final_results)

        return {
            "success": True,
            "total_files": len(files),
            "excel_file": excel_file_path,
            "results": final_results
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }