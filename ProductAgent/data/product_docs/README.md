# Sample Product Documentation - README

This directory contains sample product specification documents for testing the Product Agent's RAG (Retrieval-Augmented Generation) capabilities.

## Purpose

These documents are used to:
1. Populate the ChromaDB vector database with product information
2. Test RAG query functionality
3. Demonstrate semantic search capabilities
4. Provide accurate source material for product questions

## Documents Included

### Fiber Products
- `fiber_1g_spec.txt` - Business Fiber 1 Gbps specifications
- `fiber_5g_spec.txt` - Business Fiber 5 Gbps specifications (to be added)
- `fiber_10g_spec.txt` - Business Fiber 10 Gbps specifications (to be added)

### Coax Products
- `coax_internet_guide.txt` - Business Coax Internet products (to be added)

### General Documentation
- `business_internet_guide.txt` - General business internet guide (to be added)
- `sla_terms.txt` - Service Level Agreement terms (to be added)

## Document Format

Each document follows this structure:
1. **Product Overview** - Basic product information
2. **Technical Specifications** - Detailed technical specs
3. **Service Features** - Core and optional features
4. **SLA Terms** - Service level guarantees
5. **Hardware Specifications** - Equipment details
6. **Installation** - Installation process and timeline
7. **Pricing** - Pricing and contract options
8. **Use Cases** - Ideal customers and applications
9. **FAQ** - Common questions

## Adding New Documents

To add new product documentation:

1. **Create the document** in this directory
2. **Follow the format** of existing documents
3. **Use clear sections** for easy chunking
4. **Include metadata** (Product ID, version, date)
5. **Run ingestion script** to add to ChromaDB

### Example Ingestion Script

```python
from product_agent.utils.vector_db import get_vector_db
import os

def ingest_document(filename, product_id):
    vector_db = get_vector_db()
    
    with open(f"./data/product_docs/{filename}", "r") as f:
        content = f.read()
    
    # Split into sections (simplified)
    sections = content.split("\n## ")
    
    documents = []
    metadatas = []
    
    for section in sections[1:]:  # Skip first split
        section_title = section.split("\n")[0]
        section_content = "\n".join(section.split("\n")[1:])
        
        documents.append(section_content)
        metadatas.append({
            "product_id": product_id,
            "source": filename,
            "section": section_title
        })
    
    vector_db.add_documents(documents, metadatas)
    print(f"Ingested {len(documents)} sections from {filename}")

# Run ingestion
ingest_document("fiber_1g_spec.txt", "FIB-1G")
```

## Document Maintenance

### When to Update
- New product releases
- Specification changes
- Price updates
- Feature additions
- SLA term changes

### Update Process
1. Update the text file
2. Re-run ingestion to update vector DB
3. Test queries to verify updates
4. Document changes in version history

## Testing with Documents

### Example Queries

Test the RAG system with these queries:

```python
from product_agent.tools.rag_tools import query_product_documentation

# Technical specs
result = query_product_documentation(
    "What is the upload speed of Fiber 1G?",
    product_id="FIB-1G"
)

# Features
result = query_product_documentation(
    "What features are included with Fiber 1G?",
    product_id="FIB-1G"
)

# SLA
result = query_product_documentation(
    "What is the uptime guarantee?",
    product_id="FIB-1G"
)

# Hardware
result = query_product_documentation(
    "What router is included with Fiber 1G?",
    product_id="FIB-1G"
)
```

## Document Quality Guidelines

### Writing Guidelines
1. **Be Specific**: Include exact numbers, not ranges
2. **Be Comprehensive**: Cover all aspects of the product
3. **Be Consistent**: Use consistent terminology
4. **Be Accurate**: Double-check all specifications
5. **Be Clear**: Write for both technical and non-technical audiences

### Format Guidelines
1. Use markdown headers (##, ###) for sections
2. Use bullet points (•, ✓) for lists
3. Use tables for comparisons
4. Include product ID in first section
5. Add version and date at bottom

## Troubleshooting

### Documents Not Found in Queries
- Check if document was ingested: `vector_db.get_collection_stats()`
- Verify product_id metadata matches query
- Try broader queries first

### Poor Query Results
- Improve document structure with clear sections
- Add more context to each section
- Use consistent terminology across documents
- Consider adding synonyms or alternative phrasings

## Future Enhancements

### Planned Additions
1. PDF support (convert PDFs to text)
2. Auto-ingestion on file change
3. Document versioning in metadata
4. Multi-language support
5. Image/diagram support

---

**Last Updated**: February 10, 2026  
**Maintained By**: Product Agent Development Team
