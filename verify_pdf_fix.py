
import os
import sys
# Add project root to sys.path
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch

# Build the mock chain BEFORE importing the module to avoid import-time issues or side effects if needed, 
# though here we just need to patch the calls inside the function.

# We will patch 'app.services.report_generator.get_dynamic_table' and 'app.services.report_generator.select'
# inside the test block.

from app.services.report_generator import generate_pdf_report

def run_test():
    # Mock DB session
    mock_db = MagicMock()
    
    # Create a dummy issue with the problematic character
    dummy_issue = {
        "dataset_name": "Test Dataset",
        "column_name": "Test Column",
        "issue": "Test Issue with ≈ symbol",  # <--- Problematic character checks
        "severity": "Critical",
        "original_value": "123",
        "corrected_value": "456",
        "ai_explanation": "Test explanation with ≈ symbol."
    }

    # Setup mock return values for the database result
    mock_row = MagicMock()
    # dict(i) in the code calls the iterator/conversion, simple way is to make the list items dicts
    # The code does: issues = db.execute(...).mappings().all() -> returns list of dict-like objects
    
    with patch("app.services.report_generator.get_dynamic_table") as mock_get_table, \
         patch("app.services.report_generator.select") as mock_select:
        
        mock_get_table.return_value = "mock_table"
        mock_select.return_value = "mock_statement"
        
        # db.execute("mock_statement").mappings().all() returns [dummy_issue]
        mock_execute_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = [dummy_issue]
        mock_execute_result.mappings.return_value = mock_mappings
        mock_db.execute.return_value = mock_execute_result
        
        print("Attempting to generate PDF with special characters...")
        try:
            tables = ["issues_test"]
            output_file = generate_pdf_report(tables, mock_db)
            print(f"Success! PDF generated at: {output_file}")
            
            # Verify file exists and is non-zero
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print("PDF file exists and has content.")
                # Cleanup
                os.remove(output_file)
                print("Cleanup successful.")
            else:
                print("PDF file missing or empty.")
                
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_test()
