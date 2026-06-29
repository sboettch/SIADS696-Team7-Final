"""
Upload reproducible report figures to Google Drive and make them web-viewable.
Saves image IDs/URIs for use by gdoc_update.py.
"""
import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
FIGURES_DIR = os.path.join(SCRIPT_DIR, 'outputs', 'visualizations', 'reproducible_report_figures')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'gdoc_image_ids.json')

FIGURES = [
    'figure_01_supervised_model_comparison.png',
    'figure_02_predictions_residuals.png',
    'figure_03_residual_map.png',
    'figure_04_rf_feature_importance.png',
    'figure_05_rf_ablation.png',
    'figure_06_rf_sensitivity.png',
    'figure_07_dbscan_pca_scatter.png',
    'figure_08_dbscan_cluster_profile.png',
    'figure_09_kmeans_pca_scatter.png',
    'figure_10_kmeans_cluster_profile.png',
    'figure_11_unsupervised_parameter_search.png',
]


def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    drive = build('drive', 'v3', credentials=creds)

    # Create a folder for the report images
    folder_meta = {
        'name': 'SIADS696_Report_Figures',
        'mimeType': 'application/vnd.google-apps.folder',
    }
    folder = drive.files().create(body=folder_meta, fields='id').execute()
    folder_id = folder['id']
    print(f"Created Drive folder: {folder_id}")

    # Make folder publicly readable
    drive.permissions().create(
        fileId=folder_id,
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()

    image_info = {}
    for fname in FIGURES:
        fpath = os.path.join(FIGURES_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  ⚠️  Missing: {fname}")
            continue

        file_meta = {
            'name': fname,
            'parents': [folder_id],
        }
        media = MediaFileUpload(fpath, mimetype='image/png')
        uploaded = drive.files().create(
            body=file_meta,
            media_body=media,
            fields='id,webContentLink',
        ).execute()

        file_id = uploaded['id']

        # Make file publicly readable
        drive.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # Get the direct content link
        # Google Drive content link format for embedding
        content_uri = f"https://drive.google.com/uc?id={file_id}&export=download"

        image_info[fname] = {
            'id': file_id,
            'uri': content_uri,
        }
        print(f"  ✅ Uploaded: {fname} → {file_id}")

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(image_info, f, indent=2)

    print(f"\n✅ All images uploaded. Info saved to: {OUTPUT_FILE}")
    return image_info


if __name__ == '__main__':
    main()
