"""Quick test to check Google Cloud configuration"""
import os
import sys

print("="*60)
print("Google Cloud Configuration Check")
print("="*60)

# Check 1: Environment variables
print("\n1. Checking environment variables...")
gcp_project = os.environ.get("GCP_PROJECT_ID")
gcp_region = os.environ.get("GCP_REGION", "us-central1")
gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")

if gcp_project and gcp_project != "your-project-id-here":
    print(f"   ✓ GCP_PROJECT_ID: {gcp_project}")
else:
    print(f"   ✗ GCP_PROJECT_ID not configured in .env file")
    
print(f"   ✓ GCP_REGION: {gcp_region}")
print(f"   ✓ GEMINI_MODEL: {gemini_model}")

# Check 2: Google Auth
print("\n2. Checking Google Cloud authentication...")
try:
    import google.auth
    credentials, project = google.auth.default()
    print(f"   ✓ Authentication configured")
    print(f"   ✓ Project from credentials: {project}")
    
    if gcp_project and gcp_project != "your-project-id-here":
        if project == gcp_project:
            print(f"   ✓ Project matches .env configuration")
        else:
            print(f"   ⚠ Warning: Credential project ({project}) differs from .env ({gcp_project})")
    
except Exception as e:
    print(f"   ✗ Authentication not configured")
    print(f"   Error: {e}")
    print(f"\n   Fix: Run 'gcloud auth application-default login'")

# Check 3: Vertex AI availability
print("\n3. Checking Vertex AI access...")
try:
    import vertexai
    
    if gcp_project and gcp_project != "your-project-id-here":
        vertexai.init(project=gcp_project, location=gcp_region)
        print(f"   ✓ Vertex AI initialized for project: {gcp_project}")
        print(f"   ✓ Region: {gcp_region}")
    else:
        print(f"   ⚠ Cannot test - GCP_PROJECT_ID not configured")
        
except Exception as e:
    print(f"   ✗ Vertex AI initialization failed")
    print(f"   Error: {e}")

# Summary
print("\n" + "="*60)
print("Configuration Summary")
print("="*60)

if gcp_project and gcp_project != "your-project-id-here":
    try:
        import google.auth
        credentials, project = google.auth.default()
        print("\n✅ Configuration looks good!")
        print("\nYou should be able to use the chat endpoint now.")
        print("\nRestart the server with:")
        print("  python main_server.py")
    except:
        print("\n⚠️ Partial configuration")
        print("\nNext steps:")
        print("  1. Install Google Cloud SDK")
        print("  2. Run: gcloud auth application-default login")
        print("  3. Run: gcloud config set project " + gcp_project)
        print("\nSee GOOGLE_CLOUD_SETUP.md for detailed instructions")
else:
    print("\n❌ Not configured")
    print("\nNext steps:")
    print("  1. Copy .env.template to .env")
    print("  2. Edit .env and set your GCP_PROJECT_ID")
    print("  3. Follow steps in GOOGLE_CLOUD_SETUP.md")

print("\n" + "="*60)
