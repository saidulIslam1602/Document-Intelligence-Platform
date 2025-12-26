"""
Azure Form Recognizer Service
Advanced document analysis and data extraction using Azure Form Recognizer
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import DomainEvent, EventType, EventBus
from ...shared.rate_limiting import form_recognizer_rate_limit

class FormRecognizerService:
    """Azure Form Recognizer service for document analysis"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize Form Recognizer client
        self.client = DocumentAnalysisClient(
            endpoint=self.config.form_recognizer_endpoint,
            credential=AzureKeyCredential(self.config.form_recognizer_key)
        )
        
        # Supported document types and their models
        self.document_models = {
            "invoice": "prebuilt-invoice",
            "receipt": "prebuilt-receipt",
            "business_card": "prebuilt-businessCard",
            "id_document": "prebuilt-idDocument",
            "tax_document": "prebuilt-tax.us.w2",
            "general": "prebuilt-document",
            "layout": "prebuilt-layout"
        }
    
    @form_recognizer_rate_limit
    async def analyze_document(self, document_content: bytes, 
                             model_type: str = "general") -> Dict[str, Any]:
        """
        Analyze document using specified model
        Rate limited to prevent quota exhaustion
        """
        try:
            model = self.document_models.get(model_type, "prebuilt-document")
            
            # Run analysis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            poller = await loop.run_in_executor(
                None,
                lambda: self.client.begin_analyze_document(model, document_content)
            )
            
            result = await loop.run_in_executor(None, lambda: poller.result())
            
            return await self._process_analysis_result(result, model_type)
            
        except ResourceNotFoundError as e:
            self.logger.error(f"Form Recognizer model not found: {str(e)}")
            raise
        except ServiceRequestError as e:
            self.logger.error(f"Form Recognizer service error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error analyzing document: {str(e)}")
            raise
    
    async def extract_text(self, document_content: bytes) -> Dict[str, Any]:
        """Extract text from document"""
        try:
            result = await self.analyze_document(document_content, "general")
            
            return {
                "text": result.get("content", ""),
                "paragraphs": result.get("paragraphs", []),
                "lines": result.get("lines", []),
                "words": result.get("words", []),
                "confidence": result.get("confidence", 0.0),
                "page_count": result.get("page_count", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting text: {str(e)}")
            raise
    
    async def extract_tables(self, document_content: bytes) -> List[Dict[str, Any]]:
        """Extract tables from document"""
        try:
            result = await self.analyze_document(document_content, "layout")
            
            tables = []
            for table in result.get("tables", []):
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [],
                    "confidence": table.confidence
                }
                
                for cell in table.cells:
                    cell_data = {
                        "content": cell.content,
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "confidence": cell.confidence,
                        "is_header": cell.kind == "columnHeader" if hasattr(cell, 'kind') else False
                    }
                    table_data["cells"].append(cell_data)
                
                tables.append(table_data)
            
            return tables
            
        except Exception as e:
            self.logger.error(f"Error extracting tables: {str(e)}")
            raise
    
    async def extract_key_value_pairs(self, document_content: bytes) -> List[Dict[str, Any]]:
        """Extract key-value pairs from document"""
        try:
            result = await self.analyze_document(document_content, "layout")
            
            key_value_pairs = []
            for kvp in result.get("key_value_pairs", []):
                pair_data = {
                    "key": kvp.key.content if kvp.key else "",
                    "value": kvp.value.content if kvp.value else "",
                    "confidence": kvp.confidence,
                    "key_confidence": kvp.key.confidence if kvp.key else 0.0,
                    "value_confidence": kvp.value.confidence if kvp.value else 0.0
                }
                key_value_pairs.append(pair_data)
            
            return key_value_pairs
            
        except Exception as e:
            self.logger.error(f"Error extracting key-value pairs: {str(e)}")
            raise
    
    async def analyze_invoice(self, document_content: bytes) -> Dict[str, Any]:
        """Analyze invoice document"""
        try:
            result = await self.analyze_document(document_content, "invoice")
            
            invoice_data = {
                "vendor_name": "",
                "vendor_address": "",
                "customer_name": "",
                "customer_address": "",
                "invoice_date": "",
                "due_date": "",
                "invoice_number": "",
                "total_amount": 0.0,
                "tax_amount": 0.0,
                "subtotal": 0.0,
                "line_items": [],
                "confidence": 0.0
            }
            
            # Extract fields from invoice
            if "fields" in result:
                fields = result["fields"]
                
                # Basic invoice information
                if "VendorName" in fields:
                    invoice_data["vendor_name"] = fields["VendorName"].value
                if "VendorAddress" in fields:
                    invoice_data["vendor_address"] = fields["VendorAddress"].value
                if "CustomerName" in fields:
                    invoice_data["customer_name"] = fields["CustomerName"].value
                if "CustomerAddress" in fields:
                    invoice_data["customer_address"] = fields["CustomerAddress"].value
                if "InvoiceDate" in fields:
                    invoice_data["invoice_date"] = fields["InvoiceDate"].value
                if "DueDate" in fields:
                    invoice_data["due_date"] = fields["DueDate"].value
                if "InvoiceNumber" in fields:
                    invoice_data["invoice_number"] = fields["InvoiceNumber"].value
                
                # Financial information
                if "InvoiceTotal" in fields:
                    invoice_data["total_amount"] = float(fields["InvoiceTotal"].value) if fields["InvoiceTotal"].value else 0.0
                if "TotalTax" in fields:
                    invoice_data["tax_amount"] = float(fields["TotalTax"].value) if fields["TotalTax"].value else 0.0
                if "SubTotal" in fields:
                    invoice_data["subtotal"] = float(fields["SubTotal"].value) if fields["SubTotal"].value else 0.0
                
                # Line items
                if "Items" in fields:
                    for item in fields["Items"].value:
                        line_item = {
                            "description": item.value.get("Description", "").value if item.value.get("Description") else "",
                            "quantity": float(item.value.get("Quantity", "").value) if item.value.get("Quantity") and item.value.get("Quantity").value else 0.0,
                            "unit_price": float(item.value.get("UnitPrice", "").value) if item.value.get("UnitPrice") and item.value.get("UnitPrice").value else 0.0,
                            "total_price": float(item.value.get("TotalPrice", "").value) if item.value.get("TotalPrice") and item.value.get("TotalPrice").value else 0.0
                        }
                        invoice_data["line_items"].append(line_item)
                
                # Overall confidence
                invoice_data["confidence"] = result.get("confidence", 0.0)
            
            return invoice_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing invoice: {str(e)}")
            raise
    
    async def analyze_receipt(self, document_content: bytes) -> Dict[str, Any]:
        """Analyze receipt document"""
        try:
            result = await self.analyze_document(document_content, "receipt")
            
            receipt_data = {
                "merchant_name": "",
                "merchant_address": "",
                "transaction_date": "",
                "transaction_time": "",
                "total_amount": 0.0,
                "tax_amount": 0.0,
                "tip_amount": 0.0,
                "items": [],
                "confidence": 0.0
            }
            
            # Extract fields from receipt
            if "fields" in result:
                fields = result["fields"]
                
                if "MerchantName" in fields:
                    receipt_data["merchant_name"] = fields["MerchantName"].value
                if "MerchantAddress" in fields:
                    receipt_data["merchant_address"] = fields["MerchantAddress"].value
                if "TransactionDate" in fields:
                    receipt_data["transaction_date"] = fields["TransactionDate"].value
                if "TransactionTime" in fields:
                    receipt_data["transaction_time"] = fields["TransactionTime"].value
                if "Total" in fields:
                    receipt_data["total_amount"] = float(fields["Total"].value) if fields["Total"].value else 0.0
                if "TotalTax" in fields:
                    receipt_data["tax_amount"] = float(fields["TotalTax"].value) if fields["TotalTax"].value else 0.0
                if "Tip" in fields:
                    receipt_data["tip_amount"] = float(fields["Tip"].value) if fields["Tip"].value else 0.0
                
                # Items
                if "Items" in fields:
                    for item in fields["Items"].value:
                        item_data = {
                            "name": item.value.get("Name", "").value if item.value.get("Name") else "",
                            "quantity": float(item.value.get("Quantity", "").value) if item.value.get("Quantity") and item.value.get("Quantity").value else 0.0,
                            "price": float(item.value.get("Price", "").value) if item.value.get("Price") and item.value.get("Price").value else 0.0,
                            "total_price": float(item.value.get("TotalPrice", "").value) if item.value.get("TotalPrice") and item.value.get("TotalPrice").value else 0.0
                        }
                        receipt_data["items"].append(item_data)
                
                receipt_data["confidence"] = result.get("confidence", 0.0)
            
            return receipt_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing receipt: {str(e)}")
            raise
    
    async def detect_document_type(self, document_content: bytes) -> Dict[str, Any]:
        """
        Optimized document type detection using single API call + heuristics
        Reduces from 7 API calls to 1-2 (85% cost reduction)
        """
        try:
            # Step 1: Single API call to layout model (extracts all text and structure)
            layout_result = await self.analyze_document(document_content, "layout")
            
            # Step 2: Extract text content for heuristic analysis
            text_content = layout_result.get("content", "").lower()
            
            # Step 3: Use heuristics to determine document type
            detected_type, confidence = self._classify_document_by_heuristics(
                text_content,
                layout_result
            )
            
            # Step 4: Optionally validate with specific model if confidence is medium
            # (only if we need higher accuracy - adds 1 more API call)
            if 0.6 <= confidence < 0.85 and detected_type != "general":
                try:
                    # Verify with specific model
                    specific_result = await self.analyze_document(document_content, detected_type)
                    specific_confidence = specific_result.get("confidence", 0.0)
                    
                    # Use higher confidence
                    if specific_confidence > confidence:
                        confidence = specific_confidence
                        
                except Exception:
                    # If specific model fails, stick with heuristic result
                    pass
            
            self.logger.info(
                f"Document type detected: {detected_type} "
                f"(confidence: {confidence:.2%}, API calls: 1-2 vs 7)"
            )
            
            return {
                "detected_types": [{
                    "type": detected_type,
                    "confidence": confidence,
                    "model": self.document_models.get(detected_type, "prebuilt-document")
                }],
                "primary_type": detected_type,
                "primary_confidence": confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting document type: {str(e)}")
            raise
    
    def _classify_document_by_heuristics(
        self,
        text_content: str,
        layout_result: Dict[str, Any]
    ) -> tuple[str, float]:
        """
        Classify document using text pattern matching and heuristics
        Fast, no API calls required
        
        Returns:
            (document_type, confidence)
        """
        # Invoice keywords and patterns
        invoice_keywords = [
            "invoice", "bill to", "invoice number", "invoice date",
            "amount due", "total amount", "subtotal", "tax amount",
            "payment terms", "due date", "remittance", "vendor"
        ]
        
        # Receipt keywords and patterns
        receipt_keywords = [
            "receipt", "thank you for your purchase", "cashier",
            "transaction", "payment method", "card ending", "merchant",
            "store #", "terminal", "cash"
        ]
        
        # Business card keywords
        business_card_keywords = [
            "tel:", "phone:", "mobile:", "email:", "fax:",
            "linkedin", "twitter", "website:", "www.",
            "ceo", "manager", "director", "president", "vp"
        ]
        
        # ID document keywords
        id_keywords = [
            "driver license", "driver's license", "passport",
            "identification", "id number", "date of birth", "dob",
            "nationality", "issued by", "expiration date", "expires"
        ]
        
        # Tax document keywords
        tax_keywords = [
            "w-2", "w2", "form 1099", "1099", "tax year",
            "employer identification", "ein", "social security",
            "federal income", "state income", "irs"
        ]
        
        # Count keyword matches for each type
        scores = {
            "invoice": self._count_keywords(text_content, invoice_keywords),
            "receipt": self._count_keywords(text_content, receipt_keywords),
            "business_card": self._count_keywords(text_content, business_card_keywords),
            "id_document": self._count_keywords(text_content, id_keywords),
            "tax_document": self._count_keywords(text_content, tax_keywords)
        }
        
        # Additional heuristics based on document structure
        table_count = len(layout_result.get("tables", []))
        word_count = len(text_content.split())
        
        # Business cards are typically short
        if word_count < 50 and scores["business_card"] >= 2:
            scores["business_card"] += 3
        
        # Invoices and receipts typically have tables
        if table_count > 0:
            scores["invoice"] += 2
            scores["receipt"] += 1
        
        # Find best match
        if not scores or max(scores.values()) == 0:
            # No clear match, use general model
            return "general", 0.5
        
        best_type = max(scores.items(), key=lambda x: x[1])
        document_type = best_type[0]
        keyword_count = best_type[1]
        
        # Calculate confidence based on keyword matches
        # More matches = higher confidence
        if keyword_count >= 5:
            confidence = 0.95
        elif keyword_count >= 3:
            confidence = 0.85
        elif keyword_count >= 2:
            confidence = 0.75
        elif keyword_count >= 1:
            confidence = 0.65
        else:
            confidence = 0.50
            document_type = "general"
        
        return document_type, confidence
    
    def _count_keywords(self, text: str, keywords: list[str]) -> int:
        """Count how many keywords appear in text"""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count
    
    async def _process_analysis_result(self, result, model_type: str) -> Dict[str, Any]:
        """Process Form Recognizer analysis result"""
        try:
            processed_result = {
                "model_used": self.document_models.get(model_type, "prebuilt-document"),
                "page_count": len(result.pages) if result.pages else 0,
                "confidence": 0.0,
                "content": "",
                "paragraphs": [],
                "lines": [],
                "words": [],
                "tables": [],
                "key_value_pairs": [],
                "fields": {},
                "pages": []
            }
            
            # Extract content
            if hasattr(result, 'content') and result.content:
                processed_result["content"] = result.content
            
            # Process pages
            if result.pages:
                for page in result.pages:
                    page_data = {
                        "page_number": page.page_number,
                        "width": page.width,
                        "height": page.height,
                        "unit": page.unit,
                        "lines": [],
                        "words": []
                    }
                    
                    # Extract lines and words
                    if hasattr(page, 'lines'):
                        for line in page.lines:
                            line_data = {
                                "content": line.content,
                                "bounding_box": line.bounding_box,
                                "confidence": line.confidence
                            }
                            page_data["lines"].append(line_data)
                            processed_result["lines"].append(line_data)
                    
                    if hasattr(page, 'words'):
                        for word in page.words:
                            word_data = {
                                "content": word.content,
                                "bounding_box": word.bounding_box,
                                "confidence": word.confidence
                            }
                            page_data["words"].append(word_data)
                            processed_result["words"].append(word_data)
                    
                    processed_result["pages"].append(page_data)
            
            # Process paragraphs
            if hasattr(result, 'paragraphs'):
                for paragraph in result.paragraphs:
                    paragraph_data = {
                        "content": paragraph.content,
                        "bounding_box": paragraph.bounding_box,
                        "confidence": paragraph.confidence
                    }
                    processed_result["paragraphs"].append(paragraph_data)
            
            # Process tables
            if hasattr(result, 'tables'):
                for table in result.tables:
                    table_data = {
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": [],
                        "confidence": table.confidence
                    }
                    
                    for cell in table.cells:
                        cell_data = {
                            "content": cell.content,
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "confidence": cell.confidence
                        }
                        table_data["cells"].append(cell_data)
                    
                    processed_result["tables"].append(table_data)
            
            # Process key-value pairs
            if hasattr(result, 'key_value_pairs'):
                for kvp in result.key_value_pairs:
                    kvp_data = {
                        "key": kvp.key.content if kvp.key else "",
                        "value": kvp.value.content if kvp.value else "",
                        "confidence": kvp.confidence
                    }
                    processed_result["key_value_pairs"].append(kvp_data)
            
            # Process fields (for prebuilt models)
            if hasattr(result, 'fields'):
                for field_name, field_value in result.fields.items():
                    processed_result["fields"][field_name] = {
                        "value": field_value.value if field_value else None,
                        "confidence": field_value.confidence if field_value else 0.0
                    }
            
            # Calculate overall confidence
            confidences = []
            if processed_result["lines"]:
                confidences.extend([line["confidence"] for line in processed_result["lines"]])
            if processed_result["words"]:
                confidences.extend([word["confidence"] for word in processed_result["words"]])
            if processed_result["tables"]:
                confidences.extend([table["confidence"] for table in processed_result["tables"]])
            
            if confidences:
                processed_result["confidence"] = sum(confidences) / len(confidences)
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            raise