from app import create_app
import sys

# Set stdout encoding
sys.stdout.reconfigure(encoding='utf-8')

app = create_app()
with app.app_context():
    rules = [str(r) for r in app.url_map.iter_rules()]
    print("=== Registered Routes ===")
    for rule in sorted(rules):
        if "profiles" in rule or "action-prediction" in rule:
            print(f"FOUND: {rule}")
    print("=== End Routes ===")
