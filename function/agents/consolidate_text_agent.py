import logging
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .parse_text_agent import AgentState

def consolidate_text_agent(state: AgentState) -> AgentState:
    """Consolidate text with synonyms and generate PDF"""
    text = state.get("text", "")
    synonyms = state.get("synonyms", {})
    
    # Apply synonym enhancements
    enhanced_text = text
    for word, synonym_list in synonyms.items():
        if synonym_list:
            enhanced_text = enhanced_text.replace(word, synonym_list[0])
    
    state["enhanced_text"] = enhanced_text
    
    # Generate PDF
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph("Enhanced Text Document", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Original text section
        orig_title = Paragraph("Original Text:", styles['Heading2'])
        story.append(orig_title)
        orig_para = Paragraph(text, styles['Normal'])
        story.append(orig_para)
        story.append(Spacer(1, 12))
        
        # Enhanced text section
        enh_title = Paragraph("Enhanced Text:", styles['Heading2'])
        story.append(enh_title)
        enh_para = Paragraph(enhanced_text, styles['Normal'])
        story.append(enh_para)
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Convert to base64 for response
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        state["pdf_content"] = pdf_base64
        
        logging.info("PDF generated successfully")
        
    except Exception as e:
        logging.error(f"PDF generation failed: {str(e)}")
        state["pdf_content"] = ""
    
    return state