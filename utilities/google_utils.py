#!/usr/bin/env python3
"""
google_utils.py - Unified Google Services Utilities using OAuth
Combines Gmail, Google Drive, and Google Sheets functionality
All authentication is done via OAuth2 (no gcloud required)
"""

import os
import pickle
import base64
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleServices:
    """Unified Google Services API client using OAuth for all services."""
    
    def __init__(self, project_id: str = None, gmail_account: str = None):
        self.project_id = project_id
        self.gmail_account = gmail_account
        self._gmail_service = None
        self._sheets_service = None
        self._drive_service = None
        self._creds = None
    
    def authenticate_all_services(self, credentials_file: str = 'credentials.json', 
                                 scopes: List[str] = None):
        """Authenticate Gmail, Sheets, and Drive with OAuth."""
        if not scopes:
            scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        
        # Create a unique token file name
        if self.gmail_account:
            token_file = f"token_all_services_{self.gmail_account.replace('@', '_').replace('.', '_')}.pickle"
        else:
            token_file = "token_all_services.pickle"
        
        creds = None
        
        # Load existing token
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self._creds = creds
        
        # Build all services
        self._gmail_service = build('gmail', 'v1', credentials=creds)
        self._sheets_service = build('sheets', 'v4', credentials=creds)
        self._drive_service = build('drive', 'v3', credentials=creds)
        
        # Verify Gmail account if specified
        if self.gmail_account:
            profile = self._gmail_service.users().getProfile(userId='me').execute()
            actual_email = profile['emailAddress']
            if actual_email != self.gmail_account:
                raise Exception(f"Wrong account! Expected {self.gmail_account}, got {actual_email}")
            print(f"✅ Authenticated as: {actual_email}")
        
        return True
    
    def authenticate_gmail(self, credentials_file: str = 'credentials.json'):
        """Legacy method - just calls authenticate_all_services"""
        return self.authenticate_all_services(credentials_file)
    
    # ===== GMAIL METHODS =====
    
    def get_gmail_messages(self, query: str = None, max_results: int = 100, 
                          label_ids: List[str] = None) -> List[dict]:
        """Get Gmail messages with optional query."""
        if not self._gmail_service:
            raise Exception("Gmail not authenticated. Call authenticate_all_services() first.")
        
        if not label_ids:
            label_ids = ['INBOX']
        
        messages = []
        page_token = None
        
        while len(messages) < max_results:
            try:
                params = {
                    'userId': 'me',
                    'labelIds': label_ids,
                    'maxResults': min(500, max_results - len(messages))
                }
                
                if query:
                    params['q'] = query
                if page_token:
                    params['pageToken'] = page_token
                
                results = self._gmail_service.users().messages().list(**params).execute()
                
                batch = results.get('messages', [])
                messages.extend(batch)
                
                page_token = results.get('nextPageToken')
                if not page_token or not batch:
                    break
                    
            except HttpError as error:
                print(f"An error occurred: {error}")
                break
        
        return messages[:max_results]
    
    def get_gmail_message(self, msg_id: str) -> dict:
        """Get a specific Gmail message by ID."""
        if not self._gmail_service:
            raise Exception("Gmail not authenticated. Call authenticate_all_services() first.")
        
        try:
            message = self._gmail_service.users().messages().get(
                userId='me', 
                id=msg_id
            ).execute()
            return message
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def extract_email_body(self, payload: dict) -> str:
        """Extract email body from Gmail message payload."""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(
                payload['body']['data']).decode('utf-8', errors='ignore')
        
        return body
    
    # ===== GOOGLE SHEETS METHODS =====
    
    def create_spreadsheet(self, title: str, sheet_names: List[str] = None) -> str:
        """Create a new spreadsheet."""
        if not self._sheets_service:
            raise Exception("Sheets not authenticated. Call authenticate_all_services() first.")
        
        if not sheet_names:
            sheet_names = ['Sheet1']
        
        sheets = []
        for i, name in enumerate(sheet_names):
            sheet = {
                'properties': {
                    'title': name,
                    'index': i,
                    'gridProperties': {
                        'frozenRowCount': 1  # Freeze header row
                    }
                }
            }
            sheets.append(sheet)
        
        spreadsheet = {
            'properties': {
                'title': title
            },
            'sheets': sheets
        }
        
        try:
            result = self._sheets_service.spreadsheets().create(body=spreadsheet).execute()
            return result['spreadsheetId']
        except HttpError as error:
            print(f"An error occurred: {error}")
            raise
    
    def get_spreadsheet_info(self, spreadsheet_id: str) -> dict:
        """Get spreadsheet metadata."""
        if not self._sheets_service:
            raise Exception("Sheets not authenticated. Call authenticate_all_services() first.")
        
        try:
            spreadsheet = self._sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            return spreadsheet
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def get_sheet_values(self, spreadsheet_id: str, range_name: str) -> List[List]:
        """Get values from a sheet range."""
        if not self._sheets_service:
            raise Exception("Sheets not authenticated. Call authenticate_all_services() first.")
        
        try:
            result = self._sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def append_to_sheet(self, spreadsheet_id: str, sheet_name: str, 
                       values: List[List]) -> dict:
        """Append rows to a Google Sheet."""
        if not self._sheets_service:
            raise Exception("Sheets not authenticated. Call authenticate_all_services() first.")
        
        body = {
            'values': values
        }
        
        try:
            result = self._sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:A",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            raise
    
    def update_sheet_values(self, spreadsheet_id: str, range_name: str, 
                          values: List[List]) -> dict:
        """Update values in a sheet range."""
        if not self._sheets_service:
            raise Exception("Sheets not authenticated. Call authenticate_all_services() first.")
        
        body = {
            'values': values
        }
        
        try:
            result = self._sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            raise
    
    def create_or_update_sheet(self, spreadsheet_id: str, sheet_name: str, 
                             headers: List[str]) -> bool:
        """Create a new sheet tab or ensure headers exist."""
        if not self._sheets_service:
            raise Exception("Sheets not authenticated. Call authenticate_all_services() first.")
        
        try:
            # Get spreadsheet info
            spreadsheet = self.get_spreadsheet_info(spreadsheet_id)
            if not spreadsheet:
                return False
            
            # Check if sheet exists
            sheets = spreadsheet.get('sheets', [])
            sheet_exists = any(s['properties']['title'] == sheet_name for s in sheets)
            
            if not sheet_exists:
                # Create new sheet
                request = {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        }
                    }
                }
                
                self._sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': [request]}
                ).execute()
            
            # Check if headers exist
            values = self.get_sheet_values(spreadsheet_id, f"{sheet_name}!A1:Z1")
            
            if not values:
                # Add headers
                self.append_to_sheet(spreadsheet_id, sheet_name, [headers])
            
            return True
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False
    
    def update_email_analysis_sheet(self, spreadsheet_id: str, 
                                  analysis_results: List[dict]) -> None:
        """Update Google Sheet with email analysis results."""
        sheet_name = "Email_Analysis"
        
        # Define headers
        headers = [
            "ID", "Timestamp", "Sender Name", "Sender Email", "Domain",
            "Subject", "Body Preview", "Spam Score", "Category", 
            "Indicators", "Analyzed At", "Manual Review", "Notes"
        ]
        
        # Ensure sheet exists with headers
        self.create_or_update_sheet(spreadsheet_id, sheet_name, headers)
        
        # Convert analysis results to rows
        rows = []
        for result in analysis_results:
            row = [
                result.get('id', ''),
                result.get('timestamp', ''),
                result.get('sender_name', ''),
                result.get('sender_email', ''),
                result.get('domain', ''),
                result.get('subject', ''),
                result.get('body_preview', ''),
                str(result.get('spam_score', '')),
                result.get('category', ''),
                result.get('indicators', ''),
                result.get('analyzed_at', ''),
                '',  # Manual Review column (empty for user to fill)
                ''   # Notes column (empty for user to fill)
            ]
            rows.append(row)
        
        # Append rows to sheet
        if rows:
            self.append_to_sheet(spreadsheet_id, sheet_name, rows)
            print(f"✅ Added {len(rows)} emails to Google Sheet")
    
    # ===== GOOGLE DRIVE METHODS =====
    
    def list_drive_files(self, folder_id: str = None, query: str = None) -> List[dict]:
        """List files in Google Drive."""
        if not self._drive_service:
            raise Exception("Drive not authenticated. Call authenticate_all_services() first.")
        
        try:
            # Build query
            if folder_id and not query:
                query = f"'{folder_id}' in parents and trashed=false"
            elif not query:
                query = "trashed=false"
            
            # Get files
            results = self._drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, modifiedTime, parents)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def create_drive_folder(self, name: str, parent_id: str = None) -> str:
        """Create a folder in Google Drive."""
        if not self._drive_service:
            raise Exception("Drive not authenticated. Call authenticate_all_services() first.")
        
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        try:
            folder = self._drive_service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            return folder.get('id')
        except HttpError as error:
            print(f"An error occurred: {error}")
            raise
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Download a file from Google Drive."""
        if not self._drive_service:
            raise Exception("Drive not authenticated. Call authenticate_all_services() first.")
        
        try:
            request = self._drive_service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as f:
                downloader = request.execute()
                f.write(downloader)
            
            return True
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False