"""
Authenticate with Google APIs and make a copy of the source report doc.
Saves token for future use so you only need to auth once.
"""
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]

CREDS_FILE = os.path.join(
    os.path.dirname(__file__),
    'client_secret_338926584320-nqv51hnagrnj266fi0n7uaac01f5kvnf.apps.googleusercontent.com.json'
)
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

SOURCE_DOC_ID = '1W6kmN1h6vWuI4dQHlCWzGxHaVaY7Rqqp_QejDuXlkPc'


def get_credentials():
    """Get or refresh OAuth2 credentials."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds


def main():
    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # Make a copy of the source document
    copy_metadata = {
        'name': 'SIADS 696 Team 7 Final Report – Working Copy'
    }
    copied_file = drive_service.files().copy(
        fileId=SOURCE_DOC_ID,
        body=copy_metadata
    ).execute()

    new_doc_id = copied_file['id']
    new_doc_url = f"https://docs.google.com/document/d/{new_doc_id}/edit"

    print(f"✅ Document copied successfully!")
    print(f"   New Doc ID: {new_doc_id}")
    print(f"   URL: {new_doc_url}")

    # Save the new doc ID for future scripts
    info = {'doc_id': new_doc_id, 'url': new_doc_url}
    info_path = os.path.join(os.path.dirname(__file__), 'gdoc_info.json')
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2)
    print(f"   Doc info saved to: gdoc_info.json")

    return new_doc_id


if __name__ == '__main__':
    main()
