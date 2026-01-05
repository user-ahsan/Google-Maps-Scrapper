from src import sheets_utils

def test_prune():
    print("Testing Prune...")
    client = sheets_utils.connect_to_sheets()
    if not client: return
    
    ws = sheets_utils.get_or_create_worksheet(client)
    
    # 1. Add a dummy duplicate
    print("Adding duplicate row...")
    ws.append_row(["Test Duplicate", "123 Fake St", "example.com", "example.com", "555-0199", "Test", "Test", "0", "0", "0", "0", "http://maps.google.com", "test", "now"])
    ws.append_row(["Test Duplicate", "123 Fake St", "example.com", "example.com", "555-0199", "Test", "Test", "0", "0", "0", "0", "http://maps.google.com", "test", "now"])
    
    # 2. Run Prune
    sheets_utils.prune_duplicates(ws)
    
    print("Done.")

if __name__ == "__main__":
    test_prune()
